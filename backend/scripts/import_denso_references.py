"""Import reviewed cross-reference cells without re-embedding any PDF."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.settings import Settings
from app.repositories.replacements import ReplacementRepository
from app.services.denso_reference_parser import SOURCE_SHA, SCHEMA, extract_references


def main():
    settings = Settings()
    repo = ReplacementRepository(settings.runtime_dir)
    with repo.fitments.connect() as db:
        cached = db.execute("SELECT 1 FROM external_reference_sources WHERE sha=? AND schema=?", (SOURCE_SHA, SCHEMA)).fetchone()
    if not cached:
        path = settings.backend_dir / "data/sources/extra/denso_spark_plug_references_2025.pdf"
        records = extract_references(path, path.name)
        if not records:
            raise ValueError("No reviewed references extracted.")
        repo.replace_external_source(SOURCE_SHA, SCHEMA, records)
    with repo.fitments.connect() as db:
        print(json.dumps({"cached": bool(cached), "counts_by_original_brand": db.execute("SELECT brand,count(*) FROM external_references GROUP BY brand").fetchall()}), flush=True)


if __name__ == "__main__":
    main()
