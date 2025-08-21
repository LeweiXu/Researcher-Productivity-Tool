from app.database import SessionLocal
from app.models import Publications, Journals, Researchers
from fuzzywuzzy import process

def match_journals(threshold=95, force=False, university="all"):
    print("Matching Journal Names With ABDC Rankings")
    db = SessionLocal()
    try:
        journals = db.query(Journals).all()
        journal_names = [j.name for j in journals]
        journal_dict = {j.name: j for j in journals}
        query = db.query(Publications)
        if university != "all":
            query = query.join(Researchers).filter(Researchers.university == university)
        publications = query.all()
        for pub in publications:
            if pub.journal_id and not force:
                continue
            if not pub.journal_name:
                continue
            match, score = process.extractOne(pub.journal_name, journal_names)
            if score >= threshold:
                matched_journal = journal_dict.get(match)
                if matched_journal:
                    pub.journal_id = matched_journal.id
        db.commit()
    finally:
        db.close()

# # Rapidfuzz Implementation by Frank
# def rank_lookup(journal: Optional[str], names: List[str], ranks: List[str]) -> Optional[str]:
#     """Return the ranking string for the given journal, if matched; else None."""
#     if not journal or not names:
#         return None
#     j = journal.strip()
#     if rf_fuzz is not None:
#         scores = [rf_fuzz.token_set_ratio(j, str(n)) for n in names]
#         if not scores:
#             return None
#         best_i = max(range(len(scores)), key=lambda i: scores[i])
#         if scores[best_i] >= FUZZ_THRESHOLD:
#             return ranks[best_i]
#         return None
#     jl = j.lower()
#     for i, n in enumerate(names):
#         if jl == str(n).lower():
#             return ranks[i]
#     return None


if __name__ == "__main__":
    match_journals(university="UA")
