# -*- coding: utf-8 -*-
"""
UQ_Scraper_fixed.py — UQ Business School (Accounting/Finance) via OpenAlex

What it does
1) Scrape staff profile links from UQ team pages (requests + BeautifulSoup).
2) Resolve a best‑match OpenAlex Author at the University of Queensland for each staff (name cleaning + institution filter + fuzzy score).
3) Pull ALL works with cursor pagination (no per‑work extra HTTP calls).
4) Write a CSV compatible with your pipeline, and optionally add ABDC/JQL ranking from the latest CSV under app/files/.

Usage
    pip install pyalex rapidfuzz requests beautifulsoup4 pandas
    python app/scripts/UQ_Scraper_fixed.py --out app/files/uq_openalex.csv

Notes
- ABDC/JQL CSV: put the latest file in app/files/ (any name). Columns are auto‑detected.
- Fuzzy match uses rapidfuzz if available; falls back to exact match.
- Rate limit: OpenAlex is generous but we still sleep 0.25s per page.
"""
from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

# Optional deps
try:
    from rapidfuzz import fuzz as rf_fuzz
except Exception:
    rf_fuzz = None

try:
    import pandas as pd
except Exception:
    pd = None

# OpenAlex client
from pyalex import Works, Authors, Institutions, config as pyalex_config

# ------------- Config -------------
TEAM_URLS = [
    "https://business.uq.edu.au/team/accounting-discipline",
    "https://business.uq.edu.au/team/finance-discipline",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}
ABDC_DIR = Path("app/files")  # place your ABDC/JQL csv here
FUZZ_THRESHOLD = 90  # journal matching
SLEEP_PER_PAGE = 0.25
NAME_MIN_SCORE = 72  # author name similarity threshold

# etiquette (optional)
# pyalex_config.email = "your_email@uq.edu.au"


@dataclass
class Staff:
    name: str
    profile_url: str


# ------------- Utilities -------------

