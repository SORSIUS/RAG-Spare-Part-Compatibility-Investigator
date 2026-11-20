## Retrieval and output guardrails

Vehicle, year and market matches outrank repeated category keywords. Generic passages are labelled general_reference and cannot establish a requested vehicle's layout or compatibility. General explanations are filtered after generation for vehicle names, numeric specifications, chassis/part identifiers, unsupported layout and ABS-fitment statements. Unsupported vehicle claims are withheld while safe generic explanations remain. Missing fitment coverage produces a clear limitation rather than repeating already supplied questions. Chat and parts overviews use the same checks. Saved older replies are unchanged; resend a question to use these rules.

Validation: the full 131-test backend suite and 13 frontend tests passed. Five focused grounding tests subsequently passed, including the additional pad-versus-drum mistake discovered in one live Groq call. The captured reply and its local post-fix recheck are in docs/GUARDRAIL_LIVE_CHECK.json. These conservative checks cover known failure patterns; they are not a complete semantic proof of arbitrary model output.

## Chat and parts usability fixes

- The chat uses the page scroll; messages have no independent height cap and the composer is not sticky.
- Each saved conversation has Delete and Undo. Deletion hides the conversation without destroying its messages; the restore endpoint brings it back.
- Brake compatibility questions no longer trigger the two-car suspension-swap clarification.
- All parts highlights All parts and interleaves available indexed categories on the first result page. General category cards cover filters, brakes, ignition, suspension, engine and electrical parts; product cards still require structured catalogue evidence.
- Find parts requests one GPT-OSS 120B explanation with document findings, labelled general explanations and any documented candidate numbers. Exact code/application details remain expandable. Successful explanations are cached for 15 minutes per query and selected evidence. Initial page load and category switching do not call the LLM.
- Contents/index snippets are filtered before category explanations. General concept questions avoid unrelated vehicle-application rows. Invalid generated claims are discarded, while remaining claims still require matching quotations. Semantic correctness is not guaranteed by quote matching.
- All 10 newly downloaded PDFs reached ready status; the full active library has 23 ready documents. The separate verification fixture is excluded. The ATE brake catalogue has 1,038 pages and 6,811 indexed chunks.

Validation: 127 backend checks and 13 frontend tests passed; the final source-selection adjustment also passed the four focused owner-UX checks. Browser inspection confirmed the non-sticky input and unbounded message area. A live 120B overview returned five citation-checked claims plus a general explanation. Provider usage for that successful test was 3,723 tokens; earlier diagnostic attempts also consumed tokens. No model output establishes installation approval.

## General assistant, Corolla-focused evidence

The interface serves all car owners. Corolla is the current primary document focus, not a default assumption about the user's vehicle. General explanations are separate from evidence-backed vehicle-specific findings. Other makes can be discussed; verified coverage depends on each manufacturer's source and its year, engine and market.

`START_PROJECT.cmd` is a plain-text Windows batch launcher. It changes into the frontend folder, runs `node server.mjs` (which starts the local frontend and Python backend), and keeps the terminal open to show errors. Double-click it from File Explorer; close an existing project terminal before starting another copy. It was made by saving Windows command lines in a file with the `.cmd` extension.

Official expansion references are saved in `backend/data/sources/official_expansion/`. `backend/scripts/expand_official_library.py` downloads and checks PDFs, skips content duplicates, registers them, and resumes local indexing without using the chat model. See `docs/OFFICIAL_PDF_DOWNLOADS.json` for exact URLs, markets and download results. US/Canadian/Australian/European references are labelled by market and do not establish Pakistan-specific Corolla fitment.

## Owner-friendly interface (20 November 2026)

