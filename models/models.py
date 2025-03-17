from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class UrgencyLevel(str, Enum):
    EMERGENCY = "emergency"
    URGENT = "urgent"
    ROUTINE = "routine"

class HospitalPolicy(BaseModel):
    hospital_id: str
    name: str
    sla_rules: Dict[UrgencyLevel, int]  
    max_cases_per_specialist: int = 5
    max_cases_per_general: int = 6
    working_hours: Dict[str, str]  

class HospitalPolicyUpdate(BaseModel):
    name: Optional[str]
    sla_rules: Optional[Dict[str, int]] = None  
    max_cases_per_specialist: Optional[int] = None
    max_cases_per_general: Optional[int] = None
    working_hours: Optional[Dict[str, str]] = None 

class HospitalResponse(BaseModel):
    hospital_id: str
    name: str
    sla_rules: Dict[str, int]
    max_cases_per_specialist: int
    max_cases_per_general: int
    working_hours: Dict[str, str]

class PatientProfile(BaseModel):
    patient_id: str
    age: int
    gender: str
    medical_history: List[str]
    symptoms: List[str]
    urgency_level: UrgencyLevel
    preferred_doctor: Optional[str] = None
    arrival_time: datetime
    triage_score: Optional[float] = None

class PatientResponse(BaseModel):
    patient_id: str
    age: int
    gender: str
    medical_history: List[str]
    symptoms: List[str]
    urgency_level: UrgencyLevel
    preferred_doctor: Optional[str] = None
    arrival_time: datetime
    triage_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

class DoctorProfile(BaseModel):
    doctor_id: str
    name: str
    specialty: str
    hospital_id: str
    availability: bool = True
    working_hours: dict  
    current_workload: int
    max_daily_cases: int
    experience_years: int
    patient_rating: float
    specialization_tags: List[str] = []
    success_rate: Optional[float] = None

class DoctorResponse(BaseModel):
    doctor_id: str
    name: str
    specialty: str
    hospital_id: str
    availability: bool
    working_hours: Dict[str, str]
    current_workload: int
    max_daily_cases: int
    experience_years: int
    patient_rating: float
    specialization_tags: List[str] = []
    success_rate: Optional[float] = None

class Case(BaseModel):
    case_id: str
    hospital_id: str
    patient: PatientProfile
    assigned_doctor: Optional[DoctorProfile] = None
    status: str = "pending"
    priority_score: float = 0.0
    ml_priority_score: Optional[float] = None
    created_at: datetime
    last_updated: datetime
    sla_deadline: datetime
    assignment_history: List[Dict] = []
    predicted_duration: Optional[float] = None
    complexity_score: Optional[float] = None

class CaseResponse(BaseModel):
    case_id: str
    hospital_id: str
    patient_id: str
    assigned_doctor_id: Optional[str] = None
    status: str
    priority_score: float
    ml_priority_score: Optional[float] = None
    created_at: datetime
    last_updated: datetime
    sla_deadline: datetime
    assignment_history: List[Dict] = []
    predicted_duration: Optional[float] = None
    complexity_score: Optional[float] = None

class CaseOutcome(BaseModel):
    case_id: str
    final_status: str
    actual_duration: float
    patient_satisfaction: Optional[float]
    was_reassigned: bool
    met_sla: bool
    created_at: datetime

class CaseOutcomeResponse(BaseModel):
    id: str
    case_id: str
    final_status: str
    actual_duration: float
    patient_satisfaction: Optional[float] = None
    was_reassigned: bool
    met_sla: bool
    created_at: datetime
    updated_at: datetime
