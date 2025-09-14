import pandas as pd
from app.models import Journals
from app.database import SessionLocal

# Path to the CSV file
CSV_PATH = "./app/files/2022 JQL.csv"

def import_journals():
    df = pd.read_csv(CSV_PATH)
    # Strip whitespace from column names and values
    df.columns = [col.strip() for col in df.columns]
    df = df[["Journal Title", "Publisher", "2022 rating"]]
    df = df.rename(columns={
        "Journal Title": "name",
        "Publisher": "publisher",
        "2022 rating": "abdc_rank"
    })
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

    session = SessionLocal()
    try:
        for _, row in df.iterrows():
            # Check if journal already exists
            existing = session.query(Journals).filter_by(name=row['name']).first()
            if not existing:
                journal = Journals(
                    name=row['name'],
                    abdc_rank=row['abdc_rank'],
                    #impact_factor=None,
                    #h_index=None,
                    publisher=row['publisher']
                )
                session.add(journal)
        session.commit()
    finally:
        session.close()

if __name__ == "__main__":
    import_journals()