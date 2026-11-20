# Detailed change history

## 2026-11-20 — Vehicle/year/engine questions without part numbers

- Added engine size/code, component and optional market filtering to indexed fitment retrieval; exposed these through REST and engine input in the frontend.
- Added ordinary-owner question parsing and a saved year/engine clarification flow. Complete structured vehicle questions return checked cited catalogue details without Groq calls; unknown engine details remain explicit.
- Imported 60 reviewed Toyota Taiwan spark-plug application rows from DENSO Asia pages 99–100, preserving model variants, engine, production range, OEM number, standard plug and physical source page. Generic model names normalize variants while keeping the full original label.
- Excluded ambiguous cells, engine-less rows and unsupported date forms. Kept explicit regional mismatches out of structured results and avoided converting source-market rows into global approvals.
- Verification: 120 backend / 13 frontend tests; live multi-turn history, engine/component filters, PDF sources and actual MCP queries passed. No re-embedding or paid LLM calls; no new browser walkthrough.

## 2026-11-20 — More official catalogues and useful incomplete answers

- Downloaded and indexed DENSO Japan, Europe/USA and Others/cross-reference sections: 179 pages, 3,217 new embedding windows. Older documents were reused.
- Added a hash-locked, column-bounded OEM-to-standard-DENSO parser and cached external reference tables. Imported 1,341 number references (137 Toyota); retained vehicle-fitment caveats. This is alongside, not equivalent to, the existing 345 KYB application references.
- Improved empty lookup messages, added continuation into chat, and retained checked cited findings in partial answers. Missing evidence never becomes an invented yes/no.
- Extended identifier/citation guardrails, safe checked fallback, parser/partial-answer regressions and live API/MCP verification. Final checks: 116 backend / 13 frontend tests; no LLM calls. Fresh browser interaction was not tested.

## 2026-11-20 — Materials and directed replacement references

- Registered four user-added learning/product-overview PDFs: all ready, 989 local embedding windows combined. Older documents were reused.
- Added an indexed original-brand/number lookup, derived only from reviewed single-OEM/single-aftermarket KYB cells. Current snapshot: 345 qualified application references, 144 distinct brand/original combinations, 14 makes; 168 Toyota application references.
- Added REST `/api/replacements`, an expandable frontend lookup, and replacement-question evidence through the existing MCP search tool. Preserved source hashes/pages and application conditions.
- Grouped cells, reverse/transitive links and arbitrary uploaded tables do not create replacement edges. Source reimport invalidates its derived links.
- Added registration/live-verification scripts, regression coverage and a material-download guide. No Groq calls were needed for this update. Browser visual QA was not run.

## 2026-11-20 — Gradients, new reference PDFs and chat recovery

Added gradient themes, original illustrative automotive image, conversation bubbles/composer, pending-question feedback and helpful retry replies. Provider errors now create source-preserving assistant recovery messages; exports include them. Improved short vehicle-detail follow-up context. Added two official DENSO 2025 PDF references with a reusable bounded download/index script and provenance manifest.

Verification finished with 107 backend tests, 13 frontend tests, JS syntax and the Node/Python HTTP/MCP HTTP+stdio walkthrough passing. Browser visual QA was blocked by the computer-use URL-confidence policy and remains explicitly outstanding. README/setup and progress notes updated. No further LLM/image calls were used for the final verification; no commit or push.

## 2026-11-20 — Vehicle-first interface and indexed fitment links

Added the official KYB MEA accessories importer and local SQLite vehicle/application/component/part/source index. Supported tables supplied 3,814 associations, 14 makes and 178 model groups, including 395 Corolla associations. Hash/schema history reuses completed imports, and matching questions skip broad lexical/Chroma retrieval. OEM cell groups remain grouped rather than invented individual interchangeability mappings. Other PDF layouts require separate reviewed adapters.

Built automotive navigation, make/model/year/position/chassis selection, application cards, source actions, compact catalogue uploads and saved investigations. Existing light/dark modes and ordinary document RAG remain. Drawings are labelled illustrations; no prices/stock or installation approval are implied. Research and coverage limits: FITMENT_INDEX.md.

Fixed duplicate PDF header contamination and model names containing digits. The live LLM explanation changed a production code; validation rejected it. Added a checked source-wording fallback, disclosed in the UI, plus fabricated KYB/chassis identifier rejection. The final live retest used that fallback.

