# ML Training Pipeline and Monitoring System
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
import joblib
import logging
from datetime import datetime, timedelta
import asyncio
import redis
from dataclasses import asdict
import json
import optuna
from optuna.integration.mlflow import MLflowCallback
import warnings
from matcher import FeatureEngineering, Student, Teacher
warnings.filterwarnings("ignore")
import os
from dotenv import load_dotenv
import redis

load_dotenv()

class ModelTrainer:
    """Handle model training and evaluation"""
    
    def __init__(self, experiment_name: str = "teacher_student_matching"):
        self.experiment_name = experiment_name
        mlflow.set_experiment(experiment_name)
        self.logger = logging.getLogger(__name__)
        self.feature_engineer = FeatureEngineering()
    
    def prepare_training_data(self, interactions_df: pd.DataFrame, 
                            students_df: pd.DataFrame, 
                            teachers_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare feature matrix and target vector for training"""
        features = []
        targets = []
        
        for _, interaction in interactions_df.iterrows():
            student_data = students_df[students_df['id'] == interaction['student_id']].iloc[0]
            teacher_data = teachers_df[teachers_df['id'] == interaction['teacher_id']].iloc[0]
            
            # Convert to internal objects
            student = Student(
                id=student_data['id'],
                subjects=student_data['subjects'].split(','),
                learning_style=student_data['learning_style'],
                availability=student_data['availability'].split(','),
                location_preference=student_data['location_preference'],
                budget_range=(student_data['budget_min'], student_data['budget_max']),
                experience_level=student_data['experience_level'],
                age=student_data.get('age', 20)
            )
            
            teacher = Teacher(
                id=teacher_data['id'],
                subjects=teacher_data['subjects'].split(','),
                teaching_style=teacher_data['teaching_style'],
                availability=teacher_data['availability'].split(','),
                location_preference=teacher_data['location_preference'],
                hourly_rate=teacher_data['hourly_rate'],
                experience_years=teacher_data['experience_years'],
                rating=teacher_data['rating'],
                total_students=teacher_data['total_students'],
                specializations=teacher_data['specializations'].split(','),
                gender=teacher_data['gender'],
                languages=teacher_data['languages'].split(',')
            )
            
            # Extract features
            feature_vector = self.feature_engineer.extract_features(student, teacher)
            features.append(feature_vector)
            targets.append(interaction['rating'])
        
        return np.array(features), np.array(targets)
    
    def train_model(self, features: np.ndarray, targets: np.ndarray) -> Dict[str, Any]:
        """Train the matching model with hyperparameter optimization"""
        
        with mlflow.start_run():
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, targets, test_size=0.2, random_state=42
            )
            
            # Hyperparameter optimization with Optuna
            def objective(trial):
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                    'max_depth': trial.suggest_int('max_depth', 3, 20),
                    'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
                    'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
                    'random_state': 42
                }
                
                model = RandomForestRegressor(**params)
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                
                return mean_squared_error(y_test, y_pred)
            
            # Run optimization
            study = optuna.create_study(direction='minimize')
            study.optimize(objective, n_trials=50)
            
            # Train final model with best parameters
            best_params = study.best_params
            model = RandomForestRegressor(**best_params)
            model.fit(X_train, y_train)
            
            # Evaluate model
            y_pred_train = model.predict(X_train)
            y_pred_test = model.predict(X_test)
            
            metrics = {
                'train_mse': mean_squared_error(y_train, y_pred_train),
                'test_mse': mean_squared_error(y_test, y_pred_test),
                'train_mae': mean_absolute_error(y_train, y_pred_train),
                'test_mae': mean_absolute_error(y_test, y_pred_test),
                'train_r2': r2_score(y_train, y_pred_train),
                'test_r2': r2_score(y_test, y_pred_test)
            }
            
            # Log parameters and metrics
            mlflow.log_params(best_params)
            mlflow.log_metrics(metrics)
            
            # Log model
            mlflow.sklearn.log_model(model, "model")
            
            # Feature importance
            feature_names = [
                'subject_score', 'schedule_score', 'location_match', 
                'budget_match', 'style_compatibility', 'rating_norm',
                'experience_norm', 'student_count_norm', 'gender_match'
            ]
            
            importance_dict = dict(zip(feature_names, model.feature_importances_))
            mlflow.log_dict(importance_dict, "feature_importance.json")
            
            self.logger.info(f"Model trained with test R2: {metrics['test_r2']:.4f}")
            
            return {
                'model': model,
                'metrics': metrics,
                'best_params': best_params,
                'feature_importance': importance_dict
            }

class DataDriftDetector:
    """Detect data drift in incoming requests"""
    
    def __init__(self, reference_data: np.ndarray):
        self.reference_data = reference_data
        self.reference_stats = self._calculate_stats(reference_data)
    
    def _calculate_stats(self, data: np.ndarray) -> Dict[str, float]:
        """Calculate statistical measures for data"""
        return {
            'mean': np.mean(data, axis=0),
            'std': np.std(data, axis=0),
            'min': np.min(data, axis=0),
            'max': np.max(data, axis=0)
        }
    
    def detect_drift(self, new_data: np.ndarray, threshold: float = 2.0) -> Dict[str, Any]:
        """Detect if new data has drifted from reference"""
        new_stats = self._calculate_stats(new_data)
        
        drift_scores = []
        for i in range(len(self.reference_stats['mean'])):
            # Z-score based drift detection
            z_score = abs((new_stats['mean'][i] - self.reference_stats['mean'][i]) / 
                         (self.reference_stats['std'][i] + 1e-8))
            drift_scores.append(z_score)
        
        max_drift = max(drift_scores)
        has_drift = max_drift > threshold
        
        return {
            'has_drift': has_drift,
            'max_drift_score': max_drift,
            'drift_scores': drift_scores,
            'threshold': threshold
        }

class ModelMonitor:
    """Monitor model performance and trigger retraining"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        self.performance_threshold = 0.8  # R2 score threshold
        
    async def track_prediction(self, prediction_data: Dict[str, Any]):
        """Track individual predictions for monitoring"""
        prediction_key = f"predictions:{datetime.now().isoformat()}"
        await self.redis_client.setex(
            prediction_key, 
            timedelta(days=7), 
            json.dumps(prediction_data)
        )
    
    async def track_feedback(self, feedback_data: Dict[str, Any]):
        """Track feedback for model performance calculation"""
        feedback_key = f"feedback:{feedback_data['student_id']}:{feedback_data['teacher_id']}"
        await self.redis_client.setex(
            feedback_key,
            timedelta(days=30),
            json.dumps(feedback_data)
        )
    
    async def calculate_model_performance(self, days_back: int = 7) -> Dict[str, float]:
        """Calculate recent model performance metrics"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Get feedback data from Redis
        pattern = "feedback:*"
        feedback_keys = await self.redis_client.keys(pattern)
        
        predictions = []
        actuals = []
        
        for key in feedback_keys:
            data = await self.redis_client.get(key)
            if data:
                feedback = json.loads(data)
                timestamp = datetime.fromisoformat(feedback.get('timestamp', ''))
                
                if start_date <= timestamp <= end_date:
                    # Would need to retrieve corresponding prediction
                    # For now, using mock data
                    predictions.append(feedback.get('predicted_rating', 4.0))
                    actuals.append(feedback['rating'])
        
        if len(predictions) < 10:  # Need minimum samples
            return {'insufficient_data': True}
        
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        metrics = {
            'mse': mean_squared_error(actuals, predictions),
            'mae': mean_absolute_error(actuals, predictions),
            'r2': r2_score(actuals, predictions),
            'sample_count': len(predictions)
        }
        
        return metrics
    
    async def check_retrain_trigger(self) -> bool:
        """Check if model needs retraining"""
        performance = await self.calculate_model_performance()
        
        if performance.get('insufficient_data'):
            return False
        
        # Trigger retraining if performance drops
        if performance['r2'] < self.performance_threshold:
            self.logger.warning(f"Model performance degraded: R2 = {performance['r2']:.4f}")
            return True
        
        # Check feedback volume
        feedback_count = await self.redis_client.dbsize()  # Simplified check
        if feedback_count > 1000:  # Threshold for new data
            self.logger.info("Sufficient new feedback data for retraining")
            return True
        
        return False

class AutoMLPipeline:
    """Automated ML pipeline for continuous learning"""
    
    def __init__(self, redis_url: str = None):
        self.trainer = ModelTrainer()
        self.redis_client = None
        self.monitor = None
        self.drift_detector = None
        self.logger = logging.getLogger(__name__)
        
        # Store redis_url as instance variable, with fallback to env variable
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    async def initialize(self):
        """Initialize Redis connection and components"""
        # Now use self.redis_url instead of redis_url
        self.redis_client = redis.from_url(self.redis_url)
        self.monitor = ModelMonitor(self.redis_client)
    
    async def run_training_pipeline(self, force_retrain: bool = False):
        """Run the complete training pipeline"""
        try:
            # Check if retraining is needed
            if not force_retrain and not await self.monitor.check_retrain_trigger():
                self.logger.info("No retraining needed")
                return
            
            self.logger.info("Starting model retraining...")
            
            # Load data (mock implementation)
            interactions_df = await self._load_interactions_data()
            students_df = await self._load_students_data()
            teachers_df = await self._load_teachers_data()
            
            # Prepare training data
            features, targets = self.trainer.prepare_training_data(
                interactions_df, students_df, teachers_df
            )
            
            # Initialize drift detector with current data
            if self.drift_detector is None:
                self.drift_detector = DataDriftDetector(features)
            else:
                # Check for drift
                drift_result = self.drift_detector.detect_drift(features)
                if drift_result['has_drift']:
                    self.logger.warning(f"Data drift detected: {drift_result['max_drift_score']:.4f}")
            
            # Train model
            training_result = self.trainer.train_model(features, targets)
            
            # Save model artifacts
            model_path = f"models/matching_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            joblib.dump(training_result['model'], model_path)
            
            # Update model in production (would typically update model registry)
            await self._update_production_model(model_path, training_result['metrics'])
            
            self.logger.info(f"Model retraining completed. Test R2: {training_result['metrics']['test_r2']:.4f}")
            
            return training_result
            
        except Exception as e:
            self.logger.error(f"Training pipeline failed: {str(e)}")
            raise
    
    async def _load_interactions_data(self) -> pd.DataFrame:
        """Load interaction data for training"""
        try:
            # Load your actual dataset
            interactions_df = pd.read_csv('data/interactions.csv')  # Fixed path
            print(f"Loaded {len(interactions_df)} interactions from CSV")
            return interactions_df
        except FileNotFoundError:
            print("Error: data/interactions.csv not found!")
            print("Run 'python dataset_generator.py' to generate sample data")
            return pd.DataFrame()

    async def _load_students_data(self) -> pd.DataFrame:
        try:
            return pd.read_csv('data/students.csv')  # Fixed path
        except FileNotFoundError:
            print("Error: data/students.csv not found!")
            return pd.DataFrame()

    async def _load_teachers_data(self) -> pd.DataFrame:
        try:
            return pd.read_csv('data/teachers.csv')  # Fixed path - was incomplete
        except FileNotFoundError:
            print("Error: data/teachers.csv not found!")
            return pd.DataFrame()
    
    async def _update_production_model(self, model_path: str, metrics: Dict[str, float]):
        """Update the production model"""
        # Store model metadata in Redis
        model_metadata = {
            'model_path': model_path,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat(),
            'version': f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        await self.redis_client.set(
            "current_model_metadata",
            json.dumps(model_metadata)
        )
        
        self.logger.info(f"Production model updated: {model_path}")

# Monitoring Dashboard Data
class MonitoringDashboard:
    """Generate monitoring dashboard data"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        return {
            'total_matches_today': await self._count_matches_today(),
            'average_response_time': await self._get_avg_response_time(),
            'success_rate': await self._get_success_rate(),
            'active_users': await self._count_active_users(),
            'model_performance': await self._get_model_performance(),
            'system_health': 'healthy'
        }
    
    async def _count_matches_today(self) -> int:
        """Count matches made today"""
        # Mock implementation
        return 156
    
    async def _get_avg_response_time(self) -> float:
        """Get average API response time"""
        return 0.245  # seconds
    
    async def _get_success_rate(self) -> float:
        """Get matching success rate"""
        return 0.94
    
    async def _count_active_users(self) -> int:
        """Count active users in last hour"""
        return 23
    
    async def _get_model_performance(self) -> Dict[str, float]:
        """Get current model performance"""
        return {
            'r2_score': 0.87,
            'mae': 0.34,
            'prediction_drift': 0.12
        }

# Usage Example
async def main():
    """Main execution example"""
    # Initialize pipeline
    pipeline = AutoMLPipeline()
    await pipeline.initialize()
    
    # Run training pipeline
    result = await pipeline.run_training_pipeline(force_retrain=True)
    
    if result:
        print(f"Training completed with R2 score: {result['metrics']['test_r2']:.4f}")
        print(f"Feature importance: {result['feature_importance']}")
    
    # Monitor system
    dashboard = MonitoringDashboard(pipeline.redis_client)
    metrics = await dashboard.get_system_metrics()
    print(f"System metrics: {json.dumps(metrics, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())