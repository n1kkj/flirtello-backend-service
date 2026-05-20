import os
from typing import Optional
from uuid import UUID

import sentry_sdk
from gotrue import AuthResponse, UserResponse
from gotrue.errors import AuthApiError
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from supabase import Client, create_client

from .chat_models import AuthUser, ChatUser
from .content_models import ContentCharacter  # just to load to the SQLModel context
from .crypto import encrypt


class SupabaseAuth:
    supabase_url: str
    supabase_key: str
    supabase: Client
    engine: Engine
    passkey = os.environ.get("PASSKEY")

    def __init__(self, supabase_url, supabase_key, passkey, engine) -> None:
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.passkey = passkey
        self.engine = engine

    def create_normal_user(self, email: str, password: str) -> Optional[dict]:
        supabase = create_client(self.supabase_url, self.supabase_key)
        response = supabase.auth.sign_up({"email": email, "password": password})
        supabase.auth.sign_out()
        if response.user:
            return response.user.dict()
        return None

    def create_tg_user(self, tg_id, tg_name) -> ChatUser:
        email = f"{tg_id}@tg.flirtello.com"
        password = encrypt(email, self.passkey)
        supabase = create_client(self.supabase_url, self.supabase_key)
        try:
            response = supabase.auth.sign_up({"email": email, "password": password})
            user = response.user
            supabase.auth.sign_out()
        except AuthApiError as e:
            sentry_sdk.set_context("supabase_error", dict(e.to_dict()))

            # If the error indicates the user already exists, try to fetch them.
            if e.status == 422 and "User already registered" in e.message:
                admin_client = create_client(self.supabase_url, self.supabase_key)
                users_response = admin_client.auth.admin.list_users()
                
                user = next((u for u in users_response if u.email == email), None)
                
                if not user:
                    # This case is unlikely if the error is "User already registered",
                    # but we handle it just in case.
                    raise Exception(f"Failed to find user '{email}' after 'already registered' error.") from e
            else:
                # For any other errors, re-raise the exception.
                raise e

        if not user:
            raise Exception("Supabase user creation or retrieval failed.")

        with Session(self.engine) as session:
            db_user = session.exec(
                select(ChatUser).where(ChatUser.id == user.id)
            ).first()
            if not db_user:
                # This should ideally not happen if user creation syncs with our DB.
                # But as a fallback, we can create the ChatUser record.
                db_user = ChatUser(id=UUID(user.id))
                session.add(db_user)
                # Fall-through to update properties

            db_user.tg_id = tg_id
            db_user.display_name = tg_name
            session.add(db_user)
            session.commit()
            session.refresh(db_user)

        return db_user

    def delete_user(self, id: str):
        supabase = create_client(self.supabase_url, self.supabase_key)
        supabase.auth.admin.delete_user(id)
        supabase.auth.sign_out()
        return

    def login_with_password_and_get_client(self, login, password):
        client = create_client(self.supabase_url, self.supabase_key)
        client.auth.sign_in_with_password({"email": login, "password": password})
        return client

    def login_with_telegram_and_get_client(self, tg_id: str, tg_name: str) -> Client:
        """Get a Supabase client with an authenticated session for a Telegram user.
        If the user does not exist, it will be created.

        Args:
            tg_id: Telegram user ID
            tg_name: Telegram display name (for creation)

        Returns:
            Authenticated Supabase client instance
        """
        # First find the user by telegram ID
        user = self.find_user_by_tg_id(tg_id)
        if not user:
            # If user doesn't exist, create them.
            user = self.create_tg_user(tg_id, tg_name)

        auth_user = self.find_auth_user(user.id)
        if not auth_user or not auth_user.email:
            raise ValueError(f"No auth.users record or email found for ChatUser ID: {user.id}")

        # Create a client instance. This client will be used for admin ops first,
        # then it will be authenticated as the target user.
        # Ensure this client is initialized with the service_role_key for admin operations.
        # If self.supabase_key is already the service_role_key, this is fine.
        client = create_client(self.supabase_url, self.supabase_key)

        # Step 1: Admin generates a magic link's components for the user
        try:
            link_response = client.auth.admin.generate_link(
                {"type": "magiclink", "email": auth_user.email}
            )
            # The response object itself is AdminUserResponse, its 'properties' attribute
            # is GenerateLinkProperties which contains hashed_token.
            if not link_response.properties or not link_response.properties.hashed_token:
                raise ValueError("Failed to generate magic link properties or hashed_token.")

            hashed_token = link_response.properties.hashed_token
            # email_otp = link_response.properties.email_otp # usually same as hashed_token for magiclink

        except Exception as e:
            # Log the error appropriately
            print(f"Error generating magic link: {e}")
            raise

        # Step 2: Verify the OTP/magic link components to establish a session for the user
        # This makes the *current client instance* authenticated as the user.
        try:
            # For 'magiclink' or 'email' type OTPs, token_hash is often used directly.
            # The 'email' parameter is also typically required for 'magiclink' or 'email' type.
            session_response = client.auth.verify_otp(
                {
                    "type": "magiclink",  # or "email" if that's what generate_link produces for verification
                    "token_hash": hashed_token,
                }
            )

            # After verify_otp, the client's session should be set.
            # session_response.session contains tokens, session_response.user contains user info.
            if not session_response or not session_response.session:
                raise ValueError("Failed to verify OTP and establish session.")

        except Exception as e:
            # Log the error appropriately
            print(f"Error verifying OTP: {e}")
            raise

        # The 'client' is now authenticated as the target user.
        return client

    def delete_user_by_email(self, email: str):
        supabase = create_client(self.supabase_url, self.supabase_key)
        users = supabase.auth.admin.list_users()
        for user in users:
            if user.email == email:
                return supabase.auth.admin.delete_user(user.id)

    def get_user(self, id: str) -> UserResponse:
        supabase = create_client(self.supabase_url, self.supabase_key)
        return supabase.auth.admin.get_user_by_id(id)

    def find_user_by_tg_id(self, tg_id) -> Optional[ChatUser]:
        with Session(self.engine) as session:
            stmt = select(ChatUser).where(ChatUser.tg_id == str(tg_id))
            users = list(session.exec(stmt))

            if len(users) == 0:
                print("not found")
                return None
            if len(users) > 1:
                raise Exception(f"tg_id {tg_id} is not unique")
            else:
                print(users)
                return users[0]

    def find_auth_user(self, user_id) -> Optional[AuthUser]:
        with Session(self.engine) as session:
            stmt = select(AuthUser).where(AuthUser.id == user_id)
            return session.exec(stmt).first()


def get_auth_user(session: Session, user_id) -> Optional[AuthUser]:
    stmt = select(AuthUser).where(AuthUser.id == user_id)
    return session.exec(stmt).first()
