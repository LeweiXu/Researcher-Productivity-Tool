# -*- coding: utf-8 -*-
"""
Selenium 版本：抓取 UQ Business School -> 个人主页 -> Publications
- 入口页：Accounting / Finance discipline team pages
- 过滤职位：Lecturer / Senior Lecturer / Professor / Associate Professor / Senior Research Fellow
- 进入个人主页后解析 Publications（Journal / Conference / Working Paper 等）
- 在 app/files/ 中自动挑“最新年份”的 ABDC/JQL CSV，做期刊排名模糊匹配
- 输出 uq_publications.csv

运行：
  PowerShell（临时放开执行策略）：
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    venv\Scripts\activate
    python -u app\scripts\scrape_uq_business_selenium.py

依赖：selenium, beautifulsoup4, rapidfuzz, pandas
"""
import csv
import random
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup
from rapidfuzz import fuzz, process

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ----------------- 配置 -----------------
TEAM_URLS = [
    "https://business.uq.edu.au/team/accounting-discipline",
    "https://business.uq.edu.au/team/finance-discipline",
]

KEEP_TITLES = [
    "lecturer",
    "senior lecturer",
    "professor",
    "associate professor",
    "senior research fellow",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)

SLEEP_RANGE = (0.3, 0.7)   # 请求间隔（秒）
OUT_CSV = Path("uq_publications.csv")
FUZZ_THRESHOLD = 90        # 期刊名匹配阈值（0-100）

# 不同年份 CSV 的列名可能不同，这里列出候选
JOURNAL_COL_CANDIDATES = ["Journal Title", "Journal title", "Title", "Source title", "Journal", "name"]
RANK_COL_CANDIDATES    = ["ABDC 2022 Rating", "ABDC Rating", "ABDC Rank", "Ranking", "Rank", "Rating", "JQL", "abdc_rank"]

# ----------------- 工具函数 -----------------
def PROJECT_ROOT() -> Path:
    return Path(__file__).resolve().parents[2]

ROOT = PROJECT_ROOT()
ABDC_DIR = ROOT / "app" / "files"

def _sleep():
    lo, hi = SLEEP_RANGE
    time.sleep(random.uniform(lo, hi))

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def contains_any(hay: str, needles: List[str]) -> bool:
    h = (hay or "").lower()
    return any(n in h for n in needles)

def extract_year(text: str) -> Optional[str]:
    m = re.search(r"(19|20)\d{2}", text or "")
    return m.group(0) if m else None

def pick_doi_or_link(block: BeautifulSoup) -> Optional[str]:
    for a in block.select("a[href]"):
        href = a.get("href", "")
        if "doi.org" in href.lower():
            return href
    for a in block.select("a[href]"):
        href = a.get("href", "")
        if href.startswith("http"):
            return href
    return None

def extract_title(block: BeautifulSoup) -> Optional[str]:
    a = block.select_one("a")
    if a:
        t = norm(a.get_text())
        if t:
            return t
    for sel in ("strong", "b", "em", "i"):
        tag = block.select_one(sel)
        if tag:
            t = norm(tag.get_text())
            if t:
                return t
    txt = norm(block.get_text(" "))
    return txt.split(".")[0][:200] if txt else None

def extract_journal(block: BeautifulSoup) -> Optional[str]:
    for sel in ("em", "i"):
        for tag in block.select(sel):
            cand = norm(tag.get_text())
            if cand and len(cand) > 3:
                return cand
    txt = norm(block.get_text(" "))
    if "doi.org" in txt.lower():
        left = txt[:txt.lower().rfind("doi.org")]
        parts = [p.strip() for p in re.split(r"[.;]", left) if p.strip()]
        if parts:
            cand = re.sub(r"\([^)]*\)", "", parts[-1]).strip()
            if re.search(r"(Journal|Review|Quarterly|Finance|Management|Economics|Accounting)", cand, re.I):
                return cand
    return None

def section_type_from_heading(h: str) -> str:
    hl = (h or "").lower()
    if "journal" in hl:
        return "Journal Article"
    if "conference" in hl:
        return "Conference Paper"
    if "working" in hl:
        return "Working Paper"
    if "publication" in hl:
        return "Publication"
    return "Other"

def _pick_latest_csv(dirpath: Path) -> Optional[Path]:
    csvs = list(dirpath.glob("*.csv"))
    if not csvs:
        return None
    def year_from_name(p: Path) -> int:
        m = re.search(r"(20\d{2})", p.name)
        return int(m.group(1)) if m else -1
    csvs.sort(key=lambda p: (year_from_name(p), p.stat().st_mtime), reverse=True)
    return csvs[0]

