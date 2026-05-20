import pytest

from lib.config import config
from lib.mailing.sendgrid_mailer import SendGridMailer


@pytest.fixture(scope="session")
def sendgrid_mailer():
    return SendGridMailer(api_key=config.sendgrid_api_key.get_secret_value())


def test_send_email_dynamic_template(sendgrid_mailer: SendGridMailer):
    sender_email = "sender_tester@gmail.com"
    recipient_email = "recipient_tester@gmail.com"
    subject = "Test subject"
    dynamic_template_id = config.sendgrid_token_pack_dynamic_template_id
    dynamic_template_data = {
        "payment_id": "12349",
        "amount_paid": "542.99",
        "date_paid": "2855-47-27",
        "paid_name": "Premium Membership",
    }
    sandbox_mode = True
    assert not sendgrid_mailer.send_email_dynamic_template(
        sender_email,
        recipient_email,
        subject,
        dynamic_template_id,
        dynamic_template_data,
        sandbox_mode,
    )
