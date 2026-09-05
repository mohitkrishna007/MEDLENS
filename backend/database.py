import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./medlens.db")

# SQLite specific connect args for multithreading
connect_args = {"check_same_thread": False} if DB_PATH.startswith("sqlite") else {}

engine = create_engine(DB_PATH, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
