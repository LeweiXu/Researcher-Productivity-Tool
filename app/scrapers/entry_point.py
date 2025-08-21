from app.scrapers.UWA_Scraper import scrape_UWA
from app.scrapers.MU_Scraper import scrape_MU
from app.scrapers.ANU_Scraper import scrape_ANU
from app.scrapers.helpers.save_functions import write_to_csv, write_to_db
from app.scripts.journal_matching import match_journals
import csv

def standardize(all_data):
    pass

def update_all(csv=True, db=True):
    # Scrapers return a list of lists ["Title", "Year", "Type", "Journal Name", "Article URL", "Researcher Name", "Profile URL"]
    UWA_data = scrape_UWA()
    MU_data = scrape_MU()
    ANU_data = scrape_ANU()

    all_data = UWA_data + MU_data + ANU_data
    # Data returned from scrapers is raw data, need to standardize format 
    # E.g. (Publication Type --> "Journal Article", "Contribution to Journal" are the same thing)
    # E.g. (Researcher Name --> Strip Titles Dr, Proffessor etc.)
    standardize(all_data)

    if csv: write_to_csv(all_data, "app/files/all_data.csv")
    if db: write_to_db(all_data)

    # match journal name to ABDC rankings (populate Publications.journal ForeignKey)
    match_journals()

def update_UWA(csv=True, db=True):
    UWA_data = scrape_UWA()
    standardize(UWA_data)
    if csv: write_to_csv(UWA_data, "app/files/UWA_data.csv")
    if db: write_to_db(UWA_data)
    match_journals()

def import_from_csv(csv_path="app/files/all_data.csv"):
    all_data = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_data.append([
                row["Title"],
                row["Year"],
                row["Type"],
                row["Journal"],
                row["Article URL"],
                row["Researcher Name"],
                row["Profile URL"]
            ])

    standardize(all_data)
    write_to_db(all_data)
    match_journals()