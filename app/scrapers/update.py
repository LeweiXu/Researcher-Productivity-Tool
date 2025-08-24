from app.scrapers.UWA_Scraper import scrape_UWA
from app.scrapers.MU_Scraper import scrape_MU
from app.scrapers.ANU_Scraper import scrape_ANU
from app.scrapers.UNSW_Scraper import scrape_UNSW
from app.scrapers.UA_Scraper import scrape_UA
from app.scrapers.UQ_Scraper import scrape_UQ
from app.scrapers.UM_Scraper import scrape_UM
from app.scrapers.USYD_Scraper import scrape_USYD
from app.scrapers.helpers.shared_functions import write_to_csv, write_to_db
from app.scrapers.helpers.shared_functions import match_journals
from app.scrapers.helpers.util import standardize, import_from_csv

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

def update_USYD(csv=True, db=True, match=True):
    USYD_data = scrape_USYD()
    standardize(USYD_data)
    if csv: write_to_csv(USYD_data, "app/files/USYD_data.csv")
    if db: write_to_db(USYD_data, "USYD")
    if match: match_journals(university="USYD")

if __name__ == "__main__":
    # update_UM(csv=True, db=True, match=True)
    update_UM(csv=True, db=True, match=True)