"""Register user-supplied educational PDFs once; resume indexing from the queue."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.settings import Settings
from app.repositories.document_library import DocumentLibrary

MATERIALS = [
    ("A Complete List of Car Body Parts [Names & Functions] PDF.pdf", "education"),
    ("List of 22 Basic Car Engine Parts & Their Functions [PDF].pdf", "education"),
    ("Automobile Engineering.pdf", "education"),
    ("CATALOGUE-flipbook.pdf", "product_group_overview"),
]


def main():
    settings = Settings()
    library = DocumentLibrary(settings.runtime_dir)
    manifest = []
    for name, role in MATERIALS:
        path = settings.backend_dir / "data/sources/automotive" / name
        if not path.is_file():
            print(json.dumps({"name": name, "status": "not_present"}), flush=True)
            continue
        result = library.register(path, name)
        manifest.append({"name": name, "role": role, "provenance": "user supplied; original download URL not provided", "registration": result})
        print(json.dumps({"name": name, "duplicate": result["duplicate"], "role": role}), flush=True)
    (settings.runtime_dir / "learning_materials.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    library.run_pending()
    identifiers = {entry["registration"]["id"] for entry in manifest}
    print(json.dumps([row for row in library.list() if row["id"] in identifiers]), flush=True)


if __name__ == "__main__":
    main()
