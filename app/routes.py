from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals
router = APIRouter()

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