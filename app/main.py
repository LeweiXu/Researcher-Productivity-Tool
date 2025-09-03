# app/main.py
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from app.routes import router
from app.database import Base, engine
from app import models  # Ensure models are imported so tables are created

# --- DB setup ---
Base.metadata.create_all(bind=engine)

# --- App ---
app = FastAPI()

# Templates (if you want to use them globally)
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["url_for"] = lambda name, **params: app.url_path_for(name, **params)

# Include all routes from routes.py
app.include_router(router)