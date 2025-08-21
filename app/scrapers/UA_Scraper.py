# app/scripts/Adelaide_Scraper.py
import time
import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from app.database import SessionLocal
from app.models import Researchers, Publications

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
    import undetected_chromedriver as uc
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,1100")
    opts.add_argument("--lang=en-US,en")
    return uc.Chrome(options=opts, version_main=138)

def wait_for_body(driver, timeout: int):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

def gentle_scroll(driver, steps: int = SCROLL_STEPS, pause: float = SCROLL_PAUSE):
    for _ in range(max(1, steps)):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)

def collect_entry_links(pages: List[str], driver) -> List[str]:
    from selenium.webdriver.common.by import By
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
    from selenium.webdriver.common.by import By
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
        (By.XPATH, "//a[contains(., 'View My Researcher Profile')]") ,
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
    from selenium.webdriver.common.by import By
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

def parse_journal_table(html: str) -> Tuple[str, List[Dict[str, Optional[str]]]]:
    soup = BeautifulSoup(html, "lxml")
    name = ""
    for sel in ["h1", "h1.name", "header h1", "[data-testid='profile-name']"]:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            name = el.get_text(strip=True)
            break
    pubs: List[Dict[str, Optional[str]]] = []
    rows = soup.select("table tbody tr")
    if rows:
        for tr in rows:
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue
            year_txt = (tds[0].get_text(strip=True) or "")
            year = int(year_txt) if year_txt.isdigit() else None
            cit = tds[1]
            jnode = cit.find("em") or cit.find("i")
            if not jnode:
                continue
            journal = jnode.get_text(strip=True)
            if not journal:
                continue
            a = cit.find("a", href=True)
            url = a["href"] if a else None
            if not url:
                doi_a = cit.find("a", href=re.compile(r"doi\\.org", re.I))
                url = doi_a.get("href") if doi_a else ""
            title = a.get_text(strip=True) if a else cit.get_text(strip=True)[:200]
            pubs.append({
                "title": title or None,
                "year": year,
                "publication_type": "Journal article",
                "journal_name": journal,
                "publication_url": url or "",
            })
        return name, pubs
    containers = soup.select(
        "div.publications-list .publication-item, "
        "li.publication, "
        "div.rendering_researchoutput_portal-short, "
        "[class*='publication']"
    )
    for c in containers:
        jnode = c.select_one(".journal, .journal a, span.journal a span, em, i")
        if not jnode:
            continue
        journal = jnode.get_text(strip=True)
        if not journal:
            continue
        title_el = c.select_one("h3 a, .title a, a[href*='/publications/']") or c.select_one("h3, .title")
        title = title_el.get_text(strip=True) if title_el else None
        href = title_el.get("href") if title_el and title_el.name == "a" else None
        if not href:
            doi_a = c.find("a", href=re.compile(r"doi\\.org", re.I))
            href = doi_a.get("href") if doi_a else ""
        year = None
        yel = c.select_one(".year, .date, time")
        if yel:
            m = re.search(r"(19|20)\d{2}", yel.get_text(strip=True))
            if m:
                year = int(m.group(0))
        pubs.append({
            "title": title,
            "year": year,
            "publication_type": "Journal article",
            "journal_name": journal,
            "publication_url": href or "",
        })
    return name, pubs

def upsert_researcher(db, name: str, profile_url: str) -> Researchers:
    r = (
        db.query(Researchers)
        .filter(Researchers.name == name, Researchers.university == UNIVERSITY_NAME)
        .one_or_none()
    )
    if r:
        if profile_url and not r.profile_url:
            r.profile_url = profile_url
        return r
    r = Researchers(name=name, university=UNIVERSITY_NAME, profile_url=profile_url)
    db.add(r)
    db.flush()
    return r

def add_publication_if_new(db, researcher_id: int, p: Dict[str, Optional[str]]):
    title = (p.get("title") or "").strip()
    journal = (p.get("journal_name") or "").strip()
    url = (p.get("publication_url") or "").strip()
    if not title or not journal:
        return
    year = p.get("year")
    existing = (
        db.query(Publications)
        .filter(
            Publications.title == title,
            Publications.year == year,
            Publications.researcher_id == researcher_id,
        )
        .one_or_none()
    )
    if existing:
        return
    pub = Publications(
        title=title,
        year=year,
        publication_type=p.get("publication_type"),
        publication_url=url,
        journal_name=journal,
        researcher_id=researcher_id,
        journal_id=None,
    )
    db.add(pub)

def run(headless: bool = False):
    db = SessionLocal()
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
                print("  ! Could not resolve to profile:", entry)
        profiles = sorted(profiles)
        print(f"Resolved {len(profiles)} researcher profile URLs.")
        for i, profile_url in enumerate(profiles, 1):
            print(f"[{i}/{len(profiles)}] {profile_url}")
            html = open_publications_journals(driver, profile_url)
            name, pubs = parse_journal_table(html)
            name = (name or "").strip()
            if not name:
                print("  ! No name; skipping")
                continue
            r = upsert_researcher(db, name, profile_url)
            added = 0
            for p in pubs:
                before = len(list(db.new))
                add_publication_if_new(db, r.id, p)
                after = len(list(db.new))
                if after > before:
                    added += 1
            db.commit()
            print(f"  -> {name}: parsed={len(pubs)}, added={added}")
            time.sleep(POLITE_DELAY)
    finally:
        try:
            driver.quit()
        except Exception:
            pass
        db.close()

if __name__ == "__main__":
    run(headless=False)
