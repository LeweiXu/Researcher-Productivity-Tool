from fastapi import APIRouter, Request
from fastapi import Path
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def read_root():
    # Get ranking as a list of tuples
    db_ranking = []
    db = SessionLocal()
    try:
        # Main ranking: researchers with at least one matched journal article
        results = (
            db.query(
                Researchers.name,
                Researchers.university,
                Researchers.profile_url,
                func.count(Publications.id).label('abdc_count')
            )
            .join(Publications, Researchers.id == Publications.researcher_id)
            .join(Journals, Publications.journal_id == Journals.id)
            .filter(Publications.journal_id.isnot(None))
            .group_by(Researchers.id)
            .order_by(func.count(Publications.id).desc())
            .all()
        )
        db_ranking = results
        # Researchers with no journal article output (no Publications with journal_id)
        subq = db.query(Publications.researcher_id).filter(Publications.journal_id.isnot(None)).distinct()
        no_output = (
            db.query(Researchers.name, Researchers.university, Researchers.profile_url)
            .filter(~Researchers.id.in_(subq))
            .all()
        )
    finally:
        if db:
            db.close()
    html = "<h1>Welcome to the G8 Research Portal</h1>"
    html += "<h2>Researcher ABDC Journal Article Ranking:</h2><ol>"
    for row in db_ranking:
        html += f"<li>{row.name} ({row.university}) - {row.abdc_count} ABDC journal articles</li>"
    for row in no_output:
        html += f"<li>{row.name} ({row.university}) - 0 ABDC journal articles</li>"
    html += "</ol>"
    return html


@router.get("/home", response_class=HTMLResponse)
def home(request: Request):
    universities = [
        {
            "name": "The University of Melbourne",
            "desc": "A leading research university in Melbourne, Victoria.",
            "img": "https://about.unimelb.edu.au/__data/assets/image/0021/408504/230428_UOM_Campus-0130-copy.jpg",
            "logo": "https://universitiesaustralia.edu.au/wp-content/uploads/2019/05/UoM_Logo_Vert_Housed_RGB-1.jpg"
        },
        {
            "name": "The Australian National University",
            "desc": "A leading research university in Canberra, Australia.",
            "img": "https://www.uvic.ca/international-experiences/_assets/images/content-main/australian-national-university.jpg",
            "logo": "https://usercontent.one/wp/studyoptions.com/wp-content/uploads/2021/07/Logo-ANU.jpg"
        },
        {
            "name": "The University of Sydney",
            "desc": "A leading research university in Sydney, New South Wales.",
            "img": "https://offloadmedia.feverup.com/secretsydney.com/wp-content/uploads/2024/03/14121456/University-of-Sydney-Eriksson-Luo-Unsplash-1.jpg",
            "logo": "https://usercontent.one/wp/studyoptions.com/wp-content/uploads/2021/09/USydLogo-1.jpg"
        },
        {
            "name": "The University of Queensland",
            "desc": "A leading research university in Brisbane, Queensland.",
            "img": "https://www.uq.edu.au/sites/default/files/styles/uqds_card/public/2023-12/st-lucia-campus.jpg?itok=39nkzdMY",
            "logo": "https://cdn.prod.website-files.com/678e6d991abe09b73901f4e2/67b84906e9d57bd0aa0d7373_uqlogo.webp"
        },
        {
            "name": "The University of New South Wales",
            "desc": "A leading research university in Sydney, New South Wales.",
            "img": "https://www.ncuk.ac.uk/wp-content/uploads/2020/11/University-of-New-South-Wales-UNSW-Sydney-Image-Gallery-3.jpg",
            "logo": "https://www.mollerinstitute.com/wp-content/uploads/2024/04/University-of-New-South-Wales-Logo-565x565.png"
        },
        {
            "name": "Monash University",
            "desc": "A leading research university in Melbourne, Victoria.",
            "img": "https://www.usnews.com/object/image/00000153-ec2c-d802-ab7f-feacb9230000/160406-monashu-submitted.jpg?update-time=1459956316556&size=responsiveFlow970",
            "logo": "https://usercontent.one/wp/studyoptions.com/wp-content/uploads/2021/09/MonashLogo.jpg"
        },
        {
            "name": "The University of Western Australia",
            "desc": "A leading research university in Perth, Western Australia.",
            "img": "https://www.uwa.edu.au/seek-wisdom/-/media/project/uwa/uwa/winthrop-hall---seekers-space-banner.jpg?w=1440&hash=AEF28B0F77A0D2F84887B24A48875055",
            "logo": "https://coursera-university-assets.s3.amazonaws.com/fa/e5fc20724e11e5bf36bff635f1f3bb/UWA-Full-Ver-CMYK3.png"
        },
        {
            "name": "The University of Adelaide",
            "desc": "A leading research university in Adelaide, South Australia.",
            "img": "https://www.adelaide.edu.au/about/_jcr_content/root/container/container/container/column_0/teaser.coreimg.jpeg/1707460811850/08077-uoa.jpeg",
            "logo": "https://courseseeker.edu.au/assets/images/institutions/3010.png"
        }
    ]
    return templates.TemplateResponse("home.html", {"request": request, "universities": universities})


@router.get("/researchers", response_class=HTMLResponse, name="researcher_list")
def researcher_list(request: Request):
    # Dummy data for demonstration; replace with DB query later
    researchers = [
        {"id": "nicole-ang", "name": "Nicole Ang"},
        {"id": "lee-smales", "name": "Lee Smales"}
    ]
    return templates.TemplateResponse("researcher_list.html", {"request": request, "researchers": researchers})


@router.get("/researcher/{researcher_id}", response_class=HTMLResponse, name="researcher_profile")
def researcher_profile(request: Request, researcher_id: str = Path(...)):
    # Dummy data for demonstration; replace with DB query later
    researcher_data = {
        "nicole-ang": {
            "name": "Nicole Ang",
            "level": "Senior Lecturer",
            "department": "Department of Finance"
        },
        "lee-smales": {
            "name": "Lee Smales",
            "level": "Associate Professor",
            "department": "Department of Accounting"
        }
    }
    res = researcher_data.get(researcher_id, None)
    if not res:
        return HTMLResponse(content="Researcher not found", status_code=404)
    publications = [
        {"title": "Finance in Australia", "journal": "Journal of Finance", "year": 2022, "ranking": "A*", "h_index": 12},
        {"title": "Economics Today", "journal": "Economic Review", "year": 2021, "ranking": "A", "h_index": 10},
        {"title": "A Comprehensive Study of Market Trends", "journal": "Journal of Economic Perspectives", "year": 2023, "ranking": "C", "h_index": 5}
    ]
    return templates.TemplateResponse("researcher.html", {"request": request, "researcher": res, "publications": publications})
