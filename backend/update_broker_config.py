from database.session import SessionLocal
from database.models import TradingConfiguration, User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update():
    db = SessionLocal()
    try:
        # Get or create admin user
        admin = db.query(User).filter(User.email == "admin@trade.system").first()
        if not admin:
            admin = User(email="admin@trade.system", hashed_password="dummy_password")
            db.add(admin)
            db.commit()
            db.refresh(admin)

        config = db.query(TradingConfiguration).filter(TradingConfiguration.user_id == admin.id).first()
        if not config:
            config = TradingConfiguration(user_id=admin.id)
            db.add(config)
        
        config.broker_type = "zerodha"
        config.broker_api_key = "hzte2aqce2ju4gdd"
        config.broker_api_secret = "mmd0u7brai56spm2ukyb6nzvjaotzxe7"
        # I will leave totp_secret for the user to paste in the UI or I can try to set it if they provided it.
        # They said "totp secrect verifu if its working" so they likely pasted it already in the UI? 
        # No, I reset the DB, so they have to paste it again.
        
        db.commit()
        logger.info("Zerodha credentials updated in Database successfully.")
    except Exception as e:
        logger.error(f"Failed to update DB: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update()
