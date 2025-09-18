import pandas as pd
from app.models import Journals
from app.database import SessionLocal

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
                    abdc_rank=row['rating'],
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
            for i in range(0, len(issns), batch_size):
                batch = issns[i:i+batch_size]
                f.write(";".join(batch) + "\n")
            # Write eISSNs in batches after a line break
            f.write("\n")
            for i in range(0, len(eissns), batch_size):
                batch = eissns[i:i+batch_size]
                f.write(";".join(batch) + "\n")
    finally:
        session.close()
        
if __name__ == "__main__":
    print_issns_in_batches()