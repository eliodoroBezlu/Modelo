from fastapi import APIRouter

from app.api.endpoints import training, recommendations, feedback

router = APIRouter()

# Ahora sí con prefix correcto
router.include_router(training.router, prefix="/train", tags=["training"])
router.include_router(recommendations.router, prefix="/recommend", tags=["recommendations"])
router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])