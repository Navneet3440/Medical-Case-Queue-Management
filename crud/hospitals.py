from typing import Optional, List
from sqlalchemy.orm import Session
from database import Hospital

def create_hospital(db: Session, hospital: Hospital) -> Hospital:
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return hospital

def get_hospital(db: Session, hospital_id: str) -> Optional[Hospital]:
    return db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()

def update_hospital(db: Session, hospital_id: str, hospital_data: dict) -> Optional[Hospital]:
    hospital = get_hospital(db, hospital_id)
    if hospital:
        for key, value in hospital_data.items():
            if value:
                setattr(hospital, key, value)
        db.commit()
        db.refresh(hospital)
    return hospital

def delete_hospital(db: Session, hospital_id: str) -> bool:
    hospital = get_hospital(db, hospital_id)
    if hospital:
        db.delete(hospital)
        db.commit()
        return True
    return False

def get_hospitals(db: Session, skip: int = 0, limit: int = 100) -> List[Hospital]:
    return db.query(Hospital).offset(skip).limit(limit).all()
