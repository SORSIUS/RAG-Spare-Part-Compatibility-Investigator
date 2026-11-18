from pathlib import Path

from pypdf import PdfReader


def read_pdf(file_path: str) -> list[dict]:
    pdf_path = Path(file_path)

    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Please provide a PDF file.")

    pages = []

    with pdf_path.open("rb") as pdf_file:
        reader = PdfReader(pdf_file)

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""

            pages.append({
                "source": pdf_path.name,
                "page_number": page_number,
                "text": text.strip(),
            })

    return pages


def read_document(file_path: str | Path) -> list[dict]:
    document_path = Path(file_path)

    if document_path.suffix.lower() == ".pdf":
        return read_pdf(str(document_path))

    if document_path.suffix.lower() == ".txt":
        return [{
            "source": document_path.name,
            "page_number": 1,
            "text": document_path.read_text(encoding="utf-8-sig").strip(),
        }]

    raise ValueError("Supported document formats are .pdf and UTF-8 .txt.")
