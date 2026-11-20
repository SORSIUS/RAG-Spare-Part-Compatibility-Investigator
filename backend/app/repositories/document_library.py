import hashlib
import json
import os
import re
import sqlite3
import threading
import traceback
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from filelock import FileLock, Timeout

from app.integrations.local_embeddings import SCHEMA
from app.services.document_reader import read_document
from app.services.text_chunker import TextChunker
from app.services.library_reader import read_library_document
from app.services.query_language import expand_owner_question


class DocumentLibrary:
    def __init__(self, runtime, vector_store=None):
        self.runtime = Path(runtime).resolve()
        if os.name == "nt" and not str(self.runtime).startswith("\\\\?\\"):
            self.runtime = Path("\\\\?\\" + str(self.runtime))
        self.root = self.runtime / "library"
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = self.root / "documents.sqlite3"
        self.stop_event = threading.Event()
        self.thread = None
        self._vectors = vector_store
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, name TEXT NOT NULL, path TEXT NOT NULL, status TEXT NOT NULL, pages INTEGER NOT NULL DEFAULT 0, chunks INTEGER NOT NULL DEFAULT 0, indexed INTEGER NOT NULL DEFAULT 0, error TEXT, schema TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
            connection.execute("UPDATE documents SET status='queued',indexed=0,schema=? WHERE schema<>?", (SCHEMA, SCHEMA))

    @property
    def vectors(self):
        if self._vectors is None:
            from app.repositories.vector_store import VectorStore
            self._vectors = VectorStore(self.runtime)
        return self._vectors

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def register(self, path, name, fingerprint=None):
        identifier = fingerprint or hashlib.sha256(Path(path).read_bytes()).hexdigest()
        name = re.sub(r"[^\w.() -]", "_", Path(name.replace("\\", "/")).name)[:160]
        timestamp = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            existing = connection.execute("SELECT * FROM documents WHERE id=?", (identifier,)).fetchone()
            if existing is None:
                connection.execute("INSERT INTO documents(id,name,path,status,schema,created_at,updated_at) VALUES(?,?,?,'queued',?,?,?)", (identifier, name, str(Path(path).resolve()), SCHEMA, timestamp, timestamp))
            elif existing["schema"] != SCHEMA:
                connection.execute("UPDATE documents SET status='queued',indexed=0,schema=?,updated_at=? WHERE id=?", (SCHEMA, timestamp, identifier))
        return {**self.get(identifier), "duplicate": existing is not None}

    def list(self):
        with self.connect() as connection:
            return [{key: row[key] for key in row.keys() if key not in {"path", "schema"}} for row in connection.execute("SELECT * FROM documents ORDER BY created_at DESC")]

    def get(self, identifier):
        return next((row for row in self.list() if row["id"] == identifier), None)

    def path(self, identifier):
        with self.connect() as connection:
            row = connection.execute("SELECT path FROM documents WHERE id=?", (identifier,)).fetchone()
        return Path(row["path"]) if row else None

    def update(self, identifier, **values):
        allowed = {"status", "pages", "chunks", "indexed", "error"}
        if not values.keys() <= allowed:
            raise ValueError("Unsupported document fields.")
        values["updated_at"] = datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute("UPDATE documents SET " + ",".join(key + "=?" for key in values) + " WHERE id=?", [*values.values(), identifier])

    def process(self, identifier):
        path = self.path(identifier)
        record = self.get(identifier)
        if record is None or record["status"] == "ready":
            return
        try:
            self.update(identifier, status="indexing", error=None)
            # Only the reviewed catalogue revision has a table adapter. Other
            # uploads keep the generic PDF/Chroma path; never guess their fitment.
            from app.services.kyb_fitment_parser import SOURCE_SHA, SOURCE_URL, SCHEMA as FITMENT_SCHEMA, extract_catalogue
            if identifier == SOURCE_SHA and not self.fitments.imported(identifier, FITMENT_SCHEMA):
                records, inspected = extract_catalogue(path, identifier)
                if not records:
                    raise ValueError("The supported fitment catalogue yielded no rows.")
                for item in records:
                    item["source"] = record["name"]
                self.fitments.replace_source(identifier, record["name"], FITMENT_SCHEMA, SOURCE_URL, inspected, records)
            cache = self.root / (identifier[:24] + "-chunks.json")
            if cache.exists():
                saved = json.loads(cache.read_text(encoding="utf-8"))
                if saved.get("sha256") != identifier:
                    raise ValueError("Chunk cache revision mismatch.")
                pages_count, chunks = saved["pages"], saved["chunks"]
                warnings = saved.get("unreadable_pages", [])
            else:
                denso_cache = self.runtime / "denso_page_chunks.json"
                baseline = json.loads(denso_cache.read_text(encoding="utf-8")) if denso_cache.exists() else {}
                if baseline.get("sha256") == identifier:
                    chunks = baseline["chunks"]
                    pages_count = max(chunk["page_number"] for chunk in chunks)
                    warnings = []
                else:
                    pages, warnings = read_library_document(path)
                    if len(pages) > 1500:
                        raise ValueError("This document exceeds the 1500-page indexing limit.")
                    chunks = [asdict(chunk) for page in pages for chunk in TextChunker(160, 25).chunk_page(page, identifier)]
                    pages_count = len(pages)
                saved = {"sha256": identifier, "pages": pages_count, "chunks": chunks, "unreadable_pages": warnings}
                temporary = cache.with_suffix(".tmp")
                temporary.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
                temporary.replace(cache)
            if not chunks:
                self.update(identifier, status="needs_ocr", pages=pages_count, error="No extractable text. Upload a text PDF or run OCR first.")
                return
            self.update(identifier, pages=pages_count)
            segments = []
            for chunk in chunks:
                for text in self.vectors.embeddings.split(chunk["text"]):
                    number = len(segments)
                    segments.append({"id": identifier + "-" + str(number), "source": record["name"], "page_number": chunk["page_number"], "chunk_number": number, "text": text})
            self.update(identifier, chunks=len(segments))
            self.vectors.add(identifier, segments, lambda count, total: self.update(identifier, indexed=count, chunks=total))
            note = f"{len(warnings)} page(s) could not be read. Answers use the indexed text pages only." if warnings else None
            self.update(identifier, status="ready", indexed=len(segments), error=note)
        except Exception as error:
            (self.root / (identifier[:24] + "-error.json")).write_text(json.dumps({"type": type(error).__name__, "message": str(error)[:500], "traceback": traceback.format_exc()[-5000:]}), encoding="utf-8")
            self.update(identifier, status="failed", error="Indexing failed. Check that the document is readable and that the local embedding model is available; retry this document.")

    def run_pending(self):
        for record in self.list():
            if self.stop_event.is_set():
                return
            if record["status"] not in {"queued", "indexing"}:
                continue
            try:
                with FileLock(str(self.root / (record["id"][:24] + ".lock")), timeout=0):
                    self.process(record["id"])
            except Timeout:
                continue

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        def worker():
            while not self.stop_event.is_set():
                self.run_pending()
                self.stop_event.wait(.5)
        self.thread = threading.Thread(target=worker, daemon=True, name="document-indexer")
        self.thread.start()

    @property
    def fitments(self):
        from app.repositories.fitments import FitmentRepository
        return FitmentRepository(self.runtime)

    def linked_sources(self, query, limit=8):
        from app.repositories.replacements import ReplacementRepository
        return ReplacementRepository(self.runtime).question_sources(query, limit) or self.fitments.question_sources(query, limit)

    def stop(self):
        self.stop_event.set()

    def names_document(self, query):
        return any(record["name"].casefold() in query.casefold() for record in self.list())

    def search(self, query, limit=12):
        from chromadb.errors import InternalError
        try:
            return self._semantic_search(query, limit)
        except InternalError:
            # Keep original PDF/page provenance if the local vector index is unavailable.
            return self.cached_search(query, limit)

    def cached_search(self, query, limit=12):
        records = [row for row in self.list() if row["status"] == "ready"]
        named = [row for row in records if row["name"].casefold() in query.casefold()]
        if self.names_document(query) and not named:
            return []
        terms = set(re.findall(r"[a-z0-9]{3,}", query.casefold())) - {"the", "and", "what", "for", "which", "are", "can", "parts"}
        matches = []
        for record in named or records:
            path = self.root / (record["id"][:24] + "-chunks.json")
            if not path.is_file():
                continue
            saved = json.loads(path.read_text(encoding="utf-8"))
            if saved.get("sha256") != record["id"]:
                continue
            for chunk in saved["chunks"]:
                text = chunk["text"]
                from app.services.passage_quality import substantive
                if not substantive(text):
                    continue
                words = set(re.findall(r"[a-z0-9]{3,}", text.casefold()))
                score = len(terms & words)
                if not score:
                    continue
                page = chunk["page_number"]
                matches.append((score, {"chunk_id": chunk.get("id", hashlib.sha256(text.encode()).hexdigest()), "title": record["name"] + " · page " + str(page), "content": text, "raw_excerpt": text, "source": record["name"], "page_number": page, "section": "document_passage", "document_id": record["id"], "retrieval_method": "cached keyword fallback", "pdf_url": f"/api/documents/{record['id']}/pdf#page={page}"}))
        matches.sort(key=lambda pair: -pair[0])
        return [source for _, source in matches[:limit]]

    def _semantic_search(self, query, limit=12):
        records = [record for record in self.list() if record["status"] == "ready"]
        named = [record for record in records if record["name"].casefold() in query.casefold()]
        if self.names_document(query) and not named:
            return []
        selected = named or records
        # A named file is an explicit search scope, not a semantic keyword.
        for record in named:
            query = re.sub(re.escape(record["name"]), " ", query, flags=re.IGNORECASE)
        ready = [record["id"] for record in selected]
        if named and ready:
            matches = self.vectors.search(expand_owner_question(query), ready, limit=max(limit * 3, 24), max_distance=1.0)
            terms = set(re.findall(r"[a-z]{3,}", query.casefold())) - {"the", "and", "are", "what", "according", "cite", "uploaded", "pdf", "types"}
            matches.sort(key=lambda source: (-len(terms & set(re.findall(r"[a-z]{3,}", source["content"].casefold()))), source.get("cosine_distance", 1)))
            matches = matches[:limit]
        else:
            matches = self.vectors.search(expand_owner_question(query), ready, limit=limit) if ready else []
        if named:
            matches = [{**source, "retrieval_scope": "named_document"} for source in matches]
        return matches

    def lookup_identifier(self, identifier):
        ready = [record["id"] for record in self.list() if record["status"] == "ready"]
        return self.vectors.lookup_identifier(identifier, ready) if ready else []

    def status(self):
        rows = self.list()
        return {"backend": "Chroma", "embedding_model": "all-MiniLM-L6-v2 (local ONNX, 384 dimensions)", "ready_documents": sum(row["status"] == "ready" for row in rows), "pending_documents": sum(row["status"] in {"queued", "indexing"} for row in rows), "indexed_chunks": sum(row["indexed"] for row in rows if row["status"] == "ready"), "documents": rows}

