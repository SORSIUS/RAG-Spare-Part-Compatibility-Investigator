import re
import threading
import unicodedata

from app.integrations.groq_client import GroqClient, ProviderError
from app.models.chat import GeneratedAnswer
from app.repositories.conversations import ConversationRepository
from app.services.rag_retriever import RagRetriever
from app.services.vehicle_questions import needs_vehicle_details, VEHICLE_QUESTIONS
from app.services.comparison_answer import comparison_answer


NOTICE = "Catalogue evidence is not installation approval. Confirm the exact vehicle, production dates, region, and all application qualifiers with a qualified parts professional."


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


class CitationError(ValueError):
    pass


def validate_citations(answer: GeneratedAnswer, sources: list[dict]) -> None:
    indexed = {source["id"]: source for source in sources}
    if len(answer.claims) > 6 or len(answer.unknowns) > 5 or len(answer.follow_up_questions) > 3:
        raise CitationError("The response exceeded the supported answer size.")
    if not answer.insufficient_evidence and not answer.claims and not answer.general_guidance.strip():
        raise CitationError("The response contained no supported claims.")
    for claim in answer.claims:
        if not claim.text.strip() or len(claim.text) > 1600 or not claim.citations or len(claim.citations) > 6:
            raise CitationError("A factual statement lacked supporting citations.")
        for citation in claim.citations:
            source = indexed.get(citation.source_id)
            if source is None or len(normalized(citation.quote)) < 12 or normalized(citation.quote) not in normalized(source["content"]):
                raise CitationError("A citation did not match a retrieved source excerpt.")
        identifiers = set(re.findall(r"\bDCF\d{3}[PKA]\b", claim.text, re.IGNORECASE))
        supporting_text = " ".join(indexed[citation.source_id]["content"] for citation in claim.citations)
        if any(indexed[c.source_id].get("section") == "part_cross_reference" for c in claim.citations):
            codes = re.findall(r"\b[A-Z]+\d[A-Z0-9]*(?:-[A-Z0-9]+)*\b", claim.text)
            if any(not re.search(r"(?<!\w)" + re.escape(code) + r"(?!\w)", supporting_text) for code in codes):
                raise CitationError("A replacement identifier was absent from its cited reference.")
        if any(identifier.casefold() not in supporting_text.casefold() for identifier in identifiers):
            raise CitationError("A part number in the answer was absent from its cited sources.")
        if any(indexed[citation.source_id].get("section") == "vehicle_part_link" for citation in claim.citations):
            linked_codes = re.findall(r"\b[A-Z]{1,5}\d{2,7}[A-Z0-9]{0,3}\b", claim.text, re.I)
            if any(not re.search(r"(?<!\w)" + re.escape(code) + r"(?!\w)", supporting_text, re.I) for code in linked_codes):
                raise CitationError("A KYB part or chassis code was absent from its cited catalogue application.")
        numbers = set(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)", claim.text))
        source_numbers = set(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)", supporting_text))
        if not {number.replace(",", ".") for number in numbers} <= {number.replace(",", ".") for number in source_numbers}:
            raise CitationError("An answer introduced a number absent from its cited sources.")


