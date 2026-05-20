import logging
import os
from unittest.mock import MagicMock

import pytest
from dotenv import load_dotenv
from fastapi.security import HTTPAuthorizationCredentials
from supabase import Client, create_client

from src.lib.verifier import TokenVerifier

load_dotenv(".env.dev")
load_dotenv("src/.env.dev")
from .verifier import TokenVerifier


def delete_user_by_email(supabase, email):
    users = supabase.auth.admin.list_users()
    for user in users:
        if user.email == email:
            return supabase.auth.admin.delete_user(user.id)


@pytest.mark.asyncio
async def test_token_verifier():
    api_url = os.environ.get("API_URL", "")
    anon_key = os.environ.get("ANON_KEY", "")
    srk = os.environ.get("SERVICE_ROLE_KEY", "")
    if api_url == "" or anon_key == "" or srk == "":
        raise Exception("API_URL and ANON_KEY and SERVICE_ROLE_KEY must be set")

    verifier = TokenVerifier(api_url, anon_key)
    with pytest.raises(Exception):
        verifier.verify_token("test_token")

    client: Client = create_client(api_url, srk)
    email = "test@flirtello.com"
    password = "w3eufnp2i3unf23&)&*(&)"
    delete_user_by_email(client, email)
    user = client.auth.sign_up({"email": email, "password": password})

    if user.session is None:
        raise Exception("Failed to create user")

    valid_token = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=user.session.access_token
    )
    invalid_token = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=user.session.access_token + "Invalid"
    )
    wrong_token = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="eyJhbGciOiJIUzI1NiIsImtpZCI6Ik5mWnk4MldsbWxHOWFwa0MiLCJ0eXAiOiJKV1QifQ.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzE3MDEzNzg3LCJpYXQiOjE3MTcwMTAxODcsImlzcyI6Imh0dHBzOi8vbmt4Y3JwZndwbXFtbmlvdm12cW4uc3VwYWJhc2UuY28vYXV0aC92MSIsInN1YiI6IjI1ODdlMzU4LTc3ZWMtNDVkMS05OGRjLTJjZWUxMzUyNmI3NCIsImVtYWlsIjoiMTMwODIyNTE4NUB0Zy5mbGlydGVsbG8uY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6eyJlbWFpbCI6IjEzMDgyMjUxODVAdGcuZmxpcnRlbGxvLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwicGhvbmVfdmVyaWZpZWQiOmZhbHNlLCJzdWIiOiIyNTg3ZTM1OC03N2VjLTQ1ZDEtOThkYy0yY2VlMTM1MjZiNzQifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTcxNzAxMDE4N31dLCJzZXNzaW9uX2lkIjoiODNmN2Q2ZmYtM2RhNC00MWE1LWFiMTctMmYxM2M4MGMzZWMyIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.XFRcb9oVRNEFIW-S5TyJw2ZIumbGDJ7R5jPUMkkYjH8",
    )

    result = await verifier.get_current_user(valid_token)

    assert result is not None

    with pytest.raises(Exception):
        await verifier.get_current_user(invalid_token)

    with pytest.raises(Exception):
        await verifier.get_current_user(wrong_token)

    print(user)

    client.auth.sign_out()
    delete_user_by_email(client, email)

    # assert verifier.verify_token("test_token") == True


@pytest.fixture
def mock_supabase_client():
    client = MagicMock()
    user = MagicMock()
    user.user.id = "test_user_id"
    client.auth.get_user.return_value = user
    return client


@pytest.fixture
def token_verifier(mock_supabase_client):
    verifier = TokenVerifier(
        supabase_url="https://example.supabase.co", supabase_anon_key="test_anon_key"
    )
    verifier.get_supabase_client = MagicMock(return_value=mock_supabase_client)
    verifier.decode_jwt_token = MagicMock(return_value={"sub": "test_user_id"})
    return verifier


def test_verify_token_cache(token_verifier, mock_supabase_client):
    token = "test_token"

    assert mock_supabase_client.auth.get_user.call_count == 0
    # First call: Should call the actual function
    result = token_verifier.verify_token(token)
    assert result.user_id == "test_user_id"
    assert mock_supabase_client.auth.get_user.call_count == 1

    # Second call with the same token: Should hit the cache
    result_cached = token_verifier.verify_token(token)
    assert result_cached.user_id == "test_user_id"
    assert (
        mock_supabase_client.auth.get_user.call_count == 1
    )  # Ensure the client was not called again

    # Call with a different token: Should call the actual function again
    new_token = "new_test_token"
    token_verifier.verify_token(new_token)
    assert (
        mock_supabase_client.auth.get_user.call_count == 2
    )  # Ensure the client was called for the new token and call_cout increased
    # Call with first token
    token_verifier.verify_token(token)
    assert (
        mock_supabase_client.auth.get_user.call_count == 2
    )  # Ensure the client was not called again
