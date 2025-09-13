import time
import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ========= CONFIG =========
UNIVERSITY_NAME = "The University of Queensland"
STAFF_INDEX_PAGES = [
    ("https://business.uq.edu.au/team/accounting-discipline", "Accounting"),
    ("https://business.uq.edu.au/team/finance-discipline", "Finance"),
]
POLITE_DELAY = 0.6
INDEX_WAIT_SEC = 12
PROFILE_WAIT_SEC = 12
SCROLL_STEPS = 5
SCROLL_PAUSE = 0.7

PUBTYPE_MAP = {
    "journal articles": "Journals",
    "conference papers": "Conference Papers",
    "research report": "Research Report",
    "book chapters": "Book Chapters",
    "theses": "Theses",
}
# =========================


# ---------- Driver ----------
def make_driver(headless: bool = False):
    """构建稳定的 UC Chrome；不写死 version_main，避免和本机不匹配。"""
    opts = uc.ChromeOptions()
    if headless:
        opts.add_argument("--headless=old")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,1100")
    opts.add_argument("--lang=en-US,en")
    return uc.Chrome(options=opts)


def wait_for_body(driver, timeout: int):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )


def gentle_scroll(driver, steps: int = SCROLL_STEPS, pause: float = SCROLL_PAUSE):
    for _ in range(max(1, steps)):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)


def _is_uq_profile_url(href: str) -> bool:
    if not href:
        return False
    href = href.split("#")[0].rstrip("/")
    parsed = urlparse(href)
    return (
        parsed.netloc.endswith("business.uq.edu.au")
        and parsed.path.startswith("/profile/")
        and parsed.path.count("/") >= 2  # /profile/{id}/{slug}
    )


# ---------- 抓入口 ----------
def collect_entry_links(pages: List[Tuple[str, str]], driver) -> List[Tuple[str, str]]:
    found = set()
    for url, dept in pages:
        print("Index:", url, "| Department:", dept)
        driver.get(url)
        wait_for_body(driver, INDEX_WAIT_SEC)
        time.sleep(1.2)
        gentle_scroll(driver)

        try:
            btn = driver.find_element(
                By.XPATH,
                "//button[contains(., 'Accept') or contains(., 'Agree') or contains(., 'accept')]"
            )
            btn.click()
            time.sleep(0.6)
        except Exception:
            pass

        for a in driver.find_elements(By.CSS_SELECTOR, "a[href*='/profile/']"):
            href = (a.get_attribute("href") or "").strip()
            if not href or href.startswith("#"):
                continue
            href = href.split("#")[0].rstrip("/")
            if _is_uq_profile_url(href):
                found.add((href, dept))

    print(f"Collected {len(found)} entry links.")
    return sorted(found)


def resolve_to_profile(driver, entry_with_dept: Tuple[str, str]) -> Optional[Tuple[str, str]]:
    entry_url, dept = entry_with_dept
    if _is_uq_profile_url(entry_url):
        return (entry_url.split("#")[0].rstrip("/"), dept)

    driver.get(entry_url)
    wait_for_body(driver, PROFILE_WAIT_SEC)
    time.sleep(0.8)

    try:
        for a in driver.find_elements(By.CSS_SELECTOR, "a[href*='/profile/']"):
            href = (a.get_attribute("href") or "").split("#")[0].rstrip("/")
            if _is_uq_profile_url(href):
                return (href, dept)
    except Exception:
        pass
    return None


def open_publications_journals(driver, profile_url: str) -> str:
    driver.get(profile_url)
    wait_for_body(driver, PROFILE_WAIT_SEC)
    time.sleep(0.8)

    gentle_scroll(driver, steps=3, pause=0.6)

    for _ in range(3):
        try:
            btn = driver.find_element(
                By.XPATH,
                "//button[contains(translate(., 'LOADSHOWMORE', 'loadshowmore'), 'load')"
                " or contains(translate(., 'LOADSHOWMORE', 'loadshowmore'), 'show')]"
            )
            btn.click()
            time.sleep(1.0)
            gentle_scroll(driver, steps=1)
        except Exception:
            break

    return driver.page_source


