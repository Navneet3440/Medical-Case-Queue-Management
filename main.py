from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import *
from models.models import *
from database import get_db
from services.queue_manager import QueueManager
from ml.model_manager import ModelManager
from crud.doctors import get_doctor, update_doctor, delete_doctor
from crud.cases import get_case, update_case, delete_case
from scheduler import start_scheduler
from typing import Optional, List


app = FastAPI(title="Medical Case Queue Management System")

@app.on_event("startup")
def on_startup():
    start_scheduler()

@app.post('/hospitals', response_model=HospitalResponse)
async def register_hospital_ep(policy: HospitalPolicy, db_session: Session = Depends(get_db)):
    queue_manager = QueueManager(db_session)
    queue_manager.add_hospital(policy)
    return policy

@app.get('/hospitals/{hospital_id}', response_model=HospitalResponse)
async def get_hospital_ep(hospital_id: str, db_session: Session = Depends(get_db)):
    queue_manager = QueueManager(db_session)
    hospital = queue_manager.get_hospital(hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return hospital

@app.put('/hospitals/{hospital_id}', response_model=HospitalResponse)
async def update_hospital_ep(hospital_id: str, policy: HospitalPolicyUpdate, db_session: Session = Depends(get_db)):
    queue_manager = QueueManager(db_session)
    policy = queue_manager.update_hospital(hospital_id, policy)
    return policy

@app.delete('/hospitals/{hospital_id}')
async def delete_hospital_ep(hospital_id: str, db_session: Session = Depends(get_db)):
    queue_manager = QueueManager(db_session)
    if not queue_manager.delete_hospital(hospital_id):
        raise HTTPException(status_code=404, detail="Hospital not found")
    return {"message": "Hospital deleted successfully"}


@app.post('/doctors', response_model=DoctorResponse)
async def register_doctor_ep(doctor: DoctorProfile, db_session: Session = Depends(get_db)):
    queue_manager = QueueManager(db_session)
    queue_manager.register_doctor(doctor)
    return doctor

@app.get('/doctors/{doctor_id}', response_model=DoctorResponse)
async def get_doctor_ep(doctor_id: str, db_session: Session = Depends(get_db)):
    doctor =  get_doctor(db_session, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

@app.put('/doctors/{doctor_id}', response_model=DoctorResponse)
async def update_doctor_ep(doctor_id: str, doctor_data: dict, db_session: Session = Depends(get_db)):
    doctor = update_doctor(db_session, doctor_id, doctor_data)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

@app.delete('/doctors/{doctor_id}')
async def delete_doctor_ep(doctor_id: str, db_session: Session = Depends(get_db)):
    if not delete_doctor(db_session, doctor_id):
        raise HTTPException(status_code=404, detail="Doctor not found")
    return {"message": "Doctor deleted successfully"}


@app.post('/cases/{hospital_id}', response_model=CaseResponse)
async def create_case_ep( hospital_id: str, patient: PatientProfile, db_session: Session = Depends(get_db)):
    queue_manager = QueueManager(db_session)
    case = queue_manager.add_case(patient, hospital_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not Queued")
    return case

@app.get('/cases/{case_id}', response_model=CaseResponse)
async def get_case_ep(case_id: str, db_session: Session = Depends(get_db)):
    case = get_case(db_session, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@app.put('/cases/{case_id}', response_model=CaseResponse)
async def update_case_ep(case_id: str, case_data: dict, db_session: Session = Depends(get_db)):
    case = update_case(db_session, case_id, case_data)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@app.delete('/cases/{case_id}')
async def delete_case_ep(case_id: str, db_session: Session = Depends(get_db)):
    case = get_case(db_session, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.assigned_doctor_id:
        raise HTTPException(status_code=400, detail="Case cannot be deleted as it is assigned to a doctor")
    if not delete_case(db_session, case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return {"message": "Case deleted successfully"}

@app.post('/cases/{case_id}/outcome')
async def record_case_outcome(case_id: str, outcome: CaseOutcome, db_session: Session = Depends(get_db)):
    queue_manager = QueueManager(db_session)
    queue_manager.record_case_outcome(outcome)
    return {"message": "Case outcome recorded successfully"}


@app.post('/ml/load')
async def load_ml_model(version: Optional[str] = None, db_session: Session = Depends(get_db)):
    """Load model with distributed locking to ensure only one pod loads the model at a time."""
    model_manager = ModelManager()
    success = model_manager.load_model(version)
    if not success:
        if model_manager.is_model_loaded():
            # Model is already loaded in another pod
            return {
                "success": True,
                "message": "Model is being loaded by another pod",
                "version": model_manager.get_model_version()
            }
        raise HTTPException(status_code=500, detail="Failed to load model")
    return {
        "success": True,
        "message": "Model loaded successfully",
        "version": model_manager.get_model_version()
    }

@app.post('/ml/train')
async def train_ml_model(db_session: Session = Depends(get_db)):
    model_manager = ModelManager()
    success = model_manager.train_ml_model()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to train model")
    return {"success": True, "message": "Model training started"}

# @app.get('/ml/versions')
# async def list_model_versions(db_session: Session = Depends(get_db)):
#     model_manager = ModelManager()
#     versions = model_manager.list_model_versions()
#     return {"versions": versions}


# @app.get('/analytics/{hospital_id}')
# async def get_hospital_analytics(hospital_id: str, db_session: Session = Depends(get_db)):
#     queue_manager = QueueManager(db_session)
#     analytics = queue_manager.get_hospital_analytics(hospital_id)
#     if not analytics:
#         raise HTTPException(status_code=404, detail="Hospital not found")
#     return analytics

# @app.get('/analytics/{hospital_id}/ml')
# async def get_ml_analytics(hospital_id: str, db_session: Session = Depends(get_db)):
#     queue_manager = QueueManager(db_session)
#     analytics = queue_manager.get_ml_analytics(hospital_id)
#     if not analytics:
#         raise HTTPException(status_code=404, detail="Hospital not found")
#     return analytics

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
