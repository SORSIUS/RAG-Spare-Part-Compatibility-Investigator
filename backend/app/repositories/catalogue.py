import hashlib
import json
import threading
from dataclasses import dataclass

from app.core.settings import Settings
from app.services.denso_parser import DensoParser
from app.services.document_reader import read_pdf
from app.services.text_chunker import TextChunker


@dataclass(frozen=True)
class CatalogueSnapshot:
    fingerprint: str
    catalogue: dict
    page_chunks: list[dict]


class CatalogueRepository:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.lock = threading.RLock()
        self.snapshot = None

    def load(self, force: bool = False) -> CatalogueSnapshot:
        with self.lock:
            pdf = self.settings.pdf_path
            if not pdf.is_file():
                raise FileNotFoundError("The local DENSO PDF is missing. Follow docs/DATA_SOURCES.md to download it.")
            fingerprint = hashlib.sha256(pdf.read_bytes()).hexdigest()
            if not force and self.snapshot and self.snapshot.fingerprint == fingerprint:
                return self.snapshot
            self.settings.runtime_dir.mkdir(parents=True, exist_ok=True)
            path = self.settings.runtime_dir / "denso_catalogue.json"
            try:
                catalogue = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                catalogue = {}
            if force or catalogue.get("sha256") != fingerprint or catalogue.get("parser_version") != DensoParser.version:
                catalogue = DensoParser().parse(pdf)
                if not catalogue["dimensions"] or not catalogue["cross_references"]:
                    raise ValueError("The document did not produce the expected DENSO records. The previous index was kept.")
                self.write_json(path, catalogue)
            chunk_path = self.settings.runtime_dir / "denso_page_chunks.json"
            try:
                pages = json.loads(chunk_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pages = {}
            if force or pages.get("sha256") != fingerprint or pages.get("schema_version") != 1:
                from dataclasses import asdict
                chunker = TextChunker(180, 30)
                chunks = [asdict(chunk) for page in read_pdf(str(pdf)) for chunk in chunker.chunk_page(page, fingerprint)]
                pages = {"sha256": fingerprint, "schema_version": 1, "chunks": chunks}
                self.write_json(chunk_path, pages)
            if hashlib.sha256(pdf.read_bytes()).hexdigest() != fingerprint:
                raise ValueError("The catalogue changed while indexing. Retry after the file finishes saving.")
            self.snapshot = CatalogueSnapshot(fingerprint, catalogue, pages["chunks"])
            return self.snapshot

    @staticmethod
    def write_json(path, body):
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
