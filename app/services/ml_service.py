from app.models.recommendation_engine import RecommendationEngine
from app.schemas.recommendation import (
    TrainingRequest,
    RecommendationRequest,
    AnalysisRequest
)
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import json

class MLService:
    """Servicio que maneja la lógica de negocio ML"""

    def __init__(self):
        self.engine = RecommendationEngine(model_path='./models')
        self.feedback_file = Path('./data/feedback.jsonl')
        
        # Crear directorio de datos si no existe
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)

    def train_model(self, request: TrainingRequest) -> Dict[str, Any]:
        """Entrena el modelo con instancias históricas"""
        instances = request.instances

        print("======== [ML TRAIN] Limpiando datos antes del entrenamiento ========")

        cleaned_instances = []
        for inst in instances:
            inst_copy = inst.copy()

            # Limpiar todas las preguntas dentro de las secciones
            for section in inst_copy.get("sections", []):
                for question in section.get("questions", []):
                    # 1. Limpiar comentarios vacíos
                    if question.get("comment") in ["", None]:
                        question["comment"] = "sin comentario"

                    # 2. Asegurar que response y points sean numéricos o manejables
                    resp = question.get("response")
                    if resp == "N/A" or resp == "" or resp is None:
                        question["response"] = -1
                        question["points"] = 0.0
                    else:
                        try:
                            question["response"] = float(resp)
                            question["points"] = float(question.get("points", 0))
                        except (ValueError, TypeError):
                            question["response"] = 0.0
                            question["points"] = 0.0

            # Limpiar campos numéricos globales de la instancia
            numeric_fields = [
                "totalObtainedPoints",
                "totalApplicablePoints",
                "totalMaxPoints",
                "overallCompliancePercentage"
            ]
            for field in numeric_fields:
                if field in inst_copy:
                    val = inst_copy[field]
                    if val == "" or val is None:
                        inst_copy[field] = 0.0
                    else:
                        try:
                            inst_copy[field] = float(val)
                        except (ValueError, TypeError):
                            inst_copy[field] = 0.0

            cleaned_instances.append(inst_copy)

        print(f"✅ Datos limpios: {len(cleaned_instances)} instancias listas para entrenamiento")

        # Entrenar con datos limpios
        metrics = self.engine.train(cleaned_instances)

        return {
            'status': 'success',
            'message': f"Modelo entrenado exitosamente con {len(cleaned_instances)} instancias",
            'metrics': metrics
        }

    def retrain_with_feedback(
        self, 
        historical_instances: List[Dict], 
        feedback_file: str = None
    ) -> Dict[str, Any]:
        """Re-entrena el modelo incorporando feedback de usuarios"""
        
        if feedback_file is None:
            feedback_file = str(self.feedback_file)
        
        # Cargar feedbacks existentes
        feedbacks = []
        feedback_path = Path(feedback_file)
        
        if feedback_path.exists():
            print(f"📂 Cargando feedbacks desde: {feedback_file}")
            with open(feedback_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        feedback = json.loads(line.strip())
                        feedbacks.append(feedback)
                    except json.JSONDecodeError as e:
                        print(f"⚠️ Error en línea {line_num}: {e}")
                        continue
        else:
            print(f"⚠️ Archivo de feedback no encontrado: {feedback_file}")
        
        print(f"📊 Re-entrenando con {len(historical_instances)} instancias históricas + {len(feedbacks)} feedbacks")
        
        # Crear instancias sintéticas a partir de feedbacks positivos
        synthetic_instances_added = 0
        for fb in feedbacks:
            # Solo usar feedbacks de recomendaciones ML exitosas
            if fb.get("fue_recomendacion_ml") and fb.get("feedback_score", 0) > 0.5:
                try:
                    # Crear instancia sintética con la acción exitosa
                    synthetic_instance = {
                        "sections": [{
                            "questions": [{
                                "questionText": fb.get("question_text", ""),
                                "response": fb.get("current_response", 0),
                                "comment": fb.get("comment", "sin comentario"),
                                "points": fb.get("feedback_score", 1.0) * 3,  # Escalar score a puntos
                                # Incluir contexto adicional
                                "accion_aplicada": fb.get("accion_seleccionada", ""),
                                "context": fb.get("context", {}),
                            }]
                        }],
                        # Campos adicionales de la instancia
                        "totalObtainedPoints": fb.get("feedback_score", 1.0) * 3,
                        "totalApplicablePoints": 3.0,
                        "totalMaxPoints": 3.0,
                        "overallCompliancePercentage": fb.get("feedback_score", 1.0) * 100,
                        # Metadata
                        "_synthetic": True,
                        "_feedback_type": fb.get("feedback_type", "guardado"),
                        "_timestamp": fb.get("timestamp", ""),
                    }
                    
                    historical_instances.append(synthetic_instance)
                    synthetic_instances_added += 1
                    
                except Exception as e:
                    print(f"⚠️ Error procesando feedback: {e}")
                    continue
        
        print(f"✅ Se agregaron {synthetic_instances_added} instancias sintéticas desde feedback")
        
        # Entrenar con datos combinados (históricos + sintéticos)
        training_request = TrainingRequest(instances=historical_instances)
        result = self.train_model(training_request)
        
        # Agregar información sobre el feedback usado
        result['feedback_stats'] = {
            'total_feedbacks': len(feedbacks),
            'synthetic_instances_added': synthetic_instances_added,
            'feedback_file': feedback_file,
        }
        
        return result

    def save_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Guarda feedback de usuario para futuro re-entrenamiento"""
        try:
            # Agregar timestamp si no existe
            if 'timestamp' not in feedback_data:
                feedback_data['timestamp'] = datetime.now().isoformat()
            
            # Guardar en archivo JSONL (append)
            with open(self.feedback_file, 'a', encoding='utf-8') as f:
                json.dump(feedback_data, f, ensure_ascii=False)
                f.write('\n')
            
            print(f"✅ Feedback guardado: {self.feedback_file}")
            
            return {
                'status': 'success',
                'message': 'Feedback guardado exitosamente',
                'file': str(self.feedback_file),
            }
            
        except Exception as e:
            print(f"❌ Error guardando feedback: {e}")
            return {
                'status': 'error',
                'message': f'Error guardando feedback: {str(e)}',
            }

    def get_recommendation(self, request: RecommendationRequest) -> Dict[str, Any]:
        """Obtiene recomendación"""
        recommendation = self.engine.predict(
            question_text=request.question_text,
            current_response=request.current_response,
            comment=request.comment,
            context=request.context
        )
        return {
            'status': 'success',
            'recommendation': recommendation
        }

    def check_health(self) -> Dict[str, Any]:
        """Verifica estado del servicio"""
        # Contar feedbacks disponibles
        feedback_count = 0
        if self.feedback_file.exists():
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                feedback_count = sum(1 for _ in f)
        
        # 🔥 NUEVO: Obtener info del modelo actual
        model_info = None
        if self.engine.trained:
            try:
                model_dir = Path('./models')
                classifier_files = sorted(model_dir.glob('classifier_*.pkl'), reverse=True)
                
                if classifier_files:
                    latest = classifier_files[0]
                    timestamp = latest.stem.replace('classifier_', '')
                    
                    model_info = {
                        'filename': latest.name,
                        'timestamp': timestamp,
                        'size_mb': round(latest.stat().st_size / 1024 / 1024, 2),
                        'total_models': len(classifier_files)
                    }
            except Exception as e:
                print(f"⚠️ Error obteniendo info del modelo: {e}")
        
        return {
            'status': 'healthy',
            'trained': self.engine.trained,
            'model_info': model_info,  # 🔥 NUEVO
            'feedback_count': feedback_count,
            'feedback_file': str(self.feedback_file),
            'timestamp': datetime.now().isoformat()
        }
# Instancia global
ml_service = MLService()