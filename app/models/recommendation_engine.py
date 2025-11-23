import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from typing import List, Dict, Any
import joblib
import os
from datetime import datetime
from pathlib import Path  # 🔥 NUEVO
import glob  # 🔥 NUEVO

class RecommendationEngine:
    def __init__(self, model_path: str = './models'):
        self.model_path = model_path
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=100,
            ngram_range=(1, 2),
            stop_words='spanish',
            min_df=1
        )
        self.classifier = RandomForestClassifier(
            n_estimators=20,
            random_state=42,
            max_depth=5,
            min_samples_split=2,
            min_samples_leaf=1
        )
        self.trained = False
        os.makedirs(model_path, exist_ok=True)
        
        # 🔥 NUEVO: Intentar cargar modelo al iniciar
        self._load_latest_model()
    
    # 🔥 NUEVO MÉTODO: Cargar modelo más reciente
    def _load_latest_model(self):
        """Carga automáticamente el modelo más reciente disponible"""
        try:
            model_dir = Path(self.model_path)
            
            # Buscar archivos de clasificador
            classifier_files = list(model_dir.glob('classifier_*.pkl'))
            
            if not classifier_files:
                print("⚠️ No se encontraron modelos pre-entrenados")
                return
            
            # Ordenar por nombre (timestamp) - más reciente primero
            classifier_files.sort(reverse=True)
            latest_classifier = classifier_files[0]
            
            # Extraer timestamp del nombre del archivo
            # Formato: classifier_20251122_085149.pkl
            timestamp = latest_classifier.stem.replace('classifier_', '')
            vectorizer_file = model_dir / f'tfidf_{timestamp}.pkl'
            
            if not vectorizer_file.exists():
                print(f"⚠️ No se encontró vectorizador para {latest_classifier.name}")
                return
            
            # Cargar modelos
            print(f"📂 Cargando modelo: {latest_classifier.name}")
            self.classifier = joblib.load(str(latest_classifier))
            
            print(f"📂 Cargando vectorizador: {vectorizer_file.name}")
            self.tfidf_vectorizer = joblib.load(str(vectorizer_file))
            
            self.trained = True
            print(f"✅ Modelo cargado exitosamente desde {latest_classifier.name}")
            
        except Exception as e:
            print(f"❌ Error cargando modelo: {e}")
            import traceback
            traceback.print_exc()
            self.trained = False
    
    # 🔥 NUEVO MÉTODO: Limpiar modelos antiguos
    def _cleanup_old_models(self, keep_latest: int = 5):
        """Elimina modelos antiguos para ahorrar espacio"""
        try:
            model_dir = Path(self.model_path)
            
            # Obtener todos los archivos de modelo ordenados por fecha (más recientes primero)
            classifier_files = sorted(model_dir.glob('classifier_*.pkl'), reverse=True)
            vectorizer_files = sorted(model_dir.glob('tfidf_*.pkl'), reverse=True)
            
            # Eliminar archivos antiguos (mantener solo los últimos N)
            for old_file in classifier_files[keep_latest:]:
                old_file.unlink()
                print(f"🗑️ Eliminado modelo antiguo: {old_file.name}")
            
            for old_file in vectorizer_files[keep_latest:]:
                old_file.unlink()
                print(f"🗑️ Eliminado vectorizador antiguo: {old_file.name}")
                
        except Exception as e:
            print(f"⚠️ Error limpiando modelos antiguos: {e}")
    
    def prepare_data(self, instances: List[Dict[str, Any]]) -> pd.DataFrame:
        """Extrae TODAS las observaciones de TODAS las instancias"""
        data = []
        for instance in instances:
            sections = instance.get('sections', [])
            for section in sections:
                questions = section.get('questions', [])
                for question in questions:
                    response = question.get('response', 'N/A')
                    if response == 'N/A' or response == -1:  # 🔥 También saltar -1
                        continue
                    
                    data.append({
                        'question_text': question.get('questionText', ''),
                        'comment': question.get('comment', ''),
                        'response': float(response),
                        'points': question.get('points', 0),
                        'section_compliance': section.get('compliancePercentage', 0),
                        'overall_compliance': instance.get('overallCompliancePercentage', 0),
                    })
        return pd.DataFrame(data)
    
    def train(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Entrena el modelo con datos históricos"""
        print("🔄 Preparando datos...")
        df = self.prepare_data(instances)
        
        total_observations = len(df)
        print(f"📊 Total de observaciones encontradas: {total_observations}")
        
        if total_observations < 5:
            raise ValueError(
                f"❌ Datos insuficientes: {total_observations} observaciones encontradas.\n"
                f"   Se requieren al menos 5 observaciones (preguntas respondidas que no sean N/A).\n"
                f"   Instancias recibidas: {len(instances)}"
            )
        
        print(f"✅ Suficientes datos: {total_observations} observaciones de {len(instances)} instancias")
        
        # Preparar features
        text_features = df['question_text'] + ' ' + df['comment'].fillna('')
        
        try:
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(text_features)
            print(f"📝 Features de texto extraídos: {tfidf_matrix.shape[1]}")
        except ValueError as e:
            print(f"⚠️ Advertencia en TF-IDF: {e}")
            tfidf_matrix = np.zeros((len(df), 0))
        
        numeric_features = df[['section_compliance', 'overall_compliance']].values
        
        # Combinar features
        if tfidf_matrix.shape[1] > 0:
            X = np.hstack([tfidf_matrix.toarray(), numeric_features])
        else:
            X = numeric_features
            
        y = df['response'].astype(int)
        
        print(f"🚀 Entrenando modelo con {X.shape[0]} muestras y {X.shape[1]} features...")
        
        self.classifier.fit(X, y)
        train_score = self.classifier.score(X, y)
        self.trained = True
        self._save_model()
        
        # 🔥 Limpiar modelos antiguos después de guardar
        self._cleanup_old_models(keep_latest=5)
        
        print(f"✅ Modelo entrenado: accuracy = {train_score:.2%}")
        
        return {
            'accuracy': float(train_score),
            'training_samples': len(df),
            'instances_used': len(instances),
            'features': int(X.shape[1]),
            'timestamp': datetime.now().isoformat()
        }
    
    def predict(self, question_text: str, current_response: int, 
                comment: str = '', context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Genera recomendación para una observación"""
        if not self.trained:
            raise ValueError("❌ Modelo no entrenado. Por favor entrene el modelo primero.")
        
        context = context or {}
        text = f"{question_text} {comment}"
        
        # Preparar features
        try:
            tfidf_features = self.tfidf_vectorizer.transform([text])
        except:
            tfidf_features = np.zeros((1, 0))
        
        numeric_features = np.array([[
            context.get('section_compliance', 50),
            context.get('overall_compliance', 50)
        ]])
        
        # Combinar features
        if tfidf_features.shape[1] > 0:
            X = np.hstack([tfidf_features.toarray(), numeric_features])
        else:
            X = numeric_features
        
        predicted_score = int(self.classifier.predict(X)[0])
        probabilities = self.classifier.predict_proba(X)[0]
        confidence = float(probabilities[predicted_score] if len(probabilities) > predicted_score else 0.5)
        
        return self._generate_recommendation(
            current_response, predicted_score, confidence, question_text, comment
        )
    
    def _generate_recommendation(self, current: int, predicted: int, 
                                  confidence: float, question: str, comment: str) -> Dict[str, Any]:
        """Genera la recomendación formateada"""
        levels = {0: "Crítico", 1: "Deficiente", 2: "Aceptable", 3: "Óptimo"}
        actions = {
            0: ["Implementar plan correctivo inmediato", "Documentar no conformidad", "Asignar responsable"],
            1: ["Desarrollar procedimiento", "Capacitar personal", "Establecer controles"],
            2: ["Reforzar prácticas", "Documentar lecciones", "Mantener monitoreo"],
            3: ["Mantener estándares", "Compartir mejores prácticas", "Usar como caso de estudio"]
        }
        
        gap = predicted - current
        
        if gap > 0:
            priority = 'Alta' if gap >= 2 else 'Media'
            analysis = f"Brecha de {gap} punto(s). Puede alcanzar nivel {predicted}/3 con las acciones recomendadas."
        else:
            priority = 'Baja'
            analysis = f"Observación en nivel esperado ({predicted}/3). Mantener estándares actuales."
        
        return {
            'current_score': current,
            'predicted_optimal_score': predicted,
            'current_level': levels.get(current, 'Desconocido'),
            'target_level': levels.get(predicted, 'Desconocido'),
            'confidence': round(confidence, 2),
            'improvement_gap': gap,
            'priority': priority,
            'recommended_actions': actions.get(predicted, []),
            'analysis': analysis
        }
    
    def _save_model(self):
        """Guarda el modelo entrenado"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        classifier_path = f'{self.model_path}/classifier_{timestamp}.pkl'
        vectorizer_path = f'{self.model_path}/tfidf_{timestamp}.pkl'
        
        joblib.dump(self.classifier, classifier_path)
        joblib.dump(self.tfidf_vectorizer, vectorizer_path)
        
        print(f"💾 Modelo guardado: classifier_{timestamp}.pkl")
        print(f"💾 Vectorizador guardado: tfidf_{timestamp}.pkl")