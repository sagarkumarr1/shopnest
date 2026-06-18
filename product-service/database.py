from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'sqlite:///./product_db.sqlite3'
)

# 1. Engine create kiya
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite ke liye zaroori hai
)

# 2. SessionLocal ko define kiya (Yeh aapke code mein miss tha)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Base class ko define kiya (Isi ki wajah se main.py mein ImportError tha)
Base = declarative_base()

# 4. DB Dependency function
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
