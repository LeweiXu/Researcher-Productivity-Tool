from fastapi import FastAPI
from app.routes import router
from app.database import Base, engine
from app import models

# create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(router)
