from fastapi import APIRouter, Request, Form, status, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals
from typing import Optional
from app.helpers.researchers_funcs import get_researcher_data
from app.helpers.researcher_profile_funcs import get_researcher_profile

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Home page
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {"request": request}
    )

# Researcher level ranking page
@router.get("/researchers", response_class=HTMLResponse)
def researchers(request: Request):
    researcher_list, variable_label, sort_by = get_researcher_data(request)
    return templates.TemplateResponse(
        "researchers.html",
        {"request": request, "researchers": researcher_list, "variable_label": variable_label, "sort_by": sort_by}
    )

# Researcher profile/detail page
@router.get("/researchers/{researcher_id}", response_class=HTMLResponse)
def researcher_profile(request: Request, researcher_id: int = Path(...)):
    researcher_data, pub_list = get_researcher_profile(researcher_id)
    return templates.TemplateResponse(
        "researcher_profile.html",
        {"request": request, "researcher": researcher_data, "publications": pub_list},
    )

@router.get("/universities", response_class=HTMLResponse)
def universities(request: Request):
    return templates.TemplateResponse(
        "universities.html",
        {"request": request}
    )

@router.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    user = request.session.get("user")
    if not user:
        # Not logged in, redirect to login or show error
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("admin.html", {"request": request, "user": user})

@router.post("/login")
def login_post(request: Request):
    # TODO: replace with real auth
    request.session["user"] = "yuanji.wen"
    return templates.TemplateResponse(
        "admin.html",
        {"request": request}
    )

@router.get("/logout")
def logout_get(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/", status_code=303)

# # ------------------------
# # Signup
# # ------------------------
# @router.get("/signup", response_class=HTMLResponse)
# async def signup_get(request: Request, error: Optional[str] = None, message: Optional[str] = None):
#     return templates.TemplateResponse("sign_up.html", {"request": request, "error": error, "message": message})

# @router.post("/signup")
# async def signup_post(
#     request: Request,
#     name: str = Form(...),
#     email: str = Form(...),
#     password: str = Form(...),
#     confirm_password: str = Form(...),
# ):
#     if password != confirm_password:
#         return templates.TemplateResponse(
#             "sign_up.html",
#             {"request": request, "error": "Passwords do not match."},
#             status_code=status.HTTP_400_BAD_REQUEST,
#         )
#     # TODO: create user in DB here
#     return templates.TemplateResponse(
#         "Login.html",
#         {"request": request, "message": "Signup successful. Please log in."},
#     )

# # ------------------------
# # Reset password
# # ------------------------
# @router.get("/reset_password", response_class=HTMLResponse)
# async def reset_password_get(request: Request, error: Optional[str] = None, message: Optional[str] = None):
#     return templates.TemplateResponse("reset_password.html", {"request": request, "error": error, "message": message})

# @router.post("/reset_password")
# async def reset_password_post(request: Request, email: str = Form(...)):
#     # TODO: send real email with token
#     return templates.TemplateResponse(
#         "reset_password.html",
#         {"request": request, "message": f"If {email} exists, a reset link has been sent."},
#     )
