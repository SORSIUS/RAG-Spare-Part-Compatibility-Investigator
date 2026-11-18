import re

from app.models.chat import GeneratedAnswer
from app.services.catalogue_service import CatalogueService


def comparison_answer(question, sources, snapshot):
    parts = list(dict.fromkeys(re.findall(r"\bDCF\d{3}[PKA]\b", question.upper())))
    if snapshot is None or len(parts) != 2 or not re.search(r"\bcompare\b", question, re.IGNORECASE) or not re.search(r"\b(dimensions?|sizes?|length|width|height)\b", question, re.IGNORECASE):
        return None
    if any(snapshot.fingerprint not in source["pdf_url"] for source in sources):
        return None
    result = CatalogueService(snapshot.catalogue).compare(parts[0], parts[1])
    claims = []
    for side, part in [("original", parts[0]), ("candidate", parts[1])]:
        supporting = next((source for source in sources if source["section"] == "photo_guide" and ("Part number: " + part + ".") in source["content"]), None)
        if supporting is None:
            return None
        values = []
        for check in result["dimension_checks"]:
            documented = check[side + "_values"]
            if len(documented) != 1:
                return None
            values.append(check["field"].removesuffix("_mm") + " " + f"{documented[0]:g}" + " mm")
        claims.append({"text": part + " documented dimensions: " + "; ".join(values) + ".", "citations": [{"source_id": supporting["id"], "quote": supporting["content"]}]})
    claims.append({"text": "Dimension checks: " + "; ".join(check["field"].removesuffix("_mm") + " " + check["status"] for check in result["dimension_checks"]) + ".", "citations": [citation for claim in claims for citation in claim["citations"]]})
    return GeneratedAnswer(insufficient_evidence=False, claims=claims, unknowns=["Exact-vehicle fitment and interchangeability are not established by dimensions alone."], follow_up_questions=[])
