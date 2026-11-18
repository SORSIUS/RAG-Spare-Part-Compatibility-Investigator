# Main application verification

Date: 2026-11-18. This document covers the main app, separately from DEMO proto.

## Results

| Check | Result and scope |
| --- | --- |
| Backend suite | 67 passed using the project Python environment |
| Frontend unit checks | 7 passed with Node's built-in test runner |
| JavaScript syntax | Server and all 3 browser modules passed |
| Real DENSO retrieval | Dimension, application, cross-reference, balanced two-part retrieval, and unrelated-query checks passed |
| Node/Python HTTP walkthrough | Passed in an isolated temporary app copy with the actual source PDF |
| Groq protocol and errors | Passed with mocked HTTP transport; no external provider request |
| Live Groq answer | Not run: no project key configured |
| Browser visual/accessibility walkthrough | Not run: browser-control tool unavailable |

Backend suite breakdown: 41 existing ingestion/sample/catalogue checks, 21 new RAG/provider/API checks, and 5 new real-catalogue retrieval checks. Ten of the total 67 depend on the downloaded PDF and skip when it is missing.

Synthetic corrupt-PDF tests intentionally emit reader warnings. The installed TestClient currently emits a Starlette httpx deprecation warning; assertions pass. These warnings do not constitute a live-provider or browser check.

## Reproduce

