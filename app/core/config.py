from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    # 🔥 IMPORTANTE: Railway usa PORT como variable de entorno
    PORT: int = int(os.getenv("PORT", "8000"))
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:4200"
    MODEL_PATH: str = "./models"
    LOG_LEVEL: str = "INFO"
    
    @property
    def origins_list(self) -> List[str]:
        origins = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        # 🔥 En producción, permitir el origen de Railway si existe
        if self.ENVIRONMENT == "production":
            railway_url = os.getenv("RAILWAY_PUBLIC_DOMAIN")
            if railway_url:
                origins.append(f"https://{railway_url}")
        return origins
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()