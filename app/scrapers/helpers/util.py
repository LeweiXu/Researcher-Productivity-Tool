from app.scrapers.helpers.shared_functions import write_to_db
from app.scrapers.helpers.shared_functions import match_journals
from app.database import SessionLocal
from app.models import Researchers, Publications
from sqlalchemy import text
import csv
import re
import os

CSV_DIR = "app/files"
csv_paths = [os.path.join(CSV_DIR, f) for f in os.listdir(CSV_DIR) if f.endswith("_data.csv")]

# NOTE: Scrapers return a list of lists in the format ["Title", "Year", "Type", "Journal Name", "Article URL", "Researcher Name", "Profile URL", "Role"]

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
            raise ValueError(f"Missing required field in row: {row}")

        # Ensure NULL fields are set to None
        for i in [1, 3, 4]:
            if row[i] == "":
                row[i] = None

        # Clean researcher name
        if len(row) > 5 and row[5]:
            row[5] = title_pattern.sub("", row[5]).strip()

        # Remove unwanted characters from publication type for big 3 universities
        if len(row) > 2 and row[2]:
            type_val = row[2]
            if type_val[-2:] == ' ›':
                type_val = type_val[:-2]
            row[2] = type_val

        # Ensure year is numeric & set to integer
        if row[1] and row[1].isnumeric():
            row[1] = int(row[1])

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
            "Professor Emeritus": "E"
        }
        if row[7] is None:
            role_level = None
        else:
            role_level = role_level_map[row[7]]
        row.insert(8, role_level)

        # TODO: standardize "Type" e.g. journal article, contribution to journal etc. --> journal article

# Run standardize() function on all CSV files, then rewrite to database
def re_standardize():
    db = SessionLocal()
    try:
        # Clear association table first
        db.execute(text('DELETE FROM Researcher_publication_association'))
        db.commit()
        # Clear Publications and Researchers
        db.query(Publications).delete()
        db.query(Researchers).delete()
        db.commit()
    finally:
        db.close()
        print("Successfully Removed All Data")

    for csv_path in csv_paths:
        university = csv_path.split("/")[-1].split("_")[0]  # Extract university name from file name
        print(f"Re-standardizing {csv_path}")
        # Read CSV
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            return
        print(f"Successfully read {csv_path}")
        header, data = rows[0], rows[1:]
        standardize(data)
        # Write back to same file
        with open(csv_path, mode="w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(data)
        print(f"Successfully wrote standardized data to {csv_path}")
        write_to_db(data, university)
        match_journals(university=university)

def import_from_csv(university, csv_path):
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
                row["Field"]
            ])

    standardize(all_data)
    write_to_db(all_data, university)
    match_journals(university=university)

if __name__ == "__main__":
    for university in ['ANU',  'MU', 'UA', 'UM', 'UNSW', 'UQ', 'USYD', 'UWA']:
        print(f"Importing CSV for {university}")
        import_from_csv(university, os.path.join(CSV_DIR, f"{university}_data.csv"))
        print(f"Completed importing CSV for {university}")