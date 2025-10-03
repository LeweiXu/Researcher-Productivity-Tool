from fastapi.responses import RedirectResponse, FileResponse
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals
from pathlib import Path

import pandas as pd
import csv
import io
import datetime
import os
import json

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
        .select_from(Publications)
        .outerjoin(Researchers, Publications.researcher_id == Researchers.id)
        .outerjoin(Journals, Publications.journal_id == Journals.id)
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

def import_clarivate(jif_csv_path):
    session = SessionLocal()
    try:
        with open(jif_csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                issn = str(row.get("ISSN", "")).strip()
                if not issn:
                    continue
                jif = row.get("JIF", None)
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

def update_UWA_staff_fields(file_path="app/files/uploads_current/UWA_staff_field_upload.csv"):
    df = pd.read_csv(file_path)
    # Strip whitespace from column names and values
    df.columns = [col.strip() for col in df.columns]

    session = SessionLocal()
    try:
        for _, row in df.iterrows():
            researcher = session.query(Researchers).filter_by(name=row['Name']).first()
            if researcher:
                researcher.field = row['Field']
        session.commit()
    finally:
        session.close()

def save_uploaded_file(upload_file, filename, save_dir="app/files/uploads_current"):
    """
    Saves an uploaded file to the specified directory.
    Returns the saved file path.
    """
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, filename)
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

def reupload_master_spreadsheet(file_path="app/files/uploads_current/master_spreadsheet_upload.csv"):
    """
    Replaces all data in Journals, Researchers, and Publications tables
    with the data from the uploaded master spreadsheet CSV.
    """
    from app.models import Journals, Researchers, Publications
    from app.database import SessionLocal

    # Define columns as in download_master_csv
    publication_cols = [
        'publication_id', 'title', 'year', 'publication_type', 'publication_url', 
        'num_authors', 'journal_name'
    ]
    researcher_cols = [
        'researcher_id', 'researcher_name', 'university', 'profile_url', 
        'job_title', 'level', 'field'
    ]
    journal_cols = [
        'journal_id', 'journal_name_clean', 'abdc_rank', 'JIF', 'JIF_5_year', 
        'citation_percentage', 'ISSN', 'eISSN', 'publisher', 'abdc_FoR', 'year_of_inception'
    ]
    header = publication_cols + researcher_cols + journal_cols

    df = pd.read_csv(file_path, dtype=str).fillna("")

    session = SessionLocal()
    try:
        # Remove all existing data
        session.query(Publications).delete()
        session.query(Researchers).delete()
        session.query(Journals).delete()
        session.commit()

        # Insert Journals
        journals_map = {}
        for _, row in df.iterrows():
            journal_id = row['journal_id']
            if journal_id and journal_id not in journals_map:
                journal = Journals(
                    id=int(journal_id),
                    name=row['journal_name_clean'],
                    abdc_rank=row['abdc_rank'] or None,
                    JIF=float(row['JIF']) if row['JIF'] else None,
                    JIF_5_year=float(row['JIF_5_year']) if row['JIF_5_year'] else None,
                    citation_percentage=float(row['citation_percentage']) if row['citation_percentage'] else None,
                    ISSN=row['ISSN'] or None,
                    eISSN=row['eISSN'] or None,
                    publisher=row['publisher'] or None,
                    FoR=int(row['abdc_FoR']) if row['abdc_FoR'] else None,
                    year_of_inception=int(row['year_of_inception']) if row['year_of_inception'] else None
                )
                session.add(journal)
                journals_map[journal_id] = journal
        session.commit()

        # Insert Researchers
        researchers_map = {}
        for _, row in df.iterrows():
            researcher_id = row['researcher_id']
            if researcher_id and researcher_id not in researchers_map:
                researcher = Researchers(
                    id=int(researcher_id),
                    name=row['researcher_name'],
                    university=row['university'],
                    profile_url=row['profile_url'] or None,
                    job_title=row['job_title'] or None,
                    level=row['level'] or None,
                    field=row['field'] or None
                )
                session.add(researcher)
                researchers_map[researcher_id] = researcher
        session.commit()

        # Insert Publications
        for _, row in df.iterrows():
            publication_id = row['publication_id']
            if not publication_id:
                continue
            pub = Publications(
                id=int(publication_id),
                title=row['title'],
                year=int(row['year']) if row['year'] else None,
                publication_type=row['publication_type'] or None,
                publication_url=row['publication_url'] or None,
                journal_name=row['journal_name'] or None,
                num_authors=int(row['num_authors']) if row['num_authors'] else None,
                researcher_id=int(row['researcher_id']) if row['researcher_id'] else None,
                journal_id=int(row['journal_id']) if row['journal_id'] else None
            )
            session.add(pub)
        session.commit()
    finally:
        session.close()
        
def switch_db(db_name):
    """
    Switches the database URL and reloads SQLAlchemy engine/session.
    If switching to a new db (not 'main'), copy main.db to the new db if it doesn't exist.
    If switching back to 'main', delete the edit db if it exists.
    Prints the current DB URL after switching.
    """
    from shutil import copyfile
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parents[1]
    main_db_path = project_dir / "app" / "main.db"
    target_db_path = project_dir / "app" / f"{db_name}.db"

    # If switching to edit db, copy main.db if edit db doesn't exist
    if db_name != "main":
        if not target_db_path.exists() and main_db_path.exists():
            copyfile(main_db_path, target_db_path)
    else:
        # If switching back to main, delete edit db if it exists
        edit_db_path = project_dir / "app" / "edit_master.db"
        if edit_db_path.exists():
            edit_db_path.unlink()

    # Attempt to reload SQLAlchemy engine/session
    try:
        from app import database
        database.reload_engine(db_name)
    except Exception as e:
        print(f"Warning: Could not reload SQLAlchemy engine automatically. Please restart the server. Error: {e}")
    return f"Switched to {db_name}.db"