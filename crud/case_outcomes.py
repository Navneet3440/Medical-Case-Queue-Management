from typing import Optional, List
from sqlalchemy.orm import Session
from database import CaseOutcome

def create_case_outcome(db: Session, case_outcome: CaseOutcome) -> CaseOutcome:
    """
    Create a new case outcome.
    
    Args:
        db: SQLAlchemy database session
        case_outcome: CaseOutcome object to create
        
    Returns:
        The created CaseOutcome object
    """
    db.add(case_outcome)
    db.commit()
    db.refresh(case_outcome)
    return case_outcome

def get_case_outcome(db: Session, case_id: str) -> Optional[CaseOutcome]:
    """
    Get a case outcome by case ID.
    
    Args:
        db: SQLAlchemy database session
        case_id: ID of the case to get outcome for
        
    Returns:
        The CaseOutcome object if found, None otherwise
    """
    return db.query(CaseOutcome).filter(CaseOutcome.case_id == case_id).first()

def update_case_outcome(db: Session, case_id: str, case_outcome: CaseOutcome) -> Optional[CaseOutcome]:
    """
    Update an existing case outcome.
    
    Args:
        db: SQLAlchemy database session
        case_id: ID of the case to update
        case_outcome: CaseOutcome object with updated data
        
    Returns:
        The updated CaseOutcome object if found, None otherwise
    """
    db_case_outcome = db.query(CaseOutcome).filter(CaseOutcome.case_id == case_id).first()
    if db_case_outcome:
        for key, value in case_outcome.__dict__.items():
            if value is not None:
                setattr(db_case_outcome, key, value)
        db.commit()
        db.refresh(db_case_outcome)
        return db_case_outcome
    return None

def delete_case_outcome(db: Session, case_id: str) -> bool:
    """
    Delete a case outcome.
    
    Args:
        db: SQLAlchemy database session
        case_id: ID of the case to delete outcome for
        
    Returns:
        True if the outcome was deleted, False otherwise
    """
    db_case_outcome = db.query(CaseOutcome).filter(CaseOutcome.case_id == case_id).first()
    if db_case_outcome:
        db.delete(db_case_outcome)
        db.commit()
        return True
    return False

def get_all_case_outcomes(db: Session, skip: int = 0, limit: int = 100) -> List[CaseOutcome]:
    """
    Get all case outcomes with pagination.
    
    Args:
        db: SQLAlchemy database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of CaseOutcome objects
    """
    return db.query(CaseOutcome).offset(skip).limit(limit).all()
