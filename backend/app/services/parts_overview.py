import hashlib
import json
import threading
import time
from app.services.passage_quality import category_sources, PATTERNS
from app.services.answer_service import validate_citations, CitationError
from app.integrations.groq_client import ProviderError

_cache={}
_lock=threading.Lock()

def overview(library, settings, client_factory, body):
    category=str(body.get("category","all"))
    categories=list(PATTERNS) if category=="all" else [category] if category in PATTERNS else []
    query=" ".join(str(body.get(key,""))[:60] for key in ("make","model","year","engine","chassis"))
    sources=[];coverage=[]
    for name in categories:
        matches=category_sources(library,name,query,1)
        ids=[]
        for source in matches:
            source={**source,"id":"S"+str(len(sources)+1)};sources.append(source);ids.append(source["id"])
        coverage.append({"category":name,"source_ids":ids})
    if hasattr(library,"fitments"):
        year=str(body.get("year", ""))
        candidates=library.fitments.search(make=str(body.get("make",""))[:60],model=str(body.get("model",""))[:100],year=int(year) if year.isdigit() else None,category=category,engine=str(body.get("engine",""))[:40],chassis=str(body.get("chassis",""))[:40],limit=2)
        for record in candidates["records"]:
            sources.append({**library.fitments.evidence(record),"id":"S"+str(len(sources)+1)})
    key=hashlib.sha256(json.dumps([query,category,settings.model,settings.configured,[(s['document_id'],s['page_number'],s['content']) for s in sources]],sort_keys=True).encode()).hexdigest()
    with _lock:
        entry=_cache.get(key)
        if entry and time.monotonic()-entry[0]<900:return {**entry[1],"cached":True,"usage":{}}
    result={"sources":sources,"coverage":coverage,"claims":[],"general_guidance":"","unknowns":[],"follow_up_questions":[],"model":None,"usage":{},"cached":False}
    if not settings.configured:
        return {**result,"message":"The assistant is unavailable. You can still browse the documented part candidates below."}
    question=("Give a concise, owner-friendly parts overview for "+query+". Categories: "+", ".join(categories)+". Explain each part group and what the documents establish. Do not list raw PDF snippets or contents pages. Use short Markdown sections. Put specific documented part numbers separately and do not invent them. General functions may go in general_guidance. Explain which exact fitment details remain unknown; do not claim the available documents cover every part. Use the structured vehicle-part sources for real candidate numbers where provided, keeping the application conditions and saying candidates are not guaranteed fits. Do not repeat marketing claims such as perfect fit, and do not present a generic mileage interval as a recommendation for this car.")
    try:
        answer,usage=client_factory(settings).generate(question,sources,[])
        from app.services.answer_guardrails import guard_answer
        answer=guard_answer(answer,sources,question)
        checked=[]
        for claim in answer.claims:
            try:
                validate_citations(answer.model_copy(update={"claims":[claim],"unknowns":[],"follow_up_questions":[]}),sources)
                checked.append(claim)
            except CitationError:
                continue
        answer=answer.model_copy(update={"claims":checked[:6],"unknowns":answer.unknowns[:5],"follow_up_questions":answer.follow_up_questions[:3],"insufficient_evidence":answer.insufficient_evidence or not checked})
        validate_citations(answer,sources)
        result.update(answer.model_dump(exclude={"insufficient_evidence"}),model=settings.model,usage=usage)
    except (ProviderError,CitationError) as error:
        result["validation_note"]=str(error)
        result["error_code"]=getattr(error,"code","citation_validation")
        result["message"]="The explanation could not be prepared. You can still browse documented candidates or try again."
        return result
    with _lock:
        if len(_cache)>64:_cache.clear()
        _cache[key]=(time.monotonic(),result)
    return result



