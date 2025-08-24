# app/scrapers/USYD_journals.py
import csv, re, time
from typing import List, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# URLS 
URLS = [
    # Accounting
    "https://www.sydney.edu.au/research/our-research/find-a-researcher.html?+facultyCode=5000053050F0000&+schoolCode=5000053050F0000F2050&+departmentCode=5000053050F0000F2050F0200&Academic=true",
    # Finance 
    "https://www.sydney.edu.au/research/our-research/find-a-researcher.html?+facultyCode=5000053050F0000&+schoolCode=5000053050F0000F2050&+departmentCode=5000053050F0000F2050F0300&Academic=true",
]
#DRIVER_PATH = "/home/imrea1m/.wdm/drivers/chromedriver/linux64/136.0.7103.113/chromedriver-linux64/chromedriver"
CSV_OUT = "usyd_publications.csv"

# ---------- driver ----------
def make_driver(headless: bool = False):
    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1280,1100")
    return webdriver.Chrome(options=opts)

def wait_css(driver, css, t=15):
    return WebDriverWait(driver, t).until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))

def gentle_scroll(driver, steps=8, pause=0.35):
    for _ in range(steps):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)

# ---------- expand all (only) ----------
def click_expand_all_in_pane(driver, pane_css: str) -> bool:
    """Click 'Expand all' inside a specific pane (this case, '#home')."""
    try:
        pane = driver.find_element(By.CSS_SELECTOR, pane_css)
        btn = pane.find_element(By.CSS_SELECTOR, "#b-js-pub-expand-all")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.1)
        try:
            btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn)
        time.sleep(0.4)
        return True
    except Exception:
        return False  

# ---------- list researchers ----------
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, ElementClickInterceptedException

RESULTS_WRAPPER_CSS = "div.m-find-a-researcher__search-results"
PROFILE_WRAPPER_CSS = "div.m-find-a-researcher__profile-wrapper"
NAME_LINK_CSS = "a.m-find-a-researcher__profile-wrapper--profile-name"
NEXT_BTN_XPATH = "//button[contains(@class,'pagination--ds__item--next')]"

def _wait_results_loaded(driver, t=15):
    # Wait for the search-results container and at least one profile to show up
    wrapper = WebDriverWait(driver, t).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, RESULTS_WRAPPER_CSS))
    )
    WebDriverWait(driver, t).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, f"{RESULTS_WRAPPER_CSS} {PROFILE_WRAPPER_CSS}"))
    )
    return wrapper

def _get_scoped_page_researchers(driver):
    # Only collect profiles from within the results area
    wrapper = driver.find_element(By.CSS_SELECTOR, RESULTS_WRAPPER_CSS)
    cards = wrapper.find_elements(By.CSS_SELECTOR, f"{PROFILE_WRAPPER_CSS} {NAME_LINK_CSS}")
    out = []
    for a in cards:
        name_el = a.find_element(By.CSS_SELECTOR, "h3.m-title")
        name = (name_el.text or "").strip()
        href = (a.get_attribute("href") or "").split("#")[0]
        if name and href:
            out.append((name, href))
    return out

def _scroll_to_results_top(driver):
    # Ensure we’re back at the top of the results region before clicking Next
    try:
        results = driver.find_element(By.CSS_SELECTOR, RESULTS_WRAPPER_CSS)
        driver.execute_script("arguments[0].scrollIntoView({block:'start'});", results)
    except Exception:
        driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.15)

def _has_next_enabled(driver):
    # check if the next page button is visible/enabled
    try:
        btn = driver.find_element(By.XPATH, NEXT_BTN_XPATH)
    except Exception:
        return False
    classes = (btn.get_attribute("class") or "").lower()
    aria_dis = (btn.get_attribute("aria-disabled") or "").lower()
    style = (btn.get_attribute("style") or "").lower()
    if "disabled" in classes or aria_dis in ("true","1"): return False
    if "display: none" in style or "visibility: hidden" in style: return False
    return True

