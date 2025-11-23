from fastapi import APIRouter, HTTPException, Request
from app.schemas.recommendation import TrainingRequest
from app.services.ml_service import ml_service
from pydantic import ValidationError

router = APIRouter()

@router.post("/")
async def train_model(request: Request):
    """Entrena el modelo ML"""
    # Logging inicial del request
    print("\n======== [ML TRAIN] Request recibido ========")
    print(f"Headers: {dict(request.headers)}")
    raw_body = await request.body()
    print(f"Tamaño de body (bytes): {len(raw_body)}")

    try:
        json_body = await request.json()
        print(f"Keys principales del body: {list(json_body.keys())}")
        if "instances" in json_body and json_body["instances"]:
            print(f"Cantidad de instancias: {len(json_body['instances'])}")
            print("Primera instancia keys:", list(json_body['instances'][0].keys()))
            print("Primera instancia status:", json_body['instances'][0].get("status"))
        # Validación con Pydantic
        payload = TrainingRequest(**json_body)
        result = ml_service.train_model(payload)
        print("======== [ML TRAIN] Entrenamiento exitoso ========")
        return result
    except ValidationError as ve:
        print("======== [ML TRAIN] Error de validación ========")
        print(str(ve))
        raise HTTPException(status_code=422, detail=ve.errors())
    except ValueError as e:
        print("======== [ML TRAIN] Error ValueError ========")
        print(str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("======== [ML TRAIN] Error general ========")
        print(str(e))
        raise HTTPException(status_code=500, detail=f"Error entrenando: {str(e)}")