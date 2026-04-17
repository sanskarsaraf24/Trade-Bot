from database.session import engine
from database.models import Base
import logging
import sys
import os

# Add the current directory to path so it can find database module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset():
    logger.info("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database reset complete!")

if __name__ == "__main__":
    reset()
