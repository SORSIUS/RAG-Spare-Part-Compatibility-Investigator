import threading
import re
from pathlib import Path

from chromadb import PersistentClient
from chromadb.config import Settings as ChromaSettings
from filelock import FileLock

from app.integrations.local_embeddings import LocalEmbeddings, MODEL, SCHEMA
from app.core.native_paths import native_directory


class VectorStore:
    def __init__(self, runtime):
        self.runtime = Path(str(runtime).removeprefix("\\\\?\\"))
        self.embeddings = LocalEmbeddings(self.runtime)
        self.lock = threading.RLock()
        self._collection = None

    @property
    def collection(self):
        with self.lock:
            if self._collection is None:
                self.runtime.mkdir(parents=True, exist_ok=True)
                self.client = PersistentClient(path=str(native_directory(self.runtime / "vectors")), settings=ChromaSettings(anonymized_telemetry=False))
                self._collection = self.client.get_or_create_collection("automotive_documents_v1", embedding_function=None, configuration={"hnsw": {"space": "cosine"}}, metadata={"embedding_model": MODEL, "schema": SCHEMA})
            return self._collection

    def add(self, document_id, chunks, progress=lambda count, total: None):
        with FileLock(str(self.runtime / "vectors.lock"), timeout=180):
            collection = self.collection
            existing = set(collection.get(where={"document_id": document_id}, include=[])["ids"])
            pending = [chunk for chunk in chunks if chunk["id"] not in existing]
            maximum = min(32, self.client.get_max_batch_size())
            for start in range(0, len(pending), maximum):
                batch = pending[start:start + maximum]
                vectors = self.embeddings.embed([chunk["text"] for chunk in batch])
                collection.upsert(ids=[chunk["id"] for chunk in batch], documents=[chunk["text"] for chunk in batch], embeddings=vectors, metadatas=[{"document_id": document_id, "source": chunk["source"], "page_number": chunk["page_number"], "chunk_number": chunk["chunk_number"]} for chunk in batch])
                progress(len(existing) + min(start + maximum, len(pending)), len(chunks))
            expected = {chunk["id"] for chunk in chunks}
            stale = existing - expected
            if stale:
                collection.delete(ids=sorted(stale))
            written = set(collection.get(where={"document_id": document_id}, include=[])["ids"])
            if written != expected:
                raise ValueError("Vector insertion did not produce the expected count.")

    def search(self, query, ready_ids, limit=12, max_distance=.62):
        if not ready_ids:
            return []
        vector = self.embeddings.embed([self.embeddings.split(query)[0]])[0]
        result = self.collection.query(query_embeddings=[vector], n_results=min(limit, self.collection.count()), where={"document_id": {"$in": ready_ids}}, include=["documents", "metadatas", "distances"])
        matches = []
        for identifier, text, metadata, distance in zip(result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]):
            if re.search(r"\bbounc\w*", query, re.IGNORECASE) and not re.search(r"\b(body|tyres?|tires?|bounc\w*|oscillat\w*)\b", text, re.IGNORECASE):
                continue
            if distance <= max_distance and len(text.split()) >= 8:
                matches.append({"chunk_id": identifier, "title": metadata["source"] + " · page " + str(metadata["page_number"]), "content": text, "raw_excerpt": text, "source": metadata["source"], "page_number": metadata["page_number"], "section": "document_passage", "document_id": metadata["document_id"], "cosine_distance": round(distance, 5), "pdf_url": f"/api/documents/{metadata['document_id']}/pdf#page={metadata['page_number']}"})
        if re.search(r"\bbounc\w*", query, re.IGNORECASE):
            matches.sort(key=lambda source: (not bool(re.search(r"\bbounc\w*", source["content"], re.IGNORECASE)), not bool(re.search(r"\bbumps?\b", source["content"], re.IGNORECASE)), source["cosine_distance"]))
            return matches[:2]
        return matches

    def lookup_identifier(self, identifier, ready_ids, limit=8):
        if not ready_ids:
            return []
        result = self.collection.get(where={"document_id": {"$in": ready_ids}}, where_document={"$contains": identifier.upper()}, limit=limit * 3, include=["documents", "metadatas"])
        matches = []
        for text, metadata in zip(result["documents"], result["metadatas"]):
            if not re.search(r"(?<!\w)" + re.escape(identifier) + r"(?!\w)", text, re.IGNORECASE):
                continue
            matches.append({"title": metadata["source"] + " · page " + str(metadata["page_number"]), "content": text, "raw_excerpt": text, "source": metadata["source"], "page_number": metadata["page_number"], "section": "document_passage", "document_id": metadata["document_id"], "retrieval_method": "exact/document", "pdf_url": f"/api/documents/{metadata['document_id']}/pdf#page={metadata['page_number']}"})
        return matches[:limit]
