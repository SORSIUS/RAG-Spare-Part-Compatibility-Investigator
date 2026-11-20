import re


def retrieve_sources(lexical, library, question, top_k):
    if library is not None and hasattr(library, "names_document") and library.names_document(question):
        return [{**source, "id": "S" + str(index + 1), "retrieval_method": "semantic/named document"}
                for index, source in enumerate(library.search(question, top_k))]
    linked = library.linked_sources(question, top_k) if library is not None and hasattr(library, "linked_sources") else []
    if linked:
        return [{**source, "id": "S" + str(index + 1)} for index, source in enumerate(linked)]
    keywords = lexical.retrieve(question, top_k)
    if library is None:
        return keywords
    from app.services.passage_quality import category_sources, PATTERNS, substantive
    concept = bool(re.search(r"what .*?(?:does|do|is|are)|how .*?work|purpose|function", question, re.I))
    categories=[category for category,pattern in PATTERNS.items() if re.search(pattern,question,re.I)]
    if categories and hasattr(library,"cached_search"):
        focused=category_sources(library,categories[0],question,top_k)
        if concept:
            return [{**source,"id":"S"+str(i+1)} for i,source in enumerate(focused)]
        if categories[0] not in {"filters","ignition","suspension"}:
            # The structured DENSO cabin-filter catalogue cannot answer brake questions.
            return [{**source,"id":"S"+str(i+1)} for i,source in enumerate(focused)]
    known = set(lexical.identifiers)
    requested = [value.lower() for value in re.findall(r"\bDCF\d{3}[PKA]\b", question, re.IGNORECASE)]
    extra = []
    for value in requested:
        if value not in known:
            matches = library.lookup_identifier(value) if hasattr(library, "lookup_identifier") else []
            if not matches:
                return []
            extra.extend(matches)
    semantic = library.search(question, max(top_k * 2, 12))
    if requested:
        semantic = [source for source in semantic if any(value in source["content"].lower() for value in requested)]
    suspension = bool(re.search(r"\b(suspensions?|shocks?|struts?|springs?)\b", question, re.IGNORECASE))
    if suspension:
        keywords = []
        semantic = [source for source in semantic if re.search(r"\b(suspensions?|shocks?|struts?|springs?)\b", source["content"], re.IGNORECASE)]
    structured_vehicle = sum(source["section"] == "application" for source in keywords) >= 2
    combined = list(keywords) + extra if requested or structured_vehicle else list(keywords[:max(1, top_k // 2)])
    combined.extend(semantic)
    combined.extend(keywords)
    seen, result = set(), []
    for source in combined:
        identity = (source["source"], source["page_number"], source["content"])
        if identity in seen:
            continue
        seen.add(identity)
        result.append({**source, "id": "S" + str(len(result) + 1), "retrieval_method": source.get("retrieval_method", "semantic" if "cosine_distance" in source else "exact/keyword")})
        if len(result) >= top_k:
            break
    return result
