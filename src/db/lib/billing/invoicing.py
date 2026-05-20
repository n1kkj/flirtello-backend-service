from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, insert, select, update

from .common.content_billing_models import BaseService, Invoice, TariffPlan, TokenPack
from .common.enums import InvoiceStatus, ServiceTypes
from .common.exceptions import NoSuchInvoiceError, NoSuchServiceError
from .payment_system.enums import PaymentSystems


def create_invoice(
    session: Session,
    customer_id: UUID,
    service_id: UUID,
    service_type: ServiceTypes,
    total: Decimal,
    currency_type_id: int,
    callback_url: str,
    status: InvoiceStatus = InvoiceStatus.UNPAID,
    payment_system_name: Optional[PaymentSystems] = None,
) -> int:
    stmt = (
        insert(Invoice)
        .values(
            customer_id=customer_id,
            service_id=service_id,
            service_type=service_type,
            currency_type_id=currency_type_id,
            total=total,
            status=status,
            callback_url=callback_url,
            payment_system_name=payment_system_name,
        )
        .returning(Invoice.id)
    )
    invoice_id = session.exec(stmt).scalar_one()
    session.commit()
    return invoice_id


def pay_the_invoice(session: Session, invoice_id: int) -> None:
    stmt = update(Invoice).where(Invoice.id == invoice_id).values(status=InvoiceStatus.PAID)
    session.exec(stmt)
    session.commit()


def add_payment_system_transaction_id_to_invoice(
    session: Session, invoice_id: int, payment_system_transaction_id: str
) -> None:
    stmt = (
        update(Invoice)
        .where(Invoice.id == invoice_id)
        .values(payment_system_transaction_id=payment_system_transaction_id)
    )
    session.exec(stmt)
    session.commit()


class ServiceDataset(BaseModel):
    service_type: ServiceTypes
    service_id: UUID


def get_service_model(session: Session, service_dataset: ServiceDataset) -> BaseService:
    service_id = service_dataset.service_id
    service_type = service_dataset.service_type
    if service_type == ServiceTypes.TARIFF_PLAN:
        stmt = select(TariffPlan).where(
            (TariffPlan.id == service_id) & (TariffPlan.is_trial == False)
        )
    else:
        stmt = select(TokenPack).where(TokenPack.id == service_id)
    res = session.exec(stmt).first()
    if not res:
        raise NoSuchServiceError(service_id, service_type.value)
    return res


class InvoiceValidator:
    def __init__(self, session: Session, invoice_id: int) -> None:
        self._session = session
        self.invoice = self._resolve_invoice_from_id(invoice_id)

    def is_invoice_paid(self) -> bool:
        return self.invoice.status == InvoiceStatus.PAID

    def _resolve_invoice_from_id(self, invoice_id: int) -> Invoice:
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        invoice = self._session.exec(stmt).first()

        if not invoice:
            raise NoSuchInvoiceError(invoice_id)

        return invoice
