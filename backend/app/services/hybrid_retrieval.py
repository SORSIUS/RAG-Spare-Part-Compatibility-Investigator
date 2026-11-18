import re


def retrieve_sources(lexical, library, question, top_k):
    keywords = lexical.retrieve(question, top_k)
    if library is None:
        return keywords
    if hasattr(library, "names_document") and library.names_document(question):
        return [{**source, "id": "S" + str(index + 1), "retrieval_method": "semantic/named document"}
                for index, source in enumerate(library.search(question, top_k))]
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
