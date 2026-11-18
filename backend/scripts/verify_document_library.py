import argparse
import asyncio
import hashlib
import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from mcp import Client
from reportlab.pdfgen.canvas import Canvas

from app.core.settings import Settings
from app.repositories.document_library import DocumentLibrary


def main():
    parser = argparse.ArgumentParser(description="Verify real asynchronous uploads, Chroma retrieval, and deduplication against the running app.")
    parser.add_argument("--url", default="http://127.0.0.1:3201")
    arguments = parser.parse_args()
    if not arguments.url.startswith("http://127.0.0.1:"):
        parser.error("Use a loopback app URL.")
    checks, details = {}, {}
    with httpx.Client(base_url=arguments.url, timeout=30) as client:
        baseline = client.get("/api/documents").json()
        before = {row["id"]: row["updated_at"] for row in baseline["documents"] if row["status"] == "ready"}
        buffer = io.BytesIO()
        canvas = Canvas(buffer, invariant=1)
        for number, text in enumerate([
            "FICTIONAL TRAINING REFERENCE. Dampers reduce oscillation after road impacts.",
            "A vehicle may bounce repeatedly when its shock absorbers cannot control spring movement.",
            "This teaching fixture does not establish compatibility between any real vehicle models.",
        ]):
            canvas.drawString(35, 780 - 25 * number, text)
        canvas.save()
        data = buffer.getvalue()
        identifier = hashlib.sha256(data).hexdigest()
        library = DocumentLibrary(Settings().runtime_dir)
        existing = library.get(identifier)
        if existing and existing["status"] == "verification":
            library.update(identifier, status="queued")
        started = time.monotonic()
        response = client.post("/api/documents/upload", files={"file": ("verification_training_reference.pdf", data, "application/pdf")})
        elapsed = time.monotonic() - started
        document = response.json()
        checks["upload_acknowledged"] = response.status_code == 202
        details["upload_seconds"] = round(elapsed, 3)
        details["initial_status"] = document.get("status")
        checks["upload_under_two_seconds"] = elapsed < 2
        identifier = hashlib.sha256(data).hexdigest()
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            listing = client.get("/api/documents").json()
            record = next(row for row in listing["documents"] if row["id"] == identifier)
            if record["status"] in {"ready", "failed", "needs_ocr"}:
                break
            time.sleep(.5)
        checks["new_pdf_became_ready"] = record["status"] == "ready"
        duplicate = client.post("/api/documents/upload", files={"file": ("same_bytes_new_name.pdf", data, "application/pdf")}).json()
        checks["duplicate_reused_history"] = duplicate.get("duplicate") and duplicate["id"] == identifier and duplicate["status"] == "ready"
        after = client.get("/api/documents").json()
        checks["existing_documents_not_reindexed"] = all(next(row for row in after["documents"] if row["id"] == key)["updated_at"] == value for key, value in before.items())
        response = client.get("/api/documents/" + identifier + "/pdf")
        checks["uploaded_pdf_bytes_match"] = response.status_code == 200 and response.content == data
        sources = client.post("/api/catalogue/search", json={"query": "Why does my car keep bouncing after a bump?", "limit": 8}).json()["sources"]
        checks["semantic_source_found"] = any(source.get("document_id") == identifier for source in sources)
        checks["semantic_sources_have_pages"] = all(source["page_number"] > 0 and source["pdf_url"] for source in sources)
        details["semantic_sources"] = [{"source": source["source"], "page": source["page_number"], "method": source.get("retrieval_method"), "distance": source.get("cosine_distance")} for source in sources]
        checks["unsupported_file_rejected"] = client.post("/api/documents/upload", files={"file": ("bad.exe", b"bad")}).status_code == 415
        checks["unrelated_query_empty"] = not client.post("/api/catalogue/search", json={"query": "quantum banana lasagna recipe", "limit": 8}).json()["sources"]
        exact = client.post("/api/catalogue/search", json={"query": "DCF002K dimensions", "limit": 2}).json()["sources"]
        checks["exact_part_preserved"] = exact[0]["section"] == "photo_guide" and "282 mm" in exact[0]["content"]
    reopened = DocumentLibrary(Settings().runtime_dir)
    checks["reopened_registry_ready"] = reopened.get(identifier)["status"] == "ready"
    checks["reopened_chroma_retrieves"] = bool(reopened.search("shock absorbers reduce vehicle bouncing", 8))
    encoder = reopened.vectors.embeddings
    encoder.prepare()
    stored_texts = reopened.vectors.collection.get(include=["documents"])["documents"]
    maximum = max(len(encoder.tokenizer.encode(text).ids) for text in stored_texts)
    details["maximum_stored_embedding_tokens"] = maximum
    checks["token_windows_fit_encoder"] = maximum <= 256
    checks["real_embeddings_have_384_dimensions"] = len(encoder.embed(["A vehicle shock absorber."])[0]) == 384

    async def mcp_check():
        async with Client(arguments.url + "/mcp") as client:
            result = await client.call_tool("search_catalogue", {"query": "Why does my car keep bouncing after a bump?", "limit": 8})
            return not result.is_error and any(source.get("document_id") == identifier for source in result.structured_content["sources"])
    checks["mcp_searches_uploaded_pdf"] = asyncio.run(mcp_check())
    reopened.update(identifier, status="verification")
    checks["fictional_fixture_excluded_after_test"] = not any(source.get("document_id") == identifier for source in reopened.search("vehicle bouncing after road impacts", 8))
    report = {"checks": checks, "details": details, "all_passed": all(checks.values()), "fixture": "Fictional one-page PDF; no real fitment approval is asserted."}
    (Settings().runtime_dir / "document_library_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["all_passed"]:
        parser.exit(1, "Review the document-library verification report.\n")


if __name__ == "__main__":
    main()
