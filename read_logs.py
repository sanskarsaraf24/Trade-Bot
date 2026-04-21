from database.session import SessionLocal
from database.models import SystemLog
import json

db = SessionLocal()
try:
    logs = db.query(SystemLog).order_by(SystemLog.timestamp.desc()).limit(20).all()
    for log in logs:
        print(f"[{log.timestamp}] {log.level} | {log.event_type}: {log.message}")
finally:
    db.close()
