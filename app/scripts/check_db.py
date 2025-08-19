from app.database import SessionLocal
from app.models import Researchers, Publications, Journals

def main():
    db = SessionLocal()
    try:
        adl_researchers = db.query(Researchers).filter_by(university="University of Adelaide").count()
        adl_pubs = (
            db.query(Publications)
            .join(Researchers)
            .filter(Researchers.university == "University of Adelaide")
            .count()
        )
        matched = db.query(Publications).filter(Publications.journal_id.isnot(None)).count()

        print("Researchers (Adelaide):", adl_researchers)
        print("Publications (Adelaide):", adl_pubs)
        print("Matched Publications:", matched)
    finally:
        db.close()

if __name__ == "__main__":
    main()
