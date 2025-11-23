from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class QuestionResponse(BaseModel):
    questionText: str
    response: Any  # Puede ser 0,1,2,3 o "N/A"
    points: float
    comment: Optional[str] = ""

class SectionResponse(BaseModel):
    sectionId: str
    questions: List[QuestionResponse]
    maxPoints: float
    obtainedPoints: float
    applicablePoints: float
    naCount: int
    compliancePercentage: float
    sectionComment: Optional[str] = ""

class InstanceData(BaseModel):
    """Modelo que representa una instancia completa de MongoDB"""
    sections: List[SectionResponse]
    templateId: Any
    verificationList: Dict[str, Any] = {}
    overallCompliancePercentage: float
    totalObtainedPoints: float
    totalApplicablePoints: float
    status: str

class TrainingRequest(BaseModel):
    instances: List[Dict[str, Any]]

class RecommendationRequest(BaseModel):
    question_text: str
    current_response: int = Field(..., ge=0, le=3)
    comment: Optional[str] = ""
    context: Optional[Dict[str, Any]] = {}

class RecommendationResponse(BaseModel):
    current_score: int
    predicted_optimal_score: int
    current_level: str
    target_level: str
    confidence: float
    improvement_gap: int
    priority: str
    recommended_actions: List[str]
    analysis: str

class AnalysisRequest(BaseModel):
    instances: List[Dict[str, Any]]
    template_id: str
    
class FeedbackRequest(BaseModel):
    question_text: str
    current_response: int
    comment: str
    accion_seleccionada: str
    fue_recomendacion_ml: bool
    indice_recomendacion: Optional[int] = None
    context: Optional[Dict[str, Any]] = {}
    feedback_type: str  # 'guardado', 'cerrado', 'aprobado', 'rechazado'
    feedback_score: float  # -1.0 a +2.0