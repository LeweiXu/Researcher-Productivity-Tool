import time
import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ========= CONFIG =========
UNIVERSITY_NAME = "University of Adelaide"
STAFF_INDEX_PAGES = [
    "https://business.adelaide.edu.au/research/finance-and-business-analytics",
    "https://business.adelaide.edu.au/research/accounting#lead-researchers",
]
POLITE_DELAY = 0.6
INDEX_WAIT_SEC = 12
PROFILE_WAIT_SEC = 12
SCROLL_STEPS = 5
SCROLL_PAUSE = 0.7
# =========================

def make_driver(headless: bool = False):
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,1100")
    opts.add_argument("--lang=en-US,en")
    return uc.Chrome(options=opts, version_main=138)

def wait_for_body(driver, timeout: int):
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

def gentle_scroll(driver, steps: int = SCROLL_STEPS, pause: float = SCROLL_PAUSE):
    for _ in range(max(1, steps)):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)

def collect_entry_links(pages: List[str], driver) -> List[str]:
    found = set()
    for url in pages:
        print("Index:", url)
        driver.get(url)
        wait_for_body(driver, INDEX_WAIT_SEC)
        time.sleep(1.2)
        gentle_scroll(driver)
        for a in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
            href = (a.get_attribute("href") or "").strip()
            if not href or href.startswith("#"):
                continue
            href = href.split("#")[0].rstrip("/")
            netloc = urlparse(href).netloc
            if (
                "researchers.adelaide.edu.au" in netloc
                or ("business.adelaide.edu.au" in netloc and "/people/" in href)
                or ("adelaide.edu.au" in netloc and "/directory/" in href)
            ):
                found.add(href)
    print(f"Collected {len(found)} entry links (mixed).")
    return sorted(found)

def resolve_to_profile(driver, entry_url: str) -> Optional[str]:
    if "researchers.adelaide.edu.au" in entry_url and "/profile/" in entry_url and "?name=" not in entry_url:
        return entry_url.split("#")[0].rstrip("/")
    print(f"Getting {entry_url}")
    driver.get(entry_url)
    wait_for_body(driver, PROFILE_WAIT_SEC)
    time.sleep(0.8)
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='researchers.adelaide.edu.au/profile/']")
        for link in links:
            href = (link.get_attribute("href") or "").split("#")[0].rstrip("/")
            if "/profile/" in href and "?name=" not in href:
                return href
    except Exception:
        pass
    locators = [
        (By.XPATH, "//a[contains(., 'View My Researcher Profile')]"),
        (By.PARTIAL_LINK_TEXT, "Researcher Profile")
    ]
    for locator in locators:
        try:
            el = driver.find_element(*locator)
            href = (el.get_attribute("href") or "").split("#")[0].rstrip("/")
            if "researchers.adelaide.edu.au" in href and "/profile/" in href and "?name=" not in href:
                return href
        except Exception:
            pass
    try:
        for a in driver.find_elements(By.CSS_SELECTOR, "a[href*='researchers.adelaide.edu.au']"):
            href = (a.get_attribute("href") or "").split("#")[0].rstrip("/")
            if "/profile/" in href and "?name=" not in href:
                return href
    except Exception:
        pass
    return None

def open_publications_journals(driver, profile_url: str) -> str:
    driver.get(profile_url)
    wait_for_body(driver, PROFILE_WAIT_SEC)
    time.sleep(0.8)
    for target in [profile_url + "#publications", profile_url.rstrip("/") + "/publications"]:
        try:
            driver.get(target)
            wait_for_body(driver, PROFILE_WAIT_SEC)
            time.sleep(1.0)
            break
        except Exception:
            pass
    gentle_scroll(driver, steps=2)
    locators = [
        (By.PARTIAL_LINK_TEXT, "Journal articles"),
        (By.PARTIAL_LINK_TEXT, "Journals"),
        (By.XPATH, "//a[contains(translate(., 'JOURNAL','journal'),'journal')]") ,
        (By.CSS_SELECTOR, "button[data-filter*='journal'], a[data-filter*='journal']")
    ]
    for locator in locators:
        try:
            el = driver.find_element(*locator)
            el.click()
            time.sleep(1.0)
            break
        except Exception:
            pass
    wait_for_body(driver, PROFILE_WAIT_SEC)
    gentle_scroll(driver, steps=3)
    return driver.page_source

def parse_researcher_profile(html: str, profile_url : str):
    soup = BeautifulSoup(html, "lxml")
    # Extract Researcher Name
    name_tag = soup.find("h1")
    researcher_name = name_tag.get_text(strip=True) if name_tag else ""
    publications = []
    # Only process these publication types
    valid_types = {"Journals", "Book Chapters", "Conference Papers", "Theses"}
    for acc_item in soup.select("li.c-accordion__item"):
        # Get publication type from heading
        heading = acc_item.select_one(".c-accordion__heading")
        pub_type = heading.get_text(strip=True) if heading else ""
        if pub_type not in valid_types:
            continue
        # Find publication table rows
        for row in acc_item.select("tbody tr"):
            tds = row.find_all("td")
            if len(tds) < 2:
                continue
            year_raw = tds[0].get_text(strip=True)
            year = year_raw if year_raw and year_raw != "-" else None
            citation_td = tds[1]
            citation_span = citation_td.find("span")
            citation_text = citation_span.get_text(" ", strip=True) if citation_span else citation_td.get_text(" ", strip=True)
            # Extract title: after the year in parentheses and full stop, support (n.d.) as well
            title = ""
            m = re.search(r"\((\d{4}|n\.d\.)\)\.\s*(.*?)(?:\.|<)", citation_text)
            if m:
                title = m.group(2).strip()
            # Journal Name: first <i> after the title
            journal_name = ""
            i_tags = citation_td.find_all("i")
            if i_tags and pub_type == "Journals":
                journal_name = i_tags[0].get_text(strip=True)
            # Article URL: first <a href> after the citation
            article_url = ""
            a_tag = citation_td.find("a", href=True)
            if a_tag:
                article_url = a_tag["href"]
            publications.append([title, year, pub_type, journal_name, article_url, researcher_name, profile_url])
    return publications

def scrape_UA(headless: bool = False):
    driver = make_driver(headless=headless)
    try:
        entries = collect_entry_links(STAFF_INDEX_PAGES, driver)
        print(entries)
        profiles = set()
        for entry in entries:
            prof = resolve_to_profile(driver, entry)
            if prof:
                profiles.add(prof.rstrip("/"))
            else:
                print("  ! No researcher profile found:", entry)
        profiles = sorted(profiles)
        print(f"Resolved {len(profiles)} researcher profile URLs.")
        all_data = []
        for i, profile_url in enumerate(profiles, 1):
            print(f"[{i}/{len(profiles)}] {profile_url}")
            html = open_publications_journals(driver, profile_url)
            publications = parse_researcher_profile(html, profile_url)
            print(publications)
            all_data.extend(publications)
            time.sleep(POLITE_DELAY)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return all_data
