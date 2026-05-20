import logging
from datetime import UTC, date, datetime
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from uuid import UUID, uuid4

import sentry_sdk
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import AnyUrl
from sqlmodel import Session, select

from src.db.lib.auth import get_auth_user
from src.db.lib.billing.clearing.clearing import instant_tariff_plan_debit
from src.db.lib.billing.common.content_billing_models import (
    TariffPlan,
    TokenPack,
    UserPlan,
)
from src.db.lib.billing.common.enums import ServiceTypes, SourceNames
from src.db.lib.billing.common.exceptions import (
    BillingError,
    NoSuchInvoiceError,
    PaymentSystemError,
    TariffPlanExpired,
)
from src.db.lib.billing.invoicing import (
    InvoiceValidator,
    ServiceDataset,
    add_payment_system_transaction_id_to_invoice,
    create_invoice,
    get_service_model,
    pay_the_invoice,
)
from src.db.lib.billing.paid_actions import validate_tariff_plan
from src.db.lib.billing.payment_system.payment_system import Truevo
from src.db.lib.billing.payment_system.schemes import (
    InitialPaymentResponse,
    PaymentResponse,
    TransactionStatuses,
)
from src.db.lib.billing.service_processing import (
    TariffPlanProcessor,
    TokenPackProcessor,
)
from src.db.lib.config import config as db_config
from src.db.lib.mailing.common.base import BaseMailer
from src.db.lib.mailing.common.exceptions import NotSuccessResponseStatus
from src.lib.billing import (
    PaymentSystems,
    get_user_current_tariff_plan,
    map_current_payment_system_to_billing_balance,
)
from src.lib.config import config
from src.lib.mailing import get_mailing_dto
from src.lib.url_config import add_query_param_to_url
from src.schemas.invoicing import PaymentStatus

from ..dependencies import get_current_user, get_mailer, get_payment_system, get_session
from ..lib.verifier import TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoicing", tags=["Invoicing"])

templates = Jinja2Templates(directory="src/templates")

# Add signature
CALLBACK_PAYMENT_URL = "invoicing/payment-callback"
FAKE_PAYMENT_URL = "invoicing/payment"


class ProcessPurchaseRequest(ServiceDataset):
    callback_url: AnyUrl


class ProcessPurchaseResponse(InitialPaymentResponse):
    pass


