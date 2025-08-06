from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.routes import router
from app import models

# --- DATABASE SETUP ---
DATABASE_URL = "sqlite:///app/test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

Base.metadata.create_all(bind=engine)

# --- FASTAPI APP ---
app = FastAPI()
app.include_router(router)