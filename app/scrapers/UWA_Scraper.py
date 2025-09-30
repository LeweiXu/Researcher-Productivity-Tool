import undetected_chromedriver as uc
import pandas as pd
import csv
from app.scrapers.helpers.big3_functions import scrape_publications, find_profile_urls

def scrape_UWA():
    # Load classification CSV
    df = pd.read_csv("app/files/uploads_current/UWA_staff_field_upload.csv", encoding="latin1")
    field_lookup = dict(zip(df["Name"], df["Field"]))

    options = uc.ChromeOptions()
    # options.add_argument("--no-sandbox")
    # options.add_argument("--disable-gpu")
    # options.add_argument("--window-size=1280,800")
    # options.add_argument("--lang=en-US,en")
    # options.add_argument("--headless")  # Uncomment for headless mode
    driver = uc.Chrome()
    print("Chrome launched!")
    profiles_url = "https://www.uwa.edu.au/schools/business/accounting-and-finance"
    base = "https://research-repository.uwa.edu.au"

    profile_urls = find_profile_urls(profiles_url, base, driver)
    print(f"Found {len(profile_urls)} profile URLs")

    csv_header = ["Title", "Year", "Type", "Journal Name", "Article URL", "Researcher Name", "Profile URL", "Job Title", "Field"]
    with open("app/files/temp/UWA_data.csv", mode="w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)

    for profile_url in profile_urls:
        print(f"Scraping profile: {profile_url}")
        name, job_title, publications_info = scrape_publications(profile_url, driver)
        
        # Lookup field in csv
        print('Getting fields from "UWA Accounting Finance Staff_YW.csv"')
        field = field_lookup.get(name, None)
        print(f"Researcher: {name}, Field: {field}")

        print(f"Found {len(publications_info)} publications in {profile_url}")
        for line in publications_info:
            with open("app/files/temp/UWA_data.csv", mode="a", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(line + [name, profile_url, job_title, field])  # Append fields