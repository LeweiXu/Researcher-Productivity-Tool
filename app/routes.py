from fastapi import APIRouter, Request, Form, status, Path
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals
from typing import Optional
from app.helpers.researchers_funcs import get_researcher_data
from app.helpers.researcher_profile_funcs import get_researcher_profile
from app.helpers.universities_funcs import get_university_data

import csv
import io
import sys
import datetime
import threading
import traceback
from contextlib import redirect_stdout
from app.scrapers import update as scraper_update

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# --- New Global State Variable with 'logs' key ---
# This dictionary now holds logs in addition to progress and messages.
scraper_status_data = {"progress": 0, "message": "Not started", "logs": []}

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
# Documentation page
# ------------------------
@router.get("/documentation", response_class=HTMLResponse)
def documentation(request: Request):
    return templates.TemplateResponse(
        "documentation.html",
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
    university_list, variable_label = get_university_data(request)

    ranked = competition_rank(
        sorted(university_list, key=lambda u: u.get("variable_value") or 0, reverse=True),
        value_fn=lambda u: u.get("variable_value") or 0
    )
    universities_with_rank = [{**u, "rank": rk} for rk, u in ranked]

    return templates.TemplateResponse(
        "universities.html",
        {
            "request": request,
            "universities": universities_with_rank,
            "variable_label": variable_label
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
# ------------------------
# Scraper Endpoints
# ------------------------


class FrontendLogHandler(io.StringIO):
    """
    A custom stream handler that captures print statements
    and appends them to our global status dictionary's log list.
    """
    def write(self, s):
        global scraper_status_data
        line = s.strip()
        if line:
            scraper_status_data["logs"].append(line)
        # Also write to the actual stdout to see logs in the terminal
        sys.__stdout__.write(s)
        sys.__stdout__.flush()


def run_scraper_task():
    """
    This function runs in a separate thread and uses the FrontendLogHandler
    to capture all print outputs.
    """
    global scraper_status_data
    scraper_status_data['progress'] = 0
    scraper_status_data['message'] = 'Scraping started...'
    scraper_status_data['logs'] = [] # Reset logs for a new run
    
    log_capture = FrontendLogHandler()
    
    try:
        # Redirect all standard output within this block to our handler
        with redirect_stdout(log_capture):
            scraper_update.update_all(progress_callback=update_progress)
        
        if scraper_status_data.get('progress') != -1:
             scraper_status_data['message'] = 'Completed successfully!'

    except Exception as e:
        # Capture any exceptions as well
        error_message = traceback.format_exc()
        scraper_status_data['logs'].append(error_message)
        scraper_status_data['progress'] = -1
        scraper_status_data['message'] = f"An error occurred: {e}"

def update_progress(progress):
    """Callback function to update the global progress status."""
    global scraper_status_data
    scraper_status_data['progress'] = progress

@router.post("/admin/run-scraper")
async def run_scraper(request: Request):
    """Endpoint to start the scraper thread."""
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/", status_code=303)
    
    if any("run_scraper_task" in t.name for t in threading.enumerate()):
        return JSONResponse(content={"message": "Scraper is already running."}, status_code=409)

    global scraper_status_data
    scraper_status_data = {"progress": 0, "message": "Not started", "logs": []}
    
    thread = threading.Thread(target=run_scraper_task, name="run_scraper_task")
    thread.start()
    
    return JSONResponse(content={"message": "Scraper started"})

@router.get("/admin/scraper-status")
async def scraper_status(request: Request):
    """Endpoint for the frontend to poll for scraper progress and logs."""
    global scraper_status_data
    return JSONResponse(content=scraper_status_data)

