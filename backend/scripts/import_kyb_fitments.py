"""Download once; import source-linked application rows once per PDF revision."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from app.core.settings import Settings
from app.repositories.document_library import DocumentLibrary
from app.services.kyb_fitment_parser import extract_catalogue, SCHEMA, SOURCE_URL, SOURCE_SHA


def main():
    settings = Settings()
    target = settings.backend_dir / "data/sources/extra/kyb_mea_accessories.pdf"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        with httpx.stream("GET", SOURCE_URL, timeout=90, follow_redirects=True) as response:
            response.raise_for_status()
            data = bytearray()
            for block in response.iter_bytes():
                data.extend(block)
                if len(data) > 25 * 1024 * 1024:
                    raise ValueError("Catalogue exceeds 25 MB.")
        if not data.startswith(b"%PDF"):
            raise ValueError("Source did not return a PDF.")
        target.write_bytes(data)
    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    if sha != SOURCE_SHA:
        raise ValueError("The source edition changed. Review the new table layout before importing it.")
    library = DocumentLibrary(settings.runtime_dir)
    library.register(target, target.name, sha)
    if not library.fitments.imported(sha, SCHEMA):
        records, pages = extract_catalogue(target, sha, lambda page: print(f"Read application page {page}", flush=True))
        if not records:
            raise ValueError("No supported table rows found. The existing index is unchanged.")
        library.fitments.replace_source(sha, target.name, SCHEMA, SOURCE_URL, pages, records)
    else:
        print("Cached fitment index reused; no PDF extraction.", flush=True)
    options = library.fitments.options()
    summary = {"records": options["record_count"], "makes": len({v["make"] for v in options["vehicles"]}), "model_groups": len(options["vehicles"]), "sources": options["sources"]}
    (settings.runtime_dir / "fitment_import.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary), flush=True)
    # The normal background worker handles semantic chunks independently. The
    # relational lookup above is usable as soon as its transaction commits.


if __name__ == "__main__":
    main()
