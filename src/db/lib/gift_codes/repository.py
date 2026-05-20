import logging
import os
from datetime import UTC, datetime
from uuid import UUID

from dateutil.relativedelta import relativedelta
from sqlmodel import Session, select

from ..billing.balance_transactions import transfer_currency_from_balance_to_balance
from ..billing.clearing.clearing import create_token_batch
from ..billing.common.enums import SourceNames, TopUpWithdrawTransactionTypes
from .common.dto import GiftCodeActivationDTO
from .common.exceptions import (
    GiftCodeAlreadyActivated,
    GiftCodeInactive,
    GiftCodeNotFound,
)
from .common.models import GiftCode, GiftCodeUserLink

logger = logging.getLogger(__name__)

# Special users who can activate gift codes multiple times
MULTI_ACTIVATION_USER_IDS = [
    # UUID("d7452cfc-5405-46d5-9dcc-74a63d367df6"),  # Mike
    # Add more user IDs here as needed
]


class GiftCodeRepository:
    def __init__(self, session: Session):
        logger.info("GiftCodeRepository initialized")
        self.session = session

    def activate_gift_code(self, code: str, user_id: UUID) -> GiftCodeActivationDTO:
        """Activate a gift code for a user"""
        # Get the gift code
        logger.info(f"Activating gift code {code} for user {user_id}")
        gift_code = self.session.exec(select(GiftCode).where(GiftCode.code == code)).first()
        if not gift_code:
            raise GiftCodeNotFound(code=code)

        if not gift_code.is_active:
            raise GiftCodeInactive(code=code)
        logger.info(f"Found gift code {gift_code}")
        # Check if user already activated this code
        existing_activation = self.session.exec(
            select(GiftCodeUserLink).where(
                (GiftCodeUserLink.gift_code_id == gift_code.id)
                & (GiftCodeUserLink.user_id == user_id)
            )
        ).first()

        # Allow special users to activate gift codes multiple times
        if existing_activation and user_id not in MULTI_ACTIVATION_USER_IDS:
            raise GiftCodeAlreadyActivated(
                code=code, user_id=user_id, activated_at=existing_activation.activated_at
            )
        elif existing_activation and user_id in MULTI_ACTIVATION_USER_IDS:
            logger.info(f"Allowing multi-activation for special user {user_id}: code {code}")

        # Create activation
        activation = GiftCodeUserLink(
            gift_code_id=gift_code.id, user_id=user_id, activated_at=datetime.now(UTC)
        )
        logger.info(f"Creating activation {activation}")
        self.session.add(activation)
        return GiftCodeActivationDTO(gift_code=gift_code, gift_code_activation=activation)

    def sell_gift_code(self, gift_code: GiftCode, user_id: UUID) -> GiftCodeUserLink:
        # TODO: add expiration date
        expiration_date = datetime.now(UTC) + relativedelta(hours=gift_code.tokens_lifetime_hours)
        create_token_batch(
            session=self.session,
            user_id=user_id,
            tokens_amount=gift_code.token_amount,
            expiration_date=expiration_date,
        )
        company_token_balance_id = os.environ.get("TOKEN_COMPANY_BALANCE_ID")
        assert company_token_balance_id, "Token company balance id is't set"
        company_token_balance_id = int(company_token_balance_id)
        transfer_currency_from_balance_to_balance(
            session=self.session,
            balance_from=company_token_balance_id,
            balance_to=user_id,
            amount=gift_code.token_amount,
            currency_type="TOKEN",
            transactions_type=TopUpWithdrawTransactionTypes,
            service_id=gift_code.id,
            source_name=SourceNames.WEB_SITE,
            additional_data=None,
        )

    def process_gift_code(self, gift_code: str, user_id: UUID) -> GiftCodeUserLink:
        gift_code_dto = self.activate_gift_code(gift_code, user_id)
        self.sell_gift_code(gift_code_dto.gift_code, user_id)
        return gift_code_dto.gift_code_activation
