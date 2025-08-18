from app.main import SessionLocal
from app.models import Researcher, Article
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import time
import csv
import datetime

def scrape_articles(profile_url, driver):
    """
    Finds article info for a given researcher
    Returns: (name, articles_info) where articles_info is a list of [Title, Date, Type, Journal, Article URL]
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
    articles_info = []
    page = 0
    while True:
        page_url = f"{profile_url}/publications/?page={page}"
        driver.get(page_url)
        time.sleep(2)
        article_divs = driver.find_elements(By.CSS_SELECTOR, "div.rendering_researchoutput_portal-short")
        if not article_divs:
            break
        for div in article_divs:
            # Title and URL
            try:
                a_tag = div.find_element(By.CSS_SELECTOR, "h3.title a")
                title = a_tag.text.strip()
                article_url = a_tag.get_attribute("href")
            except Exception:
                title = ""
                article_url = ""
            # Year
            try:
                date_span = div.find_element(By.CSS_SELECTOR, "span.date")
                date = date_span.text.strip()
            except Exception:
                date = ""
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
                    journal = journal_span.text.strip()
                else:
                    journal = "N/A"
            except Exception:
                journal = "N/A"
            articles_info.append([title, date, type_val, journal, article_url])
            print(f"Found article: {title}")
        page += 1
    return name, articles_info

def find_profile_urls(org, driver):
    """Finds the urls to profiles on an organization main page, handling pagination."""
    profile_urls = set()
    page = 0
    while True:
        page_url = f"{org}?page={page}"
        driver.get(page_url)
        time.sleep(2)
        urls = driver.find_elements(By.CSS_SELECTOR, "ul.grid-results li.grid-result-item h3.title a")
        found_on_page = 0
        for url in urls:
            href = url.get_attribute("href")
            if href and href.startswith("https://research-repository.uwa.edu.au/en/persons/"):
                profile_urls.add(href)
                found_on_page += 1
        if found_on_page == 0:
            break
        page += 1
    return list(profile_urls)    

def write_to_csv(articles_info, name, profile_url, csv_filename):
    print("Writing scraped data to CSV")
    with open(csv_filename, mode="a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        for article in articles_info:
            csv_write = article.copy()
            csv_write.append(name)
            csv_write.append(profile_url)
            writer.writerow(csv_write)

def write_to_db(articles_info, name, profile_url):
    print("Writing scraped data to database")
    db = SessionLocal()
    try:
        # Check if researcher exists
        researcher = db.query(Researcher).filter_by(name=name, profile_url=profile_url).first()
        if not researcher:
            researcher = Researcher(name=name, university="UWA", profile_url=profile_url)
            db.add(researcher)
            db.commit()
            db.refresh(researcher)
        for article in articles_info:
            title, date_str, type_val, journal, article_url = article
            # Parse date string to datetime.date or None
            date_obj = None
            if date_str:
                try:
                    # Expecting format '01 Jan 2025'
                    date_obj = datetime.datetime.strptime(date_str, "%d %b %Y").date()
                except Exception:
                    date_obj = None
            db_article = db.query(Article).filter_by(title=title, article_url=article_url).first()
            if not db_article:
                db_article = Article(title=title, date=date_obj, article_type=type_val, article_url=article_url)
                db.add(db_article)
                db.commit()
                db.refresh(db_article)
            # Link researcher and article (if not already linked)
            if db_article not in researcher.articles:
                researcher.articles.append(db_article)
                db.commit()
    finally:
        db.close()

def main():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--lang=en-US,en")
    # options.add_argument("--headless")  # Uncomment for headless mode

    driver = uc.Chrome(version_main=138, options=options)

    organizations = ['https://research-repository.uwa.edu.au/en/organisations/chief-finance-office/persons/']
                    #  'https://research-repository.uwa.edu.au/en/organisations/uwa-business-school/persons/'
    
    profile_urls = []
    for org in organizations:
        print(f"Searching for profile URLs for field: {org}")
        profile_urls.extend(find_profile_urls(org, driver))
        print(f"Found {len(profile_urls)} profile URLs")

    csv_header = ["Title", "Date", "Type", "Journal", "Article URL", "Researcher Name", "Profile URL"]
    csv_filename = "./app/files/UWA.csv"
    with open(csv_filename, mode="w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)

    for profile_url in profile_urls:
        print(f"Scraping profile: {profile_url}")
        time.sleep(5)
        name, articles_info = scrape_articles(profile_url, driver)
        print(f"Found {len(articles_info)} articles in {profile_url}")

        write_to_csv(articles_info, name, profile_url, csv_filename)
        write_to_db(articles_info, name, profile_url)

# Example usage:
if __name__ == "__main__":
    main()