Verification: 107 backend tests, 12 frontend tests, JS syntax, exact/empty API queries, fingerprinted PDF, cached import, desktop/mobile browser checks, saved history and part-to-question flow. Local indexed-query median 6.17 ms over 20 calls excludes HTTP/LLM time. No commit/push or demo changes in this update. Setup remains in the root README.

Historical entries describe the state at the time. See the root README for current setup and capabilities.

## Milestones

- 2026-11-16: Teacher selection, modular scaffold, and separate fictional prototype.
- 2026-11-17: PDF ingestion, sample comparison, and real DENSO catalogue CLI.
- 2026-11-18: Main local web app, Groq adapter, source desk, conversation storage, citation checks, and automated integration verification. Live-provider and visual browser verification remain pending.

## Change record — 2026-11-18: workflow audit, comparison, reports, and MCP

This section is an appended learning record. Earlier sections describe the prior milestone; this record supersedes their statements that the main comparison matrix is future work and that the suite contains 67 backend/7 frontend checks. The earlier text is retained so we can see how the project developed.

### What we checked against the main workflow

**Read documents → retrieve evidence → compare requirements → explain matches, conflicts, and unknowns.**

| Stage | Current implementation | Check performed |
| --- | --- | --- |
| Read documents | Existing pypdf reader and DENSO-specific parser | Existing ingestion/parser tests and actual 141-page local PDF |
| Retrieve evidence | BM25-style record/page retrieval with fresh source fingerprints | Exact identifiers, unknown query, applications, references, balanced two-part retrieval |
| Compare requirements | Existing deterministic domain rules, now available in the browser, REST, and MCP | Field conflict/match/unknown, direct reference, unknown part, input rejection, PDF citations |
| Explain findings | Groq answer service with checked citations; matrix explanations do not use an LLM | Mock-provider checks, withheld bad citations, missing-key handling; live Groq still pending |
| Preserve investigation | Existing SQLite chat history plus new downloads | Exported saved source snapshots, repeated follow-ups, history after Python reload |
| Let agents use it | Official MCP SDK and typed REST operations share the same catalogue services | Real MCP discovery, calls, and resource reads over HTTP and stdio |

### Every implementation change in this update

| Files / area | What changed and why | Concept to learn |
| --- | --- | --- |
| backend/app/models/catalogue.py | Added validated comparison, evidence-search, and lookup requests; rejects blank fields, extra properties, and out-of-range limits | Pydantic schemas and input boundaries |
| backend/app/services/catalogue_tools.py | Added a shared facade for metadata, search, bounded lookup, and cited comparisons; no LLM or chat writes | Reuse one service layer across interfaces |
| backend/app/services/answer_service.py | Persisted the resolved retrieval query so successive pronoun follow-ups keep the original part | Conversation context differs from retrieved evidence |
| backend/app/services/report_service.py | Added Markdown/JSON conversation exports preserving claims, quotes, source snapshots, dates, and per-question citation scope | Reporting from saved records rather than regenerating answers |
| backend/app/main.py | Added catalogue REST operations, export routes, agent-interface metadata, and mounted MCP with its required session-manager lifecycle | FastAPI routes, shared dependencies, ASGI lifespan |
| backend/app/mcp_server.py | Added four annotated, structured-output MCP tools and two resources; supports stdio and Streamable HTTP | MCP discovery, tools, resources, transports, tool errors |
| backend/mcp_entry.py | Added an absolute-script entry for clients that start outside the backend folder | Python script import paths and process working directories |
| backend/requirements.txt | Pinned official mcp==2.3.0; installed dependencies and checked compatibility | Reproducible dependencies and pip check |
| backend/scripts/print_mcp_config.py | Prints client configuration using the current environment's absolute Python and entry paths; no key or external app edits | JSON configuration and portable process launch arguments |
| frontend/server.mjs | Proxies /mcp and /openapi.json, forwards MCP protocol/Accept headers, serves the added component assets | Protocol-aware proxying rather than assuming every API is ordinary JSON |
| frontend/src/components/comparison.js | Added safe DOM rendering for a side-by-side matrix, source links, missing-value labels, and downloadable comparison Markdown/JSON | Separate presentation, formatting, and download functions |
| frontend/comparison.css and frontend/index.html | Added a collapsible comparison form, responsive table, explicit status labels, and conversation download links | Component styles, accessible labels, status without color alone |
| frontend/src/app.js | Connected comparison requests, exports, form busy state, and elapsed-time feedback; clears old comparison output before a new request | UI state and asynchronous operations |
| frontend/src/services/api.js | Added comparison response-shape validation | Detect an incompatible/stale backend before rendering |
| frontend/package.json | Extended syntax checks to include the comparison module | Keep verification commands aligned with added files |
| backend/tests/test_agent_features.py | Added 9 focused tests for the API, reports, repeated pronouns, MCP discovery/results/resources, validation, and origin protection | Test observable behavior and failure paths |
| frontend/tests/comparison.test.mjs | Added 3 checks for missing/different values, cited report content, and stale comparison responses | Test logic that can fail independently of the browser |
| backend/scripts/verify_main_app.py | Extended the real-catalogue walkthrough with comparison, exports, schema discovery, actual MCP HTTP and stdio, and preserved reload checks | Unit tests and real transport integration answer different questions |
| docs/MCP_AND_API.md, PROJECT_README.md, PROPOSAL_README.md, docs/VERIFICATION.md | Documented operation, scope, results, and what is still unverified; appended milestone notes to existing documents | Maintain a traceable record of changes and evidence |

