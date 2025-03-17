from typing import Optional, List
from sqlalchemy.orm import Session
from database import Case

def create_case(db: Session, case: Case) -> Case:
    db.add(case)
    db.commit()
    db.refresh(case)
    return case

def get_case(db: Session, case_id: str) -> Optional[Case]:
    return db.query(Case).filter(Case.case_id == case_id).first()

def update_case(db: Session, case_id: str, case_data: dict) -> Optional[Case]:
    case = get_case(db, case_id)
    if case:
        for key, value in case_data.items():
            if value:
                setattr(case, key, value)
        db.commit()
        db.refresh(case)
    return case

def delete_case(db: Session, case_id: str) -> bool:
    case = get_case(db, case_id)
    if case:
        db.delete(case)
        db.commit()
        return True
    return False

def get_cases(db: Session, skip: int = 0, limit: int = 100) -> List[Case]:
    return db.query(Case).offset(skip).limit(limit).all()
