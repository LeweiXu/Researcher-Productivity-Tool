import undetected_chromedriver as uc
from app.scrapers.helpers.big3_functions import scrape_publications, find_profile_urls
import csv

def scrape_MU():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--lang=en-US,en")
    # options.add_argument("--headless")  # Uncomment for headless mode
    driver = uc.Chrome(options=options)

    profiles_urls = [
        ("https://research.monash.edu/en/organisations/department-of-accounting/persons/", "Accounting"),
        ("https://research.monash.edu/en/organisations/banking-finance/persons/", "Finance"),
        ("https://research.monash.edu/en/organisations/centre-for-quantitative-finance-and-investment-strategies/persons/", "Finance")
    ]
    base = "https://research.monash.edu"
    pairs = []
    for url, field in profiles_urls:
        print(f"Finding profile URLs on: {url}")
        found = find_profile_urls(url, base, driver)  # returns list[str]
        pairs.extend((u, field) for u in found)
    profile_urls = list(set(pairs))
    print(f"Found {len(profile_urls)} profile URLs")

    csv_header = ["Title", "Year", "Type", "Journal Name", "Article URL", "Researcher Name", "Profile URL", "Job Title", "Field"]
    with open("app/files/temp/MU_data.csv", mode="w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)

    for profile_url, field in profile_urls:
        print(f"Scraping profile: {profile_url} ({field})")
        name, job_title, publications_info = scrape_publications(profile_url, driver)
        print(f"Found {len(publications_info)} publications in {profile_url}")
        for line in publications_info:
            with open("app/files/temp/MU_data.csv", mode="a", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(line + [name, profile_url, job_title, field])  # Append fields