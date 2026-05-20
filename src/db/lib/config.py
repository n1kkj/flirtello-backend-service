import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import AnyUrl, EmailStr, SecretStr
from pydantic_settings import BaseSettings

from .billing.payment_system.enums import PaymentSystemCurrencyTypes, PaymentSystems
from .llm.llm_enums import LLMProviders


class Config(BaseSettings):
    def __init__(self, **values):
        load_dotenv()
        super().__init__(**values)
        self.create_certificates()

    # LLM microservices
    caption_service_url: AnyUrl
    context_image_service_url: AnyUrl
    guardrail_service_url: AnyUrl
    guardrail_retries: int

    llm_services_api_key: SecretStr

    openrouter_api_key: SecretStr
    default_llm_provider: LLMProviders
    default_llm_model: str

    payment_system_api_key_recurrent: SecretStr
    payment_system_token_recurrent: SecretStr
    public_key_recurrent: SecretStr
    private_key_recurrent: SecretStr
    cert_folder_name_recurrent: str = "cert_recurrent"

    payment_system_api_key_regular: SecretStr
    payment_system_token_regular: SecretStr
    public_key_regular: SecretStr
    private_key_regular: SecretStr
    cert_folder_name_regular: str = "cert_regular"

    public_key_name: str = "public.pem"
    private_key_name: str = "private.pem"
    payment_system_currency: PaymentSystemCurrencyTypes

    use_payment_system_test_server: bool

    token_packs_payment_system: PaymentSystems
    tariff_plans_payment_system: PaymentSystems

    sendgrid_api_key: SecretStr
    sendgrid_tariff_plan_dynamic_template_id: str
    sendgrid_token_pack_dynamic_template_id: str
    sendgrid_sender_email: str

    # Billing balances
    payment_system_balance_id: int
    truevo_payment_system_balance_id: int
    telegram_stars_payment_system_balance_id: int
    eur_company_balance_id: int

    def create_certificates(self):
        public_cert_content_recurrent = self.public_key_recurrent.get_secret_value()
        private_cert_content_recurrent = self.private_key_recurrent.get_secret_value()
        public_cert_content_regular = self.public_key_regular.get_secret_value()
        private_cert_content_regular = self.private_key_regular.get_secret_value()

        cert_folder_regular = self.cert_folder_name_regular
        cert_folder_recurrent = self.cert_folder_name_recurrent
        os.makedirs(cert_folder_regular, exist_ok=True)
        os.makedirs(cert_folder_recurrent, exist_ok=True)

        with open(os.path.join(cert_folder_regular, self.public_key_name), "w") as public_file:
            public_file.write(public_cert_content_regular)

        with open(os.path.join(cert_folder_regular, self.private_key_name), "w") as private_file:
            private_file.write(private_cert_content_regular)

        with open(os.path.join(cert_folder_recurrent, self.public_key_name), "w") as public_file:
            public_file.write(public_cert_content_recurrent)

        with open(os.path.join(cert_folder_recurrent, self.private_key_name), "w") as private_file:
            private_file.write(private_cert_content_recurrent)


config = Config()
