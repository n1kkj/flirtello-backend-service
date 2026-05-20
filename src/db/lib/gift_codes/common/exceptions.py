from datetime import datetime
from typing import Optional


class GiftCodeError(Exception):
    @property
    def message(self):
        return "An error occurred during gift code execution"


class GiftCodeAlreadyActivated(GiftCodeError):
    def __init__(self, code: str, user_id: int, activated_at: datetime) -> None:
        self.code = code
        self.user_id = user_id
        self.activated_at = activated_at

    @property
    def message(self):
        return f"Gift code '{self.code}' was already activated by user {self.user_id} at {self.activated_at.year}.{self.activated_at.month}.{self.activated_at.day}"


class GiftCodeInactive(GiftCodeError):
    def __init__(self, code: str) -> None:
        self.code = code

    @property
    def message(self):
        return f"Gift code '{self.code}' is no longer active"


class GiftCodeNotFound(GiftCodeError):
    def __init__(self, code: str) -> None:
        self.code = code

    @property
    def message(self):
        return f"Gift code '{self.code}' not found"
