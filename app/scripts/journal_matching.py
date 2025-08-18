from app.main import SessionLocal
from app.models import Publications, Journals
from fuzzywuzzy import process

def match_journals(threshold=95):
    db = SessionLocal()
    try:
        journals = db.query(Journals).all()
        journal_names = [j.name for j in journals]
        publications = db.query(Publications).all()
        for pub in publications:
            if not pub.journal_name:
                continue
            match, score = process.extractOne(pub.journal_name, journal_names)
            if score >= threshold:
                matched_journal = next((j for j in journals if j.name == match), None)
                if matched_journal:
                    pub.journal_id = matched_journal.id
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    match_journals()
