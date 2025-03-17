import redis
import os
from datetime import timedelta
from redis.connection import ConnectionPool
from redis.lock import Lock
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from database import Hospital, Patient, Case, CaseOutcome, Doctor
from models.models import HospitalPolicy, PatientProfile, HospitalPolicyUpdate, DoctorProfile
from ml.model_manager import ModelManager
import logging
from crud.hospitals import *
from crud.cases import *
from crud.doctors import *
from crud.patients import *
from crud.case_outcomes import *
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

class QueueManager:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.redis_pool = ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        self.redis_client = redis.Redis(connection_pool=self.redis_pool)
        self.model_manager = ModelManager()

    def add_hospital(self, policy: HospitalPolicy):
        hospital = Hospital(**policy.model_dump())
        create_hospital(self.db, hospital)
        

    def get_hospital(self, hospital_id: str):
        return get_hospital(self.db, hospital_id)

    def add_case(self, patient: PatientProfile, hospital_id: str):
        db_patient = Patient(
            patient_id=patient.patient_id,
            age=patient.age,
            gender=patient.gender,
            medical_history=patient.medical_history,
            symptoms=patient.symptoms,
            urgency_level=patient.urgency_level,
            preferred_doctor=patient.preferred_doctor,
            arrival_time=patient.arrival_time
        )
        create_patient(self.db, db_patient)

        sla_minutes = self.db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first().sla_rules.get(patient.urgency_level.value, 120)
        sla_deadline =datetime.now() + timedelta(minutes=sla_minutes)
        db_case = Case(
            case_id=f"case_{datetime.now().timestamp()}_{uuid.uuid4()}",
            hospital_id=hospital_id,
            patient_id=patient.patient_id,
            status="pending",
            priority_score=0.0,
            created_at=datetime.now(),
            sla_deadline=sla_deadline
        )
        case = create_case(self.db, db_case)

        try:
            score = sla_deadline.timestamp()
            self.redis_client.zadd(f"hospital_queue:{hospital_id}", {db_case.case_id: score})
            return case
        except redis.RedisError as e:
            logger.error(f"Redis error: {str(e)}")
            return None

    def update_doctor_availability(self, hospital_id: str, doctor_id: str, available: bool):
        doctor = self.db.query(Doctor).filter(Doctor.id == doctor_id, Doctor.hospital_id == hospital_id).first()
        if doctor:
            doctor.availability = available
            self.db.commit()

    def assign_next_case(self, hospital_id: str) -> Optional[Case]:
        try:
            case_id = self.redis_client.zrange(f"hospital_queue:{hospital_id}", 0, 0)[0]
        except redis.RedisError as e:
            logger.error(f"Redis error: {str(e)}")
            return None

        if not case_id:
            return None

        case_id = case_id.decode('utf-8')
        case = self.db.query(Case).filter(Case.id == case_id).first()
        doctor = self.find_best_doctor(case)
        if doctor:
            case.assigned_doctor_id = doctor.id
            case.status = "assigned"
            case.last_updated = datetime.now()
            doctor.current_workload += 1
            self.db.commit()
            try:
                self.redis_client.zrem(f"hospital_queue:{hospital_id}", case_id)
            except redis.RedisError as e:
                logger.error(f"Redis error: {str(e)}")
            return case
        return None

    def find_best_doctor(self, case: Case) -> Optional[Doctor]:
        available_doctors = self.db.query(Doctor).filter(
            Doctor.hospital_id == case.hospital_id,
            Doctor.availability == True,
            Doctor.current_workload < Doctor.max_daily_cases
        ).all()

        if not available_doctors:
            return None

        best_doctor = max(available_doctors, key=lambda doc: self.calculate_doctor_score(doc, case))
        return best_doctor
    

    def calculate_doctor_score(self, doctor: Doctor, case: Case) -> float:
        score = (0.5 * (doctor.experience_years / 20) + 0.3 * doctor.patient_rating)
        if doctor.success_rate:
            score += 0.2 * doctor.success_rate
        if any(tag in case.patient.symptoms for tag in doctor.specialization_tags):
            score *= 1.2
        #TODO Extract feature and call model to get ml score
        workload_ratio = doctor.current_workload / doctor.max_daily_cases
        score *= (1 - workload_ratio)
        return score

    def record_case_outcome(self, outcome: CaseOutcome):
        create_case_outcome(self.db, outcome)

    def update_hospital(self, hospital_id: str, policy: HospitalPolicyUpdate):
        hospital_data = {
            "name": policy.name,
            "sla_rules": policy.sla_rules,
            "max_cases_per_specialist": policy.max_cases_per_specialist,
            "max_cases_per_general": policy.max_cases_per_general,
            "working_hours": policy.working_hours
        }
        hospital = update_hospital(self.db, hospital_id, hospital_data)
        if policy.sla_rules is not None:
            self.update_queue_priorities(hospital_id)
    
    def delete_hospital(self, hospital_id):
        return delete_hospital(self.db, hospital_id)

    def register_doctor(self, doctor: DoctorProfile) -> Doctor:

        doctor_data = Doctor(**doctor.model_dump())
        return create_doctor(self.db, doctor_data)


    def update_queue_priorities(self, hospital_id: str):    
        lock_key = f"queue_update_lock:{hospital_id}"
        lock = Lock(self.redis_client, lock_key, timeout=10)
        
        try:
            if lock.acquire(blocking_timeout=1):
                try:
                    with self.db.begin():
                        cases = self.db.query(Case).filter(
                            Case.hospital_id == hospital_id,
                            Case.status == "pending"
                        ).all()
                        
                        hospital = self.db.query(Hospital).filter(
                            Hospital.hospital_id == hospital_id
                        ).first()
                        if not hospital:
                            raise ValueError(f"Hospital {hospital_id} not found")
                        
                        queue_key = f"hospital_queue:{hospital_id}"
                        self.redis_client.delete(queue_key)
                    
                        for case in cases:
                            sla_minutes = hospital.sla_rules.get(case.patient.urgency_level, 120)
                            sla_deadline = case.created_at + timedelta(minutes=sla_minutes)
                            score = sla_deadline.timestamp()
                            self.redis_client.zadd(queue_key, {case.case_id: score})
                        
                        logger.info(f"Re-prioritized queue for hospital {hospital_id}")
                finally:
                    lock.release()
            else:
                logger.warning(f"Could not acquire lock for queue update on hospital {hospital_id}")
                
        except Exception as e:
            logger.error(f"Error updating queue priorities for hospital {hospital_id}: {str(e)}")
            if lock.locked():
                lock.release()
            raise

    def predict(self, features):
        try:
            if not self.model_manager.validate_model():
                raise Exception('Model is not loaded or trained')
            return self.model_manager.get_model().predict(features)
        except Exception as e:
            logger.error(f'Prediction error: {str(e)}')
            raise

    def extract_feature(self, case_id):
        #TODO Extract feature of patient and Doctor
        pass