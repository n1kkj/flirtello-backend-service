import os
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import APIKeyHeader
from sqlmodel import Session, case, func, select

from src.db.lib.billing.balance_transactions import (
    transfer_currency_from_balance_to_balance,
)
from src.db.lib.billing.clearing.scheduler import main
from src.db.lib.billing.common.content_billing_models import (
    CurrencyType,
    Transaction,
    UserBalance,
)
from src.db.lib.billing.common.enums import (
    CurrenciesTypes,
    SourceNames,
    TopUpWithdrawTransactionTypes,
)
from src.db.lib.billing.common.exceptions import BillingError
from src.db.lib.chat_models import AuthUser
from src.db.lib.content_models import Banner, Config, DirectusFile
from src.db.lib.gift_codes.common.exceptions import (
    GiftCodeAlreadyActivated,
    GiftCodeInactive,
    GiftCodeNotFound,
)
from src.db.lib.gift_codes.repository import GiftCodeRepository
from src.lib.characters import get_character, get_characters
from src.lib.config import config
from src.lib.images import get_directus_filename_disk
from src.lib.verifier import TokenData
from src.schemas.banners import BannerResponse
from src.schemas.service import (
    EmailExistingRequest,
    EmailExistingResponse,
    RoleplayConfig,
    RoleplayConfigsResponse,
)

from ..dependencies import get_current_user, get_gift_code_activator, get_session

router = APIRouter(prefix="/service", tags=["SERVICE"])

api_key_header = APIKeyHeader(name="API-KEY", auto_error=False)


def validate_api_key(api_key: str):
    if api_key != config.api_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")


@router.patch("/give_login_bonus")
async def give_login_bonus_to_user(
    session: Session = Depends(get_session),
    current_user: TokenData = Depends(get_current_user),
):
    user_id = UUID(current_user.user_id)
    company_trial_token_balance_id = os.environ.get("TRIAL_TOKEN_COMPANY_BALANCE_ID")
    assert company_trial_token_balance_id, "Trial token company balance id is't set"
    company_trial_token_balance_id = int(company_trial_token_balance_id)
    trial_bonus_mark = "login_trial_bonus"

    stmt = select(Transaction).where(
        Transaction.user_id == user_id,
        Transaction.balance_id_from == company_trial_token_balance_id,
        Transaction.additional_data[trial_bonus_mark].as_boolean() == True,
    )
    res = session.exec(stmt).all()

    # Bonus constant tokens amount
    tokens_amount = 10
    if not res:
        stmt = (
            select(UserBalance)
            .where(
                UserBalance.user_id == user_id,
                UserBalance.balance_type.has(CurrencyType.name == CurrenciesTypes.TOKEN.value),
            )
            .with_for_update()
        )
        user_tokens_amount = session.exec(stmt).first().balance_amount
        transfer_currency_from_balance_to_balance(
            session,
            user_id,
            company_trial_token_balance_id,
            user_tokens_amount,
            "TOKEN",
            TopUpWithdrawTransactionTypes,
            None,
            SourceNames.WEB_SITE,
        )
        transfer_currency_from_balance_to_balance(
            session,
            company_trial_token_balance_id,
            user_id,
            tokens_amount,
            "TOKEN",
            TopUpWithdrawTransactionTypes,
            None,
            SourceNames.WEB_SITE,
            {trial_bonus_mark: True},
        )
        session.commit()
        return {"status": "success"}
    raise HTTPException(status_code=403, detail="Only one login bonus allowed")


@router.get("/get_banner")
async def get_random_banner(
    session: Session = Depends(get_session),
) -> BannerResponse | None:

    stmt = (
        select(Banner)
        .where(Banner.is_active == True)
        .order_by(
            case((Banner.is_prioritized == True, 0), else_=1)
        )  # Prioritize `is_prioritized` banners
        .order_by(func.random())  # Randomize selection
        .limit(1)
    )
    banner = session.exec(stmt).first()
    if banner:
        desktop_background_file = session.get(DirectusFile, banner.desktop_background).filename_disk
        mobile_background_file = session.get(DirectusFile, banner.mobile_background).filename_disk
        return BannerResponse(
            title=banner.title,
            description=banner.description,
            desktop_background=desktop_background_file,
            mobile_background=mobile_background_file,
            button_url=banner.button_url,
        )
    return None


