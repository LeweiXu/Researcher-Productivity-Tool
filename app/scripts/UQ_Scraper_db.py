# -*- coding: utf-8 -*-
"""
UQ_Scraper_fixed.py — UQ Business School (Accounting/Finance) via OpenAlex

====================================================
Usage
====================================================
# 1) Install dependencies:
pip install pyalex rapidfuzz requests beautifulsoup4 pandas sqlalchemy

# 2) (Optional) Ensure Journals table is populated first:
python app/scripts/import_journals.py

# 3) Export CSV only:
python app/scripts/UQ_Scraper_fixed.py --out app/files/uq_openalex.csv

# 4) Export CSV + write to DB (journal_id left NULL):
#    Requires app.main.SessionLocal to be importable, or set DATABASE_URL.
python app/scripts/UQ_Scraper_fixed.py --out app/files/uq_openalex_db.csv --to_db
python -m app.scripts.UQ_Scraper_db --out app/files/uq_openalex_db.csv --to_db

# 5) After scraping, match journals to fill Publications.journal_id:
python app/scripts/journal_matching.py
====================================================

What it does
1) Scrape staff profile links from UQ team pages (requests + BeautifulSoup).
2) Resolve a best-match OpenAlex Author at the University of Queensland for each staff (name cleaning + institution filter + fuzzy score).
3) Pull ALL works with cursor pagination (no per-work extra HTTP calls).
4) Write a CSV compatible with your pipeline, and optionally add ABDC/JQL ranking from the latest CSV under app/files/.
5) (Optional) Also write Researchers and Publications into the database; journal_id is intentionally left NULL for journal_matching.py.

Notes
- ABDC/JQL CSV: put the latest file in app/files/ (any name). Columns are auto-detected.
- Fuzzy match uses rapidfuzz if available; falls back to exact match.
- Rate limit: OpenAlex is generous but we still sleep 0.25s per page.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Dict, Iterable, List, Optional, Tuple
from contextlib import contextmanager

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

# --- Make 'app' importable when running the file directly (fixes ModuleNotFoundError) ---
ROOT = Path(__file__).resolve().parents[2]  # repo root (folder that contains 'app/')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Database session + models (aligned with import_journals.py and journal_matching.py)
_sqlalchemy_ok = True
SessionLocal = None
try:
    # Prefer the same SessionLocal used by your other scripts
    from app.main import SessionLocal as _SL  # noqa: E402
    SessionLocal = _SL
except Exception:
    # Fallback for standalone use (won't affect your other scripts)
    try:
        from sqlalchemy.orm import sessionmaker  # noqa: E402
        from sqlalchemy import create_engine     # noqa: E402
        DB_URL = os.getenv("DATABASE_URL", "sqlite:///app/files/uq_publications.db")
        _engine = create_engine(DB_URL, future=True)
        SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    except Exception as _e:
        _sqlalchemy_ok = False
        _import_error = _e

try:
    # Import your ORM models; names must match your provided models
    from app.models import (  # noqa: E402
        Researchers,
        Publications,
        Journals,
        researcher_publication_association,  # not used directly; kept for clarity
    )
except Exception as _e:
    _sqlalchemy_ok = False
    _import_error = _e

# OpenAlex client
from pyalex import Works, Authors, Institutions  # noqa: E402

# ------------- Config -------------
TEAM_URLS = [
    "https://business.uq.edu.au/team/accounting-discipline",
    "https://business.uq.edu.au/team/finance-discipline",
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}
ABDC_DIR = Path("app/files")  # place your ABDC/JQL csv here
FUZZ_THRESHOLD = 90  # journal matching (for CSV "ranking" column only)
SLEEP_PER_PAGE = 0.25
NAME_MIN_SCORE = 70  # author name similarity threshold (tunable)
UQ_UNIVERSITY_NAME = "University of Queensland"

# etiquette (optional)
# from pyalex import config as pyalex_config
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


def load_abdc(dirpath: Path) -> Tuple[List[str], List[str]]:
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
    """Return the ranking string for the given journal, if matched; else None."""
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
    """Scrape staff names and profile URLs from UQ team pages."""
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
    """Find the OpenAlex institution id for 'University of Queensland'."""
    insts = Institutions().search("University of Queensland").get(per_page=5)
    best = max(insts, key=lambda x: (x.get("works_count") or 0))
    return best["id"].split("/")[-1]


def _clean_name(name: str) -> str:
    """Strip common titles and qualifiers from a name string."""
    s = (name or "").strip()
    for p in [
        "Professor ", "Prof ", "Prof. ", "Associate Professor ", "A/Prof ",
        "Adjunct ", "Emeritus Prof ", "Dr ", "Mr ", "Mrs ", "Ms "
    ]:
        if s.lower().startswith(p.lower()):
            s = s[len(p):]
            break
    s = re.sub(r"\([^)]*\)", " ", s)   # remove nicknames in parentheses
    s = re.sub(r",.*$|\|.*$", "", s)   # remove trailing qualifiers
    s = re.sub(r"\s+", " ", s).strip()
    return s


def best_author_id(name: str, inst_id: str) -> Optional[str]:
    """
    Clean the name → search and filter by UQ institution → local similarity score.
    Accept top non-UQ hit only if similarity is very high (>=92).
    """
    q = name or ""
    q = re.sub(r"^(Professor|Prof\.?|Associate Professor|A/Prof|Adjunct|Emeritus Prof|Dr|Mr|Mrs|Ms)\s+",
               "", q, flags=re.I)
    q = re.sub(r"\([^)]*\)", " ", q)           # remove nickname parentheses
    q = re.sub(r",.*$|\|.*$", "", q)           # remove trailing qualifiers
    q = re.sub(r"\s+", " ", q).strip()

    # Strict filter: last_known_institutions.id (plural form)
    picks = Authors().search(q).filter(last_known_institutions={"id": inst_id}).get(per_page=20)
    # Less strict: affiliations.institution.id
    if not picks:
        picks = (Authors().search(q)
                 .filter(affiliations={"institution": {"id": inst_id}})
                 .get(per_page=25))
    # Fallback: plain search (validate locally)
    if not picks:
        picks = Authors().search(q).get(per_page=25)

    best, best_score = None, -1
    for a in picks:
        # Check if this author is associated with UQ
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

        # Prefer UQ authors; otherwise require a very high similarity
        if has_uq or score >= 92:
            if score > best_score:
                best, best_score = a, score

    if best and best_score >= NAME_MIN_SCORE:
        return best["id"].split("/")[-1]
    return None


def iter_author_works(auth_id: str) -> Iterable[dict]:
    """Iterate over all works by an author using cursor-based pagination."""
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
    """Derive venue (journal name) from work."""
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
    """Pick the best available URL: landing page, DOI, or OpenAlex ID."""
    url = (
        _dig(w, "primary_location", "landing_page_url")
        or _dig(w, "best_oa_location", "landing_page_url")
        or ("https://doi.org/" + w.get("doi")) if w.get("doi") else None
        or w.get("id")
    )
    return url


def work_to_row(staff: Staff, w: dict, names: List[str], ranks: List[str]) -> Optional[Dict[str, str]]:
    """Convert an OpenAlex work record into a CSV row."""
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


import re

def normalize_title(title: str) -> str:
    """去掉 HTML 标签并统一大小写"""
    clean = re.sub(r"<.*?>", "", title or "")  # 去掉 HTML 标签
    return clean.strip().lower()


def filter_duplicates(rows):
    """
    去重逻辑: 同一个研究者 + 相同标题 + 相同年份
    如果有多个版本，优先保留非 SSRN 的版本。
    """
    seen = {}
    for r in rows:
        key = (r.get("Researcher"), normalize_title(r.get("Title")), r.get("Year"))
        if key not in seen:
            seen[key] = r
        else:
            # 如果已有的是 SSRN，新来的不是 SSRN -> 替换
            if (seen[key].get("Journal Name") == "SSRN Electronic Journal" 
                and r.get("Journal Name") != "SSRN Electronic Journal"):
                seen[key] = r
            # 如果两个都是 SSRN 或两个都不是，就保留第一个
    return list(seen.values())


def write_rows_csv(rows: Iterable[Dict[str, str]], out_path: Path) -> None:
    """写入 CSV（去重 + SSRN 优化过滤）"""
    # 先做去重和过滤
    rows = filter_duplicates(rows)

    # 二次去重（保证不会有其它重复）
    seen = set()
    unique_rows = []
    for r in rows:
        key = (r.get("Researcher"), normalize_title(r.get("Title")), r.get("Year"))
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)

    ensure_parent_dir(out_path)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        if not unique_rows:
            return
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in unique_rows:
            if r:
                w.writerow(r)




# ------------- DB helpers -------------

@contextmanager
def db_session_or_none():
    """Yield a SessionLocal DB session if available; otherwise yield None (CSV-only mode)."""
    if not _sqlalchemy_ok or SessionLocal is None:
        yield None
        return
    sess = SessionLocal()
    try:
        yield sess
        sess.commit()
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()


def get_or_create_researcher(sess, name: str, university: str, profile_url: str) -> int:
    """
    Insert or fetch a Researcher by (name, university).
    If profile_url is missing on an existing row, update it.
    """
    existing = (
        sess.query(Researchers)
        .filter(Researchers.name == name, Researchers.university == university)
        .first()
    )
    if existing:
        if (not existing.profile_url) and profile_url:
            existing.profile_url = profile_url
            sess.add(existing)
        return existing.id
    obj = Researchers(name=name, university=university, profile_url=profile_url or "")
    sess.add(obj)
    sess.flush()
    return obj.id


def insert_publication_and_link(sess, row: Dict[str, str], researcher_id: int) -> int:
    """
    Insert a Publications row and ensure the many-to-many association is present.
    - journal_id is left NULL for journal_matching.py to fill.
    - Publications.publication_url and journal_name are NOT NULL in your model;
      store empty string when source value is missing.
    Dedup key: (title, year, researcher_id).
    """
    title = row["Title"]
    year = int(row["Year"]) if row.get("Year") else None
    wtype = row.get("Type") or None
    purl = row.get("Article URL") or ""  # NOT NULL column
    jname = row.get("Journal") or ""     # NOT NULL column

    existing = (
        sess.query(Publications)
        .filter(
            Publications.title == title,
            Publications.year == year,
            Publications.researcher_id == researcher_id,
        )
        .first()
    )
    if existing:
        pub = existing
    else:
        pub = Publications(
            title=title,
            year=year,
            publication_type=wtype,
            publication_url=purl,
            journal_name=jname,
            researcher_id=researcher_id,
            journal_id=None,
        )
        sess.add(pub)
        sess.flush()

    # Maintain the many-to-many association via ORM relationship
    researcher = sess.get(Researchers, researcher_id)
    if researcher is not None:
        if all(p.id != pub.id for p in researcher.publication):
            researcher.publication.append(pub)
            sess.add(researcher)

    return pub.id


# ------------- Main -------------

def run(out_csv: Path, to_db: bool = False) -> None:
    names, ranks = load_abdc(ABDC_DIR)

    staff_list = get_staff(TEAM_URLS)
    print(f"Staff collected: {len(staff_list)}")

    inst_id = uq_institution_id()

    all_rows: List[Dict[str, str]] = []
    skipped: List[str] = []

    if to_db and (not _sqlalchemy_ok or SessionLocal is None):
        raise RuntimeError(
            f"--to_db requested but database is not available. "
            f"Import error: {_import_error if '_import_error' in globals() else 'unknown'}"
        )

    with db_session_or_none() as sess:
        for s in staff_list:
            aid = best_author_id(s.name, inst_id)
            if not aid:
                skipped.append(s.name)
                continue
            # If writing to DB, ensure we have a researcher_id
            researcher_id = None
            if to_db and sess is not None:
                researcher_id = get_or_create_researcher(sess, s.name, UQ_UNIVERSITY_NAME, s.profile_url)

            for w in iter_author_works(aid):
                row = work_to_row(s, w, names, ranks)
                if row:
                    all_rows.append(row)
                    if to_db and sess is not None and researcher_id:
                        insert_publication_and_link(sess, row, researcher_id)

    write_rows_csv(all_rows, out_csv)
    if skipped:
        print(f"Skipped (no reliable author match): {skipped}")
    print(f"[DONE] → {out_csv.resolve()}")
    if to_db:
        print("[DONE] DB writes completed (Researchers + Publications; journal_id left NULL).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="app/files/uq_openalex_db.csv", help="Output CSV path")
    ap.add_argument("--to_db", action="store_true", help="Also write Researchers & Publications to the DB (journal_id left NULL)")
    args = ap.parse_args()
    run(Path(args.out), to_db=args.to_db)
