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
    Columns are properly organized and prefixed to avoid confusion.
    """
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/", status_code=303)

    db: Session = SessionLocal()

    # Define clean, organized column structure
    # Publication columns (core data)
    publication_cols = [
        'publication_id', 'title', 'year', 'publication_type', 'publication_url', 
        'num_authors', 'journal_name'
    ]
    
    # Researcher columns
    researcher_cols = [
        'researcher_id', 'researcher_name', 'university', 'profile_url', 
        'job_title', 'level', 'field'
    ]
    
    # Journal columns
    journal_cols = [
        'journal_id', 'journal_name_clean', 'abdc_rank', 'JIF', 'JIF_5_year', 
        'citation_percentage', 'ISSN', 'eISSN', 'publisher', 'abdc_FoR', 'year_of_inception'
    ]

    # Build query with proper column selection and aliasing
    qry = (
        db.query(
            # Publication data
            Publications.id.label('publication_id'),
            Publications.title,
            Publications.year,
            Publications.publication_type,
            Publications.publication_url,
            Publications.num_authors,
            Publications.journal_name,
            
            # Researcher data
            Researchers.id.label('researcher_id'),
            Researchers.name.label('researcher_name'),
            Researchers.university,
            Researchers.profile_url,
            Researchers.job_title,
            Researchers.level,
            Researchers.field,
            
            # Journal data
            Journals.id.label('journal_id'),
            Journals.name.label('journal_name_clean'),
            Journals.abdc_rank,
            Journals.JIF,
            Journals.JIF_5_year,
            Journals.citation_percentage,
            Journals.ISSN,
            Journals.eISSN,
            Journals.publisher,
            Journals.FoR.label('abdc_FoR'),
            Journals.year_of_inception
        )
        .join(Researchers, Publications.researcher_id == Researchers.id)
        .join(Journals, Publications.journal_id == Journals.id)
    )

    # Clean header with all columns
    header = publication_cols + researcher_cols + journal_cols

    def csv_iter():
        buf = io.StringIO()
        writer = csv.writer(buf)

        # Write header
        writer.writerow(header)
        yield buf.getvalue()
        buf.seek(0); buf.truncate(0)

        # Write data rows
        for row in qry.yield_per(500):
            # Convert row to list and handle None values
            row_data = []
            for value in row:
                if value is None:
                    row_data.append('')
                else:
                    row_data.append(str(value))
            writer.writerow(row_data)
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