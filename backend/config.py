import os
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    stripe_secret_key: str = Field(..., env="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(..., env="STRIPE_WEBHOOK_SECRET")
    stripe_price_id: str = Field(..., env="STRIPE_PRICE_ID")

    aws_access_key_id: str = Field(..., env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(..., env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field("us-east-1", env="AWS_REGION")
    aws_s3_bucket: str = Field(..., env="AWS_S3_BUCKET")

    cors_origins: str = Field("http://localhost:3000", env="CORS_ORIGINS")
    database_url: str = Field("postgresql://postgres:postgres@localhost:5432/tonal_backend", env="DATABASE_URL")

    webhook_path: str = Field("/payments/webhook")
    app_url: str = Field("http://localhost:3000", env="APP_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def get_cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


def get_settings() -> Settings:
    return Settings()
