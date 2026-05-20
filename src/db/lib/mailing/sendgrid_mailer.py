from logging import getLogger
from typing import Any

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import From, Mail, MailSettings, SandBoxMode, To

from .common.base import BaseMailer
from .common.exceptions import NotSuccessResponseStatus

logger = getLogger(__name__)


class SendGridMailer(BaseMailer):
    def __init__(self, api_key: str):
        logger.debug(f"SendGridMailer successfully initialized with")
        self.client = SendGridAPIClient(api_key)

    def send_email_dynamic_template(
        self,
        sender_email: str,
        recipient_email: str,
        subject: str,
        dynamic_template_id: str,
        dynamic_template_data: dict[str, str],
        sandbox_mode: bool = False,
    ) -> None:
        logger.info(
            f"Sending email to {recipient_email} with subject {subject}, dynamic_template_id {dynamic_template_id} and dynamic_template_data {dynamic_template_data}"
        )
        mail = Mail(
            from_email=From(sender_email),
            to_emails=To(recipient_email),
            subject=subject,
        )
        mail.template_id = dynamic_template_id
        mail.dynamic_template_data = dynamic_template_data
        # Enable sandbox mode for testing
        logger.debug(f"Sandbox mode is set to {sandbox_mode}")
        if sandbox_mode:
            mail.mail_settings = MailSettings()
            mail.mail_settings.sandbox_mode = SandBoxMode(True)

        response = self.client.send(mail)

        if not str(response.status_code).startswith("2"):
            raise NotSuccessResponseStatus(response.status_code, response)
        logger.info(
            f"Email sent successfully to {recipient_email} with status code {response.status_code}"
        )
