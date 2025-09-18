from fastapi.responses import RedirectResponse, FileResponse
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals

import csv
import io
import datetime

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

