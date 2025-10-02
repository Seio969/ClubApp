from database.session import engine
from database.models import Base

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Base de datos inicializada correctamente.")

if __name__ == "__main__":
    init_db()
