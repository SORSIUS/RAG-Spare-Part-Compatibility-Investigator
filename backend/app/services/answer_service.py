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
    if not answer.insufficient_evidence and not answer.claims:
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
        if any(identifier.casefold() not in supporting_text.casefold() for identifier in identifiers):
            raise CitationError("A part number in the answer was absent from its cited sources.")
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
            clarification = history and conversation["messages"][-1].get("follow_up_questions") and re.search(r"^(?:19|20)\d{2}|^(front|rear|both)\b", query, re.IGNORECASE)
            if history and (clarification or re.search(r"\b(it|its|that|those|these|same|them)\b", query, re.IGNORECASE)):
                previous = conversation["messages"][-1]
                query = previous.get("retrieval_query", previous["question"])[:2000] + " " + query
            sources = self.sources(query, settings.top_k)
            direct_comparison = comparison_answer(query, sources, self.retriever.snapshot if self.retriever else None)
            base = {"mode": request.mode, "retrieval_query": query, "sources": sources, "notice": NOTICE, "model": None, "usage": {}, "claims": [], "unknowns": [], "follow_up_questions": [], "citation_checks": "Source IDs and quoted excerpts are checked; semantic entailment still requires human review."}
            if not sources:
                result = {**base, "status": "insufficient_evidence", "unknowns": ["No relevant catalogue evidence was retrieved for this question."], "follow_up_questions": ["Can you provide a DENSO or manufacturer part number, or a specific vehicle model?"]}
                if re.search(r"\b(suspensions?|shocks?|struts?|springs?|swap)\b", request.question, re.IGNORECASE):
                    result["unknowns"] = ["I cannot confirm that swap from the available documents. A shared part name does not establish compatibility."]
                    result["follow_up_questions"] = ["What are the model years of both cars?", "Which component do you mean: front strut, rear shock absorber, spring, or complete assembly?", "What are the receiving car's engine/trim and country or market?"]
            elif request.mode == "evidence":
                result = {**base, "status": "evidence_only", "unknowns": ["These are retrieved source records, not an LLM-generated answer."]}
            elif direct_comparison is not None:
                validate_citations(direct_comparison, sources)
                result = {**base, **direct_comparison.model_dump(exclude={"insufficient_evidence"}), "status": "answered", "answer_method": "catalogue_rules"}
            elif needs_vehicle_details(query):
                result = {**base, "status": "insufficient_evidence", "summary": "Not enough information to confirm this swap yet.", "unknowns": ["The model years and exact vehicles/parts have not been established. Similar part names do not prove that they fit."], "follow_up_questions": VEHICLE_QUESTIONS}
            else:
                answer, usage = self.client_factory(settings).generate(request.question, sources, history)
                try:
                    validate_citations(answer, sources)
                    result = {**base, **answer.model_dump(exclude={"insufficient_evidence"}), "status": "insufficient_evidence" if answer.insufficient_evidence else "answered", "model": settings.model, "usage": usage}
                    if answer.insufficient_evidence:
                        result["claims"] = []
                        result["unknowns"] = ["The retrieved excerpts do not establish a complete answer. Review the sources and missing details."] + result["unknowns"]
                except CitationError:
                    result = {**base, "status": "unverified_response", "unknowns": ["The model's answer failed citation checks, so it was not displayed. Review the retrieved evidence or ask a narrower question."], "model": settings.model}
            return self.conversations.append(request.conversation_id, request.question, result)
        finally:
            self.capacity.release()
