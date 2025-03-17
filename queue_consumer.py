import redis
from sqlalchemy.orm import Session
from database import SessionLocal, Case
from services.queue_manager import QueueManager
from crud.doctors import update_doctor
import logging
import time
import os
from redis.lock import Lock
from datetime import datetime
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

class CaseQueueConsumer:
    def __init__(self):
        self.redis_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        self.redis_client = redis.Redis(connection_pool=self.redis_pool)
        self.db = SessionLocal()
        self.queue_manager = QueueManager(self.db)
        self.lock_timeout = 10  
        self.lock_blocking_timeout = 1  
    def process_case(self, case_id: str, hospital_id: str):
        lock_key = f"case_lock:{case_id}"
        lock = Lock(self.redis_client, lock_key, timeout=self.lock_timeout)
        try:  
            if lock.acquire(blocking_timeout=self.lock_blocking_timeout):
                try:
                    case = self.db.query(Case).filter(Case.case_id == case_id).first()
                    if not case:
                        logger.error(f"Case {case_id} not found in database")
                        return
                    if case.status != "pending":
                        logger.info(f"Case {case_id} already processed")
                        return
                    
                    doctor = self.queue_manager.find_best_doctor(case)
                    if doctor:
                        
                        case.status = "assigned"
                        case.assigned_doctor_id = doctor.doctor_id
                        case.last_updated = datetime.now()
                        doctor.availability = False
                        doctor.current_workload += 1                        
                        self.redis_client.zrem(f"hospital_queue:{hospital_id}", case_id)
                        self.db.commit()
                        logger.info(f"Case {case_id} assigned to doctor {doctor.doctor_id}")
                    else:
                        logger.warning(f"No available doctors for case {case_id}")
                finally:
                    lock.release()
            else:
                logger.info(f"Could not acquire lock for case {case_id}, skipping...")
        except Exception as e:
            logger.error(f"Error processing case {case_id}: {str(e)}")
            logger.error(f"Traceback -{traceback.format_exc()}")
            self.db.rollback()
            if lock.locked():
                lock.release()

    def run(self):
        while True:
            try:
                
                keys = self.redis_client.keys("hospital_queue:*")
                for key in keys:
                    hospital_id = key.decode().split(":")[1]
                    
                    case_id = self.redis_client.zrange(key, 0, 0)[0]
                    if case_id:
                        case_id = case_id.decode()
                        self.process_case(case_id, hospital_id)
                
                time.sleep(1)
            except redis.RedisError as e:
                logger.error(f"Redis error: {str(e)}")
                time.sleep(5)  
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                time.sleep(1)

if __name__ == "__main__":
    consumer = CaseQueueConsumer()
    logger.info("Starting case queue consumer...")
    consumer.run()