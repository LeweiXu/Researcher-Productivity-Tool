from fastapi import APIRouter, Request, Path, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from contextlib import redirect_stdout
from app.scrapers.update import update_all
from app.scrapers.helpers.util import match_journals
from app.scripts.CSV_imports import import_all_jif
from app.helpers.researchers_funcs import get_researcher_data
from app.helpers.researcher_profile_funcs import get_researcher_profile
from app.helpers.universities_funcs import get_university_data
from app.helpers.admin_funcs import (
    download_master_csv,
    download_ABDC_template,
    download_clarivate_template,
    download_UWA_staff_field_template,
    save_uploaded_file,
    replace_ABDC_rankings
)
from app.helpers.auth_funcs import authenticate_user

import io
import sys
import threading
import traceback

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
    flash = request.session.pop("flash", None)
    if not user:
        # Not logged in, redirect to login or show error
        return templates.TemplateResponse("login.html", {"request": request, "error": None})
    return templates.TemplateResponse("admin.html", {"request": request, "user": user, "flash": flash})


@router.post("/login")
async def login_post(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    if authenticate_user(username, password):
        request.session["user"] = username
        return templates.TemplateResponse(
            "admin.html",
            {"request": request, "user": username}
        )
    else:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password."}
        )


@router.post("/logout")
def logout_post(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/", status_code=303)


# ------------------------
# Admin Download Functionalities
# ------------------------
@router.get("/admin/download/researchers.csv")
def download_master_csv_route(request: Request):
    return download_master_csv(request)


@router.get("/admin/download/abdc_template.csv")
def abdc_template_route():
    return download_ABDC_template()


@router.get("/admin/download/clarivate_template.csv")
def clarivate_template_route():
    return download_clarivate_template()


@router.get("/admin/download/UWA_staff_field_template.csv")
def uwa_staff_field_template_route():
    return download_UWA_staff_field_template()

# ------------------------
# Admin Upload Functionalities
# ------------------------

@router.post("/admin/upload/abdc")
async def upload_abdc(
    request: Request,
    abdc_csv: UploadFile = File(None)
):
    if not abdc_csv:
        return templates.TemplateResponse(
            "admin.html",
            {"request": request, "user": request.session.get("user"), "error": "No file uploaded."}
        )
    file_path = save_uploaded_file(abdc_csv)
    # Flash message
    request.session["flash"] = (
        f"File '{abdc_csv.filename}' uploaded successfully.<br>"
        "The website will be temporarily unavailable while the CSV file is being processed."
    )
    replace_ABDC_rankings(file_path)
    import_all_jif()  # Re-import all JIF data to refresh journal matches
    match_journals(force=True)  # Re-match journals after ABDC update
    return RedirectResponse(url="/admin", status_code=303)


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
            update_all(progress_callback=update_progress)
        
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