def _click_next(driver):
    # click next, made js fall back for stale/intercepted
    btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, NEXT_BTN_XPATH)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
    time.sleep(0.1)
    try:
        btn.click()
    except (ElementClickInterceptedException, StaleElementReferenceException):
        driver.execute_script("arguments[0].click();", btn)

def get_researchers(driver, url: str) -> List[Tuple[str, str]]:
    '''
    Given a search URL:
      - skim through all results,
      - collect unique (Researcher Name, Profile URL),
      - return the full list.
    Uses the first card's href as an "anchor" to detect page changes after Next.
    '''
    
    driver.get(url)
    _wait_results_loaded(driver)

    all_rows, seen = [], set()
    while True:
        # anchor: first profile href on this page (to detect page change)
        try:
            wrapper = driver.find_element(By.CSS_SELECTOR, RESULTS_WRAPPER_CSS)
            first_a = wrapper.find_element(By.CSS_SELECTOR, f"{PROFILE_WRAPPER_CSS} {NAME_LINK_CSS}")
            first_href_token = first_a.get_attribute("href") or ""
        except Exception:
            first_href_token = ""

        # collect current page (scoped)
        page_rows = _get_scoped_page_researchers(driver)
        for name, href in page_rows:
            if href not in seen:
                seen.add(href)
                all_rows.append((name, href))

        # stop if next isn’t available
        if not _has_next_enabled(driver):
            break

        # go to next page
        _scroll_to_results_top(driver)
        try:
            _click_next(driver)
            WebDriverWait(driver, 12).until(
                lambda d: (
                    # wait until first profile href changes (page advanced)
                    (lambda fh: (d.find_elements(By.CSS_SELECTOR, f"{RESULTS_WRAPPER_CSS} {PROFILE_WRAPPER_CSS} {NAME_LINK_CSS}") and
                                 (d.find_element(By.CSS_SELECTOR, f"{RESULTS_WRAPPER_CSS} {PROFILE_WRAPPER_CSS} {NAME_LINK_CSS}")
                                  .get_attribute("href") or "") != fh))(first_href_token)
                )
            )
            _wait_results_loaded(driver)
        except TimeoutException:
            # bail if page didn’t change to avoid infinite loop
            break

    return all_rows

# ---------- helpers for parsing ----------
def clean_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def text_after_year(block_text: str) -> str:
    # remove "authors (YYYY)." OR "authors (YYYY)," at the front if present--> for the 'Other' type of academic production
    return clean_spaces(re.sub(r"^.*?\)\s*[\.,]\s*", "", block_text))


def is_empty_title(s: str) -> bool:
    return not s or s.strip(".—–- ,;:").strip() == ""