def _map_pubtype(h3_text: str) -> str:
    key = (h3_text or "").strip().lower()
    return PUBTYPE_MAP.get(key, h3_text or "Journals")


def parse_researcher_profile(html: str, profile_url: str):
    soup = BeautifulSoup(html, "lxml")

    researcher_name = ""
    h1 = soup.find("h1")
    if h1:
        researcher_name = h1.get_text(strip=True)
    if not researcher_name and soup.title:
        researcher_name = re.sub(r"\s*[-|–].*$", "", soup.title.get_text(strip=True)).strip()

    publications = []

    main = soup.select_one("div.medium-9.columns") or soup

    for h3 in main.find_all("h3"):
        pub_type = _map_pubtype(h3.get_text(strip=True))
        for sib in h3.next_siblings:
            if getattr(sib, "name", None) == "h3":
                break
            if getattr(sib, "name", None) == "div" and "indexed_content__item" in (sib.get("class") or []):
                meta = sib.select_one("div.meta")
                if not meta:
                    continue

                year = ""
                y = meta.select_one("span.citation_date")
                if y:
                    year = (y.get_text(strip=True) or "").split()[0]

                title = ""
                article_url = ""
                a_title = meta.select_one("a.citation_title[href]")
                if a_title:
                    title = a_title.get_text(strip=True)
                    article_url = a_title.get("href", "").strip()

                journal_name = ""
                j = meta.select_one("span.citation_journal_name")
                if j:
                    journal_name = j.get_text(strip=True)

                if not article_url:
                    doi_span = meta.select_one("span.citation_doi")
                    if doi_span:
                        doi = doi_span.get_text(strip=True)
                        if doi and not doi.lower().startswith("http"):
                            article_url = f"https://doi.org/{doi}"

                if not title:
                    i_tag = meta.find("i")
                    if i_tag:
                        if i_tag.find("a"):
                            title = i_tag.find("a").get_text(strip=True)
                            if not article_url:
                                article_url = i_tag.find("a").get("href", "").strip()
                        else:
                            title = i_tag.get_text(strip=True)

                if year or title:
                    publications.append([
                        title or "",
                        year or "",
                        pub_type,
                        journal_name or "",
                        article_url or "",
                        researcher_name or "",
                        profile_url
                    ])

    return publications


def scrape_UQ(headless: bool = False):
    driver = make_driver(headless=headless)
    try:
        entries = collect_entry_links(STAFF_INDEX_PAGES, driver)
        print("Entry URLs:", len(entries))
        profiles = set()
        for entry in entries:
            res= resolve_to_profile(driver, entry)
            if res:
                prof_url, dept = res
                profiles.add((prof_url.rstrip("/"), dept))
            else:
                print("  ! No researcher profile found:", entry)

        profiles_sorted = sorted(profiles, key=lambda x: x[0])
        print(f"Resolved {len(profiles_sorted)} researcher profile URLs.")

        all_data = []
        for i, (profile_url, dept) in enumerate(profiles_sorted, 1):
            print(f"[{i}/{len(profiles_sorted)}] {profile_url} | Dept: {dept}")
            html = open_publications_journals(driver, profile_url)
            publications = parse_researcher_profile(html, profile_url)
            print(f"  parsed {len(publications)} pubs")
            for row in publications:
                all_data.append(row + [dept])  # append department as a separate field

            time.sleep(POLITE_DELAY)
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return all_data


if __name__ == "__main__":
    test_profiles = [
        "https://business.uq.edu.au/profile/1433/ankit-jain",
        "https://business.uq.edu.au/profile/17730/chris-bell",
    ]
    driver = make_driver(headless=False)
    try:
        for url in test_profiles:
            html = open_publications_journals(driver, url)
            rows = parse_researcher_profile(html, url)
            print(url, "parsed:", len(rows))
            for r in rows[:3]:
                print(" -", r)
    finally:
        driver.quit()
