from selenium.webdriver.common.by import By
import time

def get_page_wait_captcha(page_url, driver, wait_interval=5):
    """Load a page and block until any captcha challenge is cleared manually."""
    driver.get(page_url)
    time.sleep(2)

    def has_captcha():
        page_source = driver.page_source.lower()
        indicators = (
            "captcha",
            "verify you are human",
            "cloudflare",
            "security check",
        )
        return any(indicator in page_source for indicator in indicators)

    notified = False
    while True:
        if has_captcha():
            if not notified:
                print(f"Captcha detected at {driver.current_url}. Waiting for manual resolution...")
                notified = True
            time.sleep(wait_interval)
            continue
        if driver.current_url != page_url:
            driver.get(page_url)
            time.sleep(2)
            notified = False
            continue
        return

def find_profile_urls(page_url, base, driver):
    """Finds all researcher profile URLs on all paginated pages using Selenium by matching href prefix."""
    profile_urls = set()
    page = 0
    while True:
        paged_url = f"{page_url}?page={page}"
        get_page_wait_captcha(paged_url, driver)
        time.sleep(8)
        a_tags = driver.find_elements(By.TAG_NAME, "a")
        found_on_page = 0
        for a in a_tags:
            href = a.get_attribute("href")
            if href and href.startswith(f"{base}/en/persons/"):
                if href not in profile_urls:
                    print(f"Found profile URL: {href}")
                    profile_urls.add(href)
                    found_on_page += 1
        if found_on_page == 0:
            break
        page += 1
    return list(profile_urls)

def scrape_publications(profile_url, driver):
    """
    Finds publication info for a given researcher
    Returns: (name, job_title, publications_info) where publications_info is a list of [Title, Date, Type, Journal, Article URL]
    """
    get_page_wait_captcha(profile_url, driver)
    time.sleep(2)
    # Try to get name robustly
    try:
        # Extract name from profile_url, e.g. https://research.monash.edu/en/persons/viet-nga-cao
        name_part = profile_url.rstrip('/').split('/')[-1]  # 'viet-nga-cao'
        name = ' '.join(word.capitalize() for word in name_part.split('-'))
    except Exception:
        name = ""
    # Try to get job title
    try:
        titles = [e.text.strip() for e in driver.find_elements(By.CSS_SELECTOR, "span.job-title") if e.text.strip()]
        job_title = " ".join(dict.fromkeys(titles)) if titles else ""
        if job_title == "":
            # Try to get <p> under div.header.person-details
            try:
                job_title = driver.find_element(
                    By.CSS_SELECTOR, "div.header.person-details > div.rendering_person_persontitlerendererportal > p"
                ).text.strip()
            except Exception:
                job_title = ""
    except Exception:
        # Try to get <p> under div.header.person-details if span.job-title fails
        try:
            job_title = driver.find_element(
                By.CSS_SELECTOR, "div.header.person-details > div.rendering_person_persontitlerendererportal > p"
            ).text.strip()
        except Exception:
            job_title = ""
    publications_info = []
    page = 0
    while True:
        if page == 0: page_url = f"{profile_url}/publications/"
        else: page_url = f"{profile_url}/publications/?page={page}"
        get_page_wait_captcha(page_url, driver)
        time.sleep(10)
        publication_divs = driver.find_elements(By.CSS_SELECTOR, "div.rendering_researchoutput_portal-short")
        if not publication_divs:
            break
        for div in publication_divs:
            # Title and URL (new structure)
            try:
                a_tag = div.find_element(By.CSS_SELECTOR, "h3.title a")
                pub_title = a_tag.find_element(By.CSS_SELECTOR, "span").text.strip()
                publication_url = a_tag.get_attribute("href")
            except Exception:
                pub_title = ""
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
                if type_val[-2:] == ' ›':
                    type_val = type_val[:-2]
            except Exception:
                type_val = ""
            # Journal
            try:
                if "Contribution to journal" in type_val:
                    journal_span = div.find_element(By.CSS_SELECTOR, "span.journal a span")
                    journal = journal_span.text.strip()[:-1] # Remove trailing full stop
                else:
                    journal = ""
            except Exception:
                journal = ""
            publications_info.append([pub_title, year, type_val, journal, publication_url])
            print(f"Found publication: {pub_title}")
        page += 1
    return name, job_title, publications_info

if __name__ == "__main__":
    import undetected_chromedriver as uc
    import csv
    options = uc.ChromeOptions()
    driver = uc.Chrome()
    name, job_title, publications_info = scrape_publications("https://research-repository.uwa.edu.au/en/persons/raymond-da-silva-rosa", driver)
    field = "Finance"
    print(f"Researcher: {name}, Field: {field}")

    csv_header = ["Title", "Year", "Type", "Journal Name", "Article URL", "Researcher Name", "Profile URL", "Job Title", "Field"]
    with open("app/files/temp/raymond.csv", mode="w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
    for line in publications_info:
        with open("app/files/temp/raymond.csv", mode="a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(line + [name, "https://research-repository.uwa.edu.au/en/persons/raymond-da-silva-rosa", job_title, field])  # Append fields