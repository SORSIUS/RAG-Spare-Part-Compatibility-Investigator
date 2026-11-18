# Teacher proposal: Spare-Part Compatibility Investigator

Short name: **“Can This Part Replace That?”**

Category: RAG PROJECTS ALL

Teacher approval reported by the user: 2026-11-16

Updated: 2026-11-18

## Problem

Parts researchers must compare unavailable parts with alternatives scattered across manufacturer specifications, reference tables, and vehicle application lists. An unsupported replacement claim can look convincing even when important information is missing.

## Proposed solution and selected scope

Build a modular Python backend and Node.js frontend that follow this workflow:

**Read documents → retrieve evidence → compare requirements → explain matches, conflicts, and unknowns.**

The first real dataset is the DENSO 2026 cabin-air-filter catalogue. A document-grounded chat workflow retrieves catalogue evidence and asks Groq to explain it with quoted source references. Published references and dimensional agreement remain separate from exact-vehicle suitability.

## What is implemented

- PDF reading, page-aware text chunks, and a DENSO-specific table parser.
- Exact identifier lookup, application text search, and conservative automotive comparison through a CLI.
- A main web interface for catalogue questions, saved conversations, retrieved records, and original PDF page inspection.
- A Groq integration with structured answers, source/quotation checks, unknowns, and clear error handling.
- An evidence-only mode that works without model credentials.
- A separate fictional prototype and sample-PDF comparison pipeline for teaching.

Retrieval currently uses lexical ranking, not embeddings. Arbitrary catalogue uploads, OCR, a main-interface comparison matrix, and a complete vehicle-fitment engine are future work.

## Teacher walkthrough

1. Search for the dimensions of DCF002K and inspect PDF page 97.
2. Ask about Toyota Corolla application records; preserve the separate model/date entries.
3. Investigate the published C30001 → DCF357P reference and its brand context.
4. Compare DCF009P and DCF031P through the deterministic CLI.
5. Show that missing evidence stays unknown and a citation-check failure withholds generated claims.

Groq answers in this walkthrough require a locally configured API key. Evidence search works immediately with the local source.

## Learning outcomes

Apply classes, functions, modular files, API design, PDF extraction, lexical retrieval, LLM prompting, structured validation, persistence, exception handling, frontend/backend integration, and meaningful tests. Explain the role of each module and trace a question from input to source.

## Evaluation and current evidence

On 2026-11-18, 67 backend tests, 7 frontend tests, JS syntax checks, and a real-catalogue Node/Python HTTP walkthrough passed. Provider behavior was tested with controlled mock responses. A live Groq answer and visual browser walkthrough remain pending; no live answer-quality or fitment-accuracy score is claimed.

Evaluate source correctness, retrieval coverage, missing-information handling, conservative comparison rules, and failure behavior. Test counts do not establish real-world compatibility accuracy.

## Deliverables and limits

Source code, setup instructions, source provenance, verification notes, project architecture, this proposal, and an isolated teacher prototype are available. Downloaded manufacturer documents, secrets, and generated records stay outside Git.

Catalogue evidence is not installation approval. Exact vehicle details, production dates, region, qualifiers, and revisions still require expert verification. No redistribution permission is claimed for the manufacturer PDF.

Teacher-approved project selection remains recorded; no additional approval of the new implementation scope or rubric is assumed. Future work can add a comparison matrix, measured semantic retrieval, and further permitted automotive catalogues after the first live verification.

## Appended progress — 2026-11-18: agent-ready catalogue investigation

The main web app now includes the comparison matrix previously listed as future work. Users can compare documented dimensions with explicit match/conflict/unknown labels and cited PDF pages, and export comparison or saved-chat investigations as Markdown/JSON.

Compatible agents can discover four read-only catalogue tools through MCP over HTTP or stdio, or use equivalent typed REST operations. This reuses the validated domain services rather than asking a model to invent compatibility decisions. Agent access makes the project easier to integrate; it does not establish that a publicly hosted commercial product is complete.

The updated checks cover 76 backend tests, 10 frontend tests, and real MCP HTTP/stdio calls through the actual catalogue workflow. Browser visual review remains pending after Windows automation stopped because it could not verify the current URL; live Groq verification also remains pending. Teacher approval of the original project is unchanged; no additional rubric or production certification is assumed.

## Appended progress — 2026-11-18: accessible document investigation

The app now accepts PDF/TXT uploads, acknowledges file saving before indexing, and prepares each new document in the background. Persistent Chroma embeddings support semantic search while a SQLite registry and cached chunks prevent reprocessing unchanged files. Existing chat history remains in SQLite.

Ordinary users can ask with vehicle/component names instead of part numbers. Incomplete swap questions collect both vehicle years and simple front/back/component details; the app does not invent a yes/no decision without evidence. Exact numerical comparisons use deterministic catalogue rules. Groq explains broader supported passages with source references.

An additional official KYB South Africa 2023 catalogue was downloaded and indexed with its regional/edition limits. Physical PDF page 153 could not be parsed and was skipped with a coverage warning. Generic PDF text retrieval does not establish a complete vehicle-fitment database.

Verified: 96 backend tests, 11 frontend tests, 17 actual document-library integration checks, the original MCP/HTTP walkthrough, and a final eight-scenario question set with live Groq plus deterministic comparison. Browser visual review and broader fitment/answer-quality evaluation remain pending. This is implementation progress, not additional teacher approval or production certification.
