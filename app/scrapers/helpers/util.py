from app.database import SessionLocal
from app.models import Researchers, Publications
import csv
import re
import os
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

        # If force=True, reset all Publications.journal_id to None
        if force:
            print("Resetting all Publications.journal_id to None")
            db.query(Publications).update({Publications.journal_id: None})
            db.commit()

        def print_progress(count, total):
            filled_len = int(progress_bar_len * count // total)
            bar = '=' * filled_len + '-' * (progress_bar_len - filled_len)
            print(f"\r[{bar}] {count}/{total}", end='', flush=True)

        for idx, pub in enumerate(publications, 1):
            if pub.journal_id:
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

def write_to_db(university):
    print(f"Writing {university} data to database")
    csv_path = f"app/files/temp/{university}_data.csv"
    all_data = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_data.append([
                row["Title"],
                row["Year"],
                row["Type"],
                row["Journal Name"],
                row["Article URL"],
                row["Researcher Name"],
                row["Profile URL"],
                row["Job Title"],
                row["Field"]
            ])

    standardize(all_data) #standardize adds the Level field at index 9
    db = SessionLocal()
    try:
        for row in all_data:

            pub_title, year, type_val, journal, publication_url, name, profile_url, job_title, field, job_level = row
            
            # Don't add researcher if title is "Exclude"
            if job_title == "Exclude":
                continue

            # Don't add researcher if same Name and Profile URL
            researcher = db.query(Researchers).filter_by(name=name, profile_url=profile_url).first()
            if not researcher:
                researcher = Researchers(name=name, university=university, job_title=job_title, profile_url=profile_url, level=job_level, field=field)

                db.add(researcher)
                db.commit()
                db.refresh(researcher)
            else:
                # Update existing researcher with job title if it's not empty
                if researcher.job_title != job_title or researcher.field != field:
                    researcher.job_title = job_title
                    researcher.level = job_level
                    researcher.field = field
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

# Scientia Professor = normal professor
# Emiritus = retired
# 
def standardize(data):
    # Enhanced pattern to match titles in any order (e.g., "Professor Emeritus" or "Emeritus Professor")
    title_pattern = re.compile(
        r"^(Dr\.?|Associate Professor|Professor|Ms\.?|Mr\.?|Mrs\.?|Lecturer|Prof\.?|EmPr|AsPr"
        r"|Scientia Professor|Professor Scientia|Emeritus Professor|Professor Emeritus)\s+",
        re.IGNORECASE
    )
    for row in data:
        # Check required fields
        if row[0] == "" or row[2] == "" or row[5] == "" or row[6] == "":
            print(row)
            raise ValueError(f"Missing required field in row: {row}")

        # Ensure NULL fields are set to None
        for i in [1, 3, 4]:
            if row[i] == "":
                row[i] = None

        # Remove unwanted characters from publication type for big 3 universities
        if len(row) > 2 and row[2]:
            type_val = row[2]
            if type_val[-2:] == ' ›':
                type_val = type_val[:-2]
            row[2] = type_val

        # Ensure year is numeric & set to integer
        if row[1] and row[1].isnumeric():
            row[1] = int(row[1])

        # Blacklist certain role keywords
        title_blacklist = ["Education-Focused", "Education Focused", "Education Focussed", "Teaching-Focused", "Teaching Focused", "Teaching Focussed"]
        blacklist_pattern = re.compile(r'\b(?:' + '|'.join(re.escape(term) for term in title_blacklist) + r')\b', re.IGNORECASE)
        if row[7] and blacklist_pattern.search(row[7]):
            row[7] = "Exclude"
        else:
            # Ensure role names are expected
            # Define all possible forms and their canonical mapping
            title_map = {
                "Associate Lecturer": "Associate Lecturer",
                "Lecturer (A)": "Associate Lecturer",
                "Lecturer": "Lecturer",
                "Fellow": "Fellow",
                "Senior Lecturer": "Senior Lecturer",
                "Senior Fellow": "Senior Fellow",
                "Associate Professor": "Associate Professor",
                "Associate Prof": "Associate Professor",
                "Professor": "Professor",
                "Professorial Fellow": "Professorial Fellow",
                "Professor Emeritus": "Professor Emeritus",
                "Emeritus Professor": "Professor Emeritus"
            }
            # Sort by length so longer matches take priority
            titles = sorted(title_map.keys(), key=len, reverse=True)
            pattern = r"\b(" + "|".join(re.escape(t) for t in titles) + r")\b"
            match = re.search(pattern, row[7], flags=re.IGNORECASE)
            if match:
                raw = match.group()
                row[7] = title_map.get(raw, raw)  # map to canonical form
            else:
                row[7] = None
            
            # Check name for title if no title found
            name_roles = ["Associate Professor", "Professor"]
            name_roles = sorted(name_roles, key=len, reverse=True)
            if row[7] is None:
                for role in name_roles:
                    if role.lower() in row[5].lower():
                        row[7] =  role

        # Clean researcher name
        if len(row) > 5 and row[5]:
            row[5] = title_pattern.sub("", row[5]).strip()

        # Add role levels
        role_level_map = {
            "Associate Lecturer": "A",
            "Lecturer": "B",
            "Fellow": "B",
            "Senior Lecturer": "C",
            "Senior Fellow": "C",
            "Associate Professor": "D",
            "Professor": "E",
            "Professorial Fellow": "E",
            "Professor Emeritus": "E",
            "Exclude": None
        }
        if row[7] is None:
            role_level = None
        else:
            try:
                role_level = role_level_map[row[7]]
            except KeyError:
                role_level = None
        row.insert(9, role_level)

        # TODO: standardize "Type" e.g. journal article, contribution to journal etc. --> journal article

if __name__ == "__main__":
    write_to_db("MU")
    match_journals(university="MU")