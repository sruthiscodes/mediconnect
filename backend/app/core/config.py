from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Supabase Configuration
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Together.ai Configuration
    together_api_key: str = os.getenv("TOGETHER_API_KEY", "")
    
    # ChromaDB Configuration
    chroma_persist_directory: str = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    
    # CORS Configuration
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Application Configuration
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-this")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"

    @property
    def CORS_ORIGINS(self) -> List[str]:
        cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
        return [origin.strip() for origin in cors_origins_str.split(",")]

settings = Settings() 