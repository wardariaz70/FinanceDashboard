from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Path to local SQLite file (creates finance.db if it doesn't exist)
DATABASE_URL = "sqlite:///./finance.db"

# 2. Setup SQLite engine (check_same_thread=False allows Streamlit multi-threading)
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. Create Session local for DB queries
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Base class for ORM models
Base = declarative_base()


# Helper function to get DB session in Streamlit app
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()