from abc import ABC


class BaseMailer(ABC):
    def send_email_dynamic_template(
        self,
        sender_email: str,
        recipient_email: str,
        subject: str,
        dynamic_template_id: str,
        dynamic_template_data: dict[str, str],
        sandbox_mode: bool = False,
    ) -> None:
        pass
