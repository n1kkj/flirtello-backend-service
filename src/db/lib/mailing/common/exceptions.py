class SendGridError(Exception):
    def __init__(self, error_message: str) -> None:
        self.error_message = error_message

    @property
    def message(self):
        return f"An error occurred while interacting with SendGrid, error: {self.error_message}"


class NotSuccessResponseStatus(SendGridError):
    def __init__(self, status_code: int, error_message: str) -> None:
        self.status_code = status_code
        self.error_message = error_message

    @property
    def message(self):
        return f"Unsuccess status {self.status_code} while trying to interact with SendGrid error text: {self.error_message}"
