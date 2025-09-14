import undetected_chromedriver as uc
import pandas as pd
from app.scrapers.helpers.big3_functions import scrape_publications, find_profile_urls

# Load classification CSV
df = pd.read_csv("app/files/UWA Accounting Finance Staff_YW.csv", encoding="latin1")
field_lookup = dict(zip(df["Name"], df["Field"]))

def scrape_UWA():
    options = uc.ChromeOptions()
    # options.add_argument("--no-sandbox")
    # options.add_argument("--disable-gpu")
    # options.add_argument("--window-size=1280,800")
    # options.add_argument("--lang=en-US,en")
    # options.add_argument("--headless")  # Uncomment for headless mode
    driver = uc.Chrome(options=options)
    print("Chrome launched!")
    profiles_url = "https://www.uwa.edu.au/schools/business/accounting-and-finance"
    base = "https://research-repository.uwa.edu.au"

    profile_urls = find_profile_urls(profiles_url, base, driver)
    print(f"Found {len(profile_urls)} profile URLs")

    all_data = []
    for profile_url in profile_urls:
        print(f"Scraping profile: {profile_url}")
        name, job_title, publications_info = scrape_publications(profile_url, driver)
        print(f"Found {len(publications_info)} publications in {profile_url}")
        # Look up their field, defaulting to None
        field = field_lookup.get(name, None)
        for line in publications_info:

            all_data.append(line + [name, profile_url, job_title, field])


    return all_data