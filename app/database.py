# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import json

with open("config.json") as config_file:
    config = json.load(config_file)
    db_path = config["DB_URL"]

DB_URL = os.environ.get("DB_URL", db_path)  # <- use the real DB

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()
