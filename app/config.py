from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "NACOS E-Voting API"
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./nacos_e_voting.db"
    SECRET_KEY: str = "change-this-secret-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()
