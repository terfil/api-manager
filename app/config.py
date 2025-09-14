from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database settings
    database_url: str = "sqlite:///./api_management.db"
    
    # API settings
    api_title: str = "API Management Service"
    api_description: str = "A comprehensive service for managing API endpoints with Scalar integration"
    api_version: str = "1.0.0"
    
    # Security settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS settings
    allowed_origins: list = ["*"]
    allowed_methods: list = ["*"]
    allowed_headers: list = ["*"]
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = True
    
    # OpenAI settings (if needed for advanced analysis)
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_api_base: Optional[str] = os.getenv("OPENAI_API_BASE")
    
    class Config:
        env_file = ".env"

settings = Settings()