@router.post(
    "/process_purchase",
    description="Статус код 412, если пользователь пытается купить токен пак с триальным или просроченным тарифным планом",
)
async def process_purchase(
    service_dataset: ProcessPurchaseRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
    payment_system: Truevo = Depends(get_payment_system),
) -> ProcessPurchaseResponse | dict[str, str] | PaymentResponse:
    # Purchase button processing
    try:
        user_id = UUID(current_user.user_id)
        # TODO refactor
        if service_dataset.service_type == ServiceTypes.TARIFF_PLAN:
            stmt = select(UserPlan).where(UserPlan.user_id == user_id)
            user_plan = session.exec(stmt).first()
            if user_plan.expired_at and user_plan.expired_at > datetime.now(UTC):
                raise HTTPException(
                    status_code=412, detail="Buying tariff plan with active tariff plan not allowed"
                )

        service_model = get_service_model(session, service_dataset)
        service_id = service_model.id
        service_price = service_model.price
        service_currency_id = service_model.currency_type_id
        callback_url = service_dataset.callback_url.__str__()
        if service_dataset.service_type == ServiceTypes.TARIFF_PLAN:
            payment_system_name = db_config.tariff_plans_payment_system
        elif service_dataset.service_type == ServiceTypes.TOKEN_PACK:
            payment_system_name = db_config.token_packs_payment_system
        invoice_id = create_invoice(
            session,
            user_id,
            service_id,
            service_dataset.service_type,
            service_price,
            service_currency_id,
            callback_url,
            payment_system_name=payment_system_name,
        )
        host_url = request.base_url
        user_email = get_auth_user(session, user_id).email
        if service_dataset.service_type == ServiceTypes.TARIFF_PLAN:
            if db_config.tariff_plans_payment_system == PaymentSystems.TRUEVO:
                tariff_plan = session.exec(
                    select(TariffPlan).where(TariffPlan.id == service_id)
                ).first()
                success_callback_url = f"{host_url}{CALLBACK_PAYMENT_URL}?invoice_id={invoice_id}&status={PaymentStatus.SUCCESS.value}"
                fail_callback_url = f"{host_url}{CALLBACK_PAYMENT_URL}?invoice_id={invoice_id}&status={PaymentStatus.FAIL.value}"
                cancel_callback_url = f"{host_url}{CALLBACK_PAYMENT_URL}?invoice_id={invoice_id}&status={PaymentStatus.CANCELED.value}"
                initial_payment_response = payment_system.process_subscription(
                    tariff_plan=tariff_plan,
                    user_id=user_id,
                    user_email=user_email,
                    user_first_name=None,
                    success_url=success_callback_url,
                    fail_url=fail_callback_url,
                    cancel_url=cancel_callback_url,
                )
                truevo_subscription_id = initial_payment_response.subscription_id
                # Considering that the last part of the URL is the transaction ID
                truevo_transaction_id = initial_payment_response.action.split("/")[-1]
                payment_system.save_truevo_subscription_id(session, user_id, truevo_subscription_id)
                add_payment_system_transaction_id_to_invoice(
                    session, invoice_id, truevo_transaction_id
                )
                return initial_payment_response
            elif db_config.tariff_plans_payment_system == PaymentSystems.FAKE:
                payment_url = f"{host_url}{FAKE_PAYMENT_URL}?invoice_id={invoice_id}"
        elif service_dataset.service_type == ServiceTypes.TOKEN_PACK:
            if db_config.token_packs_payment_system == PaymentSystems.TRUEVO:
                token_pack = session.exec(
                    select(TokenPack).where(TokenPack.id == service_id)
                ).first()
                success_callback_url = f"{host_url}{CALLBACK_PAYMENT_URL}?invoice_id={invoice_id}&status={PaymentStatus.SUCCESS.value}"
                fail_callback_url = f"{host_url}{CALLBACK_PAYMENT_URL}?invoice_id={invoice_id}&status={PaymentStatus.FAIL.value}"
                cancel_callback_url = f"{host_url}{CALLBACK_PAYMENT_URL}?invoice_id={invoice_id}&status={PaymentStatus.CANCELED.value}"
                payment_response = payment_system.process_service_selling(
                    service_price=float(token_pack.price),
                    service_id=service_id,
                    user_id=user_id,
                    user_email=user_email,
                    success_url=success_callback_url,
                    fail_url=fail_callback_url,
                    cancel_url=cancel_callback_url,
                )
                truevo_transaction_id = payment_response.action.split("/")[-1]
                add_payment_system_transaction_id_to_invoice(
                    session, invoice_id, truevo_transaction_id
                )
                return payment_response
            elif db_config.token_packs_payment_system == PaymentSystems.FAKE:
                payment_url = f"{host_url}{FAKE_PAYMENT_URL}?invoice_id={invoice_id}"

    except BillingError as e:
        sentry_sdk.capture_exception(e)
        raise HTTPException(status_code=500, detail=e.message)
    return {"redirect_url": payment_url}