### Try the new features

Use START_PROJECT.cmd as before, then open http://127.0.0.1:3201. If an older app instance is running, restart it once because server/proxy files changed.

1. Expand **Compare two parts**. The default DCF009P → DCF031P pair demonstrates differing documented dimensions. Each field has a word label and PDF-page links.
2. To inspect a direct reference, enter original C30001, candidate DCF357P, and brand 1A FIRST AUTOMOTIVE. It returns a published direct reference, not installation approval.
3. Download the comparison as Markdown or JSON.
4. Run Search sources or Ask Groq in the chat. Saved investigations now have Markdown and JSON download links. Exports use the stored answer/source snapshot and make no new Groq call.
5. Connect a compatible MCP client to http://127.0.0.1:3201/mcp or generate stdio configuration using the command below.

From backend:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/print_mcp_config.py
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -X utf8 scripts/verify_main_app.py
```

MCP tools: catalogue_info, search_catalogue, lookup_part, compare_parts. They work without a Groq key and do not expose local chat history. Ordinary agents can also use the typed REST API and /openapi.json. See [MCP/API setup and examples](docs/MCP_AND_API.md).

### Observed results and remaining work

The updated automated suite contains **76 backend tests and 10 frontend tests**. Real Node/Python checks also cover actual-catalogue comparisons, saved report downloads, the MCP HTTP proxy, a separate MCP stdio process, PDF version checking, and automatic Python reload. Dependency compatibility is checked with pip check. See [verification details](docs/VERIFICATION.md).

Windows Computer Use was attempted for visual review but stopped itself because it could not confidently verify the current browser URL. No browser visual pass is claimed; no further browser input was issued. Live Groq validation still requires this project's locally configured key. No claim of universal error-free operation or measured fitment accuracy follows from passing these checks.

Next useful work: a reviewed live-answer question set, browser walkthrough, and explicit vehicle qualification rules. This is a local product foundation; hosted authentication, tenant isolation, licensing review, and deployment evaluation remain separate work. No Git commit or push was performed.

## Change record — 2026-11-18: first live Groq verification and database check

The project-local Groq key is now configured. Live answers were exercised through the running Node/Python app using openai/gpt-oss-120b, rather than only mocked provider responses. No key was printed, copied into tests, or written to reports.

### What changed after real-provider testing

- Added backend/scripts/verify_live_answers.py: explicitly sends a bounded question set to the running loopback app, checks answer/source contracts, PDF fingerprint delivery, report exports, saved follow-ups, and SQLite integrity. It saves full local evidence under ignored backend/data/runtime/live_answer_verification.json and archives the previous report before overwriting it.
- Added --delay to pace live requests against account quotas. The script stops on rate-limit/authentication/timeout responses instead of retrying in a loop. Failed checks now return a nonzero exit status; a generated report does not imply that all cases passed.
- Tightened backend/app/integrations/groq_client.py after live application answers rewrote dates and joined noncontiguous source fragments. The prompt now requires literal application labels, production ranges, qualifiers, and contiguous quotations. It separates model-generation dates from the row's production range and prohibits invented numeric differences/conversions.
- Added a regression test in backend/tests/test_rag.py showing that a quote cannot skip the production-range field and that expanded years absent from the cited record are rejected. The citation validator was not loosened to make the live responses pass.
- A later Groq request returned HTTP 429 during burst testing. That is recorded as a provider limit, not a successful answer. The final verification uses paced requests.

The app is running in a separate test instance because default port 3201 was occupied. Use the actual PROJECT_READY URL from the run; the original occupied listener was not stopped. Browser visual verification remains separate from HTTP/API checks.

### Database: already connected

| Data | Current storage | Why |
| --- | --- | --- |
| Conversations and saved answer/source snapshots | SQLite: backend/data/runtime/conversations.sqlite3 | Persists chat history and exports across restarts |
| Catalogue records and page chunks | JSON files under backend/data/runtime | Rebuildable caches tied to the PDF fingerprint |
| Retrieval ranking structures | Python memory | Current BM25-style lexical search; no embeddings/vector database |
| Manufacturer document | Local ignored PDF | Original source for page citations |

SQLite has two tables: conversations and messages. The database integrity check returned ok and the foreign-key check found no violations. The live follow-up messages were verified in the actual messages table, and JSON exports matched saved API history. The database is ignored by Git because it contains local records.

No separate database connection is required for this local assignment version. A hosted multi-user deployment could later justify PostgreSQL and authentication. A vector database would be a separate retrieval-design decision if we add embeddings; it is not required merely because the app uses RAG.

To reproduce live checks intentionally, from backend, while the app is running:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/verify_live_answers.py --url http://127.0.0.1:3201 --delay 15
```

