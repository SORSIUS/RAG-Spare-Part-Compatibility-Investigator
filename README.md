# Spare-Part Compatibility Investigator

**“Can This Part Replace That?”** helps car owners ask questions about automotive parts in everyday language and check the documents behind each answer.

Upload a catalogue or specification PDF, ask your question, and inspect the cited PDF pages. The app uses retrieval-augmented generation (RAG): it retrieves relevant evidence before asking Groq to explain it. When documents do not establish compatibility, it explains what is missing rather than inventing a yes/no answer.

## What you can do

- Ask questions without knowing a part number, and get short explanations with source citations.
- Upload PDF or UTF-8 TXT documents; preparation runs in the background while existing documents remain searchable.
- Reuse previously indexed documents: identical file contents do not trigger a full rebuild. Name a document in your question to search within it.
- Compare documented DENSO dimensions and published references without relying on LLM arithmetic.
- Reopen saved conversations, continue an investigation, and export its evidence as Markdown or JSON.
- Switch between white-and-emerald light mode and green-and-black dark mode. Your choice is saved in your browser.
- Use the REST API or read-only MCP tools from another agent.

The main app is separate from `DEMO proto/`, which remains the teacher prototype.

## How the workflow works

**Upload → save and fingerprint → extract only new documents → chunk → embed → store in Chroma → retrieve evidence → explain with the LLM → validate citations → show the answer and sources.**

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

From `backend/`, return to the project root:

```powershell
cd ..
.\START_PROJECT.cmd
```

Alternatively, run `node server.mjs` from `frontend/`. The frontend has no external npm dependencies. Wait for `PROJECT_READY`, then open the printed URL, normally **http://127.0.0.1:3201/**. Keep the terminal open; **Ctrl+C** stops the app. Use the terminal or double-click the launcher rather than VS Code's Run/Debug button.

Python starts automatically on an internal free port. Changes under `backend/app/` restart Python automatically. Refresh the page for frontend changes; restart the launcher after server or dependency changes.

## Try an investigation

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

### 2026-11-18 — Clearer answers and refreshed interface

- Improved the LLM instructions for natural owner-friendly explanations and fewer unnecessary follow-up questions, preserving evidence restrictions and citation validation.
- Replaced the provider-branded chat button with **Enter**; moved source-only search to the source desk and removed provider branding from normal interface labels.
- Added white/emerald light mode and green/black dark mode with saved preference, clearer cards, more readable text and visible keyboard focus.
- Added a History control on small screens, active conversation indicators and an empty-history message. Loading errors preserve the current conversation selection.
- Reorganized this README as the current project/setup guide. Previous detailed change entries are preserved in [the changelog](docs/CHANGELOG.md), rather than removed.

Earlier milestones: structured DENSO retrieval, Groq with checked citations, comparison and exports, MCP, persistent Chroma, incremental uploads, and named-document retrieval. See [detailed history](docs/CHANGELOG.md), [verification](docs/VERIFICATION.md), and [current progress](docs/PROGRESS.md) for evidence, limitations and unfinished work. Local modifications are not automatically committed or pushed to GitHub.

Validation for the interface update: **98 backend tests and 12 frontend tests passed**, plus JavaScript syntax checks. Browser checks confirmed a live cited answer, reopening saved chats, restoring the selected conversation on refresh, and persistence of both themes. See [verification details](docs/VERIFICATION.md). A dedicated mobile viewport walkthrough remains unverified.