def _get_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    # 1) 先做大小写无关的精确匹配
    lut = {c.lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lut:
            return lut[c.lower()]

    # 2) 兜底：模糊包含匹配
    cols = [c for c in df.columns]
    cols_l = [c.lower() for c in cols]

    # 优先包含 "abdc" 且包含 "rating"/"rank" 的列
    for i, cl in enumerate(cols_l):
        if ("abdc" in cl) and (("rating" in cl) or ("rank" in cl)):
            return cols[i]

    # 再退一步：任何包含 "rating" 或 "rank" 的列
    for i, cl in enumerate(cols_l):
        if ("rating" in cl) or ("rank" in cl):
            return cols[i]

    return None


def load_abdc_latest() -> Tuple[List[str], List[str], Path]:
    csv_path = _pick_latest_csv(ABDC_DIR)
    if not csv_path or not csv_path.exists():
        raise FileNotFoundError(f"ABDC/JQL CSV not found in: {ABDC_DIR}")
    df = pd.read_csv(csv_path)
    jcol = _get_col(df, JOURNAL_COL_CANDIDATES)
    rcol = _get_col(df, RANK_COL_CANDIDATES)
    if not jcol:
        raise KeyError(f"Cannot find journal-name column in {csv_path.name}. "
                       f"Tried: {JOURNAL_COL_CANDIDATES}\nAvailable: {list(df.columns)}")
    if not rcol:
        raise KeyError(f"Cannot find ranking column in {csv_path.name}. "
                       f"Tried: {RANK_COL_CANDIDATES}\nAvailable: {list(df.columns)}")
    names = df[jcol].astype(str).fillna("").tolist()
    ranks = df[rcol].astype(str).fillna("").tolist()
    return names, ranks, csv_path

def lookup_abdc_rank(journal: str, names: List[str], ranks: List[str],
                     threshold: int = FUZZ_THRESHOLD) -> Optional[str]:
    if not journal or not names:
        return None
    match = process.extractOne(journal, names, scorer=fuzz.token_set_ratio)
    if match and match[1] >= threshold:
        idx = names.index(match[0])
        return ranks[idx]
    return None

# ----------------- Selenium -----------------
def make_driver() -> webdriver.Chrome:
    opts = Options()
    # 新的 headless 渲染，更接近真实浏览器
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument(f"--user-agent={USER_AGENT}")
    # Selenium 4.6+ 默认用 Selenium Manager 自动下载 chromedriver
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(40)
    return driver

def go_to_publications(driver: webdriver.Chrome):
    """尽量点击进入页面中的 Publications 区域（锚点或 tab）。"""
    candidates = [
        (By.LINK_TEXT, "Publications"),
        (By.PARTIAL_LINK_TEXT, "Publications"),
        (By.LINK_TEXT, "Works"),
        (By.PARTIAL_LINK_TEXT, "Works"),
        (By.CSS_SELECTOR, 'a[href*="#publications"]'),
    ]
    for by, sel in candidates:
        try:
            el = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((by, sel)))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            el.click()
            time.sleep(0.5)
            break
        except Exception:
            continue

def expand_all_more(driver: webdriver.Chrome):
    """把“Show more / View more / Load more / More”都点开（若存在）。"""
    labels = ["Show more", "View more", "Load more", "More"]
    for _ in range(6):  # 最多点 6 次，防止死循环
        clicked = False
        try:
            buttons = driver.find_elements(By.XPATH, "//button|//a")
            for b in buttons:
                txt = (b.text or "").strip().lower()
                if any(l.lower() in txt for l in labels):
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", b)
                        b.click()
                        time.sleep(0.6)
                        clicked = True
                    except Exception:
                        pass
            if not clicked:
                break
        except Exception:
            break


def get_html(driver: webdriver.Chrome, url: str, wait_css: Optional[str] = None, timeout: int = 25) -> str:
    driver.get(url)
    if wait_css:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_css)))

    # 逐步滚动，触发懒加载
    last_h = 0
    for _ in range(10):
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
        time.sleep(0.6)
        h = driver.execute_script("return document.body.scrollHeight;")
        if h == last_h:
            break
        last_h = h
    time.sleep(0.4)
    return driver.page_source


# ----------------- 抓团队页 → 研究者 -----------------
def gather_researchers_with_selenium(driver: webdriver.Chrome, team_url: str) -> List[Dict]:
    html = get_html(driver, team_url, wait_css='a[href*="/profile/"]')
    soup = BeautifulSoup(html, "html.parser")
    people = []
    for a in soup.select('a[href*="/profile/"]'):
        name = norm(a.get_text())
        if not name:
            continue
        role = ""
        card = a.parent
        if card:
            role = norm(card.get_text(" "))
        if not role:
            continue
        if contains_any(role, KEEP_TITLES):
            profile_url = a.get("href", "")
            if profile_url and profile_url.startswith("/"):
                from urllib.parse import urljoin
                profile_url = urljoin(team_url, profile_url)
            people.append({"name": name, "role": role, "profile_url": profile_url})
    # 去重
    seen = set()
    uniq = []
    for p in people:
        if p["profile_url"] not in seen:
            uniq.append(p); seen.add(p["profile_url"])
    return uniq