Replace the URL if your PROJECT_READY address uses another port. This command consumes Groq quota and saves test conversations in the local database. See docs/VERIFICATION.md for the final observed outcomes and limitations.

### Final live results for this update

The final paced run passed all 8 scenarios: 6 real Groq answers (dimensions, width follow-up, height follow-up, published reference, dimensional comparison, Corolla applications) plus 2 no-evidence scenarios that correctly avoided the model. Cited records and actual PDF rows were reviewed for the demonstrated cases: dimensions/comparison on page 97, the published reference on page 68, and Corolla applications on page 55.

All 10 feature checks in the live runner passed, covering both comparison verdicts, read-only search, the actual fingerprinted PDF, saved follow-ups, Markdown/JSON exports, and SQLite integrity/foreign keys/persistence. Separately, 77 backend tests, 10 frontend tests, JS syntax, dependency compatibility, and the isolated main-app/MCP HTTP+stdio walkthrough passed. Earlier withheld answers and the quota-limited run remain part of the development record; the previous live report is archived locally.

The tested app instance is http://127.0.0.1:57565, started on a free port because 3201 was occupied. The port is a session-specific address; future launches can use another PROJECT_READY URL. Test conversations remain in the local SQLite database for inspection. No browser visual pass, complete catalogue coverage, universal model reliability, or exact-vehicle installation approval is claimed. No commit or push was made.

## Change record — 2026-11-18: Chroma, incremental uploads, and ordinary car-owner questions

This appended update supersedes older statements that retrieval has no embeddings, uploads are unavailable, and only SQLite/JSON are used. Previous milestones are retained for learning.

### Current workflow

Save an uploaded file → return immediately with its document ID → prepare only that file in the background → reuse cached extraction and existing vectors → search ready documents through Chroma plus exact/keyword retrieval → explain supported facts and ask for missing details.

The current tested app is http://127.0.0.1:52121. Restart an older Node instance once because the upload proxy changed; Python source edits still reload automatically.

### Changes and learning purposes

