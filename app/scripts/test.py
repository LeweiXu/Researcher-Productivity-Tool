import os
import csv
import random
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals
from app.scrapers.helpers.util import standardize

CSV_DIR = "app/files"
CSV_SUFFIX = "_data.csv"
SAMPLE_SIZE = 200

def populate_test_db():
    db = SessionLocal()
    try:
        for filename in os.listdir(CSV_DIR):
            if filename.endswith(CSV_SUFFIX):
                filepath = os.path.join(CSV_DIR, filename)
                with open(filepath, newline='', encoding='utf-8') as f:
                    reader = list(csv.reader(f))
                    header, rows = reader[0], reader[1:]
                    standardize(rows)
                    if len(rows) == 0:
                        continue
                    sample = random.sample(rows, min(SAMPLE_SIZE, len(rows)))
                    for row in sample:
                        title, year, type_val, journal, publication_url, name, profile_url = row[:7]
                        # Get or create researcher
                        researcher = db.query(Researchers).filter_by(name=name, profile_url=profile_url).first()
                        if not researcher:
                            researcher = Researchers(name=name, university=filename.split('_')[0], profile_url=profile_url)
                            db.add(researcher)
                            db.commit()
                            db.refresh(researcher)
                        # Add publication if not exists
                        db_publication = db.query(Publications).filter_by(title=title, publication_url=publication_url).first()
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
        print("Test database populated with random samples from each university CSV.")
    finally:
        db.close()

def populate_journal_test_metrics():
    db = SessionLocal()
    try:
        journals = db.query(Journals).all()
        for journal in journals:
            journal.h_index = random.randint(10, 100)
            journal.impact_factor = round(random.uniform(0, 10), 2)
        db.commit()
        print("Populated h_index and impact_factor with test data for all journals.")
    finally:
        db.close()

def main():
    populate_test_db()
    populate_journal_test_metrics()

if __name__ == "__main__":
    main()