import json
import time
from logging import getLogger
from typing import Any, Optional, Type, TypeVar

import httpx
import sentry_sdk
from pydantic import BaseModel, ValidationError

logger = getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class LLMServiceAPI:
    def __init__(self, api_url: str, api_key: str, timeout: int = 60) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout

    async def get(
        self, params: dict[str, Any], validation_schema: Type[T], endpoint_url=""
    ) -> Optional[T]:
        try:
            logger.info(f"Making a request to {self.api_url} {endpoint_url} with params {params}")
            start_time = time.time()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.api_url + endpoint_url, params=params, headers={"X-API-KEY": self.api_key}
                )

                response_time = time.time() - start_time
                logger.info(
                    f"Service {self.api_url}: {response.text} for request {params} in {response_time}"
                )
                acceptable_response_time = 10
                if int(response_time) > acceptable_response_time:
                    with sentry_sdk.push_scope() as scope:
                        scope.set_extra("url", self.api_url)
                        scope.set_extra("endpoint_url", endpoint_url)
                        scope.set_extra("response_time_seconds", f"{response_time:.2f}")
                        scope.set_extra("request_params", params)
                        sentry_sdk.capture_message(
                            "Warning: Slow response from LLM Service API (GET)", level="warning"
                        )

                if response.status_code == 200:
                    try:
                        response = validation_schema(**response.json())
                        return response
                    except ValidationError as e:
                        sentry_sdk.capture_message(
                            message=f"Response data validation failed: {self.api_url} {e.json()}",
                            level="error",
                        )
                        return None
                else:
                    sentry_sdk.capture_message(
                        message=f"Received non-200 status code: {self.api_url} {response.status_code} {response.text}",
                        level="error",
                    )

        except httpx.RequestError as e:
            sentry_sdk.capture_message(
                message=f"Error: {e.args} while trying to make a request to {self.api_url}",
                level="error",
            )

    async def post(
        self, params: dict[str, Any], validation_schema: Type[T], endpoint_url=""
    ) -> Optional[T]:
        try:
            logger.info(f"Making a request to {self.api_url} {endpoint_url} with params {params}")
            start_time = time.time()
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url + endpoint_url,
                    json=params,
                    headers={"X-API-KEY": self.api_key},
                )

                response_time = time.time() - start_time
                logger.info(
                    f"Service {self.api_url}: {response.text} for request {params} in {response_time}"
                )
                acceptable_response_time = 10
                if int(response_time) > acceptable_response_time:
                    with sentry_sdk.push_scope() as scope:
                        scope.set_extra("url", self.api_url)
                        scope.set_extra("endpoint_url", endpoint_url)
                        scope.set_extra("response_time_seconds", f"{response_time:.2f}")
                        scope.set_extra("request_params", params)
                        sentry_sdk.capture_message(
                            "Warning: Slow response from LLM Service API (POST)", level="warning"
                        )

                if response.status_code == 200:
                    try:
                        response = validation_schema(**response.json())
                        return response
                    except ValidationError as e:
                        sentry_sdk.capture_message(
                            message=f"Response data validation failed: {self.api_url} {e.json()}",
                            level="error",
                        )
                        return None
                else:
                    sentry_sdk.capture_message(
                        message=f"Received non-200 status code: {self.api_url} {response.status_code} {response.text}",
                        level="error",
                    )

        except httpx.RequestError as e:
            logger.info(f"Error: {e.args} while trying to make a request to {self.api_url}")
            sentry_sdk.capture_message(
                message=f"Error: {e.args} while trying to make a request to {self.api_url}",
                level="error",
            )
            return None
