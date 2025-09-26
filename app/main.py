# app/main.py
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from app.routes import router
from app.database import Base, engine
from app import models  # Ensure models are imported so tables are created
from starlette.middleware.sessions import SessionMiddleware

# --- DB setup ---
Base.metadata.create_all(bind=engine)

# Templates (if you want to use them globally)
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["url_for"] = lambda name, **params: app.url_path_for(name, **params)

# --- App ---
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")
app.include_router(router)

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)