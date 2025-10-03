from app.database import SessionLocal, reload_engine
from app.models import Publications

def cleanup_years(db_name="main"):
    """
    Cleans up the 'year' column in Publications table for the specified database.
    Truncates all year values to the first 4 characters (if present).
    """
    reload_engine(db_name)  # Ensure engine/session points to the correct DB

    session = SessionLocal()
    try:
        publications = session.query(Publications).all()
        print(f"Cleaning up 'year' for {len(publications)} publications in {db_name}.db")
        for pub in publications:
            year = pub.year
            if year is not None:
                year_str = str(year).strip()
                if len(year_str) >= 4:
                    cleaned_year = int(year_str[:4])
                else:
                    cleaned_year = None
                if cleaned_year != pub.year:
                    pub.year = cleaned_year
        session.commit()
    finally:
        session.close()

if __name__ == "__main__":
    cleanup_years()