from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

TEST_DB_URL = "sqlite:///app/test.db"
ROLE_TEST_DB_URL = "sqlite:///app/roletest.db"
REAL_DB_URL = "sqlite:///app/final.db"

engine = create_engine(ROLE_TEST_DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()
