import pandas as pd
from app.models import Journals
from app.database import SessionLocal
import csv
import os
import fnmatch

# Path to the CSV file
CSV_PATH = "./app/files/2022 JQL.csv"

def import_journals(CSV_PATH=CSV_PATH):
    df = pd.read_csv(CSV_PATH)
    # Strip whitespace from column names and values
    df.columns = [col.strip() for col in df.columns]

    session = SessionLocal()
    try:
        for _, row in df.iterrows():
            # Check if journal already exists
            existing = session.query(Journals).filter_by(name=row['Journal Title']).first()
            if not existing:
                journal = Journals(
                    name=row['Journal Title'],
                    abdc_rank=row['Rating'],
                    publisher=row['Publisher'],
                    ISSN=row['ISSN'],
                    eISSN=row['ISSN Online'],
                    FoR=row['FoR'],
                    year_of_inception=row['Year Inception']
                )
                session.add(journal)
        session.commit()
    finally:
        session.close()

def print_issns_in_batches(batch_size=600):
    session = SessionLocal()
    output_path = "./app/files/temp/issn_batches.txt"
    try:
        issns = [j.ISSN for j in session.query(Journals).filter(Journals.ISSN.isnot(None)).all() if j.ISSN]
        eissns = [j.eISSN for j in session.query(Journals).filter(Journals.eISSN.isnot(None)).all() if j.eISSN]
        with open(output_path, "w") as f:
            # Write ISSNs in batches
            f.write("ISSNs:\n")
            for i in range(0, len(issns), batch_size):
                batch = issns[i:i+batch_size]
                f.write(f"BATCH {i//600 + 1}:\n")
                f.write(";".join(batch) + "\n")
            # Write eISSNs in batches after a line break
            f.write("\n")
            f.write("eISSNs:\n")
            for i in range(0, len(eissns), batch_size):
                batch = eissns[i:i+batch_size]
                f.write(f"BATCH {i//600 + 1}:\n")
                f.write(";".join(batch) + "\n")
    finally:
        session.close()

def import_jif_csv(jif_csv_path):
    session = SessionLocal()
    try:
        with open(jif_csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                issn = str(row.get("ISSN", "")).strip()
                if not issn:
                    continue
                jif = row.get("2024 JIF", None)
                jif_5 = row.get("5 Year JIF", None)
                citation_pct = row.get("% of Citable OA", None)
                # Remove % and convert to float if needed
                if isinstance(citation_pct, str) and "%" in citation_pct:
                    citation_pct = citation_pct.replace("%", "").strip()
                try:
                    jif = float(jif) if jif not in [None, ""] else None
                except Exception:
                    jif = None
                try:
                    jif_5 = float(jif_5) if jif_5 not in [None, ""] else None
                except Exception:
                    jif_5 = None
                try:
                    citation_pct = float(citation_pct) if citation_pct not in [None, ""] else None
                except Exception:
                    citation_pct = None

                journal = session.query(Journals).filter_by(ISSN=issn).first()
                if journal:
                    journal.JIF = jif
                    journal.JIF_5_year = jif_5
                    journal.citation_percentage = citation_pct
        session.commit()
    finally:
        session.close()

def import_all_jif(csv_dir="app/files/uploads_current"):
    for fname in os.listdir(csv_dir):
        if fnmatch.fnmatch(fname, "JIF_*.csv"):
            path = os.path.join(csv_dir, fname)
            print(f"Importing JIF data from {path}")
            import_jif_csv(path)

if __name__ == "__main__":
    import_all_jif()