| File / area | Change | What to learn |
| --- | --- | --- |
| requirements.txt | Added pinned Chroma 1.5.9, ONNX Runtime 1.32.0, filelock, multipart upload support, and fontTools | Separate storage, local embeddings, uploads, and PDF parsing dependencies |
| app/integrations/local_embeddings.py | Local MiniLM embeddings with token-aware windows and a project-local model cache | Embedding model versus answer model; token limits |
| app/repositories/vector_store.py | Persistent cosine-search Chroma collection, batched incremental upserts, exact document-ID filtering, thresholds, and identifier lookup | A vector DB stores embeddings; it does not establish compatibility |
| app/repositories/document_library.py | SQLite registry, content-hash deduplication, saved chunks, per-document locks, background worker, retry state, interrupted-job reuse | Upload acknowledgement and indexing are separate operations |
| app/services/library_reader.py | Per-page PDF reading that retains readable pages and records failed pages | A partial extraction must keep its coverage limits visible |
| app/services/hybrid_retrieval.py | Combines semantic passages with exact identifiers/structured catalogue rows | Semantic similarity should not substitute a nearby part number |
| app/services/query_language.py | Small everyday-word retrieval expansion for symptoms, smells, and pollen | Query expansion helps search without inventing facts |
| app/services/vehicle_questions.py | Clarifies incomplete vehicle-swap questions without requiring part numbers | Collect vehicle years, component, market, and trim before a recommendation |
| app/services/answer_service.py | Searches the ready library, supports upload-only operation without the base DENSO PDF, carries year-led clarifications, and withholds factual claims when evidence is insufficient | Conversation context, uncertainty, and evidence are distinct |
| app/services/comparison_answer.py | Explicit two-part dimension questions use the existing catalogue rules and exact quotations | Prefer deterministic computations for documented numerical checks |
| app/integrations/groq_client.py | Expanded the grounding prompt to automotive documents and plain-language explanations; preserves missing-information and source limits | General documents are not proof of cross-vehicle fitment |
| app/main.py | Added document list, upload, single-document retry, and immutable source-view routes; starts the indexing worker separately | HTTP 202 queues work rather than blocking on embeddings |
| frontend/server.mjs | Streams multipart uploads to Python with a bounded size, separately from small JSON API requests | Streaming avoids buffering an entire upload in the Node proxy |
| frontend/index.html, comparison.css, src/app.js | Added upload area, per-document readiness/retry, owner-friendly question examples, nonblocking background status, and catalogue-check labels | Keep the normal user flow simple while processing continues separately |
| frontend/src/components/sources.js | Added validated uploaded-document PDF links | Source links must identify the actual indexed document/page |
| app/mcp_server.py and services/catalogue_tools.py | MCP/REST search use the same ready-document library; upload-only search can work without the base catalogue | Reuse the retrieval layer rather than building separate agent logic |
| app/core/native_paths.py and app/__init__.py | Handles Windows native Unicode-index paths and long dependency imports | Test reopening native indexes, not only inserting vectors in one process |
| scripts/install_dependencies.ps1 | Uses extended Windows paths for dependency installation | Resolve path limits without changing OS settings |
| scripts/download_reference_documents.py | Downloads accessible official references, records blocked URLs, and registers only new documents | Record actual provenance and failed downloads honestly |
| tests/test_document_library.py and frontend tests | Added upload, duplicate/restart/recovery, blank/damaged files, safe links, owner clarification, upload-only search, and deterministic-comparison checks | Verify observable workflows and failure paths |
| scripts/verify_document_library.py | Real multipart upload, local embeddings, persistent Chroma, token-bound checks, index reuse, and MCP search | Integration tests must exercise the real database and model |
| scripts/verify_main_app.py | Copies the public embedding cache and uses Windows-safe temporary paths | Keep old API/MCP smoke checks reproducible after new dependencies |
| docs/DOCUMENT_LIBRARY.md and verification/source notes | Added setup, storage roles, provenance, results, and remaining limits | Keep implemented and unverified behavior separate |

### Upload and database behavior

SQLite remains connected for chat history. A second SQLite registry tracks uploaded documents and indexing state; Chroma stores their persistent vectors under backend/data/runtime/vectors. New uploads do not rebuild the whole corpus. Identical bytes under a renamed file reuse the same hash/index. Interrupted jobs reuse saved extraction and skip vector IDs already written.

The UI accepts PDF or UTF-8 TXT up to 25 MB. It returns after file saving; extraction and embeddings run in the background. Scanned files need OCR, which is not implemented. Ready documents remain searchable while another file prepares.

