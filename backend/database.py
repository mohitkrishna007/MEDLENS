import os
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Determine writable database path for Vercel / serverless environments
default_db = "sqlite:///./medlens.db"
if os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or not os.access(".", os.W_OK):
    tmp_db_path = os.path.join(tempfile.gettempdir(), "medlens.db")
    default_db = f"sqlite:///{tmp_db_path}"

DB_PATH = os.getenv("DATABASE_URL", default_db)

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
