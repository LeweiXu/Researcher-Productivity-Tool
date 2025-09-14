import csv
from app.database import SessionLocal
from app.models import Journals

CSV_PATH = "app/files/2022 JQL.csv"

def import_journals():
    db = SessionLocal()
    try:
        with open(CSV_PATH, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Journal Title", "").strip()
                publisher = row.get("Publisher", "").strip()
                ISSN = row.get("ISSN", "").strip()
                eISSN = row.get("ISSN Online", "").strip()
                year_of_inception = row.get("Year Inception", "")
                FoR = row.get("FoR", "")
                abdc_rank = row.get("2022 rating", "").strip()

                # Convert year_of_inception and FoR to int if possible
                try:
                    year_of_inception = int(year_of_inception) if year_of_inception else None
                except Exception:
                    year_of_inception = None
                try:
                    FoR = int(FoR) if FoR else None
                except Exception:
                    FoR = None

                # Check if journal already exists
                journal = db.query(Journals).filter_by(name=name).first()
                if not journal:
                    journal = Journals(
                        name=name,
                        publisher=publisher,
                        ISSN=ISSN,
                        eISSN=eISSN,
                        year_of_inception=year_of_inception,
                        FoR=FoR,
                        abdc_rank=abdc_rank
                    )
                    db.add(journal)
            db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    import_journals()