From backend:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -X utf8 scripts/verify_main_app.py
```

From frontend:

```powershell
npm.cmd run check
npm.cmd test
```

The HTTP script creates a temporary copy under backend/data/runtime, excludes credentials and chat history, uses random ports, and starts its own Node/Python process tree. It checks static assets, status, real evidence, saved history, a pronoun follow-up, PDF delivery, stale-source rejection, request validation, hidden-file blocking, and missing-key behavior. It also modifies a copied Python module, waits for automatic restart, and verifies that history survives. It stops its own servers and removes its test copy. A summary is written to ignored data/runtime/main_app_verification.json.

Provider tests assert the official endpoint, authorization header, strict schema, prompt/data separation, missing credentials, sanitized authentication/rate errors, malformed responses, and timeout handling. Citation tests include nonexistent IDs, invented quotations, absent numbers/part identifiers, and withheld claims.

## Remaining live checks

After configuring backend/.env, run the app and ask:
1. “What are the dimensions of DCF002K?” Check that the answer states 282 × 206 × 30 mm and its citation opens PDF page 97.
2. “Which cabin filters are listed for Toyota Corolla?” Check that the response preserves source model/date distinctions and does not promise exact fitment.
3. “Does the catalogue cross-reference C30001 to DCF357P?” Inspect the external brand and published mapping.
4. “Compare the dimensions of DCF009P and DCF031P.” Check both retrieved records and the response's qualification.
5. Ask an unrelated question. Confirm the app does not invent catalogue evidence.

Record the actual model, question, answer, retrieved sources, and citation review outcome before claiming measured answer quality. A configured-key indicator alone is not authentication verification. The Groq account must support the configured model and schema mode.

## Remaining browser checks

- Open the main app at 127.0.0.1:3201; verify the setup message and Search sources without a key.
- Set the key locally, refresh status, and ask a question.
- Click a citation; compare the record, extracted excerpt, and actual PDF table.
- Open a saved conversation, send a pronoun follow-up, and start a new conversation.
- Review desktop and mobile widths, keyboard focus, scrolling, readable errors, and loading states.
- If the embedded PDF viewer is unavailable, use the source's new-tab PDF link.
- Stop with Ctrl+C and check that the owned backend exits.

## Limits of these results

No browser screenshot, real Groq answer, general extraction accuracy, semantic entailment guarantee, or installation suitability is established. Extraction counts and passing tests describe observed behavior on the supplied cases. Tests do not prove that every catalogue row was recovered or interpreted correctly.

## Appended verification — 2026-11-18: comparison, exports, and MCP

The new total is 76 backend tests (the previous 67 plus 9 agent/API/report/follow-up checks) and 10 frontend tests (the previous 7 plus 3 comparison/report/contract checks). The 10 real-source-dependent checks are still included. The comparison module is included in JS syntax validation. pip check verifies dependency compatibility after adding mcp==2.3.0.

The isolated main-app walkthrough now also verifies:

- DCF009P → DCF031P returns a documented dimension conflict through REST.
- C30001 → DCF357P under 1A FIRST AUTOMOTIVE returns a documented reference, with fitment still unknown.
- Markdown and JSON conversation report downloads preserve saved history.
- The OpenAPI schema includes typed catalogue operations.
- A real official MCP client discovers four tools, invokes metadata/search/comparison, and reads a resource over HTTP through Node.
- A second real MCP client launches a stdio subprocess and repeats those operations against the same catalogue.
- Python automatic reload still preserves history and catalogue availability.

Focused tests assert typed structured MCP outputs, read-only annotations, invalid tool inputs, foreign browser-origin rejection, repeated pronoun context, non-LLM catalogue access, and report evidence preservation. The existing Groq mocks and old workflow tests remain part of the regression suite. No third-party agent application's configuration has been changed.

Initial MCP tests exposed two integration details that were corrected: the SDK needs serializable typed dictionary output annotations, and loopback transport tests must use the same host-with-port shape as real requests. The final real HTTP/stdio checks verify behavior beyond those unit fixtures.

Windows Computer Use was attempted with the installed skill; the runtime ended browser automation because it could not determine the current URL with enough confidence to enforce policy. No further browser input was issued, and no visual pass is recorded. Live Groq still requires a configured local key. The automated report's browser field records only that visual QA is outside that script; it is not evidence of a current visual result.

Additional manual checks when reviewing the UI: expand the comparison panel, inspect both PDF sources, try an unknown part, enter an ambiguous external brand, download comparison reports, and open saved-chat exports. Review these with the previously listed live-answer and responsive-layout checks before declaring the UI fully verified.

## Appended live verification — 2026-11-18

The user configured the key in backend/.env and authorized real provider testing. The app detected it without exposing it. The live model was openai/gpt-oss-120b. The tested instance ran at http://127.0.0.1:57565 because 3201 was already occupied.

| Final scenario | Observed outcome | Cited physical PDF page |
| --- | --- | --- |
| DCF002K dimensions | Answered: length 282 mm, width 206 mm, height 30 mm | 97 |
| Follow-up width | Answered: 206 mm; original part retained | 97 |
| Follow-up height | Answered: 30 mm; original part retained again | 97 |
| C30001 → DCF357P | Answered: published reference under 1A FIRST AUTOMOTIVE | 68 |
| DCF009P vs DCF031P | Answered: 275/219/54 mm vs 340/198/17 mm; qualitative differences | 97 |
| Toyota Corolla applications | Answered with separate model labels, printed production ranges, AC/JPN/UK qualifiers, and cited part numbers | 55 |
| DCF999P | Insufficient evidence; no model call | None |
| Unrelated quantum-banana question | Insufficient evidence; no model call | None |

Final result: 8/8 scenario checks passed, with 6 actual model answers. This is a small functional check set, not a general answer-accuracy benchmark. The quoted data was reviewed against the source records and actual PDF rows. Automated checks covered source IDs/quote membership, expected facts, source-page range/text, fingerprinted links, and PDF byte identity. They do not establish semantic entailment for arbitrary future answers.

All 10 live feature checks passed: dimension conflict, documented direct reference with fitment unknown, read-only search, original PDF route, saved follow-ups, JSON export equality, Markdown export, SQLite integrity, foreign-key validity, and the actual saved message count. The isolated application walkthrough also passed actual MCP HTTP and stdio operations, schema discovery, stale-PDF rejection, validation, missing-key behavior, and reload persistence. Final regression totals: 77 backend and 10 frontend tests, with JS syntax and pip check also passing.

### What live testing found and corrected

The first Corolla response was withheld because the model joined noncontiguous quote fragments and expanded/interpreted catalogue dates. Direct review also found an incorrect month interpretation in a generated application claim. The prompt now explicitly preserves model labels, production ranges, qualifiers, and contiguous quotations. A later comparison response was also withheld; numeric differences not printed in source records are now explicitly prohibited by the prompt. The validator itself remained strict. Added regression coverage demonstrates rejected omitted-field quotations and unsupported expanded years.

A burst of repeated provider calls reached HTTP 429. The verifier recorded the failure and did not retry automatically. A subsequent paced run used 15-second intervals and passed the full set. Provider quotas still apply to future use, and generation can still fail citation checks; the app withholds failed generated claims rather than presenting them as verified.

### Artifacts and reproduction

backend/scripts/verify_live_answers.py saves the latest full report at backend/data/runtime/live_answer_verification.json. Previous reports are archived with timestamps before replacement. The diagnostic answer review remains under ignored runtime data. These files and the live test conversations contain local question/source records and are excluded from Git; they do not contain the API key.

From backend, with the app already running:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/verify_live_answers.py --url http://127.0.0.1:57565 --delay 15
```

Use the current PROJECT_READY address if it changes. This script deliberately calls the live provider, consumes quota, and saves test chats; the separate verify_main_app.py stays isolated and disables Groq. Live verification exits nonzero when checks fail or the quota prevents completion.

### Connected database

SQLite is already connected through ConversationRepository at backend/data/runtime/conversations.sqlite3, with conversations and messages tables. PRAGMA integrity_check returned ok; PRAGMA foreign_key_check returned no rows. Saved API history, direct message counts, and exported JSON agreed for the tested follow-up conversation. No external database is needed to run the current local app. Catalogue indexes are JSON and retrieval is in-memory lexical ranking; no vector database is currently connected.

