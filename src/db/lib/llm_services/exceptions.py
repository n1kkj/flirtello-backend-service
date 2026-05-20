from datetime import datetime
from decimal import Decimal
from uuid import UUID


class LLMServiceError(Exception):
    def __init__(self, service_api_url: str) -> None:
        self.service_api_url = service_api_url

    @property
    def message(self):
        return f"An error occurred while interacting with llm services at server: {self.service_api_url}"


class NotSuccessResponseStatus(LLMServiceError):
    def __init__(self, service_api_url: str, status_code: int, api_message: str) -> None:
        super().__init__(service_api_url)
        self.status_code = status_code
        self.api_message = api_message

    @property
    def message(self):
        return f"Unsuccess status {self.status_code} while trying to interact with {self.service_api_url}, error text: {self.api_message}"
