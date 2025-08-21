from selenium.webdriver.common.by import By
import time

def find_profile_urls(page_url, base, driver):
    """Finds all researcher profile URLs on all paginated pages using Selenium by matching href prefix."""
    profile_urls = set()
    page = 0
    while True:
        paged_url = f"{page_url}?page={page}"
        driver.get(paged_url)
        time.sleep(2)
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
                if type_val[-2:] == ' >':
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
            publications_info.append([title, year, type_val, journal, publication_url])
            print(f"Found publication: {title}")
        page += 1
    return name, publications_info