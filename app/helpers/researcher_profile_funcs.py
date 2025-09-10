from fastapi import Request
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals

def get_researcher_profile(researcher_id):    
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
                    "publication_url": pub.publication_url,
                    "journal": journal.name if journal else pub.journal_name,
                    "year": pub.year,
                    "ranking": journal.abdc_rank if journal else "",
                    "num_authors": pub.num_authors,
                }
            )

        researcher_data = {
            "name": researcher.name,
            "level": researcher.level,        # fill if you have this field
            "department": researcher.field,   # fill if you have this field
            "university": researcher.university,
            "profile_url": researcher.profile_url,
        }
        return researcher_data, pub_list
    finally:
        db.close()
