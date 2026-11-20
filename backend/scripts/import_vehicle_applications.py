"""Import only reviewed new application tables; no chunking/embedding rebuild."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.settings import Settings
from app.repositories.fitments import FitmentRepository
from app.services.denso_vehicle_parser import SOURCE_SHA, SOURCE_URL, SCHEMA, extract_applications


def main():
    settings = Settings()
    repo = FitmentRepository(settings.runtime_dir)
    cached = repo.imported(SOURCE_SHA, SCHEMA)
    if not cached:
        path = settings.backend_dir / "data/sources/extra/denso_spark_plug_asia_2025.pdf"
        records = extract_applications(path)
        if not records:
            raise ValueError("No reviewed application rows found; existing data unchanged.")
        repo.replace_source(SOURCE_SHA, path.name, SCHEMA, SOURCE_URL, 2, records)
    print(json.dumps({"cached": cached, "spark_plug_rows": repo.search(make="Toyota", category="ignition", limit=1)["total"]}))


if __name__ == "__main__":
    main()
