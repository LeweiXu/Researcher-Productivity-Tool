from fastapi import Request
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals

def get_researcher_data(request: Request):
    sort_by = request.query_params.get("sort_by", "total_articles")
    db = SessionLocal()
    try:
        researchers = db.query(Researchers).all()
        researcher_list = []
        for r in researchers:
            pubs = db.query(Publications).filter(Publications.researcher_id == r.id).all()
            total_articles = len(pubs)
            abdc_a_star_a = 0
            jif_list = []
            jif5_list = []
            citation_list = []
            for pub in pubs:
                journal = db.query(Journals).filter(Journals.id == pub.journal_id).first() if pub.journal_id else None
                if journal:
                    if journal.abdc_rank in ["A*", "A"]:
                        abdc_a_star_a += 1
                    if journal.JIF is not None:
                        jif_list.append(journal.JIF)
                    if journal.JIF_5_year is not None:
                        jif5_list.append(journal.JIF_5_year)
                    if journal.citation_percentage is not None:
                        citation_list.append(journal.citation_percentage)
            avg_jif = round(sum(jif_list)/len(jif_list), 2) if jif_list else 0
            avg_jif5 = round(sum(jif5_list)/len(jif5_list), 2) if jif5_list else 0
            avg_citation = round(sum(citation_list)/len(citation_list), 2) if citation_list else 0
            # Add a variable field for the selected statistic
            if sort_by == "total_articles":
                variable_value = total_articles
                variable_label = "Total Articles"
            elif sort_by == "abdc_a_star_a":
                variable_value = abdc_a_star_a
                variable_label = "A*/A Journals"
            elif sort_by == "avg_jif":
                variable_value = avg_jif
                variable_label = "Avg. JIF"
            elif sort_by == "avg_jif_5":
                variable_value = avg_jif5
                variable_label = "Avg. 5-Year JIF"
            elif sort_by == "avg_citation":
                variable_value = avg_citation
                variable_label = "Avg. Citation %"
            else:
                variable_value = total_articles
                variable_label = "Total Articles"
            researcher_list.append({
                "id": str(r.id),
                "name": r.name,
                "FoR": r.field,
                "level": r.level,
                "university": r.university,
                "total_articles": total_articles,
                "abdc_a_star_a": abdc_a_star_a,
                "avg_jif": avg_jif,
                "avg_jif5": avg_jif5,
                "avg_citation": avg_citation,
                "variable_value": variable_value,
            })
        # Sorting
        if sort_by == "total_articles":
            researcher_list.sort(key=lambda x: x["total_articles"], reverse=True)
        elif sort_by == "abdc_a_star_a":
            researcher_list.sort(key=lambda x: x["abdc_a_star_a"], reverse=True)
        elif sort_by == "avg_jif":
            researcher_list.sort(key=lambda x: x["avg_jif"], reverse=True)
        elif sort_by == "avg_jif_5":
            researcher_list.sort(key=lambda x: x["avg_jif5"], reverse=True)
        elif sort_by == "avg_citation":
            researcher_list.sort(key=lambda x: x["avg_citation"], reverse=True)
        # Pass the label for the variable column
        variable_label = variable_label if 'variable_label' in locals() else "Total Articles"
    finally:
        db.close()
    
    return researcher_list, variable_label