@router.post("/check_email")
async def check_email_existing(
    email_existing_request: EmailExistingRequest,
    session: Session = Depends(get_session),
    api_key: str = Depends(api_key_header),
) -> EmailExistingResponse:
    validate_api_key(api_key)
    stmt = select(AuthUser).where(AuthUser.email == email_existing_request.email)
    user = session.exec(stmt).first()
    if user:
        return EmailExistingResponse(exists=True)
    return EmailExistingResponse(exists=False)


@router.post("/activate_gift_code")
async def activate_gift_code(
    gift_code: str,
    current_user: TokenData = Depends(get_current_user),
    gift_code_activator: GiftCodeRepository = Depends(get_gift_code_activator),
):
    user_id = UUID(current_user.user_id)
    try:
        gift_code_activator.process_gift_code(gift_code, user_id)
    except GiftCodeNotFound as e:
        gift_code_activator.session.rollback()
        raise HTTPException(status_code=404, detail=e.message)
    except GiftCodeAlreadyActivated as e:
        gift_code_activator.session.rollback()
        raise HTTPException(status_code=400, detail=e.message)
    except GiftCodeInactive as e:
        gift_code_activator.session.rollback()
        raise HTTPException(status_code=400, detail=e.message)
    except BillingError as e:
        gift_code_activator.session.rollback()
        raise e
    except Exception as e:
        gift_code_activator.session.rollback()
        raise e
    else:
        gift_code_activator.session.commit()
        return {"status": "success"}


@router.post("/activate_clearing")
async def activate_clearing(api_key: str = Depends(api_key_header)):
    validate_api_key(api_key)
    main()


@router.get("/roleplay_configs")
async def get_all_roleplay_configs(
    api_key: str = Depends(api_key_header),
    session: Session = Depends(get_session),
) -> RoleplayConfigsResponse:
    validate_api_key(api_key)
    configs = session.exec(select(Config).where(Config.status == "published")).all()
    characters = get_characters(session)
    characters_by_id = {character["id"]: character for character in characters}
    return RoleplayConfigsResponse(
        configs=[
            RoleplayConfig(
                id=config.id,
                character=characters_by_id[config.character_id],
                public_name=config.public_name,
                description=config.description,
                background_file_url=get_directus_filename_disk(session, config.background_file_id),
                style_name=config.style_name,
            )
            for config in configs
        ]
    )


@router.get("/roleplay_configs/by_character/{character_id}")
async def get_character_roleplay_configs(
    character_id: int,
    api_key: str = Depends(api_key_header),
    session: Session = Depends(get_session),
) -> RoleplayConfigsResponse:
    validate_api_key(api_key)
    configs = session.exec(
        select(Config).where(Config.character_id == character_id).where(Config.status == "published")
    ).all()
    character = get_character(session, character_id)
    return RoleplayConfigsResponse(
        configs=[
            RoleplayConfig(
                id=config.id,
                character=character,
                public_name=config.public_name,
                description=config.description,
                background_file_url=get_directus_filename_disk(session, config.background_file_id),
                style_name=config.style_name,
            )
            for config in configs
        ]
    )


@router.get("/roleplay_configs/by_id/{config_id}")
async def get_roleplay_config(
    config_id: UUID,
    api_key: str = Depends(api_key_header),
    session: Session = Depends(get_session),
) -> RoleplayConfig:
    validate_api_key(api_key)
    config = session.exec(
        select(Config).where(Config.id == config_id).where(Config.status == "published")
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    character = get_character(session, config.character_id)
    return RoleplayConfig(
        id=config.id,
        character=character,
        public_name=config.public_name,
        description=config.description,
        background_file_url=get_directus_filename_disk(session, config.background_file_id),
        style_name=config.style_name,
    )
