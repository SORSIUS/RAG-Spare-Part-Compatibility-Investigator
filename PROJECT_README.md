# Project plan: “Can This Part Replace That?” — Spare-Part Compatibility Investigator

Planning baseline: 2026-11-16. Everything below describes proposed behavior, not an implemented system.

## Problem and intended users
Repair staff struggle to compare unavailable parts against inconsistent specifications and replacement documentation.

Intended users: Repair shops and equipment inventory staff.

## Goal and scope
Minimum viable project: One noncritical part family, a small curated catalogue, explicit comparison rules, and a cited matrix.

Later portfolio extensions: More product families, revision tracking, and technician review records.

## Inputs and records
Part catalogues, equipment manuals, specification tables, and service bulletins for a narrow noncritical product category.

Use fictional or explicitly permitted sample data. Keep original records, source identifiers, timestamps, and revisions when needed. Do not place credentials or private customer records in sample files.

## Main workflow
1. Import manuals and catalogue records with source and revision metadata.
2. Extract part identifiers, units, and documented specifications into structured records.
3. Retrieve evidence for the original component and candidate replacements.
4. Compare required specifications with deterministic rules and label matches, conflicts, and unknowns.
5. Show a compatibility matrix with citations and a list of checks still required.

## Planned architecture
Browser UI → frontend API client → Python/FastAPI routes → focused services → repositories and integrations → persisted records.

Proposed baseline: Python/FastAPI backend, Node.js with React/Vite frontend, and SQLite for structured data. These choices are planning defaults; dependency versions and provider support will be checked when implementation starts. A local vector store and an embedding model will be selected for document retrieval. Choose the LLM provider during implementation and keep provider access behind a small integration adapter.

The browser sends requests to backend routes. The backend owns secrets, model calls, validation, and persistence. The Node.js frontend is the UI development/build environment; add a separate Node server only if deployment needs it.

## Python classes and module responsibilities
Proposed domain models: `PartSpecification`, `CompatibilityRule`, `EvidenceChunk`, `CompatibilityFinding`. Use data models/classes for entities and state. Use small functions for transformations and validation, and service classes where shared dependencies or state make them useful.

Proposed service modules under `backend/app/services/`:
- `catalogue_service.py`
- `specification_service.py`
- `retrieval_service.py`
- `compatibility_service.py`

- `api/`: Routes grouped by resource or workflow; delegate business logic to services.
- `models/`: Domain objects and request/response validation.
- `repositories/`: Database reads, writes, transactions, and record lookup.
- `integrations/`: LLM, vector-store, speech, or other external API adapters as needed.
- `core/`: Configuration, shared error types, and logging setup.
- A later `main.py` will create the application and connect the routes.

Keep related functions together in focused modules. Split growing modules by responsibility; avoid a separate file for every trivial function. Add interfaces, inheritance, or multiple agents only when they solve a real requirement.

## Frontend plan
- `src/pages/`: Main workspace and detail views for the workflow.
- `src/components/`: Reusable forms, evidence/status displays, and confirmation controls.
- `src/services/`: HTTP client and API error handling.
- `src/state/`: User interaction state and current workflow selection.
- Show loading, validation errors, empty results, uncertainty, and saved versus proposed changes explicitly.
- Make every plan revision or evidence result inspectable from the main workspace.

## Course concepts to apply
- Python types, collections, conditions, loops, functions, comprehensions, and file handling for data preparation.
- Classes, composition, exceptions, modules, and packages for maintainable application structure.
- JSON, APIs, validation, environment configuration, async I/O where useful, and persistence.
- Document ingestion, chunking, embeddings, vector retrieval, source citations, and structured validation.
- Data analysis and tabular processing where the input needs it; use regex or NLP preprocessing for concrete extraction needs.
- Evaluate retrieval, decisions, or speech with representative examples. Do not add model training, CNNs, or deep learning solely to mention a course topic.

## Reliability and debugging plan
Validate inputs at the API boundary and business rules inside services. Use clear error messages and request/session identifiers. Log source IDs, tool results, and state transitions without secrets or sensitive content. Bound retries and agent steps; stop on unresolved ambiguity. Keep proposed changes separate from committed records. Use database transactions and duplicate-request protection for state-changing operations where needed.

Main project-specific concern: A proposed alternative is not a certification of safe installation; restrict the demo to noncritical equipment and require technician verification.

## Demonstration and acceptance
Demo: Two plausible replacements appear side by side; one conflicts on a required specification and another lacks documentation.

Acceptance: Every comparison cites a specification; missing values remain unknown; a conflicting required value blocks a confirmed match.

During implementation, check a successful workflow, an ambiguous or missing-data case, a rejected invalid action, and a provider failure. Include citations checks for RAG, constraint and tool-state checks for agents, or transcript/confirmation checks for voice. Report measured results honestly, including sample size and limitations. A fictional demonstration does not establish real-world accuracy.

## Implementation phases
1. Teacher selection, requirements, and synthetic sample records.
2. Domain models, repositories, and deterministic core rules.
3. Category-specific AI pipeline and focused backend routes.
4. Frontend integration and the memorable demonstration.
5. Relevant verification, debugging, and documentation updates.
6. Optional portfolio expansion after the assignment version is complete.

## Open decisions for the selected project's kickoff
Exact sample-data scope, model/speech providers, supported file formats or languages, deployment target, and teacher rubric. Record decisions here before implementing their dependent features.

## Prototype availability — 2026-11-16
An isolated [DEMO proto](DEMO%20proto/README.md) now demonstrates the concept with fictional records and deterministic rules. It is not the full planned AI implementation. All prototype backend app, data, and tests are nested under its backend folder; the Node.js frontend is separate inside the same demo folder.

## Teacher prototype v2 — 2026-11-16
Color-coded comparison of documented specifications with side-by-side source passages. The interactive DEMO proto includes a guided walkthrough and remains deterministic with fictional records. This improvement does not change the agreed separation between prototype and full implementation.
