import re

PATTERNS={"filters":r"\bfilter|filtration", "brakes":r"\bbrak|caliper|rotor", "ignition":r"spark|ignition|glow plug", "suspension":r"shock|strut|suspension|spring", "engine":r"engine|timing|coolant|gasket", "electrical":r"alternator|starter|battery|electrical|sensor"}

def substantive(text):
    if len(text.split()) < 20:
        return False
    if len(re.findall(r"\.{3,}|…",text)) >= 2:
        return False
    if re.search(r"table of contents|alphabetical index",text,re.I):
        return False
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    return not (len(lines)>4 and sum(bool(re.search(r"(?:\.{2,}|\s)\d{2,4}$",line)) for line in lines)>len(lines)*.45)

def category_sources(library, category, query, limit=3):
    pattern=PATTERNS[category]
    # Cached original passages allow deterministic filtering without any LLM expense.
    words={"filters":"filter cabin air", "brakes":"brake pads disc drum", "ignition":"spark plug ignition", "suspension":"shock strut suspension", "engine":"engine timing coolant", "electrical":"battery alternator starter"}
    sources=library.cached_search(query+' '+words[category],80)
    matches=[s for s in sources if substantive(s["content"]) and re.search(pattern,s["content"],re.I)]
    from app.services.answer_guardrails import VEHICLES
    wanted=set(token.casefold() for token in re.findall(VEHICLES,query,re.I))
    details=set(re.findall(r"\b(?:19|20)\d{2}\b|\b(?:Pakistan|Japan|Taiwan|Australia|USA|UK)\b",query,re.I))
    def relevance(source):
        text=source['content']
        vehicle_matches=sum(bool(re.search(r'\b'+re.escape(token)+r'\b',text,re.I)) for token in wanted)
        detail_matches=sum(bool(re.search(r'\b'+re.escape(token)+r'\b',text,re.I)) for token in details)
        source['evidence_scope']='vehicle_reference' if wanted and vehicle_matches==len(wanted) and (not details or detail_matches==len(details)) else 'general_reference'
        return (-vehicle_matches,-detail_matches,-min(len(re.findall(pattern,text,re.I)),5),source['page_number'])
    matches.sort(key=relevance)
    unique=[];seen=set()
    for source in matches:
        key=(source["source"],source["page_number"])
        if key not in seen: unique.append(source);seen.add(key)
        if len(unique)>=limit:break
    return unique
