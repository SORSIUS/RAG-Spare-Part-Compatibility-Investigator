import hashlib
from dataclasses import asdict
from pathlib import Path

from app.services.document_reader import read_document
from app.services.text_chunker import TextChunker


class IngestionService:
    def __init__(self, chunker: TextChunker | None = None):
        self.chunker = chunker or TextChunker()

    def ingest_directory(self, input_dir: str | Path) -> dict:
        directory = Path(input_dir).resolve()
        if not directory.is_dir():
            raise NotADirectoryError(f"Document directory not found: {directory}")

        report = {"schema_version": 1, "documents": [], "chunks": [], "errors": []}
        paths = sorted(
            path for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in {".pdf", ".txt"}
        )

        for path in paths:
            source = path.relative_to(directory).as_posix()
            try:
                document_id = hashlib.sha256(path.read_bytes()).hexdigest()
                pages = read_document(path)
                chunks = []
                empty_pages = []

                for page in pages:
                    page["source"] = source
                    if not page["text"].strip():
                        empty_pages.append(page["page_number"])
                    chunks.extend(self.chunker.chunk_page(page, document_id))

                report["documents"].append({
                    "document_id": document_id,
                    "source": source,
                    "page_count": len(pages),
                    "chunk_count": len(chunks),
                    "empty_pages": empty_pages,
                    "page_reference_type": "pdf_page" if path.suffix.lower() == ".pdf" else "single_text_document",
                    "warnings": ["No text extracted from some pages. They may be blank or need OCR."] if empty_pages else [],
                })
                report["chunks"].extend(asdict(chunk) for chunk in chunks)
            except Exception as error:
                report["errors"].append({"source": source, "error_type": type(error).__name__, "message": str(error)})

        return report