def norm(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


# ------------- ABDC / JQL ranking loader -------------
LIKELY_JCOLS = ["Journal Title", "Journal title", "Title", "Source title", "Journal", "name"]
LIKELY_RCOLS = [
    "ABDC 2022 Rating",
    "ABDC Rating",
    "ABDC Rank",
    "Ranking",
    "Rank",
    "Rating",
    "JQL",
    "2022 rating",
]


def load_abdc(dirpath: Path):
    """Return (journal_names, ranks). If none found, return ([], [])."""
    if not dirpath.exists():
        return ([], [])
    csvs = sorted(dirpath.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not csvs:
        return ([], [])
    path = csvs[0]

    if pd is not None:
        df = pd.read_csv(path)

        def pick(cols: List[str]) -> Optional[str]:
            lut = {c.lower(): c for c in df.columns}
            for c in cols:
                if c.lower() in lut:
                    return lut[c.lower()]
            # heuristic fallback
            for c in df.columns:
                cl = c.lower()
                if ("abdc" in cl and ("rating" in cl or "rank" in cl)) or ("rating" in cl or "rank" in cl):
                    return c
            return None

        jcol = pick(LIKELY_JCOLS)
        rcol = pick(LIKELY_RCOLS)
        if not jcol or not rcol:
            return ([], [])
        return (
            df[jcol].astype(str).fillna("").tolist(),
            df[rcol].astype(str).fillna("").tolist(),
        )

    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    if not rows:
        return ([], [])

    def choose(cands: List[str]) -> str:
        lower = {c.lower(): c for c in rows[0].keys()}
        for c in cands:
            if c.lower() in lower:
                return lower[c.lower()]
        return list(rows[0].keys())[0]

    jh = choose(LIKELY_JCOLS)
    rh = choose(LIKELY_RCOLS)
    return [r.get(jh, "") for r in rows], [r.get(rh, "") for r in rows]


def rank_lookup(journal: Optional[str], names: List[str], ranks: List[str]) -> Optional[str]:
    if not journal or not names:
        return None
    j = journal.strip()
    if rf_fuzz is not None:
        scores = [rf_fuzz.token_set_ratio(j, str(n)) for n in names]
        if not scores:
            return None
        best_i = max(range(len(scores)), key=lambda i: scores[i])
        if scores[best_i] >= FUZZ_THRESHOLD:
            return ranks[best_i]
        return None
    jl = j.lower()
    for i, n in enumerate(names):
        if jl == str(n).lower():
            return ranks[i]
    return None


# ------------- Staff scraping -------------

def get_staff(urls: List[str]) -> List[Staff]:
    staff: Dict[str, str] = {}
    base = "https://business.uq.edu.au"
    for url in urls:
        try:
            html = requests.get(url, headers=HEADERS, timeout=30).text
        except Exception:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/profile/" not in href:
                continue
            name = norm(a.get_text())
            if not name or len(name) < 3:
                continue
            if href.startswith("/"):
                href = base + href
            staff[name] = href
    return [Staff(name=n, profile_url=u) for n, u in staff.items()]


# ------------- OpenAlex helpers -------------

def uq_institution_id() -> str:
    insts = Institutions().search("University of Queensland").get(per_page=5)
    best = max(insts, key=lambda x: (x.get("works_count") or 0))
    return best["id"].split("/")[-1]


def _clean_name(name: str) -> str:
    s = (name or "").strip()
    # strip common titles
    for p in [
        "Professor ", "Prof ", "Prof. ", "Associate Professor ", "A/Prof ",
        "Adjunct ", "Emeritus Prof ", "Dr ", "Mr ", "Mrs ", "Ms "
    ]:
        if s.lower().startswith(p.lower()):
            s = s[len(p):]
            break
    s = re.sub(r"\([^)]*\)", " ", s)  # (nicknames)
    s = re.sub(r",.*$|\|.*$", "", s)   # trailing qualifiers
    s = re.sub(r"\s+", " ", s).strip()
    return s


NAME_MIN_SCORE = 70  # 可再调到 68

def best_author_id(name: str, inst_id: str) -> Optional[str]:
    """
    清洗姓名(去 Prof/Dr/A/Prof/括号昵称/尾随限定) →
    服务端按 UQ 机构过滤(last_known_institutions.id / affiliations.institution.id) →
    本地再校验 + 相似度打分；若无 UQ 命中且相似度极高(>=92)也接受。
    """
    # ---- 清洗姓名 ----
    q = name or ""
    q = re.sub(r"^(Professor|Prof\.?|Associate Professor|A/Prof|Adjunct|Emeritus Prof|Dr|Mr|Mrs|Ms)\s+",
               "", q, flags=re.I)
    q = re.sub(r"\([^)]*\)", " ", q)          # 去括号昵称
    q = re.sub(r",.*$|\|.*$", "", q)          # 去尾随限定
    q = re.sub(r"\s+", " ", q).strip()

    # ---- 1) 严格：按 last_known_institutions.id 过滤（字段是复数！）----
    picks = Authors().search(q).filter(last_known_institutions={"id": inst_id}).get(per_page=20)
    # ---- 2) 次严格：按 affiliations.institution.id 过滤 ----
    if not picks:
        picks = (Authors().search(q)
                 .filter(affiliations={"institution": {"id": inst_id}})
                 .get(per_page=25))
    # ---- 3) 兜底：普通搜索（稍后本地验证）----
    if not picks:
        picks = Authors().search(q).get(per_page=25)

    best, best_score = None, -1
    for a in picks:
        # 本地验证是否与 UQ 有关
        has_uq = False
        if a.get("last_known_institution"):
            try:
                has_uq |= a["last_known_institution"]["id"].endswith(inst_id)
            except Exception:
                pass
        for lki in a.get("last_known_institutions") or []:
            try:
                has_uq |= lki["id"].endswith(inst_id)
            except Exception:
                pass
        for aff in a.get("affiliations") or []:
            try:
                has_uq |= aff["institution"]["id"].endswith(inst_id)
            except Exception:
                pass

        cand = (a.get("display_name") or "").strip()
        if rf_fuzz is not None:
            score = rf_fuzz.token_set_ratio(cand, q)
        else:
            score = 100 if cand.lower() == q.lower() else 0

        # 优先 UQ 作者；若没有 UQ 也允许相似度极高(>=92)的命中
        if has_uq or score >= 92:
            if score > best_score:
                best, best_score = a, score

    if best and best_score >= NAME_MIN_SCORE:
        return best["id"].split("/")[-1]
    return None



def iter_author_works(auth_id: str) -> Iterable[dict]:
    cursor = "*"
    while True:
        page = (
            Works()
            .filter(authorships={"author": {"id": auth_id}})
            .get(per_page=200, cursor=cursor)
        )
        # normalize shapes (dict / OpenAlexResponseList / list)
        results, meta = [], {}
        try:
            if hasattr(page, "results"):
                results = page.results or []
                meta = getattr(page, "meta", {}) or {}
            elif isinstance(page, dict):
                results = page.get("results") or []
                meta = page.get("meta") or {}
            else:
                results = list(page) if page else []
                meta = {}
        except Exception:
            results, meta = [], {}

        if not results:
            break
        for w in results:
            yield w
        cursor = (meta.get("next_cursor") or meta.get("next_cursor_id") or None)
        if not cursor:
            break
        sleep(SLEEP_PER_PAGE)


# ------------- CSV writer -------------
FIELDNAMES = [
    "Researcher",
    "Title",
    "Year",
    "Type",
    "Journal",
    "ranking",
    "Article URL",
    "Profile URL",
]


def _dig(obj, *keys):
    cur = obj or {}
    for k in keys:
        if isinstance(cur, list):
            cur = cur[0] if cur else {}
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _venue_from_work(w: dict) -> str:
    v = (
        _dig(w, "host_venue", "display_name")
        or _dig(w, "primary_location", "source", "display_name")
    )
    if not v:
        for loc in w.get("locations") or []:
            src = (loc or {}).get("source") or {}
            v = (src or {}).get("display_name")
            if v:
                break
    return (v or "").strip()


def _best_url_from_work(w: dict) -> Optional[str]:
    url = (
        _dig(w, "primary_location", "landing_page_url")
        or _dig(w, "best_oa_location", "landing_page_url")
        or ("https://doi.org/" + w.get("doi")) if w.get("doi") else None
        or w.get("id")
    )
    return url


def work_to_row(staff: Staff, w: dict, names: List[str], ranks: List[str]) -> Optional[Dict[str, str]]:
    title = norm(w.get("display_name"))
    year = str(w.get("publication_year") or "")
    wtype = norm(w.get("type"))
    venue = _venue_from_work(w)
    aurl = _best_url_from_work(w)
    if not title or not year:
        return None
    rank = rank_lookup(venue, names, ranks)
    return {
        "Researcher": staff.name,
        "Title": title,
        "Year": year,
        "Type": wtype,
        "Journal": venue,
        "ranking": rank or "",
        "Article URL": aurl or "",
        "Profile URL": staff.profile_url,
    }


def write_rows_csv(rows: Iterable[Dict[str, str]], out_path: Path) -> None:
    ensure_parent_dir(out_path)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in rows:
            if r:
                w.writerow(r)


# ------------- Main -------------

def run(out_csv: Path) -> None:
    names, ranks = load_abdc(ABDC_DIR)

    staff_list = get_staff(TEAM_URLS)
    print(f"Staff collected: {len(staff_list)}")

    inst_id = uq_institution_id()

    all_rows: List[Dict[str, str]] = []
    skipped: List[str] = []

    for s in staff_list:
        aid = best_author_id(s.name, inst_id)
        if not aid:
            skipped.append(s.name)
            continue
        for w in iter_author_works(aid):
            row = work_to_row(s, w, names, ranks)
            if row:
                all_rows.append(row)

    write_rows_csv(all_rows, out_csv)
    if skipped:
        print(f"Skipped (no reliable author match): {skipped}")
    print(f"[DONE] → {out_csv.resolve()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="app/files/uq_openalex.csv", help="Output CSV path")
    args = ap.parse_args()
    run(Path(args.out))
