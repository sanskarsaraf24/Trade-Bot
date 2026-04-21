from database.session import SessionLocal
from database.models import SystemLog
import json
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

db = SessionLocal()
try:
    # Only look for errors or parsing issues
    logs = db.query(SystemLog).filter(
        (SystemLog.severity == 'error') | (SystemLog.event_type.like('%parsing%')) | (SystemLog.event_type.like('%claude%'))
    ).order_by(SystemLog.timestamp.desc()).limit(10).all()
    
    if not logs:
        print("No error logs found.")
    for log in logs:
        print(f"[{log.timestamp}] {log.severity} | {log.event_type}: {log.message}")
finally:
    db.close()
