def get_researcher_profile(request):    
    db = SessionLocal()
    try:
        researcher = (
            db.query(Researchers).filter(Researchers.id == researcher_id).first()
        )
        if not researcher:
            return HTMLResponse(content="Researcher not found", status_code=404)

        publications = (
            db.query(Publications, Journals)
            .outerjoin(Journals, Publications.journal_id == Journals.id)
            .filter(Publications.researcher_id == researcher_id)
            .all()
        )

        pub_list = []
        for pub, journal in publications:
            pub_list.append(
                {
                    "title": pub.title,
                    "journal": journal.name if journal else pub.journal_name,
                    "year": pub.year,
                    "ranking": journal.abdc_rank if journal else "",
                    "h_index": journal.h_index if journal else "",
                }
            )

        researcher_data = {
            "name": researcher.name,
            "level": "",        # fill if you have this field
            "department": "",   # fill if you have this field
            "university": researcher.university,
            "profile_url": researcher.profile_url,
        }
    finally:
        db.close()