# ----------------- 抓个人页 → Publications -----------------
def scrape_profile_publications_with_selenium(driver: webdriver.Chrome, profile_url: str) -> List[Dict]:
    driver.get(profile_url)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1, h2, h3")))
    time.sleep(0.4)

    # 跳到 Publications 分区并展开更多
    go_to_publications(driver)
    expand_all_more(driver)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    # 可能的 Publications 容器
    sections: List[BeautifulSoup] = []
    candidates = [
        '#publications', 'section#publications', 'div#publications',
        'div[id*="publications"]', 'section[id*="publications"]',
        'div.publications', 'div.view-publications',
        'div.views-element-container', 'div.field--name-field-publications',
        'div.block-views',
    ]
    for sel in candidates:
        sections.extend(soup.select(sel))

    if not sections:
        # 以“Publications/Works/Journal ...”标题为锚，找后续容器
        for hd in soup.select("h2, h3"):
            htxt = norm(hd.get_text())
            if any(k in htxt.lower() for k in ["publication", "works", "journal", "conference", "working"]):
                sec = hd.find_next(lambda t: t and t.name in ["ul", "ol", "div", "section"])
                if sec:
                    sections.append(sec)

    results: List[Dict] = []

    def consume_items(container: BeautifulSoup, heading: Optional[str]):
        work_type = section_type_from_heading(heading or "")
        items = container.select("li")
        items += container.select("article.publication, div.views-row, div.card, div.item")
        if not items:
            items = container.select("p, div, article")
        for it in items:
            text = norm(it.get_text(" "))
            title = extract_title(it)
            if not title:
                continue
            year = extract_year(text)
            journal = extract_journal(it)
            url = pick_doi_or_link(it)
            results.append({
                "Title": title,
                "Year": year,
                "Type": work_type,
                "Journal": journal,
                "Article URL": url,
            })

    if sections:
        for sec in sections:
            prev = sec.find_previous(["h2", "h3"])
            prev_title = norm(prev.get_text()) if prev else None
            consume_items(sec, prev_title)
    else:
        # 兜底：全页扫描
        for hd in soup.select("h2, h3"):
            t = norm(hd.get_text())
            if any(k in t.lower() for k in ["journal", "conference", "working", "publication", "works"]):
                sec = hd.find_next(lambda x: x and x.name in ["ul", "ol", "div", "section"])
                if sec:
                    consume_items(sec, t)

    return results



# ----------------- 主流程 -----------------
def main():
    print(f"[SCRAPER] Root: {ROOT}")
    print(f"[SCRAPER] ABDC dir: {ABDC_DIR}")

    abdc_names, abdc_ranks, chosen_csv = load_abdc_latest()
    print(f"[ABDC] Using CSV: {chosen_csv.name}")

    driver = make_driver()
    try:
        all_people: List[Dict] = []
        for url in TEAM_URLS:
            print(f"[TEAM] {url}")
            ppl = gather_researchers_with_selenium(driver, url)
            print(f"  -> {len(ppl)} people (filtered)")
            all_people.extend(ppl)

        # 去重
        seen = set()
        unique_people = []
        for p in all_people:
            if p["profile_url"] not in seen:
                unique_people.append(p); seen.add(p["profile_url"])

        print(f"[TOTAL] researchers to scrape: {len(unique_people)}")

        rows: List[Dict] = []
        for i, person in enumerate(unique_people, 1):
            print(f"[{i}/{len(unique_people)}] {person['name']}  {person['profile_url']}")
            try:
                pubs = scrape_profile_publications_with_selenium(driver, person["profile_url"])
            except Exception as e:
                print(f"  !! failed: {e}")
                continue
            for p in pubs:
                rank = lookup_abdc_rank(p.get("Journal"), abdc_names, abdc_ranks)
                rows.append({
                    "Researcher": person["name"],
                    "Title": p.get("Title"),
                    "Year": p.get("Year"),
                    "Type": p.get("Type"),
                    "Journal": p.get("Journal"),
                    "ranking": rank,
                    "Article URL": p.get("Article URL"),
                    "Profile URL": person["profile_url"],
                })

        # 去重 (Researcher, Title, Year)
        seen_keys = set()
        dedup: List[Dict] = []
        for r in rows:
            k = (r["Researcher"], r.get("Title") or "", r.get("Year") or "")
            if k not in seen_keys:
                dedup.append(r); seen_keys.add(k)

        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "Researcher",
                    "Title",
                    "Year",
                    "Type",
                    "Journal",
                    "ranking",
                    "Article URL",
                    "Profile URL",
                ],
            )
            w.writeheader()
            w.writerows(dedup)

        print(f"[DONE] Saved -> {OUT_CSV.resolve()} (rows: {len(dedup)})")
    finally:
        driver.quit()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
