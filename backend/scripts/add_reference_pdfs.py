"""Fetch official reference PDFs with bounded downloads and reusable indexing."""
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
    ('denso_spark_plug_japan_2025.pdf', 'https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_4_japan_2025.pdf'),
    ('denso_spark_plug_europe_2025.pdf', 'https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_5_europe_2025.pdf'),
    ('denso_spark_plug_references_2025.pdf', 'https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_6_others_2025.pdf'),
    ('denso_spark_plug_asia_2025.pdf', 'https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_3_asia_2025.pdf'),
    ('denso_spark_plug_information_2025.pdf', 'https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_1_products_information_2025.pdf'),
]


def main():
    settings = Settings()
    library = DocumentLibrary(settings.runtime_dir)
    folder = settings.backend_dir / 'data/sources/extra'
    folder.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, url in REFERENCES:
        path = folder / name
        if not path.exists():
            partial = path.with_suffix('.download')
            try:
                with httpx.stream('GET', url, follow_redirects=True, timeout=90) as response:
                    response.raise_for_status()
                    size = 0
                    with partial.open('wb') as output:
                        for block in response.iter_bytes():
                            size += len(block)
                            if size > 25 * 1024 * 1024:
                                raise ValueError('Reference exceeds the 25 MB limit.')
                            output.write(block)
                with partial.open('rb') as data:
                    if not data.read(8).startswith(b'%PDF'):
                        raise ValueError('Reference URL did not return a PDF.')
                PdfReader(partial)
                partial.replace(path)
            finally:
                if partial.exists():
                    partial.unlink()
        identifier = hashlib.sha256(path.read_bytes()).hexdigest()
        pages = len(PdfReader(path).pages)
        registration = library.register(path, name, identifier)
        entry = {'name': name, 'url': url, 'sha256': identifier, 'pages': pages, 'bytes': path.stat().st_size, 'duplicate': registration['duplicate']}
        manifest.append(entry)
        print(json.dumps(entry), flush=True)
    (settings.runtime_dir / 'additional_reference_pdfs.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    library.run_pending()
    print(json.dumps({'documents': [r for r in library.list() if r['name'] in {name for name, _ in REFERENCES}]}), flush=True)


if __name__ == '__main__':
    main()
