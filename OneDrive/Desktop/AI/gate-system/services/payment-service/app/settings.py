from gate_shared.settings import CommonSettings
from pydantic import Field


class Settings(CommonSettings):
    service_name: str = "payment-service"
    postgres_schema: str = "payment_service"

    payment_provider: str = Field(default="stub", alias="PAYMENT_PROVIDER")
    payment_webhook_secret: str = Field(default="dev_webhook_secret", alias="PAYMENT_WEBHOOK_SECRET")


settings = Settings()

