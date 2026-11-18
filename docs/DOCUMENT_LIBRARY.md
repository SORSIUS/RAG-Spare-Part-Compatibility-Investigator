# Uploads, Chroma, and everyday car questions

Added 2026-11-18. This is the current workflow; older milestone notes remain historical.

## Run

Use START_PROJECT.cmd from the project root. Open the actual PROJECT_READY address. The tested updated instance is http://127.0.0.1:52121.

Dependencies are already installed in this workspace. For a fresh Windows environment in a long project path, create backend/.venv and run from backend:

```powershell
.\scripts\install_dependencies.ps1
```

The helper launches the project Python with an extended Windows path, avoiding pip's long-path error without changing OS settings. On other platforms, install requirements.txt normally.

## Upload workflow

1. Choose a PDF or UTF-8 text file in Your reference documents.
2. Upload streams through Node to Python. Python checks type/header/size, saves the bytes, and computes SHA-256.
3. The server returns HTTP 202 and a document ID after saving. It does not await extraction or embeddings.
4. A background worker extracts pages, creates page-aware word chunks, and saves the extraction cache.
5. The local MiniLM tokenizer creates windows of at most 220 content tokens with overlap; the embedding model has a 256-token input limit.
6. Local ONNX inference creates normalized 384-dimensional vectors, which are upserted into persistent Chroma.
7. The document becomes ready only after its expected vector IDs are present. Only ready documents participate in search.

The UI keeps the question area available during preparation. A small per-document status tells you when it becomes searchable; processing is not a blocking upload screen. File transfer itself still depends on file size, disk, and network.

Supported: PDF and UTF-8 TXT, up to 25 MB; PDF indexing is limited to 1500 pages. Image-only PDFs require OCR, which is not implemented. Unreadable pages are skipped with a coverage notice; readable pages can still be indexed. A failed document has its own retry button.

## Incremental indexing

The SQLite document registry records content hash, display name, local path, state, page/chunk counts, embedding schema, and timestamps. Paths are not exposed by the list API.

- Same bytes, even with another filename: reuse the same document and index.
- Different bytes: create a new revision with a new hash and new vector IDs.
- New upload: process only that document; do not reparse existing ready files.
- Interrupted job: a process-safe file lock protects the document; its saved extraction is reused, and already-written vector IDs are skipped.
- Embedding/index-schema changes: explicitly requeue affected documents; this is a migration, not the behavior of a normal upload.

Per-document cache files are saved atomically. PDF links include the immutable document ID; the server checks that the stored bytes still match it. Renaming or overwriting a source outside the app cannot silently change the cited revision.

## Storage

| Location under backend/data/runtime | Role |
| --- | --- |
| conversations.sqlite3 | Existing chat history and saved answer/source snapshots |
| library/documents.sqlite3 | Document registry and indexing progress/history |
| library/*-chunks.json | Cached page extraction and word chunks |
| library/files/ | User-uploaded PDF/TXT files named by content hash |
| vectors/ | Persistent Chroma collection, embeddings, and index files |
| models/ | Downloaded local all-MiniLM-L6-v2 ONNX model and tokenizer |

The Chroma collection uses cosine distance. A distance threshold rejects weak matches; the value is a heuristic, not a probability of correctness. Exact identifiers and structured catalogue rows retain priority. Ordinary phrases can be expanded into retrieval terms, such as bouncing → shock absorbers/suspension. Expansion changes retrieval, not factual claims.

All these runtime files stay outside Git. Embeddings are computed locally. Generated answers send the question, bounded dialogue, and selected excerpts to Groq; they do not upload the complete PDF. MCP clients can retrieve ready document excerpts through search_catalogue.

## Windows native storage

This project's name contains a Unicode dash. The native Chroma HNSW backend failed to reopen its index through that Windows path. native_paths.py creates a verified ASCII directory junction named .rag-native-... beside the project folder. It points back into the project; actual data remains under backend/data/runtime.

The helper verifies the target before reusing the junction and does not change Windows security or long-path settings. The old failed development build under runtime/chroma is not the active index; runtime/vectors is active. A library can be reopened by another Python/MCP process and still query its persisted vectors.

## Everyday questions and decisions

You can ask: “Can I use Corolla suspension in a Honda City?” Part numbers are optional.

For an incomplete swap question, the app says it cannot confirm the swap yet and asks for both car years, the specific component/axle, and market/trim. A later year-led clarification can reuse the preceding question. This clarification step does not need a model call.

When documents support an answer, Groq explains the selected evidence with checked citations. It must not equate a shared part name, similar dimensions, generic installation guidance, or nearby application rows with verified interchangeability. Missing evidence stays unknown. An insufficient-evidence answer does not display model-generated factual claims as established facts.

Explicit comparisons of two documented DENSO dimension records use CatalogueService rules and exact source quotations directly. The UI marks these as CATALOGUE CHECK. Groq remains responsible for broader document Q&A, not numerical decisions that the existing rules can compute.

The structured comparison matrix still targets the DENSO catalogue. Generic uploaded PDFs and the KYB catalogue are searchable text, not newly certified fitment databases or losslessly reconstructed tables.

## Additional real source

Downloaded from the [official KYB South Africa catalogue URL](https://kyb.co.za/wp-content/uploads/2023/09/KYB-catalogue-2023.pdf):

- Local source: backend/data/sources/extra/kyb_shocks_2023.pdf.
- Edition/region: 2023 regional suspension catalogue; do not treat it as a universal or current global vehicle-fitment source.
- Size: 16,983,101 bytes; 160 PDF pages.
- SHA-256: 4b9d7d42c3be79739a348838c3273bbc67c137124c590feacbbd56ec8ef27c50.
- Indexed: 1,148 token windows. Physical PDF page 153 exceeded the PDF reader's parsing budget and was skipped; the coverage warning is retained.

Together with DENSO's 1,234 token windows, there are 2,382 ready manufacturer-reference windows. A clearly named fictional PDF is used for integration verification, then excluded from normal answers.

The DENSO product-information guide and KYB installation-sheet URLs returned HTTP 403. They were not downloaded or indexed. The download script records these outcomes and continues to accessible sources. The manufacturer's PDF and generated indexes are not committed; redistribution permission has not been established.

## Verification

From backend:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests
.\.venv\Scripts\python.exe -X utf8 scripts/verify_document_library.py --url http://127.0.0.1:52121
.\.venv\Scripts\python.exe -X utf8 scripts/verify_main_app.py
```

Use your current app URL. The document-library verifier uploads a fictional training PDF, checks real embeddings/Chroma and MCP, and excludes that test reference from later answers. It creates local test records and consumes no Groq quota. The separate verify_live_answers.py intentionally calls Groq.

Observed: 96 backend tests, 11 frontend tests, and 17 library integration checks passed. The first small-PDF upload was acknowledged in 0.014 seconds with queued state; later cached/repeated checks were faster. This measures a small local fixture, not arbitrary large-upload performance. Real embedding dimension was 384; the maximum stored token count observed was 223, below the 256-token limit.

Source/quote checks do not prove semantic entailment. Some generated answers were withheld during live testing; failed quotations are never accepted just to produce an answer. Visual browser/accessibility testing remains pending. See VERIFICATION.md for the retained live-test history.
