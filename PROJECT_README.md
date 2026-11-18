# Project: Spare-Part Compatibility Investigator

Short name: **“Can This Part Replace That?”**

Category: RAG PROJECTS ALL

Updated: 2026-11-18

## Purpose and current scope

Help a parts researcher find documented specifications, published cross-references, and vehicle application mentions. The current dataset is DENSO's 2026 cabin-air-filter catalogue. The app explains retrieved evidence and keeps missing details visible; it does not certify a substitute for installation.

Implemented: source-specific PDF extraction, page-aware retrieval, deterministic automotive CLI checks, a local chat interface, Groq structured-answer integration, source validation, PDF page links, and SQLite conversation history. Offline and full-stack HTTP checks pass. A live Groq response and browser visual walkthrough remain unverified.

## Main question workflow

1. The Node launcher starts Python on a free loopback port and serves the browser at port 3201.
2. The catalogue repository verifies the PDF hash and loads or rebuilds extracted records and page chunks.
3. A question arrives through the browser API client and Pydantic validates its length, mode, and conversation ID.
4. AnswerService reads bounded recent dialogue. Pronoun follow-ups use the previous question to help retrieval.
5. RagRetriever ranks structured records and page passages with lexical BM25-style scores, exact identifiers, and question intent. Multiple explicit part numbers receive retrieval coverage.
6. Up to RAG_TOP_K excerpts are assigned per-answer IDs such as S1 and S2. Every request retrieves again.
7. Evidence mode returns these records directly. No relevant evidence produces an insufficient-evidence response without a model call.
8. Answer mode sends the question, recent dialogue, and selected excerpts to Groq. The system prompt requires catalogue grounding and separates unknowns from claims.
9. Groq returns a strict JSON schema. Python validates structure, source IDs, quote membership, and numeric/DCF identifier presence. A response that fails citation checks is withheld.
10. A successful response, evidence-only result, or withheld/insufficient result is stored locally. Provider failures are shown as errors and are not saved as successful responses.
11. The UI renders text safely, displays unknowns, and links citations to the source desk and original PDF page.

A source link includes its catalogue SHA-256. If the local PDF changes, opening a citation for the older edition returns a source-changed error. Reindex and ask again for current evidence.

## Architecture and file responsibilities

Browser → Node asset server/API proxy → FastAPI routes → focused services → local repositories/Groq.

| Module | Responsibility |
| --- | --- |
| frontend/server.mjs | Start/stop Python, proxy requests, serve an explicit asset list, reload Python app edits |
| frontend/src/app.js | Conversation state, questions, source selection, setup/status feedback |
| frontend/src/services/api.js | Fetch timeout, readable errors, response-contract checks |
| frontend/src/components/sources.js | Text-safe source cards and validated local PDF links |
| backend/app/main.py | API routes, lifecycle, exception mapping, middleware |
| backend/app/core/settings.py | Local .env and environment settings; key excluded from repr |
| backend/app/models/chat.py | Question and structured-answer schemas |
| backend/app/repositories/catalogue.py | Fingerprinted catalogue/page cache and synchronized loading |
| backend/app/repositories/conversations.py | SQLite conversations and persisted response snapshots |
| backend/app/services/denso_parser.py | Edition-specific table extraction |
| backend/app/services/rag_retriever.py | Source units, lexical scores, part identifiers and intent |
| backend/app/services/answer_service.py | Retrieval, history, capacity bound, citation validation, saving |
| backend/app/integrations/groq_client.py | Grounding prompt, official HTTPS API, strict schema, provider errors |
| backend/app/services/catalogue_service.py | Deterministic automotive lookup/search/comparison |
| backend/app/services/document_reader.py | Generic PDF/TXT extraction for the ingestion baseline |
| backend/app/services/text_chunker.py | Overlapping chunks within individual pages |

Small domain-specific classes and functions keep parsing, retrieval, provider calls, and presentation independently testable. A separate file is used for each coherent responsibility; tiny unrelated helpers do not each require a new file.

## API contract

