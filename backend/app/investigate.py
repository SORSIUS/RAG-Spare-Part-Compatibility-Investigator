import argparse
import json
from pathlib import Path

from app.services.compatibility_service import CompatibilityService
from app.services.evidence_retriever import EvidenceRetriever
from app.services.ingestion_service import IngestionService


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Read documents, retrieve passages, and compare explicit specifications.")
    parser.add_argument("--input-dir", type=Path, default=backend_dir / "data/sample/pdf_manuals")
    parser.add_argument("--rules", type=Path, default=backend_dir / "data/sample/fan_rules.json")
    parser.add_argument("--original", default="FAN-12")
    parser.add_argument("--candidate", default="ALT-A")
    parser.add_argument("--question", default=None)
    parser.add_argument("--output", type=Path, default=backend_dir / "data/runtime/investigation.json")
    arguments = parser.parse_args()
    try:
        ingestion = IngestionService().ingest_directory(arguments.input_dir)
        if ingestion["errors"]:
            raise ValueError("Input documents failed to read: " + json.dumps(ingestion["errors"]))
        if not ingestion["chunks"]:
            raise ValueError("No text available. Check for blank or scanned pages; OCR is not implemented.")
        retriever = EvidenceRetriever(ingestion["chunks"])
        evidence = retriever.search(arguments.question or f"{arguments.original} {arguments.candidate}")
        rules = json.loads(arguments.rules.read_text(encoding="utf-8"))
        comparison = CompatibilityService(retriever, rules).compare(arguments.original, arguments.candidate)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))

    report = {"retrieval_method": "lexical term ranking; no embeddings or LLM", "documents": ingestion["documents"], "retrieved_evidence": evidence, "comparison": comparison}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    temporary_output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary_output.replace(arguments.output)
    print(f"{arguments.original} -> {arguments.candidate}: {comparison['verdict'].upper()}")
    print(comparison["explanation"])
    for check in comparison["checks"]:
        print(f"  {check['label']}: {check['status']}")
        for role in ["requirements", "candidate_evidence"]:
            for citation in check[role]:
                print(f"    {citation['source']} | page {citation['page_number']} | {citation['quote']}")
    print(f"Full report: {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