The real upload check acknowledged a small new PDF in 0.014 seconds, initially queued. It then became searchable through Chroma and MCP. Duplicate bytes reused the saved index, and existing ready documents kept exactly the same indexing timestamps. Later runs were cached; this is not a performance guarantee for all file sizes.

### Questions without part numbers

The example “Can I use Corolla suspension in a Honda City?” now produces a short clarification instead of an invented yes/no. It asks for both model years, the exact suspension component, market, and trim. The response has no unsupported factual claims and makes no unnecessary model call at that stage.

Groq handles broader supported explanations, such as documented causes of excessive bouncing. Exact numerical dimension comparisons now use CatalogueService directly and show CATALOGUE CHECK. During live testing, the model occasionally rewrote quotations; this deterministic route fixes that specific comparison path without weakening source validation.

Generic uploaded PDF tables remain extracted text. They are not automatically converted into a complete vehicle-fitment rules database, and similarity is not installation approval.

### Sources and observed checks

The existing DENSO source is indexed as 1,234 token windows. One additional official KYB South Africa 2023 suspension catalogue was downloaded and indexed as 1,148 windows. Its physical PDF page 153 exceeded the reader's safety budget and was skipped with a visible coverage notice. Two other verified URLs returned HTTP 403 and were not counted as downloaded.

Verified: **96 backend tests, 11 frontend tests, 17 actual document-library checks**, JavaScript syntax, dependency compatibility, and the existing Node/Python/MCP HTTP+stdio walkthrough. Actual vectors are 384-dimensional; the maximum stored token count measured was 223. A fictional upload fixture is excluded from ordinary answers after verification.

The initial live migration run passed the other catalogue scenarios but withheld a generated numerical comparison. That path was replaced by deterministic catalogue comparison and retested successfully. Keep the full live reports and targeted fix verification distinct; do not infer universal answer reliability from a small sample. Browser visual testing remains pending.

See [upload/Chroma setup and workflow](docs/DOCUMENT_LIBRARY.md), [verification](docs/VERIFICATION.md), and [source provenance](docs/DATA_SOURCES.md). Changes are local; no commit or push was performed.

Final paced rerun after the comparison fix: **all 8 scenarios and all 10 live feature checks passed**. Five answers used Groq; the explicit numerical comparison used catalogue rules; unknown-part and unrelated questions avoided the model. The previous failed run remains archived. The latest upload verifier passed all 17 checks, including real 384-dimensional vectors and the 223-token maximum. Plain-language swap clarifications ask about front/back and the car's version without requiring part numbers.

## 2026-11-18 - Browser PDF upload verification and named-document retrieval fix

Tested the main app through the browser at http://127.0.0.1:3201/. Downloaded the official Toyota Corolla Altis X specification PDF (1 page, 1,149,160 bytes) and uploaded it using Choose a document and Upload. The file became Ready to search with 9 indexed chunks. SHA256: 6d553954b533ce9df8687cbc62494a0121af9b70fa88585e94d55c058fd4c2fe.

The first question exposed a retrieval failure: naming the new PDF still returned KYB passages. A first scope fix selected the correct file but missed the table values. DocumentLibrary.search now recognizes registered filenames, scopes Chroma to those documents, removes the filename from the semantic query, and combines keyword coverage with semantic ranking within that scope. Named-file searches inspect a broader candidate set (cosine distance <= 1.0) before taking the requested result count. Unscoped searches retain their original threshold. Hybrid retrieval respects the explicit scope, including an empty result, so unrelated catalogues cannot silently replace a named file. This improves retrieval coverage, not factual certainty; answer validation still applies.

Retested the same question through Ask Groq: 'According to toyota_corolla_specs.pdf, what are the front and rear suspension types of the Corolla Altis X? Cite the uploaded PDF.' The final answer stated MacPherson strut front suspension and torsion beam rear suspension, each citing S4, physical PDF page 1. Checked the quotes against extracted text. Clicking S4 opened the selected-source preview. The PDF route returned application/pdf. The embedded browser PDF viewer exposed no readable accessibility text, so this check does not claim visual verification of its table layout.

Repeated the upload through the browser: 'This file is already saved. Its indexing history has been kept.' Toyota retained 9 chunks and its original updated_at value. DENSO and KYB timestamps also stayed unchanged. Total ready library: 3 documents, 2,391 chunks; the verification fixture remains excluded. Backend: 98 tests passed. Frontend: 11 tests passed. Added regression checks for named-file scoping and no unrelated fallback. Screenshot: docs/browser-upload-verification.jpg. Metadata snapshot: backend/data/runtime/browser-upload-verification.json (ignored runtime data).

