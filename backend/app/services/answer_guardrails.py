"""Conservative output checks; general knowledge must stay vehicle-agnostic."""
import re

VEHICLES = r"\b(?:toyota|corolla|altis|camry|yaris|hilux|honda|civic|city|suzuki|swift|alto|ford|focus|nissan|hyundai|kia|mazda|mercedes|bmw|volkswagen|audi|lexus|prius|rav4)\b"
SPECIFIC = re.compile(VEHICLES + r"|\d|\b(?:VIN|chassis|OEM|EPC|part[- ]?number)\b|\b(?:Pakistan|Japan|Taiwan|Europe|USA|UK|Australia|India)\b|\b(?:your|this|that|the) (?:car|vehicle) (?:has|uses|comes|is equipped)|(?:front|rear).*?(?:disc|drum)|(?:pads?|parts?).*?(?:fits?|compatible|interchange)|ABS.*?(?:caliper|same|compatible|fit)|same.*?(?:pads?|part|fit)", re.I)
FITMENT = re.compile(r"\b(?:fits?|compatible|interchangeable|equipped|uses?|comes with|front|rear|chassis)\b", re.I)


def clean_general(text):
    # Keep useful generic sentences; reject specific claims even when hidden in a bullet.
    pieces=re.split(r"(?<=[.!?])\s+|\n+", text or "")
    kept=[piece.strip() for piece in pieces if piece.strip() and not SPECIFIC.search(piece) and not re.search(r"pads?[^.!?]{0,180}(?:disc\s*\(\s*or\s*drum|(?:against|on)\s+(?:the\s+)?(?:brake\s+)?drum)",piece,re.I)]
    # Avoid orphan headings after rejected bullets.
    return "\n\n".join(piece for i,piece in enumerate(kept) if not piece.startswith('#') or (i+1<len(kept) and not kept[i+1].startswith('#')))


def guard_answer(answer, sources, question):
    indexed={source['id']:source for source in sources}
    vehicles=set(re.findall(VEHICLES,question,re.I))
    claims=[];removed=False
    for claim in answer.claims[:6]:
        quoted=' '.join(c.quote for c in claim.citations)
        records=[indexed.get(c.source_id,{}) for c in claim.citations]
        specific=bool(re.search(VEHICLES,claim.text,re.I) or (vehicles and FITMENT.search(claim.text)))
        # A generic component paragraph cannot establish a requested car's layout/fitment.
        if specific and FITMENT.search(claim.text):
            requested_models=vehicles-{'toyota','honda','ford','nissan','suzuki','hyundai','kia','mazda'}
            model_match=all(re.search(r'\b'+re.escape(model)+r'\b',quoted,re.I) for model in requested_models)
            explicit_model=bool(re.search(VEHICLES,quoted,re.I))
            if not model_match or not explicit_model:
                removed=True;continue
            # General reference passages are deliberately not installation evidence.
            if any(record.get('evidence_scope')=='general_reference' for record in records):
                removed=True;continue
        claims.append(claim)
    # Keep useful catalogue candidates even when the model omits them or wording is rejected.
    candidates=[source for source in sources if source.get('section')=='vehicle_part_link' and source.get('fitment')]
    if candidates:
        from app.services.fitment_answer import fitment_answer
        documented=fitment_answer(candidates)
        for claim,source in zip(documented.claims,candidates):
            number=source['fitment']['part_number']
            if len(claims)<6 and not any(number in existing.text for existing in claims):
                claims.append(claim)
    guidance=clean_general(answer.general_guidance)
    changed=guidance.strip() != answer.general_guidance.strip()
    if changed and not guidance:
        if re.search(r'brak|pads?',question,re.I): guidance='Brake pads press against a brake disc to slow a wheel. Disc brakes use pads; drum brakes use shoes. Exact replacement parts need a matching vehicle application.'
        elif re.search(r'filter',question,re.I): guidance='Filters remove unwanted particles from air or fluids. Different filters serve different systems. Exact replacement parts need a matching vehicle application.'
        else: guidance='A component name explains its purpose, but does not establish which replacement fits. Check a manufacturer application for the exact vehicle before buying.'
    limited=answer.insufficient_evidence or removed or (changed and bool(vehicles))
    unknowns=answer.unknowns[:5]
    questions=answer.follow_up_questions[:3]
    if limited and vehicles and re.search(r'brak|compatible|fit|part number|replacement',question,re.I):
        unknowns=['The retrieved documents do not establish an exact replacement or fit for the requested vehicle. A matching manufacturer application or verified original part number is needed.']
        # Do not keep asking for already supplied information when coverage is missing.
        questions=[]
    if candidates and any(source.get('market_unconfirmed') for source in candidates):
        markets=', '.join(sorted({source['requested_market'] for source in candidates if source.get('requested_market')}))
        limited=True
        unknowns=[f"These are sourced catalogue candidates, not confirmed fits for the {markets} market. Check the exact chassis, engine, production month, steering side and manufacturer application before ordering."]
        questions=[]
    return answer.model_copy(update={'claims':claims,'general_guidance':guidance,'insufficient_evidence':limited,'unknowns':unknowns,'follow_up_questions':questions})

