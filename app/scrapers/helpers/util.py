from app.scrapers.helpers.shared_functions import write_to_db
from app.scrapers.helpers.shared_functions import match_journals
from app.database import SessionLocal
from app.models import Researchers, Publications
from sqlalchemy import text
import csv
import re
import os

CSV_DIR = "app/files"
csv_paths = [os.path.join(CSV_DIR, f) for f in os.listdir(CSV_DIR) if f.endswith("_data.csv")]

# NOTE: Scrapers return a list of lists in the format ["Title", "Year", "Type", "Journal Name", "Article URL", "Researcher Name", "Profile URL"]

def standardize(data):
    # Data returned from scrapers is raw data, need to standardize format 
    # E.g. (Publication Type --> "Journal Article", "Contribution to Journal" are the same thing)
    # E.g. (Researcher Name --> Strip Titles Dr, Professor etc.)
    title_pattern = re.compile(r"^(Dr\.?|Associate Professor|Professor|Ms\.?|Mr\.?|Mrs\.?|Lecturer|Prof\.?|EmPr|AsPr|Scientia Professor|Emeritus Professor)\s+", re.IGNORECASE)
    for row in data:
        for i, element in enumerate(row):
            if element == "":
                row[i] = None
        if len(row) > 5 and row[5]:
            row[5] = title_pattern.sub("", row[5]).strip()
        if len(row) > 2 and row[2]:
            type_val = row[2]
            if type_val[-2:] == ' ›':
                type_val = type_val[:-2]
            row[2] = type_val

# Run standardize() function on all CSV files, then rewrite to database
def re_standardize():
    db = SessionLocal()
    try:
        # Clear association table first
        db.execute(text('DELETE FROM Researcher_publication_association'))
        db.commit()
        # Clear Publications and Researchers
        db.query(Publications).delete()
        db.query(Researchers).delete()
        db.commit()
    finally:
        db.close()
        print("Successfully Removed All Data")

    for csv_path in csv_paths:
        university = csv_path.split("/")[-1].split("_")[0]  # Extract university name from file name
        print(f"Re-standardizing {csv_path}")
        # Read CSV
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            return
        print(f"Successfully read {csv_path}")
        header, data = rows[0], rows[1:]
        standardize(data)
        # Write back to same file
        with open(csv_path, mode="w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(data)
        print(f"Successfully wrote standardized data to {csv_path}")
        write_to_db(data, university)
        match_journals(university=university)