from fastapi import Request
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals
import math

# Cache researcher stats as page very slow if requerying DB every time you reload
# Need to restart server to clear cache (for now)
RESEARCHER_STATS_CACHE = None

def filter_researchers(request, researcher_list):
    field = request.query_params.get("field", "")
    level = request.query_params.get("level", "")
    university = request.query_params.get("university", "")
    name = request.query_params.get("name", "").strip().lower()
    filtered = researcher_list
    if university:
        filtered = [r for r in filtered if (r["university"] or "").lower() == university.lower()]
    if field:
        filtered = [r for r in filtered if (r["FoR"] or "").lower() == field.lower()]
    if level:
        filtered = [r for r in filtered if (r["level"] or "").upper() == level.upper()]
    if name:
        filtered = [r for r in filtered if name in (r["name"] or "").lower()]
    return filtered

def get_researcher_data(request: Request):
    global RESEARCHER_STATS_CACHE
    sort_by = request.query_params.get("sort_by", "total_articles")

    if RESEARCHER_STATS_CACHE is None:
        db = SessionLocal()
        try:
            researchers = db.query(Researchers).all()
            publications = db.query(Publications).all()
            journals = {j.id: j for j in db.query(Journals).all()}
            pubs_by_researcher = {}
            for pub in publications:
                pubs_by_researcher.setdefault(pub.researcher_id, []).append(pub)
            researcher_list = []
            for r in researchers:
                pubs = pubs_by_researcher.get(r.id, [])
                total_articles = len(pubs)
                abdc_a_star_a = 0
                jif_list = []
                jif5_list = []
                citation_list = []
                for pub in pubs:
                    journal = journals.get(pub.journal_id)
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
                })
            RESEARCHER_STATS_CACHE = researcher_list
        finally:
            db.close()
    else:
        researcher_list = RESEARCHER_STATS_CACHE

    researcher_list = filter_researchers(request, researcher_list)

    # Add variable_value and variable_label for the selected stat
    if sort_by == "total_articles":
        variable_label = "Total Articles"
        for r in researcher_list:
            r["variable_value"] = r["total_articles"]
        researcher_list.sort(key=lambda x: x["total_articles"], reverse=True)
    elif sort_by == "abdc_a_star_a":
        variable_label = "A*/A Journals"
        for r in researcher_list:
            r["variable_value"] = r["abdc_a_star_a"]
        researcher_list.sort(key=lambda x: x["abdc_a_star_a"], reverse=True)
    elif sort_by == "avg_jif":
        variable_label = "Avg. JIF"
        for r in researcher_list:
            r["variable_value"] = r["avg_jif"]
        researcher_list.sort(key=lambda x: x["avg_jif"], reverse=True)
    elif sort_by == "avg_jif_5":
        variable_label = "Avg. 5-Year JIF"
        for r in researcher_list:
            r["variable_value"] = r["avg_jif5"]
        researcher_list.sort(key=lambda x: x["avg_jif5"], reverse=True)
    elif sort_by == "avg_citation":
        variable_label = "Avg. Citation %"
        for r in researcher_list:
            r["variable_value"] = r["avg_citation"]
        researcher_list.sort(key=lambda x: x["avg_citation"], reverse=True)
    else:
        variable_label = "Total Articles"
        for r in researcher_list:
            r["variable_value"] = r["total_articles"]
        researcher_list.sort(key=lambda x: x["total_articles"], reverse=True)

    return researcher_list, variable_label