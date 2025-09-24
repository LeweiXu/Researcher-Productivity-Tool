from fastapi import Request
from app.database import SessionLocal
from app.models import Researchers, Publications, Journals

UNIVERSITY_STATS_CACHE = None

def get_university_data(request: Request):
    global UNIVERSITY_STATS_CACHE
    sort_by = request.query_params.get("sort_by", "total_researchers")
    if UNIVERSITY_STATS_CACHE is None:
        db = SessionLocal()
        try:
            researchers = db.query(Researchers).all()
            publications = db.query(Publications).all()
            journals = {j.id: j for j in db.query(Journals).all()}
            # Build university stats
            universities = {}
            for r in researchers:
                uni = r.university or "Unknown"
                if uni not in universities:
                    universities[uni] = {
                        "name": uni,
                        "num_researchers": 0,
                        "accounting_count": 0,
                        "finance_count": 0,
                        "total_articles": 0,
                        "accounting_articles": 0,
                        "finance_articles": 0,
                        "abdc_a_star_a": 0,
                        "jif_list": [],
                        "jif5_list": [],
                    }
                universities[uni]["num_researchers"] += 1
                # Count researchers per field
                if r.field == "Accounting":
                    universities[uni]["accounting_count"] += 1
                elif r.field == "Finance":
                    universities[uni]["finance_count"] += 1
            for pub in publications:
                researcher = next((r for r in researchers if r.id == pub.researcher_id), None)
                if not researcher:
                    continue
                uni = researcher.university or "Unknown"
                universities[uni]["total_articles"] += 1
                if researcher.field == "Accounting":
                    universities[uni]["accounting_articles"] += 1
                elif researcher.field == "Finance":
                    universities[uni]["finance_articles"] += 1
                journal = journals.get(pub.journal_id)
                if journal:
                    if journal.abdc_rank in ["A*", "A"]:
                        universities[uni]["abdc_a_star_a"] += 1
                    if journal.JIF is not None:
                        universities[uni]["jif_list"].append(journal.JIF)
                    if journal.JIF_5_year is not None:
                        universities[uni]["jif5_list"].append(journal.JIF_5_year)
            # Finalize stats
            university_list = []
            for uni, stats in universities.items():
                avg_jif = round(sum(stats["jif_list"])/len(stats["jif_list"]), 2) if stats["jif_list"] else 0
                avg_jif5 = round(sum(stats["jif5_list"])/len(stats["jif5_list"]), 2) if stats["jif5_list"] else 0
                overall_avg_articles = round(stats["total_articles"]/stats["num_researchers"], 2) if stats["num_researchers"] else 0
                accounting_avg_articles = round(stats["accounting_articles"]/stats["accounting_count"], 2) if stats["accounting_count"] else 0
                finance_avg_articles = round(stats["finance_articles"]/stats["finance_count"], 2) if stats["finance_count"] else 0
                university_list.append({
                    "name": stats["name"],
                    "num_researchers": stats["num_researchers"],
                    "accounting_count": stats["accounting_count"],
                    "finance_count": stats["finance_count"],
                    "total_articles": stats["total_articles"],
                    "accounting_articles": stats["accounting_articles"],
                    "finance_articles": stats["finance_articles"],
                    "abdc_a_star_a": stats["abdc_a_star_a"],
                    "avg_jif": avg_jif,
                    "avg_jif5": avg_jif5,
                    "avg_articles_overall": overall_avg_articles,
                    "avg_articles_accounting": accounting_avg_articles,
                    "avg_articles_finance": finance_avg_articles,
                })
            UNIVERSITY_STATS_CACHE = university_list
        finally:
            db.close()
    else:
        university_list = UNIVERSITY_STATS_CACHE

    # Add variable_value and variable_label for the selected stat
    if sort_by == "total_researchers":
        variable_label = "Total Researchers"
        for u in university_list:
            u["variable_value"] = u["num_researchers"]
        university_list.sort(key=lambda x: x["num_researchers"], reverse=True)
    elif sort_by == "total_articles":
        variable_label = "Total Articles"
        for u in university_list:
            u["variable_value"] = u["total_articles"]
        university_list.sort(key=lambda x: x["total_articles"], reverse=True)
    elif sort_by == "abdc_a_star_a":
        variable_label = "A*/A Articles"
        for u in university_list:
            u["variable_value"] = u["abdc_a_star_a"]
        university_list.sort(key=lambda x: x["abdc_a_star_a"], reverse=True)
    elif sort_by == "avg_jif":
        variable_label = "Avg. JIF"
        for u in university_list:
            u["variable_value"] = u["avg_jif"]
        university_list.sort(key=lambda x: x["avg_jif"], reverse=True)
    elif sort_by == "avg_jif_5":
        variable_label = "Avg. 5-Year JIF"
        for u in university_list:
            u["variable_value"] = u["avg_jif5"]
        university_list.sort(key=lambda x: x["avg_jif5"], reverse=True)
    elif sort_by == "avg_articles":
        variable_label = "Avg. Articles/Researcher"
        for u in university_list:
            u["variable_value"] = u["avg_articles_overall"]
        university_list.sort(key=lambda x: x["avg_articles_overall"], reverse=True)
    elif sort_by == "avg_articles_accounting":
        variable_label = "Avg. Articles/Accounting Researcher"
        for u in university_list:
            u["variable_value"] = u["avg_articles_accounting"]
        university_list.sort(key=lambda x: x["avg_articles_accounting"], reverse=True)
    elif sort_by == "avg_articles_finance":
        variable_label = "Avg. Articles/Finance Researcher"
        for u in university_list:
            u["variable_value"] = u["avg_articles_finance"]
        university_list.sort(key=lambda x: x["avg_articles_finance"], reverse=True)
    else:
        variable_label = "Total Researchers"
        for u in university_list:
            u["variable_value"] = u["num_researchers"]
        university_list.sort(key=lambda x: x["num_researchers"], reverse=True)

    return university_list, variable_label
