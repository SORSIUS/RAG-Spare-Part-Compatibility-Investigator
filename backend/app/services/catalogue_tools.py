import threading
from datetime import datetime, timezone

from app.models.catalogue import ComparisonRequest, EvidenceRequest, LookupRequest
from app.services.answer_service import NOTICE
from app.services.catalogue_service import CatalogueService
from app.services.rag_retriever import RagRetriever


class CatalogueTools:
    def __init__(self, repository):
        self.repository = repository
        self.retriever = None
        self.lock = threading.Lock()

    def metadata(self):
        try:
            snapshot = self.repository.load()
        except FileNotFoundError:
            library = getattr(self.repository, "library", None)
            if library is None:
                raise
            return {"title": "Reference documents", "source_sha256": None, "library": library.status(), "notice": NOTICE, "retrieval": "Chroma semantic document search"}
        catalogue = snapshot.catalogue
        return {"title": "DENSO Cabin Air Filters", "source_sha256": snapshot.fingerprint, "pages": catalogue["page_count"], "dimensions": len(catalogue["dimensions"]), "cross_references": len(catalogue["cross_references"]), "applications": len(catalogue["applications"]), "warning_count": len(catalogue["warnings"]), "notice": NOTICE, "retrieval": "Hybrid keyword + Chroma semantic document retrieval" if hasattr(self.repository, "library") else "Keyword ranking", "library": self.repository.library.status() if hasattr(self.repository, "library") else None, "pdf_url": self.pdf_url(snapshot.fingerprint, 1)}

    @staticmethod
    def pdf_url(fingerprint, page):
        return f"/api/catalogue/pdf?version={fingerprint}#page={page}"

    def search(self, query, limit=8):
        request = EvidenceRequest(query=query, limit=limit)
        try:
            snapshot = self.repository.load()
        except FileNotFoundError:
            library = getattr(self.repository, "library", None)
            if library is None:
                raise
            sources = [{**source, "id": "S" + str(index + 1), "retrieval_method": "semantic"} for index, source in enumerate(library.search(request.query, request.limit))]
            return {"query": request.query, "source_sha256": None, "sources": sources, "notice": NOTICE, "llm_used": False}
        with self.lock:
            if self.retriever is None or self.retriever.snapshot.fingerprint != snapshot.fingerprint:
                self.retriever = RagRetriever(snapshot)
            retriever = self.retriever
        from app.services.hybrid_retrieval import retrieve_sources
        sources = retrieve_sources(retriever, getattr(self.repository, "library", None), request.query, request.limit)
        return {"query": request.query, "source_sha256": snapshot.fingerprint, "sources": sources, "notice": NOTICE, "llm_used": False}

    def lookup(self, part, brand=None, limit=8):
        request = LookupRequest(part=part, brand=brand, limit=limit)
        snapshot = self.repository.load()
        result = CatalogueService(snapshot.catalogue).lookup(request.part, request.brand)
        result["record_counts"] = {}
        for section in ["dimensions", "cross_references", "applications"]:
            result["record_counts"][section] = len(result[section])
            result[section] = [{**record, "evidence": {**record["evidence"], "pdf_url": self.pdf_url(snapshot.fingerprint, record["evidence"]["page_number"])}} for record in result[section][:limit]]
        return {**result, "source_sha256": snapshot.fingerprint, "limit_per_section": limit, "notice": NOTICE, "llm_used": False}

    def compare(self, original, candidate, brand=None):
        request = ComparisonRequest(original=original, candidate=candidate, brand=brand)
        snapshot = self.repository.load()
        service = CatalogueService(snapshot.catalogue)
        result = service.compare(request.original, request.candidate, request.brand)
        for check in result["dimension_checks"]:
            check["evidence"] = [{**evidence, "pdf_url": self.pdf_url(snapshot.fingerprint, evidence["page_number"])} for evidence in check["evidence"]]
        result["cross_reference_evidence"] = [{**evidence, "pdf_url": self.pdf_url(snapshot.fingerprint, evidence["page_number"])} for evidence in result["cross_reference_evidence"]]
        result["original_lookup_status"] = service.lookup(request.original, request.brand)["status"]
        result["candidate_lookup_status"] = service.lookup(request.candidate)["status"]
        return {**result, "brand": request.brand, "source_sha256": snapshot.fingerprint, "created_at": datetime.now(timezone.utc).isoformat(), "notice": NOTICE, "llm_used": False}
