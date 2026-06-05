from gate_shared.settings import CommonSettings


class Settings(CommonSettings):
    service_name: str = "user-service"
    postgres_schema: str = "user_service"


settings = Settings()

