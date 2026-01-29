from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    colbert_model_path: str = "/model_weights/colqwen2.5-v0.2"
    redis_password: str = ""  # Loaded from REDIS_PASSWORD env var

    class Config:
        env_file = "../.env"


settings = Settings()
