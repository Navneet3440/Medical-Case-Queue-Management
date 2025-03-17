from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum
import os
import datetime


POSTGRES_USER = os.getenv("POSTGRES_USER", "navneetkumar")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "medical_queue")

SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"


engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UrgencyLevelEnum(str, enum.Enum):
    EMERGENCY = "emergency"
    URGENT = "urgent"
    ROUTINE = "routine"

class Hospital(Base):
    __tablename__ = "hospitals"

    hospital_id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    sla_rules = Column(JSON)
    max_cases_per_specialist = Column(Integer)
    max_cases_per_general = Column(Integer)
    working_hours = Column(JSON)

    doctors = relationship("Doctor", back_populates="hospital")
    cases = relationship("Case", back_populates="hospital")

class Doctor(Base):
    __tablename__ = "doctors"

    doctor_id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    specialty = Column(String)
    hospital_id = Column(String, ForeignKey("hospitals.hospital_id"))
    availability = Column(Boolean, default=True)
    working_hours = Column(JSON)
    current_workload = Column(Integer, default=0)
    max_daily_cases = Column(Integer)
    experience_years = Column(Integer)
    patient_rating = Column(Float)
    specialization_tags = Column(JSON)
    success_rate = Column(Float)

    hospital = relationship("Hospital", back_populates="doctors")
    assigned_cases = relationship("Case", back_populates="assigned_doctor")

class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String, primary_key=True, index=True)
    age = Column(Integer)
    gender = Column(String)
    medical_history = Column(JSON)
    symptoms = Column(JSON)
    urgency_level = Column(Enum(UrgencyLevelEnum))
    preferred_doctor = Column(String, nullable=True)
    preferred_hospital = Column(String, nullable=True)
    arrival_time = Column(DateTime)
    triage_score = Column(Float, nullable=True)

    cases = relationship("Case", back_populates="patient")

class Case(Base):
    __tablename__ = "cases"

    case_id = Column(String, primary_key=True, index=True)
    hospital_id = Column(String, ForeignKey("hospitals.hospital_id"))
    patient_id = Column(String, ForeignKey("patients.patient_id"))
    assigned_doctor_id = Column(String, ForeignKey("doctors.doctor_id"), nullable=True)
    status = Column(String, default="pending")
    priority_score = Column(Float, default=0.0)
    ml_priority_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    last_updated = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))
    sla_deadline = Column(DateTime)
    assignment_history = Column(JSON, default=list)
    predicted_duration = Column(Float, nullable=True)
    complexity_score = Column(Float, nullable=True)

    hospital = relationship("Hospital", back_populates="cases")
    patient = relationship("Patient", back_populates="cases")
    assigned_doctor = relationship("Doctor", back_populates="assigned_cases")
    outcome = relationship("CaseOutcome", back_populates="case", uselist=False)

class CaseOutcome(Base):
    __tablename__ = "case_outcomes"

    id = Column(String, primary_key=True, index=True)
    case_id = Column(String, ForeignKey("cases.case_id"))
    final_status = Column(String)
    actual_duration = Column(Float)
    patient_satisfaction = Column(Float, nullable=True)
    was_reassigned = Column(Boolean)
    met_sla = Column(Boolean)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))

    case = relationship("Case", back_populates="outcome")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base.metadata.create_all(bind=engine)
