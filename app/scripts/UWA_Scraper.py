from app.main import SessionLocal
from app.models import Researchers, Publications
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import time
import csv
import datetime

def scrape_publications(profile_url, driver):
    """
    Finds publication info for a given researcher
    Returns: (name, publications_info) where publications_info is a list of [Title, Date, Type, Journal, Article URL]
    """
    driver.get(profile_url)
    time.sleep(2)
    # Try to get name robustly
    try:
        name = driver.find_element(By.CSS_SELECTOR, "h1.name").text.strip()
    except Exception:
        try:
            name = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
        except Exception:
            name = ""
    publications_info = []
    page = 0
    while True:
        page_url = f"{profile_url}/publications/?page={page}"
        driver.get(page_url)
        time.sleep(2)
        publication_divs = driver.find_elements(By.CSS_SELECTOR, "div.rendering_researchoutput_portal-short")
        if not publication_divs:
            break
        for div in publication_divs:
            # Title and URL
            try:
                a_tag = div.find_element(By.CSS_SELECTOR, "h3.title a")
                title = a_tag.text.strip()
                publication_url = a_tag.get_attribute("href")
            except Exception:
                title = ""
                publication_url = ""
            # Year
            try:
                date_span = div.find_element(By.CSS_SELECTOR, "span.date")
                year = date_span.text.strip()[-4:]
            except Exception:
                year = ""
            # Type
            try:
                type_span = div.find_element(By.CSS_SELECTOR, "span.type_classification_parent")
                type_val = type_span.text.strip()
                type_val = type_val[:-2]
            except Exception:
                type_val = ""
            # Journal
            try:
                if "Contribution to journal" in type_val:
                    journal_span = div.find_element(By.CSS_SELECTOR, "span.journal a span")
                    journal = journal_span.text.strip()[:-1] # Remove trailing full stop
                else:
                    journal = "N/A"
            except Exception:
                journal = "N/A"
            publications_info.append([title, year, type_val, journal, publication_url])
            print(f"Found publication: {title}")
        page += 1
    return name, publications_info

def find_profile_urls(page_url, driver):
    """Finds all researcher profile URLs on the page using Selenium by matching href prefix."""
    profile_urls = set()
    driver.get(page_url)
    time.sleep(2)
    a_tags = driver.find_elements(By.TAG_NAME, "a")
    for a in a_tags:
        href = a.get_attribute("href")
        if href and href.startswith("https://research-repository.uwa.edu.au/en/persons/"):
            profile_urls.add(href)
    return list(profile_urls)    

def write_to_csv(publications_info, name, profile_url, csv_filename):
    print("Writing scraped data to CSV")
    with open(csv_filename, mode="a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        for publication in publications_info:
            csv_write = publication.copy()
            csv_write.append(name)
            csv_write.append(profile_url)
            writer.writerow(csv_write)

def write_to_db(publications_info, name, profile_url):
    print("Writing scraped data to database")
    db = SessionLocal()
    try:
        # Check if researcher exists
        researcher = db.query(Researchers).filter_by(name=name, profile_url=profile_url).first()
        if not researcher:
            researcher = Researchers(name=name, university="UWA", profile_url=profile_url)
            db.add(researcher)
            db.commit()
            db.refresh(researcher)
        for publication in publications_info:
            title, year, type_val, journal, publication_url = publication
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
    finally:
        db.close()

def update():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--lang=en-US,en")
    # options.add_argument("--headless")  # Uncomment for headless mode
    driver = uc.Chrome(version_main=138, options=options)

    profile_urls = find_profile_urls("https://www.uwa.edu.au/schools/business/accounting-and-finance", driver)
    print(f"Found {len(profile_urls)} profile URLs")

    csv_header = ["Title", "Year", "Type", "Journal", "Article URL", "Researcher Name", "Profile URL"]
    csv_filename = "./app/files/UWA.csv"
    with open(csv_filename, mode="w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)

    for profile_url in profile_urls:
        print(f"Scraping profile: {profile_url}")
        time.sleep(5)
        name, publications_info = scrape_publications(profile_url, driver)
        print(f"Found {len(publications_info)} publications in {profile_url}")

        write_to_csv(publications_info, name, profile_url, csv_filename)
        write_to_db(publications_info, name, profile_url)

# Example usage:
if __name__ == "__main__":
    update()