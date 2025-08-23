from app.scrapers.UWA_Scraper import scrape_UWA
from app.scrapers.MU_Scraper import scrape_MU
from app.scrapers.ANU_Scraper import scrape_ANU
from app.scrapers.UNSW_Scraper import scrape_UNSW
from app.scrapers.UA_Scraper import scrape_UA
from app.scrapers.UQ_Scraper import scrape_UQ
from app.scrapers.UM_Scraper import scrape_UM
from app.scrapers.helpers.shared_functions import write_to_csv, write_to_db
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

def update_all(csv=True, db=True, match=True):
    update_UWA(csv, db, match)
    update_MU(csv, db, match)
    update_ANU(csv, db, match)
    update_UNSW(csv, db, match)
    update_UA(csv, db, match)
    update_UQ(csv, db, match)
    update_UM(csv, db, match)

def update_UWA(csv=True, db=True, match=True):
    UWA_data = scrape_UWA()
    standardize(UWA_data)
    if csv: write_to_csv(UWA_data, "app/files/UWA_data.csv")
    if db: write_to_db(UWA_data, "UWA")
    if match: match_journals(university="UWA")

def update_MU(csv=True, db=True, match=True):
    MU_data = scrape_MU()
    standardize(MU_data)
    if csv: write_to_csv(MU_data, "app/files/MU_data.csv")
    if db: write_to_db(MU_data, "MU")
    if match: match_journals(university="MU")

def update_ANU(csv=True, db=True, match=True):
    ANU_data = scrape_ANU()
    standardize(ANU_data)
    if csv: write_to_csv(ANU_data, "app/files/ANU_data.csv")
    if db: write_to_db(ANU_data, "ANU")
    if match: match_journals(university="ANU")

def update_UNSW(csv=True, db=True, match=True):
    UNSW_data = scrape_UNSW()
    standardize(UNSW_data)
    if csv: write_to_csv(UNSW_data, "app/files/UNSW_data.csv")
    if db: write_to_db(UNSW_data, "UNSW")
    if match: match_journals(university="UNSW")

def update_UA(csv=True, db=True, match=True):
    UA_data = scrape_UA()
    standardize(UA_data)
    if csv: write_to_csv(UA_data, "app/files/UA_data.csv")
    if db: write_to_db(UA_data, "UA")
    if match: match_journals(university="UA")

def update_UQ(csv=True, db=True, match=True):
    UQ_data = scrape_UQ()
    standardize(UQ_data)
    if csv: write_to_csv(UQ_data, "app/files/UQ_data.csv")
    if db: write_to_db(UQ_data, "UQ")
    if match: match_journals(university="UQ")
    
def update_UM(csv=True, db=True, match=True):
    UM_data = scrape_UM()
    standardize(UM_data)
    if csv: write_to_csv(UM_data, "app/files/UM_data.csv")
    if db: write_to_db(UM_data, "UM")
    if match: match_journals(university="UM")

def import_from_csv(university, csv_path):
    all_data = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_data.append([
                row["Title"],
                row["Year"],
                row["Type"],
                row["Journal Name"],
                row["Article URL"],
                row["Researcher Name"],
                row["Profile URL"]
            ])

    standardize(all_data)
    write_to_db(all_data, university)
    match_journals(university=university)

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

if __name__ == "__main__":
    re_standardize()