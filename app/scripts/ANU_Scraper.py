import undetected_chromedriver as uc
from app.scripts.big3_functions import scrape_publications, find_profile_urls
from app.scripts.save_functions import write_to_csv, write_to_db


def update_ANU():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--lang=en-US,en")
    # options.add_argument("--headless")  # Uncomment for headless mode
    driver = uc.Chrome(version_main=138, options=options) #Lewei note: local machine has issue with chrome installation, have to force use chrome version 138 to work for now

    profiles_url = "https://researchportalplus.anu.edu.au/en/organisations/anu-college-of-business-and-economics/persons/"
    base = "https://researchportalplus.anu.edu.au"
    profile_urls = find_profile_urls(profiles_url, base, driver)
    print(f"Found {len(profile_urls)} profile URLs")

    for profile_url in profile_urls:
        print(f"Scraping profile: {profile_url}")
        name, publications_info = scrape_publications(profile_url, driver)
        print(f"Found {len(publications_info)} publications in {profile_url}")

        write_to_csv(publications_info, name, profile_url, "app/files/ANU.csv")
        write_to_db(publications_info, name, profile_url)

# Example usage:
if __name__ == "__main__":
    update_ANU()