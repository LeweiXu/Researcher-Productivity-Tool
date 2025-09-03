from fastapi import APIRouter, Request, Form, status, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "home.html", {"request": request},
    )

# # -------------------------------------------------------
# # Researchers list page (navbar points here: /researcher)
# # -------------------------------------------------------
# @router.get("/researcher", response_class=HTMLResponse, name="researcher")
# def researcher_list(request: Request):
#     db = SessionLocal()
#     try:
#         researchers = db.query(Researchers).all()
#         researcher_list = [{"id": str(r.id), "name": r.name} for r in researchers]
#     finally:
#         db.close()

#     return templates.TemplateResponse(
#         "researcher.html",
#         {"request": request, "researchers": researcher_list},
#     )


# # Optional alias so /researchers still works (hidden from docs)
# @router.get("/researchers", include_in_schema=False)
# def researchers_alias(request: Request):
#     return researcher_list(request)


# # -----------------------------------
# # Researcher profile/detail page
# # -----------------------------------
# @router.get(
#     "/researcher/{researcher_id}",
#     response_class=HTMLResponse,
#     name="researcher_profile",
# )
# def researcher_profile(request: Request, researcher_id: int = Path(...)):
#     db = SessionLocal()
#     try:
#         researcher = (
#             db.query(Researchers).filter(Researchers.id == researcher_id).first()
#         )
#         if not researcher:
#             return HTMLResponse(content="Researcher not found", status_code=404)

#         publications = (
#             db.query(Publications, Journals)
#             .outerjoin(Journals, Publications.journal_id == Journals.id)
#             .filter(Publications.researcher_id == researcher_id)
#             .all()
#         )

#         pub_list = []
#         for pub, journal in publications:
#             pub_list.append(
#                 {
#                     "title": pub.title,
#                     "journal": journal.name if journal else pub.journal_name,
#                     "year": pub.year,
#                     "ranking": journal.abdc_rank if journal else "",
#                     "h_index": journal.h_index if journal else "",
#                 }
#             )

#         researcher_data = {
#             "name": researcher.name,
#             "level": "",        # fill if you have this field
#             "department": "",   # fill if you have this field
#             "university": researcher.university,
#             "profile_url": researcher.profile_url,
#         }
#     finally:
#         db.close()

#     # Reuse researcher.html; ensure the template handles both list & detail modes
#     return templates.TemplateResponse(
#         "researcher.html",
#         {"request": request, "researcher": researcher_data, "publications": pub_list},
#     )


# # Redirect root -> /login
# @router.get("/", include_in_schema=False)
# async def root():
#     return RedirectResponse(url=router.url_path_for("login_get"), status_code=status.HTTP_307_TEMPORARY_REDIRECT)

# # Keep your existing API routes (if any) from router.routes
# router.include_router(router)

# # ------------------------
# # Pages / Auth flows
# # ------------------------

# # Home page (example data)
# @router.get("/home", response_class=HTMLResponse)
# async def home(request: Request):
#     universities = [
#         {
#             "name": "The University of Melbourne",
#             "desc": "Melbourne, VIC.",
#             "img": "https://images.unsplash.com/photo-1504805572947-34fad45aed93",
#             "logo": "https://upload.wikimedia.org/wikipedia/en/8/81/University_of_Melbourne_coat_of_arms.svg",
#         },
#         {
#             "name": "The Australian National University",
#             "desc": "Canberra, ACT.",
#             "img": "https://images.unsplash.com/photo-1580789346132-30a2b497bb7a",
#             "logo": "https://upload.wikimedia.org/wikipedia/en/7/7b/Australian_National_University_coat_of_arms.svg",
#         },
#         {
#             "name": "The University of Sydney",
#             "desc": "Sydney, NSW.",
#             "img": "https://images.unsplash.com/photo-1543248939-a60ef9c6c413",
#             "logo": "https://upload.wikimedia.org/wikipedia/en/1/12/University_of_Sydney_coat_of_arms.svg",
#         },
#         {
#             "name": "The University of Queensland",
#             "desc": "Brisbane, QLD.",
#             "img": "https://images.unsplash.com/photo-1586401100295-7a809a2a2b9b",
#             "logo": "https://upload.wikimedia.org/wikipedia/en/8/88/University_of_Queensland_coat_of_arms.svg",
#         },
#         {
#             "name": "UNSW Sydney",
#             "desc": "Sydney, NSW.",
#             "img": "https://images.unsplash.com/photo-1507842217343-583bb7270b66",
#             "logo": "https://upload.wikimedia.org/wikipedia/en/2/2b/UNSW_Coat_of_Arms.svg",
#         },
#         {
#             "name": "Monash University",
#             "desc": "Melbourne, VIC.",
#             "img": "https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d",
#             "logo": "https://upload.wikimedia.org/wikipedia/en/d/d1/Monash_University_Coat_of_Arms.svg",
#         },
#         {
#             "name": "The University of Adelaide",
#             "desc": "Adelaide, SA.",
#             "img": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1",
#             "logo": "https://upload.wikimedia.org/wikipedia/en/1/10/University_of_Adelaide_coat_of_arms.svg",
#         },
#         {
#             "name": "The University of Western Australia",
#             "desc": "Perth, WA.",
#             "img": "https://images.unsplash.com/photo-1580128637393-47b5f3bbce6d",
#             "logo": "https://upload.wikimedia.org/wikipedia/en/0/02/University_of_Western_Australia_coat_of_arms.svg",
#         },
#     ]
#     return templates.TemplateResponse("home.html", {"request": request, "universities": universities})

# # ------------------------
# # Login
# # ------------------------
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
