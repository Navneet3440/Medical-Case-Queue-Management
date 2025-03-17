from typing import Optional, List
from sqlalchemy.orm import Session
from database import Doctor
from apscheduler.schedulers.background import BackgroundScheduler

def create_doctor(db: Session, doctor: Doctor) -> Doctor:
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor

def get_doctor(db: Session, doctor_id: str) -> Optional[Doctor]:
    return db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()

def update_doctor(db: Session, doctor_id: str, doctor_data: dict) -> Optional[Doctor]:
    doctor = get_doctor(db, doctor_id)
    if doctor:
        for key, value in doctor_data.items():
            setattr(doctor, key, value)
        db.commit()
        db.refresh(doctor)
    return doctor

def delete_doctor(db: Session, doctor_id: str) -> bool:
    doctor = get_doctor(db, doctor_id)
    if doctor:
        db.delete(doctor)
        db.commit()
        return True
    return False

def get_doctors(db: Session, skip: int = 0, limit: int = 100) -> List[Doctor]:
    return db.query(Doctor).offset(skip).limit(limit).all()
