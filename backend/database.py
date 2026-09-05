import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

def get_database_url():
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")
    
    # Check serverless environment (Vercel, AWS Lambda, etc.)
    is_serverless = os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
    if is_serverless:
        tmp_db_path = os.path.join(tempfile.gettempdir(), "medlens.db")
        return f"sqlite:///{tmp_db_path}"

    # Test writing to current directory
    try:
        test_file = "./.write_test"
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return "sqlite:///./medlens.db"
    except Exception:
        tmp_db_path = os.path.join(tempfile.gettempdir(), "medlens.db")
        return f"sqlite:///{tmp_db_path}"

DB_PATH = get_database_url()

# SQLite specific connect args for multithreading
connect_args = {"check_same_thread": False} if DB_PATH.startswith("sqlite") else {}

engine = create_engine(DB_PATH, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
