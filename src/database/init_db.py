from database.session import engine
from database.models import Base
from utils.logger import get_logger
logger = get_logger(__name__)

def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Base de datos inicializada correctamente.")

if __name__ == "__main__":
    init_db()
