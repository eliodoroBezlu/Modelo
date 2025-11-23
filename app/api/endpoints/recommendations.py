from fastapi import APIRouter, HTTPException, Request
from app.schemas.recommendation import RecommendationRequest
from app.services.ml_service import ml_service
from pydantic import ValidationError

router = APIRouter()

@router.post("/")
async def get_recommendation(request: Request):
    """Genera recomendación para una observación"""
    print("\n======== [ML RECOMMEND] Request recibido ========")
    print(f"Headers: {dict(request.headers)}")
    raw_body = await request.body()
    print(f"Tamaño de body (bytes): {len(raw_body)}")

    try:
        json_body = await request.json()
        print(f"Keys principales del body: {list(json_body.keys())}")
        payload = RecommendationRequest(**json_body)
        result = ml_service.get_recommendation(payload)
        print("======== [ML RECOMMEND] Recomendación exitosa ========")
        return result
    except ValidationError as ve:
        print("======== [ML RECOMMEND] Error de validación ========")
        print(str(ve))
        raise HTTPException(status_code=422, detail=ve.errors())
    except ValueError as e:
        print("======== [ML RECOMMEND] Error ValueError ========")
        print(str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("======== [ML RECOMMEND] Error general ========")
        print(str(e))
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")