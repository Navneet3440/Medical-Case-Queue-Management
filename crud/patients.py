from typing import Optional, List
from sqlalchemy.orm import Session
from database import Patient

def create_patient(db: Session, patient: Patient) -> Patient:
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient

def get_patient(db: Session, patient_id: str) -> Optional[Patient]:
    return db.query(Patient).filter(Patient.patient_id == patient_id).first()

def update_patient(db: Session, patient_id: str, patient_data: dict) -> Optional[Patient]:
    patient = get_patient(db, patient_id)
    if patient:
        for key, value in patient_data.items():
            setattr(patient, key, value)
        db.commit()
        db.refresh(patient)
    return patient

def delete_patient(db: Session, patient_id: str) -> bool:
    patient = get_patient(db, patient_id)
    if patient:
        db.delete(patient)
        db.commit()
        return True
    return False

def get_patients(db: Session, skip: int = 0, limit: int = 100) -> List[Patient]:
    return db.query(Patient).offset(skip).limit(limit).all()
