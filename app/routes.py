from fastapi import APIRouter, Request, Form, status, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals
from typing import Optional
from app.helpers.researchers_funcs import get_researcher_data
from app.helpers.researcher_profile_funcs import get_researcher_profile
from app.helpers.universities_funcs import get_university_data  # (unused now, but you can remove if you want)

import csv
import io
import datetime

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ------------------------
# Home page
# ------------------------
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


# ------------------------
# Researcher level ranking page
# ------------------------
@router.get("/researchers", response_class=HTMLResponse)
def researchers(request: Request):
    researcher_list, variable_label = get_researcher_data(request)
    return templates.TemplateResponse(
        "researchers.html",
        {
            "request": request,
            "researchers": researcher_list,
            "variable_label": variable_label
        }
    )


# ------------------------
# Researcher profile/detail page
# ------------------------
@router.get("/researchers/{researcher_id}", response_class=HTMLResponse)
def researcher_profile(request: Request, researcher_id: int = Path(...)):
    researcher_data, pub_list = get_researcher_profile(researcher_id)
    return templates.TemplateResponse(
        "researcher_profile.html",
        {"request": request, "researcher": researcher_data, "publications": pub_list},
    )


# ------------------------
# University ranking page (split researchers into Accounting vs Finance)
# ------------------------
@router.get("/universities", response_class=HTMLResponse)
def universities(request: Request):
    university_list, variable_label = get_university_data(request)
    return templates.TemplateResponse(
        "universities.html",
        {"request": request, "universities": university_list, "variable_label": variable_label},
    )

# ------------------------
# Admin page
# ------------------------
@router.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    user = request.session.get("user")
    if not user:
        # Not logged in, redirect to login or show error
        return templates.TemplateResponse("login.html", {"request": request, "error": None})
    return templates.TemplateResponse("admin.html", {"request": request, "user": user})


@router.post("/login")
def login_post(request: Request):
    # TODO: replace with real auth
    request.session["user"] = "yuanji.wen"
    return templates.TemplateResponse(
        "admin.html",
        {"request": request}
    )


@router.post("/logout")
def logout_post(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/", status_code=303)


# ------------------------
# Download Master Spreadsheet (Researchers + Publications + Journals)
# ------------------------
@router.get("/admin/download/researchers.csv")
def download_master_csv(request: Request):
    """
    Streams a master spreadsheet joining Researchers, Publications, and Journals.
    Each row = one publication of one researcher with its journal.
    All columns from all three tables are included.
    """
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/", status_code=303)

    db: Session = SessionLocal()

    # Get all columns for each table
    researcher_cols = [c.name for c in Researchers.__table__.columns]
    publication_cols = [c.name for c in Publications.__table__.columns]
    journal_cols = [c.name for c in Journals.__table__.columns]

    # Build query with all columns
    qry = (
        db.query(
            *[getattr(Publications, col) for col in publication_cols],
            *[getattr(Researchers, col) for col in researcher_cols],
            *[getattr(Journals, col) for col in journal_cols],
        )
        .join(Researchers, Publications.researcher_id == Researchers.id)
        .join(Journals, Publications.journal_id == Journals.id)
    )

    # Header: publication columns + researcher columns + journal columns
    header = publication_cols + researcher_cols + journal_cols

    def csv_iter():
        buf = io.StringIO()
        writer = csv.writer(buf)

        # header
        writer.writerow(header)
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)

        # rows
        for row in qry.yield_per(500):
            writer.writerow(row)
            yield buf.getvalue()
            buf.seek(0); buf.truncate(0)

        db.close()

    ts = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"master_spreadsheet_{ts}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(csv_iter(), media_type="text/csv", headers=headers)
    return StreamingResponse(csv_iter(), media_type="text/csv", headers=headers)