@router.get("/payment")
async def fake_payment(
    invoice_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    # Summary: Render static fake-payment page
    try:
        invoice_validator = InvoiceValidator(session, invoice_id)
    except NoSuchInvoiceError as e:
        raise HTTPException(status_code=404, detail=e.message)

    if invoice_validator.is_invoice_paid():
        return templates.TemplateResponse("invoice_already_paid.html", {"request": request})
    amplitude_key = config.amplitude_key
    ym_key = config.yandex_metric_key
    return templates.TemplateResponse(
        "fake_payment_page.html",
        {
            "request": request,
            "invoice_id": invoice_id,
            "AMPLITUDE_KEY": amplitude_key,
            "YANDEX_METRIC_KEY": ym_key,
        },
    )


@router.get("/payment/truevo")
async def fake_payment_truevo(
    action_url: str,
    payload: str,
    api_key: str,
    lang: str,
    request: Request,
    session: Session = Depends(get_session),
):
    return templates.TemplateResponse(
        "fake_payment_form_submission_page.html",
        {
            "request": request,
            "ACTION_URL": action_url,
            "PAYLOAD": payload,
            "API_KEY": api_key,
            "LANG": lang,
        },
    )


@router.get("/payment-callback")
async def payment_callback(
    invoice_id: int,
    status: PaymentStatus,
    txnRef: str,
    session: Session = Depends(get_session),
    payment_system: Truevo = Depends(get_payment_system),
    mailer: BaseMailer = Depends(get_mailer),
):
    try:
        invoice_validator = InvoiceValidator(session, invoice_id)
    except NoSuchInvoiceError as e:
        raise HTTPException(status_code=404, detail=e.message)

    if invoice_validator.is_invoice_paid():
        raise HTTPException(status_code=404, detail="Invoice already paid")

    transaction_status = payment_system.check_transaction_status(
        txnRef, invoice_validator.invoice.service_type
    )
    if transaction_status.status == TransactionStatuses.NOT_EXIST:
        sentry_sdk.capture_message(f"Transaction with txnRef={txnRef} not found", level="error")
        fail_url = add_query_param_to_url(
            url=invoice_validator.invoice.callback_url,
            param="payment",
            value=PaymentStatus.FAIL.value,
        )
        return RedirectResponse(fail_url)

    if status == PaymentStatus.CANCELED:
        cancel_url = add_query_param_to_url(
            url=invoice_validator.invoice.callback_url,
            param="payment",
            value=PaymentStatus.CANCELED.value,
        )
        return RedirectResponse(cancel_url)
    elif status == PaymentStatus.FAIL:
        fail_url = add_query_param_to_url(
            url=invoice_validator.invoice.callback_url,
            param="payment",
            value=PaymentStatus.FAIL.value,
        )
        return RedirectResponse(fail_url)
    elif status == PaymentStatus.SUCCESS:
        user_id = invoice_validator.invoice.customer_id
        user_email = get_auth_user(session, user_id).email
        service_type = invoice_validator.invoice.service_type
        service_id = invoice_validator.invoice.service_id
        service_dataset = ServiceDataset(service_type=service_type, service_id=service_id)
        payment_system.save_truevo_token_id(session, user_id, transaction_status.card.tokenId)

        if service_type == ServiceTypes.TARIFF_PLAN:
            service_processor = TariffPlanProcessor(
                session, user_id, service_dataset, SourceNames.WEB_SITE
            )
            payment_system_type = db_config.tariff_plans_payment_system
        elif service_type == ServiceTypes.TOKEN_PACK:
            service_processor = TokenPackProcessor(
                session, user_id, service_dataset, SourceNames.WEB_SITE
            )
            payment_system_type = db_config.token_packs_payment_system
        try:
            payment_system_balance_id = map_current_payment_system_to_billing_balance(
                payment_system_type
            )
            service_processor.sell_service(
                payment_system_balance_id=payment_system_balance_id,
                additional_data={"payment_system_transaction_id": txnRef},
            )
            is_user_origin_tariff_plan_trial = service_processor.apply_service()
            tariff_plan_expiration_date = None
            if service_type == ServiceTypes.TARIFF_PLAN:
                tariff_plan_expiration_date = instant_tariff_plan_debit(
                    session,
                    user_id,
                    is_user_origin_tariff_plan_trial,
                    SourceNames.WEB_SITE,
                ).strftime("%d/%m/%Y")
            mailing_dto = get_mailing_dto(
                session,
                service_type,
                service_id,
                invoice_id,
                invoice_validator.invoice.total,
                tariff_plan_expiration_date,
            )
            # Send notification to user by email
            mailer.send_email_dynamic_template(
                db_config.sendgrid_sender_email,
                user_email,
                mailing_dto.subject,
                mailing_dto.dynamic_template_id,
                mailing_dto.dynamic_template_data,
            )
        except PaymentSystemError as e:
            sentry_sdk.capture_exception(e)
            session.rollback()
            fail_url = add_query_param_to_url(
                url=invoice_validator.invoice.callback_url,
                param="payment",
                value=PaymentStatus.FAIL.value,
            )
            return RedirectResponse(fail_url)
        except BillingError as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=e.message)
        except NotSuccessResponseStatus as e:
            sentry_sdk.capture_exception(e)
        except Exception as e:
            session.rollback()
            raise e
        else:
            pay_the_invoice(session, invoice_id)
            session.commit()
        success_url = add_query_param_to_url(
            url=invoice_validator.invoice.callback_url,
            param="payment",
            value=PaymentStatus.SUCCESS.value,
        )
        return RedirectResponse(success_url)


