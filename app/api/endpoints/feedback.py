# app/api/endpoints/feedback.py

from fastapi import APIRouter, HTTPException
from app.schemas.recommendation import FeedbackRequest
from app.services.ml_service import ml_service
import json
from datetime import datetime
from pathlib import Path

router = APIRouter()

FEEDBACK_FILE = Path("./data/feedback.jsonl")
FEEDBACK_FILE.parent.mkdir(exist_ok=True)

@router.post("/")
async def receive_feedback(feedback: FeedbackRequest):
    """Recibe feedback de acciones tomadas"""
    print("\n======== [ML FEEDBACK] Recibido ========")
    print(f"Acción: {feedback.accion_seleccionada}")
    print(f"¿Fue ML?: {feedback.fue_recomendacion_ml}")
    print(f"Tipo: {feedback.feedback_type}")
    print(f"Score: {feedback.feedback_score}")
    
    # Guardar feedback en archivo JSONL
    feedback_entry = {
        **feedback.dict(),
        "timestamp": datetime.now().isoformat()
    }
    
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(feedback_entry, ensure_ascii=False) + "\n")
    
    # Contar feedbacks pendientes
    feedback_count = sum(1 for _ in open(FEEDBACK_FILE))
    
    print(f"📊 Total feedbacks acumulados: {feedback_count}")
    
    # 🔥 Re-entrenar automáticamente cada 50 feedbacks
    if feedback_count % 50 == 0:
        print("🔥 ¡50 feedbacks alcanzados! Iniciando re-entrenamiento...")
        # Aquí puedes llamar a un proceso de re-entrenamiento
        # await retrain_with_feedback()
    
    return {
        "status": "feedback_received",
        "pending_count": feedback_count,
        "message": "Feedback guardado exitosamente"
    }