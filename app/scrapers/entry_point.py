from app.scrapers.UWA_Scraper import scrape_UWA
from app.scrapers.MU_Scraper import scrape_MU
from app.scrapers.ANU_Scraper import scrape_ANU
from app.scrapers.UNSW_Scraper import scrape_UNSW
from app.scrapers.helpers.save_functions import write_to_csv, write_to_db
from app.scrapers.helpers.journal_matching import match_journals
import csv


def standardize(data):
    # Data returned from scrapers is raw data, need to standardize format 
    # E.g. (Publication Type --> "Journal Article", "Contribution to Journal" are the same thing)
    # E.g. (Researcher Name --> Strip Titles Dr, Proffessor etc.)
    pass

def update_all(csv=True, db=True, match=True):
    # Scrapers return a list of lists ["Title", "Year", "Type", "Journal Name", "Article URL", "Researcher Name", "Profile URL"]
    update_UWA(csv, db, match)
    update_MU(csv, db, match)
    update_ANU(csv, db, match)
    update_UNSW(csv, db, match)

def update_UWA(csv=True, db=True, match=True):
    UWA_data = scrape_UWA()
    standardize(UWA_data)
    if csv: write_to_csv(UWA_data, "app/files/UWA_data.csv")
    if db: write_to_db(UWA_data)
    if match: match_journals("UWA")

def update_MU(csv=True, db=True, match=True):
    MU_data = scrape_MU()
    standardize(MU_data)
    if csv: write_to_csv(MU_data, "app/files/MU_data.csv")
    if db: write_to_db(MU_data)
    if match: match_journals("MU")

def update_ANU(csv=True, db=True, match=True):
    ANU_data = scrape_ANU()
    standardize(ANU_data)
    if csv: write_to_csv(ANU_data, "app/files/ANU_data.csv")
    if db: write_to_db(ANU_data)
    if match: match_journals("ANU")

def update_UNSW(csv=True, db=True):
    UNSW_data = scrape_UNSW()
    standardize(UNSW_data)
    if csv: write_to_csv(UNSW_data, "app/files/UNSW_data.csv")
    if db: write_to_db(UNSW_data)
    match_journals("UNSW")

def import_from_csv(csv_path="app/files/all_data.csv"):
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
    write_to_db(all_data)
    match_journals()

if __name__ == "__main__":
    import_from_csv("app/files/UWA_data.csv")