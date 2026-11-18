from pathlib import Path

from pypdf import PdfReader

from app.services.document_reader import read_document


def read_library_document(path):
    path = Path(path)
    if path.suffix.lower() != ".pdf":
        return read_document(path), []
    reader = PdfReader(path)
    if len(reader.pages) > 1500:
        raise ValueError("This document exceeds the 1500-page indexing limit.")
    pages, warnings = [], []
    for number, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
            warnings.append(number)
        pages.append({"source": path.name, "page_number": number, "text": text.strip()})
    return pages, warnings
