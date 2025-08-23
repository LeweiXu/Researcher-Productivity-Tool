import undetected_chromedriver as uc
from app.scrapers.helpers.big3_functions import scrape_publications, find_profile_urls

def scrape_ANU():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--lang=en-US,en")
    # options.add_argument("--headless")  # Uncomment for headless mode
    driver = uc.Chrome(options=options)
    profiles_url = "https://researchportalplus.anu.edu.au/en/organisations/anu-college-of-business-and-economics/persons/"
    base = "https://researchportalplus.anu.edu.au"
    profile_urls = find_profile_urls(profiles_url, base, driver)
    print(f"Found {len(profile_urls)} profile URLs")

    all_data = []
    for profile_url in profile_urls:
        print(f"Scraping profile: {profile_url}")
        name, publications_info = scrape_publications(profile_url, driver)
        print(f"Found {len(publications_info)} publications in {profile_url}")
        for line in publications_info:
            all_data.append(line + [name, profile_url])

    return all_data