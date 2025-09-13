from app.database import SessionLocal
from app.models import Researchers, Publications, Journals
from fuzzywuzzy import process
import csv

def match_journals(threshold=95, force=False, university="all"):
    print("Matching Journal Names With ABDC Rankings")
    db = SessionLocal()
    try:
        journals = db.query(Journals).all()
        journal_names = [j.name for j in journals]
        journal_dict = {j.name: j for j in journals}
        query = db.query(Publications)
        if university != "all":
            query = query.join(Researchers).filter(Researchers.university == university)
        publications = query.all()
        total = len(publications)
        print(f"Total publications to process: {total}")
        progress_bar_len = 40

        def print_progress(count, total):
            filled_len = int(progress_bar_len * count // total)
            bar = '=' * filled_len + '-' * (progress_bar_len - filled_len)
            print(f"\r[{bar}] {count}/{total}", end='', flush=True)

        for idx, pub in enumerate(publications, 1):
            if pub.journal_id and not force:
                print_progress(idx, total)
                continue
            if not pub.journal_name:
                print_progress(idx, total)
                continue
            match, score = process.extractOne(pub.journal_name, journal_names)
            if score >= threshold:
                matched_journal = journal_dict.get(match)
                if matched_journal:
                    pub.journal_id = matched_journal.id
            print_progress(idx, total)
        db.commit()
        print()  # Move to next line after progress bar
    finally:
        db.close()

# # Rapidfuzz Implementation by Frank
# def rank_lookup(journal: Optional[str], names: List[str], ranks: List[str]) -> Optional[str]:
#     """Return the ranking string for the given journal, if matched; else None."""
#     if not journal or not names:
#         return None
#     j = journal.strip()
#     if rf_fuzz is not None:
#         scores = [rf_fuzz.token_set_ratio(j, str(n)) for n in names]
#         if not scores:
#             return None
#         best_i = max(range(len(scores)), key=lambda i: scores[i])
#         if scores[best_i] >= FUZZ_THRESHOLD:
#             return ranks[best_i]
#         return None
#     jl = j.lower()
#     for i, n in enumerate(names):
#         if jl == str(n).lower():
#             return ranks[i]
#     return None

def write_to_csv(all_data, csv_filename):
    print("Writing scraped data to CSV")
    csv_header = ["Title", "Year", "Type", "Journal Name", "Article URL", "Researcher Name", "Profile URL", "Job Title"]
    with open(csv_filename, mode="w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)

    with open(csv_filename, mode="a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in all_data:
            csv_write = row
            writer.writerow(csv_write)

def write_to_db(all_data, university):
    print("Writing data to database")
    db = SessionLocal()
    try:
        for row in all_data:
            pub_title, year, type_val, journal, publication_url, name, profile_url, job_title, job_level = row
            # Don't add researcher if same Name and Profile URL
            researcher = db.query(Researchers).filter_by(name=name, profile_url=profile_url).first()
            if not researcher:
                researcher = Researchers(name=name, university=university, job_title=job_title, profile_url=profile_url, level=job_level)
                db.add(researcher)
                db.commit()
                db.refresh(researcher)
            else:
                # Update existing researcher with job title if it's not empty
                if researcher.job_title != job_title:
                    researcher.job_title = job_title
                    researcher.level = job_level
                    db.commit()
            # Don't add publication if same Title and Researcher
            db_publication = db.query(Publications).filter_by(title=pub_title, researcher_id=researcher.id).first()
            if not db_publication:
                db_publication = Publications(
                    title=pub_title,
                    year=year,
                    publication_type=type_val,
                    journal_name=journal,
                    publication_url=publication_url,
                    researcher_id=researcher.id
                )
                db.add(db_publication)
                db.commit()
                db.refresh(db_publication)
            # Link researcher and publication (if not already linked)
            if db_publication not in researcher.publication:
                researcher.publication.append(db_publication)
                db.commit()
    finally:
        db.close()
        print("Completed writing to database")

if __name__ == "__main__":
    match_journals()