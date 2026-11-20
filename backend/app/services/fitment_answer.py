"""Checked catalogue wording when the LLM changes a date or quotation."""
from app.models.chat import GeneratedAnswer


def fitment_answer(sources):
    if sources and all(source.get("section") == "part_cross_reference" and source.get("replacement") for source in sources):
        claims = []
        for source in sources[:6]:
            row = source["replacement"]
            claims.append({"text": f"The manufacturer lists a reference from original {row['original_brand']} {row['original']} to {row['brand']} {row['alternative']}. This is a part-number reference; the vehicle application still needs checking.",
                           "citations": [{"source_id": source["id"], "quote": source["content"]}]})
        return GeneratedAnswer(insufficient_evidence=False, claims=claims, unknowns=["The reference does not establish vehicle fitment. Check the car model, engine, production range and market in the application catalogue."], follow_up_questions=[])
    if not sources or any(source.get('section') != 'vehicle_part_link' or not source.get('fitment') for source in sources):
        return None
    claims = []
    for source in sources[:6]:
        row = source['fitment']
        reference = f"For original {row['make']} {row['original_part']}, " if row.get('original_part') else ""
        claims.append({'text': reference + f"**{row['axle'].capitalize()} {row['component'].replace('_', ' ')} — {row.get('brand', 'KYB')} {row['part_number']}**\n\nListed for {row['make']} {row['model']}. \n\n**Engine / chassis conditions:** {row['application']}.\n\n**Production code (printed):** {row['period']}.",
                       'citations': [{'source_id': source['id'], 'quote': source['content']}]})
    return GeneratedAnswer(insufficient_evidence=False, claims=claims,
                           unknowns=['These are catalogue candidates. Confirm the exact chassis, production month, engine, steering side and market before ordering.'],
                           follow_up_questions=[])
