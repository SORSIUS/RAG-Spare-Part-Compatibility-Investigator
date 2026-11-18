# DENSO automotive workflow

## Implemented sequence

1. DensoParser opens the local PDF and extracts layout-preserving text from its 141 pages.
2. Section headers select application, cross-reference, or dimension parsing.
3. Application records retain make, vehicle wording, production range, filter part numbers, and AC/steering qualifiers as text. Wrapped vehicle labels and qualifier lines are retained where recognized.
4. Reference records retain the external brand, exact external part identifier, and DENSO identifier. Case and whitespace normalization do not discard leading zeros, hyphens, or suffixes.
5. Dimension records pair photo-guide part labels with length, width, and height in millimetres. Decimal commas are normalized to numeric values. Misaligned rows are skipped with warnings.
6. CatalogueService provides exact identifier lookup, all-term application search, and conservative comparison.
7. Every record retains a source filename, 1-based PDF page, section, and extracted evidence. Reference quotations are selected column cells with a separate brand heading. Dimension quotations are normalized column excerpts, rather than a complete unchanged page transcription.

## Files and responsibilities

- backend/app/services/denso_parser.py: source-specific extraction and anomaly reporting.
- backend/app/services/catalogue_service.py: lookups, text search, and evidence checks.
- backend/app/catalogue.py: CLI, source fingerprint checks, local index management, and report export.
- backend/tests/test_catalogue.py: 18 offline synthetic-layout and domain tests.
- backend/tests/test_denso_local_catalogue.py: 5 optional checks against the locally downloaded manufacturer source.

The existing ingestion, sample-PDF investigation, and isolated teacher demo remain available. The automotive extractor uses pypdf and Python's standard library. The main web app additionally uses FastAPI, Uvicorn, httpx, Pydantic, and python-dotenv; see backend/requirements.txt.

## Examples

From backend:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m app.catalogue index
.\.venv\Scripts\python.exe -X utf8 -m app.catalogue search --query "Toyota Corolla" --limit 2
.\.venv\Scripts\python.exe -X utf8 -m app.catalogue lookup --part DCF002K --limit 1
.\.venv\Scripts\python.exe -X utf8 -m app.catalogue lookup --part C30001 --brand "1A FIRST AUTOMOTIVE" --limit 1
.\.venv\Scripts\python.exe -X utf8 -m app.catalogue compare --original C30001 --candidate DCF357P --brand "1A FIRST AUTOMOTIVE"
.\.venv\Scripts\python.exe -X utf8 -m app.catalogue compare --original DCF009P --candidate DCF031P
```

The explicit C30001 reference should produce documented_reference, not vehicle approval. The two dimensioned DENSO parts in the final example differ and produce conflict. A missing number or equally sized pair without a direct reference remains unknown. Identical external numbers under different brands require an explicit brand before establishing a reference.

The default PDF is backend/data/sources/automotive/denso_cabin_air_filters_2026.pdf. The default index is backend/data/runtime/denso_catalogue.json. --pdf and --index accept alternative paths. Index reuse requires the same source content hash and parser version; index explicitly rebuilds. Run one indexing process per output path at a time. --output writes a full local report; lookup only limits the console preview. Application search is literal all-term matching, not semantic search, and its limit affects the saved result too.

## Validation and remaining limits

The checked edition yielded 345 dimension records, 7,798 cross-reference rows, and 3,704 application rows. No parser structural warnings were reported after the layout fixes. This does not prove every source row was extracted or correctly interpreted. The PDF reader also warns about rotated text; representative rendered pages show rotated section/tab labels, while the parsed horizontal table content was inspected. The implementation does not claim lossless extraction of every rotated element.

Visual checks covered application page 4, cross-reference page 68, and photo-guide page 97. Integration assertions additionally check dimensions on page 111, leading-zero references on page 76, and a DENSO-brand column on page 75. The source reader returns physical PDF page positions, not a separately inferred page-label scheme.

Main-backend tests: 36 passed. Optional local-catalogue checks: 5 passed. Lookup, application-search, dimension-conflict, and documented-reference CLI commands were also run successfully. The optional tests skip on a fresh clone without the manufacturer PDF. Test command:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The manufacturer's source and derived full indexes remain local and ignored by Git. No commit or push was performed.

## What this does not establish

Application records are mentions, not validated exact-vehicle matches. Region, steering side, air conditioning, build dates, trim, revision, and other qualifiers still need a dedicated validation layer. Qualifier text is retained but not converted into a complete fitment rule system. Shared application rows and equal dimensions do not imply equivalent filtration performance or authorized substitution. A reference is directional as published; no transitive cross-brand equivalence is inferred.

## Main web app and Groq follow-up — 2026-11-18

The main browser app now retrieves structured records plus page chunks and provides a Groq answer integration with source IDs, quotes, and original PDF links. This uses lexical BM25-style ranking; semantic retrieval and arbitrary PDF table extraction remain future work. The next fitment layer must ask for missing vehicle details rather than silently dropping qualifiers.

Start START_PROJECT.cmd from the project root and open http://127.0.0.1:3201. Search sources requires only the local PDF. Ask Groq additionally requires a key configured in backend/.env; live provider verification remains pending. See the root README for setup and docs/VERIFICATION.md for exact test coverage.

The expanded suite passes 67 backend tests, including 10 checks that require the actual local source, plus 7 frontend tests and a Node/Python HTTP integration walkthrough. No live Groq answer or current browser visual walkthrough is claimed. Earlier PDF-page visual checks refer to source layouts inspected during the prior parsing milestone.
