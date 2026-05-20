import logging
import os
import traceback
from time import sleep, time

import jwt
from cachetools import LRUCache, TTLCache, cached
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from gotrue.errors import AuthApiError
from pydantic import BaseModel
from supabase import Client, create_client

from .config import config

logger = logging.getLogger(__name__)

http_bearer = HTTPBearer()


class TokenData(BaseModel):
    user_id: str | None = None


class TokenVerifier:
    supabase_url: str
    supabase_anon_key: str

    def __init__(self, supabase_url: str, supabase_anon_key: str):
        self.supabase_url = supabase_url
        self.supabase_anon_key = supabase_anon_key

    def get_supabase_client(self) -> Client:
        return create_client(self.supabase_url, self.supabase_anon_key)

    def get_supabase_client_for_user_token(self, token) -> Client:
        return create_client(self.supabase_url, token)

    # @cached(TTLCache(maxsize=2048, ttl=300))  # TODO rearrange maxsize and ttl
    def verify_token(self, creds: str):
        try:
            token = creds
            payload = self.decode_jwt_token(token, options={"verify_signature": False})
            user_id: str | None = payload.get("sub")
            client = self.get_supabase_client()
            if user_id is None:
                logger.error("No sub in token")
                raise HTTPException(status_code=401, detail="Invalid token")
            user = client.auth.get_user(token)
            if user is None:
                logger.error("User not found")
                raise HTTPException(status_code=401, detail="Invalid token")
            if user.user.id != user_id:
                logger.error("User ID in token does not match user ID in database")
                raise HTTPException(status_code=401, detail="Invalid token")
            client.auth.sign_out()
            return TokenData(user_id=user_id)
        except jwt.ExpiredSignatureError as e:
            logger.error(e)
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.exceptions.InvalidTokenError as e:
            logger.error(e)
            raise HTTPException(status_code=401, detail="Invalid token")
        except AuthApiError as e:
            error_traceback = traceback.format_exc()
            logger.error(
                f"""Verification failed. {e}
                            Token payload: {payload}
                            Current timestamp: {int(time())}
                            Traceback: {error_traceback}"""
            )
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(e)
            raise HTTPException(status_code=401, detail="Invalid token")

    def decode_jwt_token(self, token: str, **kwargs) -> dict:
        return jwt.decode(token, **kwargs)

    async def get_current_user(self, token: HTTPAuthorizationCredentials = Depends(http_bearer)):
        return self.verify_token(token.credentials)


# print("Creating verifier with config", config.__str__())
# verifier = TokenVerifier(config.supabase_url, config.supabase_anon_key)
