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
    flash = request.session.pop("flash", None)
    if not user:
        # Not logged in, redirect to login or show error
        return templates.TemplateResponse("login.html", {"request": request, "error": None})
    return templates.TemplateResponse("admin.html", {"request": request, "user": user, "flash": flash})


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
