import asyncio
import hashlib
import time
from uuid import uuid4
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request, UploadFile, File, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.settings import Settings
from app.integrations.groq_client import GroqClient, ProviderError
from app.models.chat import ChatRequest
from app.models.catalogue import ComparisonRequest, EvidenceRequest, LookupRequest
from app.mcp_server import create_mcp_server
from app.repositories.catalogue import CatalogueRepository
from app.repositories.conversations import ConversationRepository
from app.repositories.document_library import DocumentLibrary
from app.services.answer_service import AnswerService
from app.services.catalogue_tools import CatalogueTools
from app.services.report_service import export_conversation


class AppError(Exception):
    def __init__(self, code, message, status=400):
        self.code, self.message, self.status = code, message, status


def create_app(settings_loader=Settings.load, catalogue_repository=None, client_factory=GroqClient, document_library=None):
    mcp_server = create_mcp_server(lambda: application.state.tools)
    mcp_app = mcp_server.streamable_http_app(json_response=True, stateless_http=True)

    @asynccontextmanager
    async def lifespan(application):
        settings = settings_loader()
        repository = catalogue_repository or CatalogueRepository(settings)
        application.state.catalogue = repository
        application.state.conversations = ConversationRepository(settings.runtime_dir / "conversations.sqlite3")
        application.state.answers = AnswerService(repository, application.state.conversations, client_factory)
        application.state.tools = CatalogueTools(repository)
        library = document_library or DocumentLibrary(settings.runtime_dir)
        application.state.library = library
        repository.library = library
        if isinstance(repository, CatalogueRepository) and settings.pdf_path.is_file():
            library.register(settings.pdf_path, settings.pdf_path.name)
        library.start()
        application.state.catalogue_error = None
        try:
            await asyncio.to_thread(repository.load)
        except (OSError, ValueError, KeyError) as error:
            application.state.catalogue_error = "The local catalogue is unavailable or could not be indexed. Check its download and retry Reindex."
        async with mcp_server.session_manager.run():
            yield
        library.stop()

    application = FastAPI(title="Automotive Spare-Part Compatibility Investigator", version="1.2.0", lifespan=lifespan)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @application.middleware("http")
    async def response_headers(request, call_next):
        length = request.headers.get("content-length", "0")
        try:
            maximum = 26 * 1024 * 1024 if request.url.path == "/api/documents/upload" else 16384
            if int(length) > maximum:
                return JSONResponse({"error": {"code": "request_too_large", "message": "The request is too large."}}, status_code=413)
        except ValueError:
            return JSONResponse({"error": {"code": "bad_request", "message": "Invalid content length."}}, status_code=400)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @application.exception_handler(AppError)
    async def app_error(request, error):
        return JSONResponse({"error": {"code": error.code, "message": error.message}}, status_code=error.status)

    @application.exception_handler(ProviderError)
    async def provider_error(request, error):
        return JSONResponse({"error": {"code": error.code, "message": str(error)}}, status_code=error.status_code)

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return JSONResponse({"error": {"code": "invalid_request", "message": "Invalid request. Check the required fields, nonempty identifiers/question, supported mode/format, and endpoint limits."}}, status_code=422)

    def current_settings():
        try:
            return settings_loader()
        except (ValueError, OSError):
            raise AppError("configuration_invalid", "Check backend/.env: timeout must be 5–90 seconds and RAG_TOP_K must be 2–12.", 503)

    @application.get("/api/health")
    def health():
        return {"status": "ok", "contract_version": 3}

    @application.get("/api/status")
    def status():
        settings = current_settings()
        snapshot = application.state.catalogue.snapshot
        catalogue = snapshot.catalogue if snapshot else None
        return {
            "contract_version": 3,
            "provider": "Groq",
            "model": settings.model,
            "llm_configured": settings.configured,
            "catalogue_ready": bool(snapshot),
            "search_ready": bool(snapshot) or application.state.library.status()["ready_documents"] > 0,
            "catalogue_error": application.state.catalogue_error,
            "catalogue": None if not catalogue else {"title": "DENSO Cabin Air Filters", "pages": catalogue["page_count"], "dimensions": len(catalogue["dimensions"]), "cross_references": len(catalogue["cross_references"]), "applications": len(catalogue["applications"]), "warnings": len(catalogue["warnings"]), "source_sha256": snapshot.fingerprint, "pdf_url": f"/api/catalogue/pdf?version={snapshot.fingerprint}#page=1"},
            "retrieval": "Hybrid: exact identifiers and keyword ranking + Chroma semantic document search",
            "document_library": application.state.library.status(),
            "agent_interfaces": {"mcp": "/mcp", "rest_schema": "/openapi.json", "tools": ["catalogue_info", "search_catalogue", "lookup_part", "compare_parts"]},
            "privacy": "Only your question, recent dialogue, and selected excerpts are sent to Groq when you choose Ask Groq. The key stays on the backend.",
        }

    @application.post("/api/chat")
    def chat(body: ChatRequest):
        try:
            result = application.state.answers.ask(body, current_settings())
            application.state.catalogue_error = None
            return result
        except FileNotFoundError:
            raise AppError("catalogue_missing", "Download the DENSO PDF into backend/data/sources/automotive/, then use Reindex.", 424)
        except ValueError as error:
            if str(error).startswith("Conversation not found"):
                raise AppError("conversation_missing", str(error), 404)
            raise AppError("catalogue_error", "The catalogue could not be read. Check the local source file and use Reindex.", 424)

    @application.get("/api/conversations")
    def conversations():
        return {"conversations": application.state.conversations.list()}

    @application.post("/api/conversations/{conversation_id}/delete")
    def delete_conversation(conversation_id: str):
        if not application.state.conversations.set_deleted(conversation_id):
            raise AppError("conversation_missing", "Conversation not found.", 404)
        return {"deleted": True}

    @application.post("/api/conversations/{conversation_id}/restore")
    def restore_conversation(conversation_id: str):
        if not application.state.conversations.set_deleted(conversation_id, False):
            raise AppError("conversation_missing", "Conversation not found.", 404)
        return {"restored": True}

    @application.post("/api/parts/overview")
    def parts_overview(body: dict):
        from app.services.parts_overview import overview
        return overview(application.state.library, current_settings(), client_factory, body)

    @application.get("/api/conversations/{conversation_id}")
    def conversation(conversation_id: str):
        result = application.state.conversations.get(conversation_id)
        if result is None:
            raise AppError("conversation_missing", "Conversation not found.", 404)
        return result

    @application.get("/api/conversations/{conversation_id}/export")
    def export(conversation_id: str, format: Literal["markdown", "json"] = "markdown"):
        result = application.state.conversations.get(conversation_id)
        if result is None:
            raise AppError("conversation_missing", "Conversation not found.", 404)
        body, media_type = export_conversation(result, format)
        extension = "md" if format == "markdown" else "json"
        return Response(body, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="investigation-{result["id"]}.{extension}"'})

    def catalogue_operation(operation, *args):
        try:
            return getattr(application.state.tools, operation)(*args)
        except FileNotFoundError:
            raise AppError("catalogue_missing", "Download the DENSO PDF, then use Reindex.", 424)
        except (ValueError, OSError, KeyError):
            raise AppError("catalogue_input", "Check the local catalogue and identifiers. The candidate must be an explicit DENSO number, such as DCF357P.", 422)

    @application.get("/api/catalogue/info")
    def catalogue_info():
        return catalogue_operation("metadata")

    @application.post("/api/catalogue/search")
    def search_catalogue(body: EvidenceRequest):
        return catalogue_operation("search", body.query, body.limit)

    @application.get("/api/documents")
    def documents():
        return application.state.library.status()

    @application.post("/api/parts/references")
    def part_references(body: dict):
        import re
        query = str(body.get("query", ""))[:500]
        category = body.get("category", "")
        terms = {"filters": r"filter|filtration", "brakes": r"brak|caliper|rotor",
                 "ignition": r"spark|ignition|glow plug", "engine": r"engine|timing|coolant|gasket",
                 "electrical": r"alternator|starter|battery|electrical|sensor"}
        pattern = terms.get(category)
        if not pattern or not query.strip():
            return {"sources": []}
        sources = application.state.answers.sources(query, 6)
        relevant = [source for source in sources if re.search(pattern, source["content"], re.I)]
        if len(relevant) < 3:
            terms = {"filters": "filter", "brakes": "brake", "ignition": "spark plug", "engine": "engine", "electrical": "electrical battery alternator"}
            extra = application.state.library.cached_search(terms[category], 24)
            seen = {(s["source"], s["page_number"], s["content"]) for s in relevant}
            for source in extra:
                key = (source["source"], source["page_number"], source["content"])
                if key not in seen and re.search(pattern, source["content"], re.I):
                    relevant.append({**source, "id": "R" + str(len(relevant) + 1)})
                    seen.add(key)
        return {"sources": relevant[:3]}

    @application.get("/api/fitments/options")
    def fitment_options():
        return application.state.library.fitments.options()

    @application.get("/api/fitments")
    def find_fitments(make: str = Query("", max_length=60), model: str = Query("", max_length=100),
                      year: int | None = Query(None, ge=1950, le=2100), category: Literal["all", "suspension", "ignition", "filters", "brakes", "electrical", "engine"] = "all",
                      axle: Literal["", "front", "rear"] = "", chassis: str = Query("", max_length=40),
                      part: str = Query("", max_length=40), limit: int = Query(24, ge=1, le=48), offset: int = Query(0, ge=0, le=100000),
                      engine: str = Query("", max_length=40), component: str = Query("", max_length=40), market: str = Query("", max_length=60)):
        return application.state.library.fitments.search(make, model, year, category, axle, chassis, part, limit, offset, engine, component, market)

    @application.get("/api/replacements")
    def replacements(brand: str = Query(..., min_length=1, max_length=60),
                     part: str = Query(..., min_length=1, max_length=40),
                     limit: int = Query(24, ge=1, le=48)):
        from app.repositories.replacements import ReplacementRepository
        return ReplacementRepository(application.state.library.runtime).search(brand, part, limit)

    @application.post("/api/documents/upload", status_code=202)
    async def upload_document(file: UploadFile = File(...)):
        library = application.state.library
        suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
        if suffix not in {".pdf", ".txt"}:
            raise AppError("unsupported_document", "Upload a PDF or UTF-8 text file.", 415)
        folder = library.root / "files"
        folder.mkdir(parents=True, exist_ok=True)
        temporary = folder / (uuid4().hex + ".upload")
        fingerprint, size, started = hashlib.sha256(), 0, time.monotonic()
        try:
            with temporary.open("wb") as output:
                while data := await file.read(1024 * 1024):
                    size += len(data)
                    if size > 25 * 1024 * 1024:
                        raise AppError("document_too_large", "Use a document smaller than 25 MB.", 413)
                    if size == len(data) and suffix == ".pdf" and not data.lstrip().startswith(b"%PDF"):
                        raise AppError("invalid_pdf", "This file does not have a PDF header.", 415)
                    fingerprint.update(data)
                    output.write(data)
            if not size:
                raise AppError("empty_document", "Choose a nonempty document.", 422)
            identifier = fingerprint.hexdigest()
            existing = library.get(identifier)
            if existing:
                return {**existing, "duplicate": True, "upload_seconds": round(time.monotonic() - started, 3)}
            target = folder / (identifier + suffix)
            temporary.replace(target)
            result = library.register(target, file.filename, identifier)
            return {**result, "upload_seconds": round(time.monotonic() - started, 3)}
        finally:
            await file.close()
            temporary.unlink(missing_ok=True)

    @application.post("/api/documents/{document_id}/retry")
    def retry_document(document_id: str):
        library = application.state.library
        record = library.get(document_id)
        if record is None:
            raise AppError("document_missing", "Document not found.", 404)
        if record["status"] == "failed":
            library.update(document_id, status="queued", error=None)
        return library.get(document_id)

    @application.get("/api/documents/{document_id}/pdf")
    def document_file(document_id: str):
        library = application.state.library
        record, path = library.get(document_id), library.path(document_id)
        if record is None or path is None or not path.is_file():
            raise AppError("document_missing", "Document not found.", 404)
        if hashlib.sha256(path.read_bytes()).hexdigest() != document_id:
            raise AppError("source_changed", "The document changed. Upload the new revision before using its citations.", 409)
        return FileResponse(path, media_type="application/pdf" if path.suffix.lower() == ".pdf" else "text/plain; charset=utf-8", filename=record["name"], content_disposition_type="inline")

    @application.post("/api/catalogue/lookup")
    def lookup_part(body: LookupRequest):
        return catalogue_operation("lookup", body.part, body.brand, body.limit)

    @application.post("/api/catalogue/compare")
    def compare_parts(body: ComparisonRequest):
        return catalogue_operation("compare", body.original, body.candidate, body.brand)

    @application.post("/api/catalogue/reindex")
    def reindex():
        try:
            application.state.catalogue.load(force=True)
            application.state.catalogue_error = None
        except (OSError, ValueError, KeyError):
            raise AppError("catalogue_error", "Could not index the local PDF. Check the source file; the previous index was not intentionally cleared.", 424)
        return status()

    @application.get("/api/catalogue/pdf")
    def catalogue_pdf(version: str | None = None):
        settings = current_settings()
        if not settings.pdf_path.is_file():
            raise AppError("catalogue_missing", "The local catalogue file is missing.", 404)
        data = settings.pdf_path.read_bytes()
        fingerprint = hashlib.sha256(data).hexdigest()
        if version is not None and version != fingerprint:
            raise AppError("source_changed", "This citation belongs to an older catalogue. Reindex and ask again to obtain current sources.", 409)
        return Response(data, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="denso_cabin_air_filters_2026.pdf"'})

    application.mount("/", mcp_app)
    return application


app = create_app()