Browser visual/accessibility testing remains pending after the earlier Computer Use stop. This live run verified HTTP/API behavior and source data, not mouse/keyboard interaction, responsive layout, or PDF iframe rendering in a browser.

## Appended Chroma/upload verification — 2026-11-18

Final automated totals for this implementation are 96 backend tests and 11 frontend tests. JS syntax and pip check pass. The new module checks cover content-hash deduplication, changed filenames, unchanged prior extraction, interrupted-job reuse, registry persistence, blank/damaged PDFs, safe filenames/links, queue acknowledgement, retry, revision protection, exact-identifier behavior, new identifiers in uploaded documents, owner clarification, upload-only operation, and deterministic numerical comparison.

verify_document_library.py passed 17 integration checks against the running app at http://127.0.0.1:52121:

- Real multipart PDF upload acknowledged with HTTP 202.
- Small local fixture acknowledged in under 2 seconds: first observed 0.014 seconds; later cached/repeated runs 0.004–0.005 seconds.
- Background indexing reaches ready.
- Same bytes with another filename reuse history.
- Existing ready-document timestamps remain unchanged.
- Source route returns exactly the uploaded bytes.
- Real semantic retrieval finds the new document and supplies source pages.
- Unsupported file types are rejected.
- An unrelated query returns no sources.
- Existing exact DCF002K evidence remains first and preserves dimensions.
- Reopened registry retains readiness.
- Another Chroma client reopens and retrieves persisted vectors.
- Stored token windows fit the 256-token encoder limit; observed maximum 223.
- Actual embedding vectors have 384 dimensions.
- Actual MCP search returns uploaded-document evidence.
- Fictional verification document is excluded from ordinary answers after the test.

These are small-fixture checks, not an arbitrary-upload speed benchmark. The checker stores a local report under runtime/document_library_verification.json.

The existing isolated Node/Python HTTP walkthrough passed after the upload migration, including static assets, chat persistence, PDF version checking, comparison/export APIs, OpenAPI, real MCP HTTP+stdio, and Python reload. Model artifacts are copied from the existing local public cache for that isolated test; user keys and histories are not copied.

### Real source and persistence findings

Downloaded KYB South Africa's 2023 suspension catalogue: 160 pages, 16,983,101 bytes, SHA-256 4b9d7d42c3be79739a348838c3273bbc67c137124c590feacbbd56ec8ef27c50. Physical PDF page 153 exceeded the reader's safety budget. The budget was not disabled; the other readable pages produced 1,148 token windows with a coverage notice. DENSO contributes 1,234 windows. Two additional official URLs returned 403 and were not indexed.

The first native Chroma build in this Unicode Windows project path could insert vectors but failed to reopen its HNSW files. native_paths.py now supplies an ASCII junction back into the same project, and reopen/query tests pass. This is why insertion-only tests were insufficient. Dependency installation also required extended Windows paths; install_dependencies.ps1 reproduces that without modifying system settings.

### Live question findings

The user's Corolla-to-City suspension question was tested. Retrieved regional application fragments did not establish that swap. The app now returns a short not-enough-information summary with no asserted fitment claims, asks for both years/component/market/trim, and does not need a model call for that clarification step.

A plain-language bouncing question retrieved KYB symptom text on PDF page 147 and produced a live Groq answer with source quotations and missing vehicle/inspection details. This demonstrates document-grounded symptom explanation, not diagnosis of the user's actual car.

One full live migration run withheld a numerical comparison because its model quotations failed validation; the other catalogue cases and all 10 storage/export/API checks passed. Explicit two-part dimension comparisons were then routed through CatalogueService and retested successfully with exact quotations and model=null. The UI labels this CATALOGUE CHECK. The historical failed report and the targeted correction report are retained separately; a final paced rerun is recorded when complete.

Some semantic answers were withheld during development; citation guards were not relaxed to force success. Source quotation membership still does not prove that every interpretation logically follows from its source. Generated answers, coverage, and fitment conditions require review. Visual browser/accessibility testing remains pending.

### Final paced rerun after the numerical-comparison fix

The full eight-scenario runner completed with all_passed=true, and all ten live API/storage/export checks passed. Five responses used Groq (dimensions, two pronoun follow-ups, direct reference, Corolla applications); comparison used catalogue_rules with exact source quotations and no model call. Unknown-part and unrelated questions returned insufficient evidence without calling Groq. The numerical comparison completed in 0.06 seconds in this run. Earlier failed reports remain archived rather than being relabeled as successful.

The final document-library run passed all 17 checks, including duplicate reuse, unchanged existing indexes, Chroma reopen/query, real 384-dimensional embeddings, maximum stored token length 223, actual MCP retrieval, and excluding the fictional test document afterward. The current ready manufacturer corpus remains 2,382 windows across DENSO and KYB.

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