# ---------- parse a profile ----------
def parse_profile(driver, researcher_name: str, profile_url: str):
    """
    Parse a single profile:
      - open page,
      - expand the 'By Type' tab (#home),
      - iterate 'li' items,
      - extract title/year/type/journal/url and return rows for this researcher.
    """
    driver.get(profile_url)
    wait_css(driver, "body")
    # wait for publications list to load, fallback to short sleep if slow
    try:
        WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#home ul.pubType li"))
    )
    except TimeoutException:
        time.sleep(1)  # fallback if pubs never show up

    # expand **By Type** only
    click_expand_all_in_pane(driver, "#home")

    # Only the active "By Type" pane to avoid duplicates from "By Year"
    items = driver.find_elements(By.CSS_SELECTOR, "#home ul.pubType li")
    if not items:
        time.sleep(0.5)  # some pages hydrate slowly
        items = driver.find_elements(By.CSS_SELECTOR, "#home ul.pubType li")

    results = []

    for li in items:
        raw_text = clean_spaces(li.text)

        # pub_type (section heading)
        try:
            pub_type = clean_spaces(li.find_element(
                By.XPATH, "ancestor::tr[1]//p/strong"
            ).text)
        except Exception:
            try:
                pub_type = clean_spaces(li.find_element(
                    By.XPATH, "preceding::p[strong][1]/strong"
                ).text)
            except Exception:
                pub_type = ""

        # Year
        m_year = re.search(r"\b(19|20)\d{2}\b", raw_text)
        year = m_year.group(0) if m_year else ""

        # DOI / URL
        article_url = ""
        for a in li.find_elements(By.CSS_SELECTOR, "a[href]"):
            href = (a.get_attribute("href") or "").strip()
            if "doi.org" in href:
                article_url = href
                break
        if not article_url:
            # fallback: any external link that isn't on sydney.edu.au
            for a in li.find_elements(By.CSS_SELECTOR, "a[href]"):
                href = (a.get_attribute("href") or "").strip()
                if href and "sydney.edu.au" not in href:
                    article_url = href
                    break

        # emphasis candidates: title/journal/book often italicized
        em_els = li.find_elements(By.CSS_SELECTOR, "em, i, cite")
        em_texts = [clean_spaces(e.text) for e in em_els if clean_spaces(e.text)]
        first_em = em_texts[0] if em_texts else ""
        last_em  = em_texts[-1] if em_texts else ""

        # looser journal detection
        pt = (pub_type or "").lower()
        looks_like_journal = (
            ("journal" in pt) or
            bool(re.search(r"\bjournal\b", raw_text, re.I)) or
            bool(re.search(r"\bvol\.|\bvolume\b|\bissue\b|\d+\s*\(\d+\)", raw_text, re.I))
        )

        # title: prefer text before FIRST <em>; if empty, use FIRST <em> 
        if first_em and first_em in raw_text:
            title_part = raw_text.split(first_em, 1)[0]
            title = clean_spaces(re.sub(r"\s*,\s*$", "", text_after_year(title_part)))
        else:
            title = text_after_year(raw_text)
        title = re.sub(r"\[\s*More Information\s*\]$", "", title).rstrip(" .")

        if is_empty_title(title) and first_em:
            # common case: the title itself is italicized
            title = first_em

        # journal name: prefer LAST <em> when it looks like a journal
        if looks_like_journal:
            journal_name = last_em or first_em
            if not journal_name:
                # tiny fallback: text right after the year up to the next comma/period
                m_j = re.search(r"\)\.\s*([^.,]+?)(?:,|\.)", raw_text)
                journal_name = clean_spaces(m_j.group(1)) if m_j else ""
        else:
            journal_name = ""

        results.append([
            title,
            year,
            pub_type,
            journal_name,
            article_url,
            researcher_name,
            profile_url
        ])

    return results




def scrape_usyd(urls: List[str], *, print_names: bool = False) -> List[List[str]]:
    """Collect and return CSV rows only (no header, no writing)."""
    d = make_driver()
    out_rows: List[List[str]] = []
    try:
        for url in urls:
            researchers = get_researchers(d, url)
            if print_names:
                print(len(researchers), "researchers found on", url, "\n")
                for name, _ in researchers:
                    print(name)
            for r_name, r_url in researchers:
                try:
                    out_rows.extend(parse_profile(d, r_name, r_url))
                except Exception as e:
                    print(f"Failed on {r_name}: {e}")
                time.sleep(0.25)
    finally:
        try:
            d.quit()
        except Exception:
            pass
    return out_rows
# ---------- main ----------

def main() -> List[List[str]]:
    """
    Entry point for running as a script:
      - scrapes all URLs,
      - writes CSV with original header,
      - prints a summary,
      - returns the rows (useful if we need to call this programs main function).
    """

    header = ["Title","Year","Type","Journal Name","Article URL","Researcher Name","Profile URL"]
    rows = scrape_usyd(URLS, print_names=True)  # set False to silence name prints
    
    
    with open(CSV_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    
    
    print(f"Wrote {len(rows)} rows to {CSV_OUT}")
    return rows


if __name__ == "__main__":
    main()

