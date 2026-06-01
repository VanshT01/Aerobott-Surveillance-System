# connect fastapi to Postgres

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BACKEND_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)    # database connection

SessionLocal = sessionmaker(    # creates database sessions
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()   # used by SQLAlchemy models


def get_db():   # gives each API request its own database session.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