| Endpoint | Behavior |
| --- | --- |
| GET /api/health | Readiness and contract version |
| GET /api/status | Catalogue counts/fingerprint and safe configuration status |
| POST /api/chat | Question, optional conversation_id, mode answer or evidence |
| GET /api/conversations | Recent local conversation list |
| GET /api/conversations/{id} | Saved response/source snapshots |
| POST /api/catalogue/reindex | Rebuild local catalogue records and page chunks |
| GET /api/catalogue/pdf?version=HASH | Fixed local PDF; rejects stale version |

No arbitrary filesystem route or file-upload endpoint is provided. The Node proxy accepts GET/POST, limits incoming request bodies, and checks browser origins. The Python host filter permits loopback hosts. These are local-development controls, not a public deployment authentication system.

## Retrieval and source interpretation

The system does not currently use embeddings or a vector database. Lexical retrieval is inspectable and appropriate for exact part numbers and catalogue terms, but broad paraphrases, multilingual questions, and incomplete vehicle descriptions can miss useful records.

Structured sources retain the source filename, physical PDF page, section, normalized record, and extracted source excerpt. An excerpt from a table is not a full reconstruction of the page layout. Raw page chunks broaden access to catalogue narrative. Check the original PDF to interpret headers and qualifiers.

Cross-reference rows are directional relationships as published. Brand ambiguity must remain visible. Applications preserve model/date/AC/steering qualifiers as text, not as a complete fitment rule engine. Neither a shared application nor equal dimensions proves equivalence.

## Groq configuration and failures

Default model: openai/gpt-oss-120b, temperature 0, low reasoning effort, maximum 3000 completion tokens. The provider adapter uses the official chat-completions endpoint and strict JSON schema. Model availability and account access are established only by a live request.

Timeout defaults to 45 seconds; retrieval defaults to 8 sources. backend/.env.example lists the settings; actual credentials stay in ignored backend/.env or process environment. No credentials are copied from other projects.

No background retry loop is used. Authentication failure, provider errors, rate limits, malformed answers, and timeouts produce readable errors. Two concurrent answer requests are allowed. Citation mismatch withholds the generated claims and retains retrieved evidence for inspection.

Quote membership and identifier/number checks are useful guards, not semantic proof. A quote can exist while a claim interprets it incorrectly. Human review and a future evidence-quality evaluation remain necessary.

## Persistence and privacy

Generated catalogue indexes, page chunks, SQLite chats, and test reports live under backend/data/runtime and stay outside Git. The downloaded manufacturer PDF is also ignored. Questions and recent dialogue are sent externally only in answer mode; selected excerpts accompany them.

The system is a single-user local workspace. Account login, multi-user permissions, deletion UI, public hosting, and production observability are not implemented. Close the local app before manually removing its chat database if you want to clear history.

## Testing and acceptance

Verified 2026-11-18: 67 backend checks and 7 frontend checks passed, plus JS syntax and an isolated Node-to-Python HTTP walkthrough. Ten backend checks require the real local PDF. Model request/response behavior is tested with mock HTTP transport. See docs/VERIFICATION.md for the exact scope and remaining manual checks.

Acceptance for this milestone:
- Real catalogue evidence can be retrieved without an API key.
- Generated factual claims require inspectable source IDs and quotes.
- Missing evidence remains explicit, and invalid citations withhold the response.
- Old PDF citations are rejected after a source revision.
- Missing credentials and provider failures are understandable.
- Conversations and their source snapshots persist locally.

A live-key answer and browser review remain necessary before declaring this milestone fully validated.

## Separate existing workflows

The sample investigation CLI compares fictional fan fields against JSON rules and returns match/conflict/unknown. It is a reproducible pipeline fixture. The automotive CLI returns conflict for known differing dimensions, documented_reference for an explicit qualified published reference, and unknown when evidence is insufficient; it never returns installation approval. The isolated teacher prototype stays inside DEMO proto.

## Future work

1. Run and review live Groq answers against a small cited question set.
2. Complete browser layout, accessibility, and citation-click checks.
3. Add a main-app deterministic comparison matrix and clearer vehicle-detail collection.
4. Measure retrieval coverage and citation interpretation; add semantic retrieval only if measured gaps justify it.
5. Support additional permitted catalogues through separate parsers with their own validation.
6. Build explicit vehicle qualification rules before making exact-fitment claims.

