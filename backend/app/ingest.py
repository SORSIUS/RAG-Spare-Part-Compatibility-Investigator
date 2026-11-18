import argparse
import json
from pathlib import Path

from app.services.ingestion_service import IngestionService
from app.services.text_chunker import TextChunker


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Read local manuals and create source-linked text chunks.")
    parser.add_argument("--input-dir", type=Path, default=backend_dir / "data/sample/manuals")
    parser.add_argument("--output", type=Path, default=backend_dir / "data/runtime/ingestion.json")
    parser.add_argument("--chunk-words", type=int, default=180)
    parser.add_argument("--overlap-words", type=int, default=30)
    arguments = parser.parse_args()

    try:
        service = IngestionService(TextChunker(arguments.chunk_words, arguments.overlap_words))
        report = service.ingest_directory(arguments.input_dir)
    except (ValueError, OSError) as error:
        parser.error(str(error))

    if not report["documents"] and not report["errors"]:
        parser.error("No supported PDF or TXT documents found. Previous output was not changed.")

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    temporary_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_output.replace(arguments.output)
    print(f"Read {len(report['documents'])} documents; created {len(report['chunks'])} chunks; {len(report['errors'])} errors.")
    print(f"Report: {arguments.output}")
    for document in report["documents"]:
        print(f"  {document['source']}: {document['page_count']} page(s), {document['chunk_count']} chunks")
        for warning in document["warnings"]:
            print(f"    Warning: {warning}")
    for error in report["errors"]:
        print(f"  Failed: {error['source']} ({error['error_type']}): {error['message']}")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