class AnswerService:
    def __init__(self, catalogue_repository, conversations: ConversationRepository, client_factory=GroqClient):
        self.catalogue_repository = catalogue_repository
        self.conversations = conversations
        self.client_factory = client_factory
        self.retriever = None
        self.lock = threading.Lock()
        self.capacity = threading.BoundedSemaphore(2)

    def sources(self, question, top_k):
        try:
            snapshot = self.catalogue_repository.load()
        except FileNotFoundError:
            library = getattr(self.catalogue_repository, "library", None)
            if library is None:
                raise
            return [{**source, "id": "S" + str(index + 1), "retrieval_method": "semantic"} for index, source in enumerate(library.search(question, top_k))]
        with self.lock:
            if self.retriever is None or self.retriever.snapshot.fingerprint != snapshot.fingerprint:
                self.retriever = RagRetriever(snapshot)
            retriever = self.retriever
        from app.services.hybrid_retrieval import retrieve_sources
        return retrieve_sources(retriever, getattr(self.catalogue_repository, "library", None), question, top_k)

    def ask(self, request, settings):
        if not self.capacity.acquire(blocking=False):
            raise ProviderError("busy", "Two requests are already running. Wait for one to finish.", 429)
        try:
            history = []
            if request.conversation_id:
                conversation = self.conversations.get(request.conversation_id)
                if conversation is None:
                    raise ValueError("Conversation not found. Start a new chat.")
                history = [{"question": message["question"][:500], "claims": [claim["text"][:400] for claim in message["claims"][:3]]} for message in conversation["messages"][-4:]]
            query = request.question
            pending_vehicle = history and conversation["messages"][-1].get("answer_method") == "vehicle_clarification"
            clarification = history and conversation["messages"][-1].get("follow_up_questions") and len(query) < 300 and (pending_vehicle or ('?' not in query and re.search(r"\b(?:19|20)\d{2}\b|^(front|rear|both)\b", query, re.IGNORECASE)))
            if history and (clarification or re.search(r"\b(it|its|that|those|these|same|them)\b", query, re.IGNORECASE)):
                previous = conversation["messages"][-1]
                query = previous.get("retrieval_query", previous["question"])[:2000] + " " + query
            library = getattr(self.catalogue_repository, "library", None)
            fitments = getattr(library, "fitments", None)
            owner = fitments.owner_context(query) if fitments and hasattr(fitments, "owner_context") else None
            exact_part = re.search(r"\b(?:KYB|DENSO)\s+[A-Z0-9-]*\d|Application:", query, re.I)
            if owner and not exact_part and request.mode == "answer":
                missing = []
                if not owner["year"]:
                    missing.append("What year is your " + owner["model"] + "?")
                if not owner["engine"] and not owner["chassis"] and not re.search(r"(?:don't|do not|dont) know.*engine|engine.*unknown", query, re.I):
                    missing.append("What is its engine size or code? You can say you don't know.")
                if missing:
                    result = {"mode": request.mode, "retrieval_query": query, "sources": [], "notice": NOTICE, "model": None, "usage": {}, "claims": [], "unknowns": [], "follow_up_questions": missing, "status": "insufficient_evidence", "answer_method": "vehicle_clarification", "assistant_text": "Let's identify your version so I can narrow down the parts. You do not need a part number."}
                    return self.conversations.append(request.conversation_id, request.question, result)
            sources = self.sources(query, settings.top_k)
            direct_comparison = comparison_answer(query, sources, self.retriever.snapshot if self.retriever else None)
            base = {"mode": request.mode, "retrieval_query": query, "sources": sources, "notice": NOTICE, "model": None, "usage": {}, "claims": [], "unknowns": [], "follow_up_questions": [], "citation_checks": "Source IDs and quoted excerpts are checked; semantic entailment still requires human review."}
            if not sources and (request.mode == "evidence" or not re.search(r"car|vehicle|toyota|corolla|filter|brake|engine|suspension|shock|strut|spark|ignition|battery|alternator|starter|steering|part|coolant|clutch|transmission|wheel|tyre|tire", query, re.I)):
                result = {**base, "status": "insufficient_evidence", "assistant_text": "I searched the imported catalogue evidence but could not confirm this yet. We can narrow the search using your car model and year, the component name, and its engine or market if known. You do not need a part number to continue.", "unknowns": ["The current results do not establish a replacement or fitment. This does not mean no replacement exists."], "follow_up_questions": ["Which car model/year and component are you checking?"]}
                if not owner and re.search(r"\b(swap|instead)\b|\b(?:can|could)\b.*\buse\b", request.question, re.IGNORECASE):
                    result["unknowns"] = ["I cannot confirm that swap from the available documents. A shared part name does not establish compatibility."]
                    result["follow_up_questions"] = ["What are the model years of both cars?", "Which component do you mean: front strut, rear shock absorber, spring, or complete assembly?", "What are the receiving car's engine/trim and country or market?"]
            elif request.mode == "evidence":
                result = {**base, "status": "evidence_only", "unknowns": ["These are retrieved source records, not an LLM-generated answer."]}
            elif direct_comparison is not None:
                validate_citations(direct_comparison, sources)
                result = {**base, **direct_comparison.model_dump(exclude={"insufficient_evidence"}), "status": "answered", "answer_method": "catalogue_rules"}
            elif owner and sources and not settings.configured and all(source.get("section") == "vehicle_part_link" for source in sources):
                from app.services.fitment_answer import fitment_answer
                answer = fitment_answer(sources)
                validate_citations(answer, sources)
                result = {**base, **answer.model_dump(exclude={"insufficient_evidence"}), "status": "answered", "answer_method": "vehicle_catalogue"}
            elif needs_vehicle_details(query):
                result = {**base, "status": "insufficient_evidence", "assistant_text": "I can help check this swap. First, tell me the year of each car and whether you mean a front strut, rear shock, spring or the whole suspension. I have kept the retrieved references below, but they do not yet confirm this exact swap.", "summary": "Let's identify the exact cars and component.", "unknowns": ["The model years and exact vehicles/parts have not been established. Similar part names do not prove that they fit."], "follow_up_questions": VEHICLE_QUESTIONS}
            else:
                try:
                    answer, usage = self.client_factory(settings).generate(request.question, sources, history)
                except ProviderError as error:
                    from app.services.chat_recovery import provider_recovery
                    result = provider_recovery(base, error, validate_citations)
                    return self.conversations.append(request.conversation_id, request.question, result)
                try:
                    from app.services.answer_guardrails import guard_answer
                    answer = guard_answer(answer, sources, query)
                    validate_citations(answer, sources)
                    result = {**base, **answer.model_dump(exclude={"insufficient_evidence"}), "status": "insufficient_evidence" if answer.insufficient_evidence else "answered", "model": settings.model, "usage": usage}
                    if answer.insufficient_evidence:
                        result["assistant_text"] = "Here is what I could establish from the sources below. I cannot confirm the remaining fitment question yet; the missing details are listed separately." if result["claims"] else "The available references do not confirm your specific request. The general explanation below can help you understand the part."
                        from app.services.answer_guardrails import VEHICLES
                        if not result["follow_up_questions"] and not re.search(VEHICLES, query, re.I):
                            result["follow_up_questions"] = ["Do you have a matching manufacturer application or original part number to check?"]

                except CitationError:
                    from app.services.fitment_answer import fitment_answer
                    fallback = fitment_answer(sources)
                    if fallback:
                        validate_citations(fallback, sources)
                        result = {**base, **fallback.model_dump(exclude={"insufficient_evidence"}), "status": "answered", "answer_method": "linked_catalogue", "generation_note": "The generated wording failed validation. Showing the checked catalogue wording instead."}
                    else:
                        result = {**base, "status": "unverified_response", "assistant_text": "I found relevant passages, but I could not verify the generated wording. You can check the references below, or ask a more specific question. I will not guess the answer.", "unknowns": [], "model": settings.model}
            return self.conversations.append(request.conversation_id, request.question, result)
        finally:
            self.capacity.release()

