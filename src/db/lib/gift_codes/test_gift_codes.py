import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine, select, text

from lib.auth import SupabaseAuth
from lib.billing.common.content_billing_models import TokenBatch, UserBalance, UserPlan
from lib.chat_models import ChatUser
from lib.gift_codes.common.enums import GiftCodeType
from lib.gift_codes.common.exceptions import (
    GiftCodeAlreadyActivated,
    GiftCodeInactive,
    GiftCodeNotFound,
)
from lib.gift_codes.common.models import GiftCode, GiftCodeUserLink
from lib.gift_codes.repository import GiftCodeRepository
from supabase import create_client

load_dotenv()
DATABASE_URL = f"postgresql://postgres:postgres@localhost:{os.environ.get('DBPORT', 54322)}/postgres"

dbschema = "content,public,extensions"

engine = create_engine(DATABASE_URL, connect_args={"options": "-csearch_path={}".format(dbschema)})
auth = SupabaseAuth(
    os.environ.get("API_URL"),
    os.environ.get("SERVICE_ROLE_KEY"),
    os.environ.get("PASSKEY"),
    engine,
)


@pytest.fixture(scope="session")
def session():
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture(name="gift_code_repository")
def gift_code_repository_fixture(session: Session):
    return GiftCodeRepository(session=session)


def test_activate_gift_code(session: Session, gift_code_repository: GiftCodeRepository):
    # Test successful activation
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        code = uuid4().hex
        gift_code = GiftCode(
            id=code,
            code=code,
            token_amount=100,
            code_type=GiftCodeType.WELCOME.value,
        )
        session.add(gift_code)
        session.flush()
        activation = gift_code_repository.activate_gift_code(
            code=code, user_id=user_id
        ).gift_code_activation

        assert activation.user_id == user_id
        assert activation.gift_code_id == UUID(code)
        assert isinstance(activation.activated_at, datetime)
    finally:
        c_u1.auth.sign_out()
        session.rollback()


def test_activate_nonexistent_gift_code(gift_code_repository: GiftCodeRepository):
    # Test activating non-existent code
    with pytest.raises(GiftCodeNotFound) as exc_info:
        gift_code_repository.activate_gift_code(code="NONEXISTENT", user_id=uuid4())

    assert "not found" in exc_info.value.message


def test_activate_inactive_gift_code(gift_code_repository: GiftCodeRepository, session: Session):
    # Test activating deactivated code
    gift_code = GiftCode(
        id=uuid4(),
        code=uuid4().hex,
        token_amount=100,
        code_type=GiftCodeType.WELCOME.value,
        is_active=False,
    )
    session.add(gift_code)

    with pytest.raises(GiftCodeInactive) as exc_info:
        gift_code_repository.activate_gift_code(code=gift_code.code, user_id=uuid4())

    assert "no longer active" in exc_info.value.message


def test_double_activation(gift_code_repository: GiftCodeRepository, session: Session):
    # Test activating same code twice for same user
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        code = uuid4().hex
        gift_code = GiftCode(
            id=code,
            code=code,
            token_amount=100,
            code_type=GiftCodeType.WELCOME.value,
        )
        session.add(gift_code)
        session.flush()
        gift_code_repository.activate_gift_code(code=code, user_id=user_id)
        with pytest.raises(GiftCodeAlreadyActivated) as exc_info:
            gift_code_repository.activate_gift_code(code=code, user_id=user_id)

        assert "already activated" in exc_info.value.message
    finally:
        c_u1.auth.sign_out()
        # auth.delete_user_by_email("rlstest1@flirtello.com")
        session.rollback()


def test_process_gift_code(gift_code_repository: GiftCodeRepository, session: Session):
    try:
        auth.delete_user_by_email("rlstest1@flirtello.com")
        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user_id = UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        user_balance = session.exec(
            select(UserBalance).where(
                (UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 1)
            )
        ).first()
        user_balance.balance_amount = 0
        session.add(user_balance)
        session.flush()
        gift_code = GiftCode(
            id=uuid4(),
            code=uuid4().hex,
            token_amount=100,
            code_type=GiftCodeType.WELCOME.value,
        )
        session.add(gift_code)
        session.flush()
        gift_code_repository.process_gift_code(gift_code.code, user_id)
        session.flush()
        updated_ub = session.exec(
            select(UserBalance).where(
                (UserBalance.user_id == user_id) & (UserBalance.currency_type_id == 1)
            )
        ).first()
        user_plan = session.exec(select(UserPlan).where(UserPlan.user_id == user_id)).first()
        assert updated_ub.balance_amount == 100
        assert user_plan.token_batches[0].token_amount == 100
        expected_expiration = datetime.now(UTC) + relativedelta(
            hours=gift_code.tokens_lifetime_hours
        )
        actual_expiration = user_plan.token_batches[0].expiration_date
        assert actual_expiration.replace(microsecond=0) == expected_expiration.replace(microsecond=0)
    finally:
        c_u1.auth.sign_out()
        session.rollback()


def test_multiple_users_activation(gift_code_repository: GiftCodeRepository, session: Session):
    try:
        # Test activating same code for different users
        auth.delete_user_by_email("rlstest1@flirtello.com")
        auth.delete_user_by_email("rlstest2@flirtello.com")

        c_u1 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user1_id = UUID(
            c_u1.auth.sign_up(
                {"email": "rlstest1@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        c_u2 = create_client(os.environ.get("API_URL"), os.environ.get("SERVICE_ROLE_KEY"))
        user2_id = UUID(
            c_u2.auth.sign_up(
                {"email": "rlstest2@flirtello.com", "password": "qweqwe123123"}
            ).user.id
        )
        code = uuid4().hex
        gift_code = GiftCode(
            id=code,
            code=code,
            token_amount=100,
            code_type=GiftCodeType.WELCOME.value,
        )
        session.add(gift_code)
        session.flush()
        activation1 = gift_code_repository.activate_gift_code(
            code=code, user_id=user1_id
        ).gift_code_activation
        activation2 = gift_code_repository.activate_gift_code(
            code=code, user_id=user2_id
        ).gift_code_activation

        assert activation1.user_id == user1_id
        assert activation2.user_id == user2_id
        assert activation1.gift_code_id == activation2.gift_code_id
    finally:
        c_u1.auth.sign_out()
        c_u2.auth.sign_out()
