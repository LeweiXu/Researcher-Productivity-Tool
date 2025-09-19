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

#------------------------
# Helper function
#------------------------
def competition_rank(sorted_rows, value_fn):
    out = []
    prev = object()
    rank = 0
    for i, row in enumerate(sorted_rows, start=1):
        val = value_fn(row) or 0
        if val != prev:
            rank = i
            prev = val
        out.append((rank, row))
    return out


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
    
    researcher_list = sorted(
        researcher_list,
        key=lambda d: d.get("variable_value") or 0,
        reverse=True
    )

    ranked = competition_rank(
        researcher_list,
        value_fn=lambda d: d.get("variable_value") or 0
    )
    researchers_with_rank = [{**d, "rank": rk} for rk, d in ranked]

    return templates.TemplateResponse(
        "researchers.html",
        {
            "request": request,
            "researchers": researchers_with_rank, 
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
    db = SessionLocal()

    # Optional sorting: allow ?sort_by=accounting_count|finance_count|total_researchers (default total_researchers)
    sort_by = request.query_params.get("sort_by", "total_researchers")
    sort_col_map = {
        "accounting_count": "accounting_count",
        "finance_count": "finance_count",
        "total_researchers": "total_researchers",
    }

    # Build aggregated query
    qry = (
        db.query(
            Researchers.university.label("name"),
            func.count(Researchers.id).label("total_researchers"),
            func.sum(case((Researchers.field == "Accounting", 1), else_=0)).label("accounting_count"),
            func.sum(case((Researchers.field == "Finance", 1), else_=0)).label("finance_count"),
        )
        .group_by(Researchers.university)
    )

    rows = qry.all()
    db.close()

    # Sort in Python based on the chosen column (descending)
    key_name = sort_col_map.get(sort_by, "total_researchers")
    universities_data = sorted(rows, key=lambda r: getattr(r, key_name) or 0, reverse=True)

    
    ranked = competition_rank(universities_data, value_fn=lambda r: getattr(r, key_name) or 0)
    universities_with_rank = [
        {
            "rank": rk,
            "name": r.name,
            "accounting_count": r.accounting_count,
            "finance_count": r.finance_count,
        }
        for rk, r in ranked
    ]

    return templates.TemplateResponse(
        "universities.html",
        {
            "request": request,
            "universities": universities_with_rank, 
            "variable_label": "Researchers by Field"
        }
    )


# ------------------------
# Admin page
# ------------------------
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
    """
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/", status_code=303)

    db: Session = SessionLocal()

    # Query join across three tables
    qry = (
        db.query(
            Researchers.id.label("researcher_id"),
            Researchers.name.label("researcher_name"),
            Researchers.university,
            Researchers.field,
            Researchers.level,
            Publications.id.label("publication_id"),
            Publications.title.label("publication_title"),
            Publications.year.label("publication_year"),
            Journals.id.label("journal_id"),
            Journals.name.label("journal_name"),
            Journals.abdc_rank.label("journal_rank"),
        )
        .join(Publications, Publications.researcher_id == Researchers.id)
        .join(Journals, Journals.id == Publications.journal_id)
    )

    # Define header
    header = [
        "researcher_id", "researcher_name", "university", "field", "level",
        "publication_id", "publication_title", "publication_year",
        "journal_id", "journal_name", "journal_rank"
    ]

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
