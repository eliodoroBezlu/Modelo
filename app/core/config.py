# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    # 🔥 Railway usa PORT como variable de entorno
    PORT: int = int(os.getenv("PORT", "8000"))
    ENVIRONMENT: str = "development"
    
    # ✅ Orígenes por defecto más permisivos
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:4200,http://localhost:3002"
    
    MODEL_PATH: str = "./models"
    LOG_LEVEL: str = "INFO"
    
    @property
    def origins_list(self) -> List[str]:
        """Construye la lista de orígenes permitidos"""
        origins = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        
        # 🔥 En producción, agregar automáticamente los dominios de Railway
        if self.ENVIRONMENT == "production":
            # Agregar el dominio público del servicio actual
            railway_url = os.getenv("RAILWAY_PUBLIC_DOMAIN")
            if railway_url:
                origins.append(f"https://{railway_url}")
            
            # ✅ Agregar URLs de otros servicios de Railway
            backend_url = os.getenv("RAILWAY_SERVICE_BACKENDFORM_URL")
            frontend_url = os.getenv("RAILWAY_SERVICE_FORMNEXT_URL")
            
            if backend_url:
                origins.append(f"https://{backend_url}")
            if frontend_url:
                origins.append(f"https://{frontend_url}")
        
        # 🔍 Debug: mostrar orígenes permitidos
        print(f"🔍 CORS Origins permitidos: {origins}")
        
        return origins
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()