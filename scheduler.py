from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from database import SessionLocal, Doctor

def reset_current_workload():
    db: Session = SessionLocal()
    try:
        db.query(Doctor).update({Doctor.current_workload: 0})
        db.commit()
        print("Current workload reset to 0 for all doctors")
    except Exception as e:
        db.rollback()
        print(f"Error resetting workload: {e}")
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(reset_current_workload, 'cron', hour=0)
    scheduler.start()
    print("Scheduler started...")


# if __name__ == '__main__':
#     reset_current_workload()