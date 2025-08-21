from app.database import SessionLocal
from app.models import Researchers, Publications
import csv


def write_to_csv(all_data, csv_filename):
    print("Writing scraped data to CSV")
    csv_header = ["Title", "Year", "Type", "Journal Name", "Article URL", "Researcher Name", "Profile URL"]
    with open(csv_filename, mode="w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)

    with open(csv_filename, mode="a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in all_data:
            csv_write = row
            writer.writerow(csv_write)

def write_to_db(all_data, university):
    print("Writing scraped data to database")
    db = SessionLocal()
    try:
        for row in all_data:
            title, year, type_val, journal, publication_url, name, profile_url = row
            # Don't add researcher if same Name and Profile URL
            researcher = db.query(Researchers).filter_by(name=name, profile_url=profile_url).first()
            if not researcher:
                researcher = Researchers(name=name, university=university, profile_url=profile_url)
                db.add(researcher)
                db.commit()
                db.refresh(researcher)
            # Don't add publication if same Title and Researcher
            db_publication = db.query(Publications).filter_by(title=title, researcher_id=researcher.id).first()
            if not db_publication:
                db_publication = Publications(
                    title=title,
                    year=year,
                    publication_type=type_val,
                    journal_name=journal,
                    publication_url=publication_url,
                    researcher_id=researcher.id
                )
                db.add(db_publication)
                db.commit()
                db.refresh(db_publication)
            # Link researcher and publication (if not already linked)
            if db_publication not in researcher.publication:
                researcher.publication.append(db_publication)
                db.commit()
    finally:
        db.close()
        print("Completed writing to database")