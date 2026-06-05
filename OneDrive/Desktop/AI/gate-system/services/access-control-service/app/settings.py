from pydantic import Field

from gate_shared.settings import CommonSettings


class Settings(CommonSettings):
    service_name: str = "access-control-service"
    postgres_schema: str = "access_service"

    entrance_fee_cents: int = Field(default=500, alias="ENTRANCE_FEE_CENTS")
    door_unlock_seconds: int = Field(default=5, alias="DOOR_UNLOCK_SECONDS")


settings = Settings()

