from fastapi.responses import RedirectResponse, FileResponse
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals

import pandas as pd
import csv
import io
import datetime
import os

def download_master_csv(request):
    """
    Streams a master spreadsheet joining Researchers, Publications, and Journals.
    Each row = one publication of one researcher with its journal.
    All columns from all three tables are included.
    """
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/", status_code=303)

    db: Session = SessionLocal()

    # Get all columns for each table
    researcher_cols = [c.name for c in Researchers.__table__.columns]
    publication_cols = [c.name for c in Publications.__table__.columns]
    journal_cols = [c.name for c in Journals.__table__.columns]

    # Build query with all columns
    qry = (
        db.query(
            *[getattr(Publications, col) for col in publication_cols],
            *[getattr(Researchers, col) for col in researcher_cols],
            *[getattr(Journals, col) for col in journal_cols],
        )
        .join(Researchers, Publications.researcher_id == Researchers.id)
        .join(Journals, Publications.journal_id == Journals.id)
    )

    # Header: publication columns + researcher columns + journal columns
    header = publication_cols + researcher_cols + journal_cols

    def csv_iter():
        buf = io.StringIO()
        writer = csv.writer(buf)

        # header
        writer.writerow(header)
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)

        # rows
        for row in qry.yield_per(500):
            writer.writerow(row)
            yield buf.getvalue()
            buf.seek(0); buf.truncate(0)

        db.close()

    ts = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"master_spreadsheet_{ts}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(csv_iter(), media_type="text/csv", headers=headers)

def download_ABDC_template():
    return FileResponse("app/files/upload_templates/ABDC_template.csv", media_type="text/csv", filename="ABDC_template.csv")

def download_clarivate_template():
    return FileResponse("app/files/upload_templates/clarivate_template.csv", media_type="text/csv", filename="clarivate_template.csv")

def download_UWA_staff_field_template():
    return FileResponse("app/files/upload_templates/UWA_staff_field_template.csv", media_type="text/csv", filename="UWA_staff_field_template.csv")

def replace_ABDC_rankings(file_path="app/files/uploads_current/ABDC_upload.csv"):
    df = pd.read_csv(file_path)
    # Strip whitespace from column names and values
    df.columns = [col.strip() for col in df.columns]

    session = SessionLocal()
    try:
        # Remove all existing data from Journals table
        session.query(Journals).delete()
        session.commit()
        # Add new data
        for _, row in df.iterrows():
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

def save_uploaded_file(upload_file, save_dir="app/files/uploads_current"):
    """
    Saves an uploaded file to the specified directory.
    Returns the saved file path.
    """
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, "ABDC_upload.csv")
    upload_file.file.seek(0)  # Ensure pointer is at start
    with open(file_path, "wb") as buffer:
        while True:
            chunk = upload_file.file.read(1024 * 1024)
            if not chunk:
                break
            buffer.write(chunk)
    # Log file path and size for confirmation
    print(f"File saved to: {file_path}")
    print(f"File size: {os.path.getsize(file_path)} bytes")
    return file_path