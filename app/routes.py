from fastapi import APIRouter, Request, Path, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
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
import threading
import shutil
import os
import time
import importlib

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
        return templates.TemplateResponse("login.html", {"request": request, "error": None})
    return templates.TemplateResponse("admin.html", {"request": request, "user": user})

@router.post("/login")
async def login_post(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    # Only allow yuanji.wen with the correct password
    if username == "yuanji.wen" and password == "Group18BestGroup":
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

def abdc_upload_workflow(file_path, new_db_path, old_db_path):
    import stat
    # Ensure the new DB file is writable
    os.chmod(new_db_path, stat.S_IWRITE | stat.S_IREAD)
    # Set DB_URL before importing anything that uses SessionLocal/engine
    os.environ["DB_URL"] = f"sqlite:///{new_db_path}"

    # Reload database and dependent modules to pick up new DB_URL
    import app.database
    importlib.reload(app.database)
    import app.helpers.admin_funcs
    importlib.reload(app.helpers.admin_funcs)
    import app.scripts.CSV_imports
    importlib.reload(app.scripts.CSV_imports)
    import app.scrapers.helpers.util
    importlib.reload(app.scrapers.helpers.util)

    try:
        # Now call the functions using the reloaded modules
        app.helpers.admin_funcs.replace_ABDC_rankings(file_path)
        app.scripts.CSV_imports.import_all_jif()
        app.scrapers.helpers.util.match_journals(force=True, university="UA")
    except Exception as e:
        print(f"Error during ABDC workflow: {e}")
    finally:
        import gc
        gc.collect()
        try:
            os.chmod(new_db_path, stat.S_IWRITE | stat.S_IREAD)
            shutil.move(new_db_path, old_db_path)
            print(f"Database replaced: {old_db_path}")
        except Exception as e:
            print(f"Error replacing DB: {e}")

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
    old_db_path = "app/W8.db"
    new_db_path = "app/W8_temp.db"
    shutil.copyfile(old_db_path, new_db_path)
    # Set permissions for the new DB file
    import stat
    os.chmod(new_db_path, stat.S_IWRITE | stat.S_IREAD)
    thread = threading.Thread(target=abdc_upload_workflow, args=(file_path, new_db_path, old_db_path))
    thread.start()
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user": request.session.get("user"),
            "success": f"File '{abdc_csv.filename}' uploaded. Processing started in background on a copy of the database."
        }
    )
