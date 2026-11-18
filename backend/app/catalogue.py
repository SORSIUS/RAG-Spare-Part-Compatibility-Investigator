import argparse
import hashlib
import json
from pathlib import Path

from app.services.catalogue_service import CatalogueService
from app.services.denso_parser import DensoParser


def main() -> int:
    backend = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="DENSO catalogue evidence lookup; no installation approval.")
    parser.add_argument("action", choices=["index", "lookup", "search", "compare"])
    parser.add_argument("--pdf", type=Path, default=backend / "data/sources/automotive/denso_cabin_air_filters_2026.pdf")
    parser.add_argument("--index", type=Path, default=backend / "data/runtime/denso_catalogue.json")
    parser.add_argument("--part", default=None)
    parser.add_argument("--brand", default=None)
    parser.add_argument("--query", default=None)
    parser.add_argument("--original", default=None)
    parser.add_argument("--candidate", default=None)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive.")
    try:
        if not args.pdf.is_file():
            raise ValueError("Catalogue PDF missing. See docs/DATA_SOURCES.md for the official download.")
        fingerprint = hashlib.sha256(args.pdf.read_bytes()).hexdigest()
        catalogue = json.loads(args.index.read_text(encoding="utf-8")) if args.index.exists() else {}
        if args.action == "index" or catalogue.get("sha256") != fingerprint or catalogue.get("parser_version") != DensoParser.version:
            catalogue = DensoParser().parse(args.pdf)
            if not catalogue["dimensions"] or not catalogue["cross_references"]:
                raise ValueError("Expected DENSO sections not extracted; previous index was not replaced.")
            args.index.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.index.with_suffix(".tmp")
            temporary.write_text(json.dumps(catalogue, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(args.index)
        service = CatalogueService(catalogue)
        if args.action == "index":
            result = {"pages": catalogue["page_count"], "dimensions": len(catalogue["dimensions"]), "cross_references": len(catalogue["cross_references"]), "applications": len(catalogue["applications"]), "warnings": catalogue["warnings"], "index": str(args.index), "limits": catalogue["limits"]}
        elif args.action == "lookup":
            if not args.part:
                raise ValueError("lookup requires --part.")
            result = service.lookup(args.part, args.brand)
        elif args.action == "search":
            if not args.query:
                raise ValueError("search requires --query.")
            result = {"query": args.query, "applications": service.search(args.query, args.limit), "limit": args.limit, "note": "Catalogue mentions only; no exact-vehicle approval."}
        else:
            if not args.original or not args.candidate:
                raise ValueError("compare requires --original and --candidate.")
            result = service.compare(args.original, args.candidate, args.brand)
        output = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
        if args.action == "lookup":
            preview = dict(result)
            for key in ["cross_references", "dimensions", "applications"]:
                preview[key + "_count"] = len(result[key])
                preview[key] = result[key][:args.limit]
            preview["display_note"] = "Lists are limited for display; use --output to save the full lookup."
            print(json.dumps(preview, ensure_ascii=False, indent=2))
        else:
            print(output)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
