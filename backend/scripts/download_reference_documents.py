import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from pypdf import PdfReader

from app.core.settings import Settings
from app.repositories.document_library import DocumentLibrary


REFERENCES = [
    ("denso_filter_guide.pdf", "https://assets.denso-am.eu/production/attachments/Cabin-Air-Filter-Product-Information-Catalogue.pdf"),
    ("kyb_installation.pdf", "https://www.kyb.com/wp-content/uploads/2026/08/KYB-Installer-Guide-Sheets-Shock-Absorber-and-Assembly.pdf"),
    ("kyb_shocks_2023.pdf", "https://kyb.co.za/wp-content/uploads/2023/09/KYB-catalogue-2023.pdf"),
]


def main():
    settings = Settings()
    folder = settings.backend_dir / "data/sources/extra"
    folder.mkdir(parents=True, exist_ok=True)
    library = DocumentLibrary(settings.runtime_dir)
    manifest = []
    for name, url in REFERENCES:
        target = folder / name
        if not target.exists():
            with httpx.stream("GET", url, timeout=60, follow_redirects=True) as response:
                if response.status_code != 200:
                    manifest.append({"name": name, "url": url, "downloaded": False, "http_status": response.status_code})
                    print(json.dumps(manifest[-1]), flush=True)
                    continue
                response.raise_for_status()
                data = bytearray()
                for block in response.iter_bytes():
                    data.extend(block)
                    if len(data) > 25 * 1024 * 1024:
                        raise ValueError("Reference exceeds the 25 MB limit.")
                if not data.startswith(b"%PDF"):
                    raise ValueError("The official URL did not return a PDF.")
                target.write_bytes(data)
        entry = {"name": name, "url": url, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "pages": len(PdfReader(target).pages)}
        manifest.append(entry)
        print(json.dumps({**entry, "registration": library.register(target, name)}), flush=True)
    (settings.runtime_dir / "reference_downloads.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    library.run_pending()
    print(json.dumps(library.status()), flush=True)


if __name__ == "__main__":
    main()
