from fastapi import FastAPI
from app.routes import router
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base  # Import Base from database.py
from app import models  # Import models to register them with Base

# --- DATABASE SETUP ---
DATABASE_URL = "sqlite:///app/test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base.metadata.create_all(bind=engine)

# --- FASTAPI APP ---
app = FastAPI()
app.include_router(router)