from fastapi import APIRouter, Request, Form, status, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals
from typing import Optional
from app.helpers.researchers_functions import get_researcher_data

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
    researcher_list, variable_label = get_researcher_data(request)
    return templates.TemplateResponse(
        "researchers.html",
        {"request": request, "researchers": researcher_list, "variable_label": variable_label}
    )

# Researcher profile/detail page
@router.get(
    "/researcher/{researcher_id}",
    response_class=HTMLResponse,
    name="researcher_profile",
)
def researcher_profile(request: Request, researcher_id: int = Path(...)):
    db = SessionLocal()
    try:
        researcher = (
            db.query(Researchers).filter(Researchers.id == researcher_id).first()
        )
        if not researcher:
            return HTMLResponse(content="Researcher not found", status_code=404)

        publications = (
            db.query(Publications, Journals)
            .outerjoin(Journals, Publications.journal_id == Journals.id)
            .filter(Publications.researcher_id == researcher_id)
            .all()
        )

        pub_list = []
        for pub, journal in publications:
            pub_list.append(
                {
                    "title": pub.title,
                    "journal": journal.name if journal else pub.journal_name,
                    "year": pub.year,
                    "ranking": journal.abdc_rank if journal else "",
                    "h_index": journal.h_index if journal else "",
                }
            )

        researcher_data = {
            "name": researcher.name,
            "level": "",        # fill if you have this field
            "department": "",   # fill if you have this field
            "university": researcher.university,
            "profile_url": researcher.profile_url,
        }
    finally:
        db.close()

    # Reuse researcher.html; ensure the template handles both list & detail modes
    return templates.TemplateResponse(
        "researcher.html",
        {"request": request, "researcher": researcher_data, "publications": pub_list},
    )

# @router.get("/login", response_class=HTMLResponse)
# async def login_get(request: Request, error: Optional[str] = None, message: Optional[str] = None):
#     return templates.TemplateResponse("Login.html", {"request": request, "error": error, "message": message})

# @router.post("/login")
# async def login_post(
#     request: Request,
#     email: str = Form(...),
#     password: str = Form(...),
#     remember: bool = Form(False),
# ):
#     # TODO: replace with real auth
#     if email == "admin@example.com" and password == "admin123":
#         return RedirectResponse(url=router.url_path_for("home"), status_code=status.HTTP_303_SEE_OTHER)
#     return templates.TemplateResponse(
#         "Login.html",
#         {"request": request, "error": "Invalid email or password."},
#         status_code=status.HTTP_400_BAD_REQUEST,
#     )

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