- Separate Home, Browse parts, Chat assistant and Documents views use hash navigation. Saved conversations and New conversation remain backed by the existing SQLite history.
- GPT-OSS 120B explains document findings in concise Markdown. General automotive knowledge is permitted in a separately labelled General explanation section. Exact vehicle fitment, identifiers and specifications still need cited evidence. Quote validation checks provenance, not full semantic correctness; prompt guardrails reduce but cannot eliminate model mistakes.
- All parts searches all indexed categories and also shows category-specific reference passages for filters, brakes, ignition, engine and electrical parts. General document matches are explicitly not confirmed vehicle applications. More verified product listings require manufacturer application documents and structured parsers; uploading a PDF makes its text searchable but does not automatically create product cards.
- Catalogue details remain available behind source links. Customer pages do not display API configuration. Setup remains in Documents. The existing illustrative parts image is reused; no new third-party product photos were imported.
- Vector search falls back to fingerprint-matched saved passage caches if Chroma raises an internal index error. It preserves PDF/page provenance and marks keyword fallback results; it does not repair the vector index.
- General explanations are saved with conversations and included in Markdown exports. Rendering supports headings, paragraphs, bullets, bold and inline code; raw HTML is treated as text.
- Restart START_PROJECT.cmd after updating, because the Node server's asset routes changed. The normal address is http://127.0.0.1:3201/.