Official specification source: https://toyota-indus.com/wp-content/uploads/2026/03/IMC-Corolla-Altis-X-Spec-Sheet.pdf
Also downloaded a readable 20-page brochure for later upload: backend/data/sources/extra/toyota_corolla_brochure.pdf, from https://toyota-indus.com/wp-content/uploads/2026/10/Toyota-X-Brochure-New.pdf. It was not included in this browser indexing test.

### Run and repeat the browser test

1. Open the main project root in VS Code. Open its PowerShell terminal.
2. Run .\START_PROJECT.cmd (not the editor Run/Debug button). Keep that terminal open.
3. Open the PROJECT_READY address printed by the launcher; the current working address is http://127.0.0.1:3201/.
4. Choose a document, select a text-based PDF, then click Upload. Wait for Ready to search; other ready files remain usable during preparation.
5. Ask a question naming that file, then choose Ask Groq. Search sources retrieves excerpts without generating an answer.
6. Click an S citation and use Open PDF page to inspect the source. Upload identical bytes again to verify reuse. Do not press Reindex for ordinary uploads.

### LLM and guardrails clarification

Ordinary questions follow question -> retrieve document evidence -> Groq with SYSTEM_PROMPT -> structured response -> server citation checks -> UI. The prompt is in backend/app/integrations/groq_client.py. It requests short everyday explanations, preserves identifiers/units, treats documents and history as untrusted data, forbids invented compatibility, and asks for missing vehicle details. Citation validation in backend/app/services/answer_service.py checks source IDs, quote membership, numbers, and cited DENSO identifiers. It withholds invalid responses. These checks do not prove that a quote semantically supports a claim; human source review remains necessary. Explicit numerical comparisons use deterministic rules to avoid model arithmetic errors. Missing-evidence clarifications and source-only search can also bypass Groq.

Changes remain local; no commit or push was performed. This appended result supersedes the earlier browser-testing-pending status without removing that history.


## 2026-11-18 — Natural answers, interface themes, and history verification

Implemented owner-friendly LLM instructions while keeping the existing schema and citation validators. The live Toyota question returned 'The front suspension uses a MacPherson strut.' and 'The rear suspension uses a torsion beam.', each with S5 citations to the uploaded PDF. No unnecessary follow-up question was generated. This is one observed live example, not a guarantee for every question.

Normal interface labels no longer show the provider name. Enter submits the question; Search sources is in the source desk. Added a separate theme preference service, white/emerald light mode, green/black dark mode, clearer cards, stronger text contrast, keyboard focus, and reduced-motion styling. The backend still uses Groq; this change removes branding from normal controls rather than changing providers. README documents data sent to the provider.

History checks in the browser: opened an older saved investigation and saw its original claims; reopened the new investigation; refreshed and confirmed its question, two cited claims, active sidebar selection and export URL persisted. The same conversation remained selected after switching to dark mode and refreshing. Light and dark preferences both survived refresh. A temporary history fetch failure now leaves the current conversation attached. Existing persistence/follow-up regressions pass. Mobile History control was added; a dedicated mobile viewport walkthrough was not performed in this update.

Issue found and resolved: the first refresh did not initialize the app because new CSS/JS assets were missing from the Node static allowlist. Added /themes.css and /src/services/theme.js and restarted the identified project server at port 3201. Verified stylesheet response type, no visible provider branding, and no horizontal document overflow at the tested browser size.

Verification: 98 backend tests, 12 frontend tests, JavaScript syntax checks, live Groq answer, browser history selection/reload and both theme preferences passed. Expected invalid-origin and malformed-PDF warnings came from negative tests. Screenshots: docs/interface-light.jpg and docs/interface-dark.jpg. The earlier upload screenshot remains available.

README is now the current project/setup guide with prerequisites, Windows commands, sources, upload/use instructions, databases, privacy, system prompt/guardrails, structure, API/MCP, tests and troubleshooting. Earlier detailed README change entries were moved intact to docs/CHANGELOG.md. No demo files were changed. No commit or push was performed.
