from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.routes import router as api_router
from app.services.ml_service import ml_service
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo de eventos de inicio y cierre de la aplicación"""
    # Startup
    print("=" * 50)
    print("🚀 ML Service iniciando...")
    print(f"📍 Environment: {settings.ENVIRONMENT}")
    print(f"📍 Port: {settings.PORT}")
    print(f"📍 Model Path: {settings.MODEL_PATH}")
    
    # Verificar modelo cargado
    health = ml_service.check_health()
    if health.get('trained'):
        print(f"✅ Modelo pre-entrenado cargado: {health.get('model_info', {}).get('filename', 'N/A')}")
    else:
        print("⚠️ No hay modelo pre-entrenado. Esperando entrenamiento inicial...")
    
    print("=" * 50)
    
    yield  # Aquí la aplicación está corriendo
    
    # Shutdown (opcional)
    print("🛑 ML Service cerrando...")


app = FastAPI(
    title="ML Recommendation Service",
    description="Servicio de recomendaciones ML para auditorías",
    version="1.0.0",
    lifespan=lifespan  # 🔥 NUEVO: usar lifespan
)

# CORS - Importante para Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(api_router, prefix="/api/ml")


@app.get("/")
async def root():
    """Health check principal"""
    return {
        "service": "ML Recommendation Service",
        "status": "running",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
async def health():
    """Health check detallado"""
    return ml_service.check_health()