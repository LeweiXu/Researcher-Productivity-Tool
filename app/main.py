from typing import Optional

from fastapi import FastAPI, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.routes import router
from app.database import Base, engine
from app import models  # noqa: F401  # ensure models are imported so tables are created

# --- DB setup ---
Base.metadata.create_all(bind=engine)

# --- App ---
app = FastAPI()

# Templates
templates = Jinja2Templates(directory="app/templates")

# Make url_for available directly in Jinja (so you can use {{ url_for('endpoint') }})
templates.env.globals["url_for"] = lambda name, **params: app.url_path_for(name, **params)

# Redirect root -> /login
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url=app.url_path_for("login_get"), status_code=status.HTTP_307_TEMPORARY_REDIRECT)

# Keep your existing API routes (if any) from app.routes
app.include_router(router)

# ------------------------
# Pages / Auth flows
# ------------------------

# Home page (example data)
@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    universities = [
        {
            "name": "The University of Melbourne",
            "desc": "Melbourne, VIC.",
            "img": "https://images.unsplash.com/photo-1504805572947-34fad45aed93",
            "logo": "https://upload.wikimedia.org/wikipedia/en/8/81/University_of_Melbourne_coat_of_arms.svg",
        },
        {
            "name": "The Australian National University",
            "desc": "Canberra, ACT.",
            "img": "https://images.unsplash.com/photo-1580789346132-30a2b497bb7a",
            "logo": "https://upload.wikimedia.org/wikipedia/en/7/7b/Australian_National_University_coat_of_arms.svg",
        },
        {
            "name": "The University of Sydney",
            "desc": "Sydney, NSW.",
            "img": "https://images.unsplash.com/photo-1543248939-a60ef9c6c413",
            "logo": "https://upload.wikimedia.org/wikipedia/en/1/12/University_of_Sydney_coat_of_arms.svg",
        },
        {
            "name": "The University of Queensland",
            "desc": "Brisbane, QLD.",
            "img": "https://images.unsplash.com/photo-1586401100295-7a809a2a2b9b",
            "logo": "https://upload.wikimedia.org/wikipedia/en/8/88/University_of_Queensland_coat_of_arms.svg",
        },
        {
            "name": "UNSW Sydney",
            "desc": "Sydney, NSW.",
            "img": "https://images.unsplash.com/photo-1507842217343-583bb7270b66",
            "logo": "https://upload.wikimedia.org/wikipedia/en/2/2b/UNSW_Coat_of_Arms.svg",
        },
        {
            "name": "Monash University",
            "desc": "Melbourne, VIC.",
            "img": "https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d",
            "logo": "https://upload.wikimedia.org/wikipedia/en/d/d1/Monash_University_Coat_of_Arms.svg",
        },
        {
            "name": "The University of Adelaide",
            "desc": "Adelaide, SA.",
            "img": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1",
            "logo": "https://upload.wikimedia.org/wikipedia/en/1/10/University_of_Adelaide_coat_of_arms.svg",
        },
        {
            "name": "The University of Western Australia",
            "desc": "Perth, WA.",
            "img": "https://images.unsplash.com/photo-1580128637393-47b5f3bbce6d",
            "logo": "https://upload.wikimedia.org/wikipedia/en/0/02/University_of_Western_Australia_coat_of_arms.svg",
        },
    ]
    return templates.TemplateResponse("home.html", {"request": request, "universities": universities})

# ------------------------
# Login
# ------------------------
@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, error: Optional[str] = None, message: Optional[str] = None):
    return templates.TemplateResponse("Login.html", {"request": request, "error": error, "message": message})

@app.post("/login")
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember: bool = Form(False),
):
    # TODO: replace with real auth
    if email == "admin@example.com" and password == "admin123":
        return RedirectResponse(url=app.url_path_for("home"), status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "Login.html",
        {"request": request, "error": "Invalid email or password."},
        status_code=status.HTTP_400_BAD_REQUEST,
    )

# ------------------------
# Signup
# ------------------------
@app.get("/signup", response_class=HTMLResponse)
async def signup_get(request: Request, error: Optional[str] = None, message: Optional[str] = None):
    return templates.TemplateResponse("sign_up.html", {"request": request, "error": error, "message": message})

@app.post("/signup")
async def signup_post(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    if password != confirm_password:
        return templates.TemplateResponse(
            "sign_up.html",
            {"request": request, "error": "Passwords do not match."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    # TODO: create user in DB here
    return templates.TemplateResponse(
        "Login.html",
        {"request": request, "message": "Signup successful. Please log in."},
    )

# ------------------------
# Reset password
# ------------------------
@app.get("/reset_password", response_class=HTMLResponse)
async def reset_password_get(request: Request, error: Optional[str] = None, message: Optional[str] = None):
    return templates.TemplateResponse("reset_password.html", {"request": request, "error": error, "message": message})

@app.post("/reset_password")
async def reset_password_post(request: Request, email: str = Form(...)):
    # TODO: send real email with token
    return templates.TemplateResponse(
        "reset_password.html",
        {"request": request, "message": f"If {email} exists, a reset link has been sent."},
    )
