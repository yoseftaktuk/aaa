from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGO_HOST: str
    MONGO_PORT: int
    MONGO_USERNAME: str
    MONGO_PASSWORD: str
    MONGO_AUTH_SOURCE: str
    MONGO_DB: str
    MONGO_COLLECTION: str

settings = Settings()    