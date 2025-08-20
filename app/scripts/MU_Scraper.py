import undetected_chromedriver as uc
from app.scripts.big3_functions import scrape_publications, find_profile_urls
from app.scripts.save_functions import write_to_csv, write_to_db


def update_MU():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--lang=en-US,en")
    # options.add_argument("--headless")  # Uncomment for headless mode
    driver = uc.Chrome(version_main=138, options=options) #Lewei note: local machine has issue with chrome installation, have to force use chrome version 138 to work for now

    profiles_urls = [
        "https://research.monash.edu/en/organisations/department-of-accounting/persons/",
        "https://research.monash.edu/en/organisations/banking-finance/persons/",
        "https://research.monash.edu/en/organisations/centre-for-quantitative-finance-and-investment-strategies/persons/"
    ]
    base = "https://research.monash.edu"
    profile_urls = []
    for url in profiles_urls:
        print(f"Finding profile URLs on: {url}")
        profile_urls.extend(find_profile_urls(url, base, driver))
    profile_urls = list(set(profile_urls))
    print(f"Found {len(profile_urls)} profile URLs")

    for profile_url in profile_urls:
        print(f"Scraping profile: {profile_url}")
        name, publications_info = scrape_publications(profile_url, driver)
        print(f"Found {len(publications_info)} publications in {profile_url}")

        write_to_csv(publications_info, name, profile_url, "app/files/MU.csv")
        write_to_db(publications_info, name, profile_url)

# Example usage:
if __name__ == "__main__":
    update_MU()