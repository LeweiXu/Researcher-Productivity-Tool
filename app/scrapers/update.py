from app.scrapers.UWA_Scraper import scrape_UWA
from app.scrapers.MU_Scraper import scrape_MU
from app.scrapers.ANU_Scraper import scrape_ANU
from app.scrapers.UNSW_Scraper import scrape_UNSW
from app.scrapers.UA_Scraper import scrape_UA
from app.scrapers.UQ_Scraper import scrape_UQ
from app.scrapers.UM_Scraper import scrape_UM
from app.scrapers.USYD_Scraper import scrape_USYD
from app.scrapers.helpers.util import write_to_db, match_journals

def update_all(db=True, match=True, progress_callback=None):
    """
    Runs all university scrapers sequentially and calls a callback function 
    to report progress after each one.
    """
    scrapers = [
        # update_UWA, # Temporarily ignored as requested due to issues
        update_MU,
        update_ANU,
        update_UNSW,
        update_UA,
        update_UQ,
        update_UM,
        update_USYD
    ]
    total_scrapers = len(scrapers)
    
    # Handle case where no scrapers are listed
    if total_scrapers == 0 and progress_callback:
        progress_callback(100)
        return

    for i, scraper_func in enumerate(scrapers):
        try:
            print(f"--- Running scraper: {scraper_func.__name__} ---")
            scraper_func(db, match)
        except Exception as e:
            # Print error but continue to the next scraper
            print(f"!!! Error in {scraper_func.__name__}: {e} !!!")
        finally:
            # This block is GUARANTEED to run, ensuring progress is always updated.
            if progress_callback:
                progress = int(((i + 1) / total_scrapers) * 100)
                progress_callback(progress)

def update_UWA(db=True, match=True):
    scrape_UWA()
    if db: write_to_db("UWA")
    if match: match_journals(university="UWA")

def update_MU(db=True, match=True):
    scrape_MU()
    if db: write_to_db("MU")
    if match: match_journals(university="MU")

def update_ANU(db=True, match=True):
    scrape_ANU()
    if db: write_to_db("ANU")
    if match: match_journals(university="ANU")

def update_UNSW(db=True, match=True):
    scrape_UNSW()
    if db: write_to_db("UNSW")
    if match: match_journals(university="UNSW")

def update_UA(db=True, match=True):
    scrape_UA()
    if db: write_to_db("UA")
    if match: match_journals(university="UA")

def update_UQ(db=True, match=True):
    scrape_UQ()
    if db: write_to_db("UQ")
    if match: match_journals(university="UQ")
    
def update_UM(db=True, match=True):
    scrape_UM()
    if db: write_to_db("UM")
    if match: match_journals(university="UM")

def update_USYD(db=True, match=True):
    scrape_USYD()
    if db: write_to_db("USYD")
    if match: match_journals(university="USYD")

if __name__ == "__main__":
    update_ANU()