@router.get("/fake-payment-callback")
async def payment_callback(
    invoice_id: int,
    status: str,
    payment_method: str,
    session: Session = Depends(get_session),
):
    try:
        invoice_validator = InvoiceValidator(session, invoice_id)
    except NoSuchInvoiceError as e:
        raise HTTPException(status_code=404, detail=e.message)

    if invoice_validator.is_invoice_paid():
        raise HTTPException(status_code=404, detail="Invoice already paid")

    if status == "success":
        pay_the_invoice(session, invoice_id)

        user_id = invoice_validator.invoice.customer_id
        service_type = invoice_validator.invoice.service_type
        service_id = invoice_validator.invoice.service_id
        service_dataset = ServiceDataset(service_type=service_type, service_id=service_id)

        if service_type == ServiceTypes.TARIFF_PLAN:
            service_processor = TariffPlanProcessor(
                session, user_id, service_dataset, SourceNames.WEB_SITE
            )
            payment_system_type = db_config.tariff_plans_payment_system
        elif service_type == ServiceTypes.TOKEN_PACK:
            service_processor = TokenPackProcessor(
                session, user_id, service_dataset, SourceNames.WEB_SITE
            )
            payment_system_type = db_config.token_packs_payment_system

        try:
            payment_system_balance_id = map_current_payment_system_to_billing_balance(
                payment_system_type
            )
            service_processor.sell_service(payment_system_balance_id=payment_system_balance_id)
            is_user_origin_tariff_plan_trial = service_processor.apply_service()
            if service_type == ServiceTypes.TARIFF_PLAN:
                instant_tariff_plan_debit(
                    session,
                    user_id,
                    is_user_origin_tariff_plan_trial,
                    SourceNames.WEB_SITE,
                )
        except BillingError as e:
            session.rollback()
            raise HTTPException(status_code=404, detail=e.message)
        except Exception as e:
            session.rollback()
            raise e
        else:
            session.commit()
        # Original callback URL
        callback_url = invoice_validator.invoice.callback_url
        # Parse the URL
        parsed_url = urlparse(callback_url)
        query_params = parse_qs(parsed_url.query)
        # Add or update the 'payment_method' parameter
        query_params["payment_method"] = payment_method
        # Reconstruct the URL with updated query parameters
        new_query = urlencode(query_params, doseq=True)
        updated_url = urlunparse(parsed_url._replace(query=new_query))
        updated_url = add_query_param_to_url(updated_url, "payment", "success")
        return RedirectResponse(updated_url)


@router.patch("/deactivate-subscription")
def deactivate_user_subscription(
    payment_system: Truevo = Depends(get_payment_system),
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    user_id = UUID(current_user.user_id)
    stmt = select(UserPlan).where(UserPlan.user_id == user_id)
    user_plan = session.exec(stmt).first()
    subscription_id = user_plan.truevo_subscription_id
    if subscription_id is None:
        raise HTTPException(
            status_code=404, detail="Deactivation not allowed without active subscription"
        )
    payment_system.deactivate_subscription(subscription_id)
    user_plan.truevo_subscription_id = None
    session.add(user_plan)
    session.commit()