Use README.md for setup, docs/AUTOMOTIVE_WORKFLOW.md for catalogue CLI details, and PROPOSAL_README.md for the teacher-facing scope.

## Appended implementation update — 2026-11-18

This update supersedes the earlier future-work item about the main-app deterministic matrix. It is now implemented in a collapsible browser panel, backed by CatalogueTools and the existing conservative CatalogueService rules. Field match is dimensional agreement, not a final compatibility verdict. Matrix rows retain PDF evidence, and users can download Markdown/JSON reports.

The current architecture also has two agent interfaces:

Browser / REST client / MCP client → interface adapter → shared catalogue tools → repository + retrieval/comparison services → cited records.

The Groq chat path remains separate and continues to use AnswerService. MCP's catalogue tools intentionally do not call Groq or write chats; an agent can use its own model to interpret returned evidence. The same four operations are exposed over REST. The MCP server uses the official mcp==2.3.0 SDK, structured tool outputs, read-only annotations, and metadata/workflow resources. HTTP runs at /mcp within FastAPI, with explicit session-manager lifespan; stdio has a separate entry script. See docs/MCP_AND_API.md.

New REST routes: GET /api/catalogue/info; POST /api/catalogue/search; POST /api/catalogue/lookup; POST /api/catalogue/compare; GET /api/conversations/{id}/export?format=markdown|json. The Node server also proxies /openapi.json. No arbitrary document/file access is introduced.

Repeated pronoun follow-ups now retain a resolved retrieval query so the third and later turns keep the original part. Conversation exports preserve saved source snapshots and scope S1/S2 identifiers to their own question. Loading feedback includes elapsed seconds.

The expanded verification is 76 backend and 10 frontend tests, plus real HTTP/stdio MCP and Node/Python integration. Visual Windows browser automation stopped because the current URL could not be verified safely; visual review and live Groq verification remain pending. Exact changes, reasons, and file responsibilities are appended to the README rather than replacing its prior milestone.

## Appended architecture update — 2026-11-18: document library

Current retrieval combines exact/keyword catalogue records with a persistent Chroma document collection. Local all-MiniLM-L6-v2 ONNX embeddings have 384 dimensions. SQLite chat storage remains; a separate SQLite registry tracks document hashes, indexing state, schema, counts, and timestamps.

Upload → save/hash → HTTP 202 → background per-document extraction/cache → token windows → incremental Chroma upsert → ready-document search. Existing ready documents are not reprocessed on a new upload. A duplicate content hash reuses the same index, and interrupted jobs reuse extraction plus existing vector IDs.

PDF/TXT uploads are bounded to 25 MB and PDFs to 1500 pages. Image-only files require future OCR. Partial PDF extraction retains a warning. Sources use /api/documents/{sha256}/pdf#page=N and are checked against stored bytes. The original DENSO-specific deterministic matrix remains scoped to that catalogue.

New routes: GET /api/documents; POST /api/documents/upload; POST /api/documents/{id}/retry; GET /api/documents/{id}/pdf. MCP search_catalogue uses the same ready-document retrieval layer. Upload-only chat/search can operate without the base DENSO PDF.

Ordinary car-owner questions do not need part numbers. Incomplete swap questions collect both car years, component, market, and trim. They do not receive invented approval. Year-led follow-up messages can reuse the preceding context. Explicit DENSO numerical comparisons are generated by existing catalogue rules with exact quotations, rather than LLM arithmetic.

Current real-reference corpus: DENSO 141 pages and KYB South Africa 2023 160 pages, with KYB page 153 skipped. The ready corpus has 2,382 token windows. An integration fixture is excluded from ordinary answers.

Windows path handling is documented in docs/DOCUMENT_LIBRARY.md. Actual data stays under backend/data/runtime; a verified ASCII junction permits native Chroma persistence in this Unicode-named project. No OS settings were changed.

Verified: 96 backend tests, 11 frontend tests, and 17 real document-library checks, plus the existing Node/Python/MCP walkthrough. Token count observed: maximum 223; embedding dimension: 384. Live model output can still fail strict citation checks, and arbitrary table extraction/semantic entailment/exact vehicle fitment are not guaranteed. Read the appended README record and docs/VERIFICATION.md for the live cases and targeted fixes.
