import os
import boto3
import logging
from contextlib import contextmanager
from filelock import FileLock
from sklearn.ensemble import RandomForestRegressor
from database import *
from enum import Enum
from sklearn.metrics import mean_squared_error, r2_score
from typing import Dict, Optional
from datetime import datetime
import joblib
from botocore.config import Config
from botocore.exceptions import NoCredentialsError, ClientError
import redis
from redis import Redis
from redis.connection import ConnectionPool
import tempfile

logger = logging.getLogger(__name__)

class UrgencyLevel(Enum):
    EMERGENCY = 1
    URGENT = 2
    ROUTINE = 3

class ModelManager:
    _instance = None
    _model_lock = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance.ml_model = None
            cls._instance.ml_model_trained = False
            cls._instance.ml_metrics = {}
            cls._instance.s3_bucket = os.getenv('S3_BUCKET_NAME', 'medical-case-queue-models')
            cls._instance.model_key_prefix = 'ml_models/'
            cls._instance.redis_pool = ConnectionPool(host='redis', port=6379, db=0)
            cls._instance.redis_client = Redis(connection_pool=cls._instance.redis_pool)
            cls._instance._initialize_model_lock()
        return cls._instance

    def _initialize_model_lock(self):
        if not self._model_lock:
            self._model_lock = self.redis_client.lock('model_loading_lock', timeout=300)
    
    @contextmanager
    def _distributed_lock(self):
        try:
            if self._model_lock.acquire(blocking=True):
                yield True
            else:
                yield False
        finally:
            self._model_lock.release()
    
    def load_model(self, version: Optional[str] = None) -> bool:
        with self._distributed_lock() as acquired:
            if not acquired:
                return False  
            try:
                if self.ml_model and (not version or version == self.get_model_version()):
                    return True

                model_key = f"{self.model_key_prefix}ml_model_v{version if version else 'latest'}.joblib"
                try:
                    s3 = boto3.client('s3')
                    with tempfile.NamedTemporaryFile() as temp_file:
                        s3.download_file(self.s3_bucket, model_key, temp_file.name)
                        self.ml_model = joblib.load(temp_file.name)
                        self.ml_model_trained = True
                        return True
                except Exception as e:
                    logger.error(f"Failed to load model: {str(e)}")
                    return False
                    
            except Exception as e:
                logger.error(f"Model loading error: {str(e)}")
                return False
    
    def get_model(self):
        return self.ml_model

    def save_model(self, version=None):
        if not self.ml_model_trained:
            return False

        model_key = f"{self.model_key_prefix}ml_model_v{version if version else 'latest'}.joblib"

        try:
            temp_model_path = '/tmp/ml_model.joblib'

            joblib.dump(self.ml_model, temp_model_path)

            s3 = boto3.client('s3')
            s3.upload_file(temp_model_path, self.s3_bucket, model_key)

            os.remove(temp_model_path)

            return True

        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            return False

    def train_ml_model(self) -> Dict:
        """Train the ML model with distributed locking"""
        with self._distributed_lock() as acquired:
            if not acquired:
                
                return self.ml_metrics

            completed_cases = self.db.query(Case).join(CaseOutcome).filter(Case.status == "completed").all()

            if len(completed_cases) < 50:
                return self.ml_metrics

            features = []
            targets = []
            feature_names = [
                'age', 'medical_history_count', 'symptoms_count',
                'is_emergency', 'is_urgent', 'is_routine',
                'wait_time_hours', 'complexity_score'
            ]

            for case in completed_cases:
                
                patient = self.db.query(Patient).filter(Patient.id == case.patient_id).first()
                features.append([
                    patient.age,
                    len(patient.medical_history),
                    len(patient.symptoms),
                    1 if patient.urgency_level == UrgencyLevel.EMERGENCY else 0,
                    1 if patient.urgency_level == UrgencyLevel.URGENT else 0,
                    1 if patient.urgency_level == UrgencyLevel.ROUTINE else 0,
                    (case.last_updated - case.created_at).total_seconds() / 3600,
                    case.complexity_score or 0
                ])
                outcome = self.db.query(CaseOutcome).filter(CaseOutcome.case_id == case.id).first()
                targets.append(outcome.actual_duration)

            split_idx = int(len(features) * 0.7)
            train_features = features[:split_idx]
            train_targets = targets[:split_idx]
            val_features = features[split_idx:]
            val_targets = targets[split_idx:]

            self.ml_model.fit(train_features, train_targets)
            self.ml_model_trained = True

            val_predictions = self.ml_model.predict(val_features)
            self.ml_metrics = {
                'mse': mean_squared_error(val_targets, val_predictions),
                'r2': r2_score(val_targets, val_predictions),
                'feature_importance': dict(zip(feature_names, self.ml_model.feature_importances_)),
                'last_trained': datetime.now().isoformat(),
                'training_size': len(features)
            }

            version = datetime.now().strftime("%Y%m%d%H%M%S")
            self.save_model(version)
            self.ml_metrics['version'] = version

            return self.ml_metrics

    def validate_model(self):
        """Validate the loaded model"""
        if not self.ml_model or not self.ml_model_trained:
            logger.warning('Model is not loaded or trained')
            return False
        return True

    def get_model_version(self) -> Optional[str]:
        """Get the currently loaded model version."""
        return self.ml_metrics.get('version')

    def is_model_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.ml_model is not None

    def __init__(self):
        try:
            self.s3_config = Config(
                retries={
                    'max_attempts': 3,
                    'mode': 'standard'
                }
            )
            self.s3_client = boto3.client('s3', config=self.s3_config)
            self.ml_model = RandomForestRegressor(n_estimators=100, random_state=42)
            logger.info('ModelManager initialized successfully')
        except Exception as e:
            logger.error(f'Error initializing ModelManager: {str(e)}')
            raise
