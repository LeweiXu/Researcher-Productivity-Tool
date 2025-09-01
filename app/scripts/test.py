import os
import csv
import random
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals
from app.scrapers.helpers.util import standardize

# Columns to fill with test data: 
    # Researchers: job_title (Research Fellow, Lecturer, Senior Lecturer, Associate Professor, Professor), level (A, B, C, D, E)
    # Journals: JIF (Float value between 0-200), JIF_5_year (Float value between 0-200), citation_percentage (Float value between 0-100)
    # Publications: num_authors (Integer value)

def fill_test_columns():
    db = SessionLocal()
    try:
        # Researchers: job_title and level
        job_levels = [
            ("Research Fellow", "A"),
            ("Lecturer", "B"),
            ("Senior Lecturer", "C"),
            ("Associate Professor", "D"),
            ("Professor", "E"),
        ]
        researchers = db.query(Researchers).all()
        for r in researchers:
            job_title, level = random.choice(job_levels)
            r.job_title = job_title
            r.level = level
        # Journals: JIF, JIF_5_year, citation_percentage
        journals = db.query(Journals).all()
        for j in journals:
            j.JIF = round(random.uniform(0, 200), 2)
            j.JIF_5_year = round(random.uniform(0, 200), 2)
            j.citation_percentage = round(random.uniform(0, 100), 2)
        # Publications: num_authors
        publications = db.query(Publications).all()
        for p in publications:
            p.num_authors = random.randint(1, 10)
        db.commit()
        print("Filled test columns with random values.")
    finally:
        db.close()

def main():
    fill_test_columns()

if __name__ == "__main__":
    main()