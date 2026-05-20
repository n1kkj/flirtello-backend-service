import argparse
import os
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from src.db.lib.auth import SupabaseAuth
from src.db.lib.chat_models import ChatUser
from src.lib.config import Config


def delete_user_data(
    engine: Engine,
    auth_client: SupabaseAuth,
    tg_id: str | None = None,
    user_id: UUID | None = None,
    dry_run: bool = False,
):
    """
    Deletes a user and all their associated data from the database.
    Can identify the user by either Telegram ID or user UUID.
    """
    with Session(engine) as session:
        user_id_to_delete: UUID | None = None

        if user_id:
            user_id_to_delete = user_id
            # We proceed even if the user is not in public.users, to clean up orphaned data.
            print(f"Attempting deletion using provided user_id: {user_id_to_delete}")
        elif tg_id:
            user_to_delete = session.exec(
                select(ChatUser).where(ChatUser.tg_id == tg_id)
            ).first()
            if not user_to_delete:
                print(f"User with tg_id '{tg_id}' not found.")
                return
            user_id_to_delete = user_to_delete.id

        if not user_id_to_delete:
            print("Could not determine user to delete.")
            return

        print(
            f"Proceeding with deletion for user_id: {user_id_to_delete} (Dry run: {dry_run})"
        )

        manual_delete_queries = [
            # Must be deleted before user_plans
            f"DELETE FROM content.token_batches WHERE user_plans_id = '{user_id_to_delete}';",
            f"DELETE FROM content.transactions WHERE user_id = '{user_id_to_delete}';",
            f"DELETE FROM content.invoices WHERE customer_id = '{user_id_to_delete}';",
            f"DELETE FROM content.balances WHERE user_id = '{user_id_to_delete}';",
            f"DELETE FROM content.user_plans WHERE user_id = '{user_id_to_delete}';",
            f"DELETE FROM content.images_views WHERE user_id = '{user_id_to_delete}';",
            f"DELETE FROM content.images_user_settings WHERE id = '{user_id_to_delete}';",
            f"DELETE FROM content.llm_stats WHERE user_id = '{user_id_to_delete}';",
            f"DELETE FROM content.gift_codes_users WHERE user_id = '{user_id_to_delete}';",
            f"DELETE FROM mktdata.mktdata_raw WHERE user_id = '{user_id_to_delete}';",
        ]

        for query in manual_delete_queries:
            try:
                if dry_run:
                    print(f"[Dry Run] Would execute: {query}")
                else:
                    print(f"Executing: {query}")
                    session.exec(text(query))
                    session.commit()
            except Exception as e:
                print(f"Could not execute query: {query}. Error: {e}")
                if not dry_run:
                    session.rollback()

        # Attempt to delete from Supabase auth, it might have been deleted already.
        if dry_run:
            print(
                f"[Dry Run] Would delete user {user_id_to_delete} from Supabase Auth."
            )
        else:
            try:
                print(
                    f"Attempting to delete user {user_id_to_delete} from Supabase Auth..."
                )
                auth_client.delete_user(str(user_id_to_delete))
                print(
                    f"Successfully deleted user {user_id_to_delete} from Supabase Auth (or it was already deleted)."
                )
            except Exception as e:
                # We can ignore errors here, as the user might already be deleted from auth
                print(
                    f"Could not delete user from Supabase Auth (they may already be deleted): {e}"
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Delete a user and all their data by Telegram ID or User ID."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--tg-id", type=str, help="The Telegram ID of the user to delete."
    )
    group.add_argument("--user-id", type=str, help="The UUID of the user to delete.")

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the deletion process without actually deleting any data.",
    )
    args = parser.parse_args()

    user_id_uuid = None
    if args.user_id:
        try:
            user_id_uuid = UUID(args.user_id)
        except ValueError:
            print("Error: Invalid UUID format for --user-id.")
            exit(1)

    config = Config()
    engine = create_engine(config.database_url)
    passkey = os.environ.get("PASSKEY")
    if not passkey:
        raise ValueError("PASSKEY environment variable not set.")

    auth_client = SupabaseAuth(
        supabase_url=config.supabase_url,
        supabase_key=config.supabase_service_role_key,
        passkey=passkey,
        engine=engine,
    )
    delete_user_data(
        engine=engine,
        auth_client=auth_client,
        tg_id=args.tg_id,
        user_id=user_id_uuid,
        dry_run=args.dry_run,
    )