Official document starting points: [Toyota manuals](https://www.toyota.com/owners/warranty-owners-manuals), [DENSO downloads](https://www.denso-am.eu/downloads), [DENSO regional spark plug PDFs](https://am.denso.com/plug-global/model-search/catalog/), [DENSO technical resources](https://www.denso.com.au/service/technical-resources). Match the vehicle year, engine and market; US owner manuals do not establish Pakistan-market part compatibility.

Validation: 123 backend unittest checks and 13 frontend tests passed. Home, category reference results, Chat navigation and saved-history visibility were checked in Chrome. Live provider generation was not called during this update to conserve API usage.

# Spare-Part Compatibility Investigator

**“Can This Part Replace That?”** helps car owners ask questions about automotive parts in everyday language and check the documents behind each answer.

Upload a catalogue or specification PDF, ask your question, and inspect the cited PDF pages. The app uses retrieval-augmented generation (RAG): it retrieves relevant evidence before asking Groq to explain it. When documents do not establish compatibility, it explains what is missing rather than inventing a yes/no answer.

## Ask by car, without a part number — 2026-11-20

Try this conversation in the main chat:

1. **Which suspension fits my Corolla?**
2. When asked for the year: **2012**
3. When asked for the engine: **1.8 front**

The assistant remembers these details and retrieves catalogue-listed candidates with source pages. It asks for missing year/engine details rather than choosing an arbitrary Corolla generation. If you do not know the engine, say **engine unknown** to browse year-based candidates with the remaining uncertainty visible. The structured owner flow uses no LLM calls.

Suspension search now filters by engine size/code and exact component as well as model, year, axle and optional chassis. The frontend vehicle finder includes an optional **Engine** field. Unknown engine codes are not silently treated as matching.

Added **60 Toyota spark-plug vehicle application rows** from the reviewed DENSO Asia 2025 tables (physical pages 99–100), linking model/version, engine, production range, OEM number, listed standard DENSO plug and source page. These are **Taiwan-market** rows. Try **Which spark plugs for Toyota Corolla 2005 1ZZ-FE Taiwan?** to retrieve K16R-U11 with its qualifications. An explicit Pakistan filter excludes these Taiwan rows; this is not universal Toyota coverage.

Run from `backend/` to reproduce the new application import:

```powershell
.\.venv\Scripts\python.exe scripts/import_vehicle_applications.py
.\.venv\Scripts\python.exe scripts/verify_vehicle_lookups.py
```

The verifier expects the app on port 3201. Importing reuses the source hash/parser version and does not rebuild chunks or embeddings. This application table is separate from the OEM cross-reference table: no universal interchangeability is inferred from a shared number.

Checks: **120 backend tests**, **13 frontend tests**, syntax checks, and live owner follow-ups/history, engine filters, source PDFs and MCP searches passed without LLM calls. Browser interaction/visual testing of the new engine field remains unverified.

## What you can do

- Find suspension candidates by make, model, year, engine, front/rear position and optional chassis code. Vehicle-linked catalogue rows retrieve their PDF evidence directly, before broad text search.
- Ask questions without knowing a part number, and get short explanations with source citations.
- Upload PDF or UTF-8 TXT documents; preparation runs in the background while existing documents remain searchable.
- Reuse previously indexed documents: identical file contents do not trigger a full rebuild. Name a document in your question to search within it.
- Compare documented DENSO dimensions and published references without relying on LLM arithmetic.
- Reopen saved conversations, continue an investigation, and export its evidence as Markdown or JSON.
- Switch between white-and-emerald light mode and green-and-black dark mode. Your choice is saved in your browser.
- Use the REST API or read-only MCP tools from another agent.
- Look up an original part number under **Have an original part number?** to see directed, application-specific OEM-to-KYB references and the original catalogue page.

The main app is separate from `DEMO proto/`, which remains the teacher prototype.

### 2026-11-20 — Broader materials and original-part replacement links

**Later coverage update:** downloaded three more official DENSO 2025 sections: Japan (53 pages), Europe/USA (61), and Others/cross-references (65). All are indexed: 3,217 new embedding windows; existing documents were reused.

A reviewed, column-bounded OEM cross-reference adapter adds **1,341 OEM-to-standard-DENSO spark-plug reference rows**, including **137 Toyota rows**, alongside the 345 existing vehicle-qualified KYB application references. These are different evidence types: an OEM number reference still requires checking the vehicle application. Annotated, clipped, wrapped or ambiguous cells and upgrade columns are skipped.

Empty lookups now explain the search boundary and next steps, with a button to continue in chat. Incomplete generated answers retain validated cited findings and separate unresolved fitment details. No unsupported yes/no is substituted for missing evidence.

Reproduce this coverage from `backend/`:

```powershell
.\.venv\Scripts\python.exe scripts/add_reference_pdfs.py
.\.venv\Scripts\python.exe scripts/import_denso_references.py
.\.venv\Scripts\python.exe scripts/verify_replacements.py
```

The final verification command expects the app running on port 3201. Downloads and embedding indexes are reused; the reference import also skips a matching hash/parser version. Try **Toyota / 90919-01095**: the published standard-plug reference is **DENSO W16ETR-S**, physical PDF page 29 (printed 414). Ask the chat for the exact vehicle application before choosing a plug.

Latest checks: **116 backend tests**, **13 frontend tests**, JavaScript syntax, live REST/PDF serving and actual MCP retrieval passed. No paid LLM calls or fresh browser visual testing were used.

The vehicle catalogue currently contains 3,814 application associations across 14 makes. A conservative replacement index adds **345 application-specific references covering 144 distinct make/original-number combinations**, including 168 Toyota application references. These counts describe this imported catalogue, not all vehicles or all parts.

Example: enter **Toyota** and **48609-12500** in the original-number lookup. The catalogue links it to **KYB SM7210** for listed applications, including Corolla entries on physical PDF page 96. Read the chassis, engine and production conditions on each result. This does not establish a Corolla-to-City suspension swap.

Only matching cells containing one OEM number and one aftermarket number become directed replacement links. Grouped cells, reverse links and inferred chains are excluded. SQLite caches these links separately from Chroma chunks; reimporting a changed source invalidates its links. Arbitrary uploads remain searchable documents until a reviewed table adapter is added.

Your four added PDFs are now searchable: body parts/functions, engine parts/functions, Automobile Engineering, and the MASTERPARTS product-group catalogue. They explain components and systems; they do not automatically prove fitment.

See [materials to download and coverage rules](docs/MATERIALS_AND_REPLACEMENTS.md). To register the same learning PDFs on another computer, put them in `backend/data/sources/automotive/`, then run from `backend/`:

```powershell
.\.venv\Scripts\python.exe scripts/register_learning_materials.py
```

Existing document hashes and indexed chunks are reused. Downloaded PDFs and databases remain local and are not bundled into GitHub.

Validation for this addition: **112 backend tests**, **13 frontend tests** and JavaScript syntax checks passed. Live REST, source-PDF and MCP replacement-search checks passed without LLM calls. The new form is served correctly; a fresh browser visual/click walkthrough remains unverified.

## How the workflow works

**Upload → save and fingerprint → extract only new documents → chunk → embed → store in Chroma → retrieve evidence → explain with the LLM → validate citations → show the answer and sources.**

For supported fitment catalogues, a second path links **vehicle → production range and application → component/position → part → original PDF row** in indexed SQLite tables. Matching vehicle questions use those links before broad lexical/Chroma search. Part-finder results need no LLM call. The index is reused rather than rebuilding the PDF for each question.

Source-only searches, incomplete-vehicle clarifications, and deterministic comparisons can skip the LLM. Each new question performs retrieval; conversation history helps interpret follow-ups but is not treated as catalogue evidence.

## Run on your computer (Windows)

### 1. Requirements and project folder

Install Python and Node.js 18 or newer. This workspace was tested with Python 3.14; dependency availability on other versions can differ. Use a short project path if possible. Open this project root in VS Code, then open its PowerShell terminal. These commands start the main app, not the demo.

If downloading a fresh copy:

```powershell
git clone https://github.com/SORSIUS/RAG-Spare-Part-Compatibility-Investigator.git
cd RAG-Spare-Part-Compatibility-Investigator
```

Cloning downloads the files currently pushed to GitHub. Changes still only on your original computer must be committed and pushed before another computer can clone them.

### 2. Set up the Python backend

From the project root:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Skip creating `.venv` if it already exists. Activation is optional because the commands call its Python directly. If Windows reports a long-path installation error, run the provided helper from `backend/`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_dependencies.ps1
```

That process-scoped option runs the local helper; it does not change your machine's execution-policy setting.

### 3. Add your own Groq key

Only if `backend/.env` does not already exist:

```powershell
Copy-Item .env.example .env
```

Edit that file locally:

```dotenv
GROQ_API_KEY=your_actual_key_here
GROQ_MODEL=openai/gpt-oss-120b
GROQ_TIMEOUT_SECONDS=45
RAG_TOP_K=8
```

Get a key from the [Groq console](https://console.groq.com/keys). Keep `.env` out of Git. Do not overwrite an existing configured file. An existing system environment variable takes precedence over `.env`. Source search works without an API key; generated answers require working credentials and provider quota.

### 4. Add reference documents

For the structured DENSO comparison workflow, download the [official DENSO cabin filter catalogue](https://assets.denso-am.eu/production/attachments/Cabin-Air-Filters-Product-Catalogue-2026.pdf) and save it as:

```text
backend/data/sources/automotive/denso_cabin_air_filters_2026.pdf
```

PDFs and runtime databases are local assets and are not included in Git. Other reference PDFs can be uploaded from the browser. The first embedding search/indexing run may need Internet access to download the local embedding model. Later runs reuse its cache. See [document storage and indexing](docs/DOCUMENT_LIBRARY.md) and [source provenance](docs/DATA_SOURCES.md).

### 5. Start the app

Before the first start, import the official KYB MEA suspension accessories catalogue from `backend/`:

```powershell
.\.venv\Scripts\python.exe scripts/import_kyb_fitments.py
```

The script downloads the reviewed PDF edition, builds the vehicle/part index and records its source hash. Repeat runs reuse the index. This workspace currently has **3,814 application links across 14 makes and 178 model groups**, including 395 Corolla links. Counts are catalogue associations, not unique parts or complete market coverage. On the first app start, generic semantic chunks prepare separately in the background. Other uploaded PDFs remain searchable but need their own reviewed table adapter to become structured fitment records. See [fitment data and workflow](docs/FITMENT_INDEX.md).

From `backend/`, return to the project root:

```powershell
cd ..
.\START_PROJECT.cmd
```

Alternatively, run `node server.mjs` from `frontend/`. The frontend has no external npm dependencies. Wait for `PROJECT_READY`, then open the printed URL, normally **http://127.0.0.1:3201/**. Keep the terminal open; **Ctrl+C** stops the app. Use the terminal or double-click the launcher rather than VS Code's Run/Debug button.

Python starts automatically on an internal free port. Changes under `backend/app/` restart Python automatically. Refresh the page for frontend changes; restart the launcher after server or dependency changes.

## Try an investigation

For a fast parts lookup, use the new **Find parts** form: Toyota → Corolla → 2012 → Front, optionally chassis **ZRE152**. This tested example returns nine catalogue associations from physical PDF page 96. Different engine/application rows remain separate. Open **Application details & reference**, **View source page**, or **Ask about this part**. A catalogue candidate still needs the exact vehicle qualifications checked.

The document upload area is now under **My catalogues & document uploads**. Saved conversations are under **Saved investigations** in the header. The question form and source desk remain below the parts results.

1. In **Your reference documents**, choose a PDF or TXT file and press **Upload**.
2. Wait until that file says **Ready to search**. Saving the file and preparing its text are separate stages.
3. Enter a question and press **Enter** (button or keyboard). Use Shift+Enter for another line.
4. Click an **S1/S2…** citation to inspect its source passage, then **Open PDF page** to check the original.
5. For retrieval without generation, use **Search sources** in the source desk.
6. Use **New conversation** for a separate investigation. Reopen an older conversation from the sidebar; on small screens, use **History**. Export links appear once a conversation has messages.
7. Use the **Dark / Light** button in the header to change theme. Theme and selected conversation are saved per browser; messages themselves persist in SQLite.

Example questions:

- “What are the dimensions of DCF002K?”
- “Which cabin filters are listed for Toyota Corolla?”
- “Compare the dimensions of DCF009P and DCF031P.”
- “Can I use Corolla suspension in a Honda City?” (expect clarification if vehicle details/evidence are missing).
- After uploading `toyota_corolla_specs.pdf`: “According to toyota_corolla_specs.pdf, what are the front and rear suspension types of the Corolla Altis X?”

A small official [Toyota specification PDF](https://toyota-indus.com/wp-content/uploads/2026/03/IMC-Corolla-Altis-X-Spec-Sheet.pdf) was used for the upload test. Save it with the example filename if you want to repeat that question exactly.

## Sources, system prompt, and guardrails

The system prompt in `backend/app/integrations/groq_client.py` requests clear everyday language, evidence-only claims, unchanged identifiers and units, and focused questions when information is missing. Uploaded documents, questions, and history are treated as untrusted data rather than system instructions.

The backend validates structured responses, source IDs, quotation membership, and cited numbers/DCF identifiers. It withholds answers that fail those checks. Citations stay clickable when you reopen a conversation. Polishing the language must preserve the evidence and its qualifications.

**A valid citation does not prove that every interpretation is correct.** Review the original PDF, especially tables. Shared dimensions or similar car names do not prove safe interchangeability. A catalogue cross-reference is not installation approval. Exact vehicle years, component, market, engine/trim and other qualifiers may still be needed.

## Data and privacy

| Storage | Purpose | Location under `backend/data/runtime/` |
| --- | --- | --- |
| Chroma | Persistent document embeddings | `vectors/` |
| SQLite | Saved questions, answers, and sources | `conversations.sqlite3` |
| SQLite document registry | File hashes and indexing history | `library/documents.sqlite3` |
| SQLite fitment index | Vehicle/application/position/part/source links | `fitments.sqlite3` |
| Local files | Uploaded PDFs, extracted chunks, embedding model | `library/`, `models/` |

No hosted database account is required. Uploads are saved locally. Generated answers send the question, selected excerpts and limited recent dialogue to Groq. The API key stays on the backend. This is a local application; it has no multi-user authentication or production hosting configuration.

## Project structure

```text
backend/
  app/
    core/             Settings and Windows path handling
    integrations/     Groq client, system prompt, local embeddings
    models/           Typed request, answer and evidence schemas
    repositories/     Catalogue, Chroma, document registry and chats
    services/         Extraction, retrieval, comparison and validation
    main.py           FastAPI endpoints and lifecycle
  data/               Source documents and ignored runtime data
  tests/              Backend regression tests
  scripts/            Install, integration and verification helpers
  mcp_entry.py        MCP stdio entry point
frontend/
  src/components/     Source cards and comparison UI
  src/services/       API client and theme preferences
  src/app.js          Chat, uploads and saved-conversation UI
  styles.css          Base layout
  themes.css          Light/dark colours and visual refinements
  comparison.css      Comparison and upload layouts
  server.mjs          Node static server and Python proxy
  tests/              Frontend tests
DEMO proto/           Isolated teacher prototype
docs/                 Workflow, API/MCP, verification and change history
```

## API and MCP

The indexed lookup is available at `GET /api/fitments` with make, model, year, axle, chassis, part, limit and offset filters. `GET /api/fitments/options` reports imported coverage. Existing MCP `search_catalogue` uses linked retrieval for matching vehicle/suspension questions; it still performs no model call.

The Node server proxies REST endpoints under `/api/` and MCP Streamable HTTP at `/mcp`. Read-only MCP tools expose catalogue information, search, part lookup and comparisons. See [API/MCP setup](docs/MCP_AND_API.md) for client configuration and [project concepts](PROJECT_README.md) for the design.

## Testing and troubleshooting

Run backend tests from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Run frontend checks from `frontend/`:

```powershell
npm.cmd test
npm.cmd run check
```

- **Port in use:** stop your previous project terminal with Ctrl+C before starting again.
- **Old UI or missing theme:** restart the launcher, then refresh the page.
- **Answer setup needed:** check `backend/.env`, then use Refresh status. That checks configuration; a successful answer verifies authentication.
- **PDF saved but not ready:** preparation runs in the background. Larger documents take longer. Failed files offer Retry.
- **Scanned PDF:** OCR is not implemented; use a text-based PDF. Upload limit is 25 MB; indexing limit is 1,500 pages.
- **Partial coverage:** unreadable pages are skipped with a visible notice. KYB's tested catalogue has one skipped page.
- **History seems missing:** history belongs to this local project and its runtime SQLite file. A different machine, project copy or cleared database does not contain those conversations. Browser storage remembers only the selected conversation and theme.

## Recent changes

### 2026-11-20 — Gradients, automotive imagery and conversational recovery

- Added coordinated light/dark gradients and an original automotive hero image. It is labelled illustrative and does not identify or verify any SKU. The saved project asset is `frontend/assets/automotive-hero.png`.
- Changed the question area into a conversation: user/assistant labels, a bounded message history, a bottom composer, pending-question display and friendly retry replies for transport failures. Follow-up prompts now invite you to type your own details rather than copying the assistant's question as your answer.
- Provider authentication, configuration, timeout and rate-limit failures now return an honest, saved chat recovery response with the retrieved sources, rather than a provider error box. Checked catalogue wording is available for structured fitment links when generation is unavailable. No unverified claims are invented. Markdown exports include recovery messages.
- Added official DENSO 2025 spark-plug Asia applications (122 pages) and product information (41 pages). Run `backend/scripts/add_reference_pdfs.py` with the backend virtual-environment Python to repeat the downloads/registration. Existing file hashes and document history are reused. These are document-RAG references, not a new structured spark-plug fitment adapter.
- Final automated checks: **107 backend tests, 13 frontend tests, JavaScript syntax checks, Node/Python HTTP integration and MCP over HTTP + stdio passed**. Integration checks also passed source-page serving, history/follow-up, exports, comparisons, missing-key chat recovery, static assets and backend auto-reload. No additional paid LLM calls were made for this final verification.
- Fresh browser visual verification of this gradient/chat iteration was blocked: Windows computer-use could not determine the current browser URL reliably enough to enforce its policy. Earlier storefront screenshots describe the previous iteration, not proof of the new visual layout. Open the running app and refresh to review it; this visual check remains outstanding.

Official PDF URLs: [Asia applications](https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_3_asia_2025.pdf) and [product information](https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_1_products_information_2025.pdf). Download hashes, sizes and pages are saved locally in `backend/data/runtime/additional_reference_pdfs.json`. PDFs and runtime data remain ignored by Git.

The original image was created with the built-in image-generation tool. Brief: unbranded suspension parts, cabin filter and spark plug on a graphite workbench, with emerald/lime lighting, no text/logos, illustrative rather than an exact SKU. No Figma connection was available; implementation was done directly in the frontend. No commit or push was performed in this update.

### 2026-11-20 — Vehicle-first parts finder and linked catalogue dataset

- Replaced the chat-dashboard-first layout with automotive navigation, a vehicle selector, suspension part cards, application details and original-PDF links. Light and dark themes, uploads and saved investigations remain available.
- Downloaded and reviewed KYB MEA's 174-page accessories catalogue. Imported supported application tables with a column-aware adapter, source hash and cached revision history. Raw catalogues and generated databases remain ignored by Git.
- Added indexed vehicle-to-part retrieval before broad search. Repeating a query performs neither PDF chunking nor corpus-wide semantic search when links match.
- Added a checked catalogue-wording fallback when the LLM changes production-date codes or fails quotation validation. Invalid generated text is not displayed; the fallback also passes citation validation. KYB/chassis code validation now rejects fabricated identifiers in linked answers.
- Tested desktop/mobile layouts, saved history access, exact and empty-result lookups, fingerprinted source serving and cached import reuse. Local indexed lookup median: 6.17 ms over 20 calls on this machine; this excludes network and LLM time.

Design references: the user's Autostore, SehgalMotors and Partfinder examples, plus PartSouq/AUTODOC vehicle-selection patterns. These informed navigation and catalogue layout; their retail listings were not used as authoritative fitment data. See [source and design research](docs/FITMENT_INDEX.md).

Final checks for this update: **107 backend tests and 12 frontend tests passed**, plus JavaScript syntax and desktop/mobile browser checks. The live structured-part explanation used the checked catalogue fallback after the model changed a date code; that behavior is documented rather than counted as a successful generated answer.

### 2026-11-18 — Clearer answers and refreshed interface

- Improved the LLM instructions for natural owner-friendly explanations and fewer unnecessary follow-up questions, preserving evidence restrictions and citation validation.
- Replaced the provider-branded chat button with **Enter**; moved source-only search to the source desk and removed provider branding from normal interface labels.
- Added white/emerald light mode and green/black dark mode with saved preference, clearer cards, more readable text and visible keyboard focus.
- Added a History control on small screens, active conversation indicators and an empty-history message. Loading errors preserve the current conversation selection.
- Reorganized this README as the current project/setup guide. Previous detailed change entries are preserved in [the changelog](docs/CHANGELOG.md), rather than removed.

Earlier milestones: structured DENSO retrieval, Groq with checked citations, comparison and exports, MCP, persistent Chroma, incremental uploads, and named-document retrieval. See [detailed history](docs/CHANGELOG.md), [verification](docs/VERIFICATION.md), and [current progress](docs/PROGRESS.md) for evidence, limitations and unfinished work. Local modifications are not automatically committed or pushed to GitHub.

Validation for the interface update: **98 backend tests and 12 frontend tests passed**, plus JavaScript syntax checks. Browser checks confirmed a live cited answer, reopening saved chats, restoring the selected conversation on refresh, and persistence of both themes. See [verification details](docs/VERIFICATION.md). A dedicated mobile viewport walkthrough remains unverified.



