# Teacher proposal: “Can This Part Replace That?” — Spare-Part Compatibility Investigator

Category: RAG PROJECTS ALL
Prepared: 2026-11-16
Decision: Teacher-approved, as reported by the user on 2026-11-16. Detailed implementation scope and rubric remain to be agreed.

## Problem statement
Repair staff struggle to compare unavailable parts against inconsistent specifications and replacement documentation.

## Intended users
Repair shops and equipment inventory staff.

## Proposed solution
Build a modular web application using a Python backend and a Node.js-based frontend. Document ingestion, chunking, embeddings, vector retrieval, source citations, and structured validation.

## Initial deliverable
One noncritical part family, a small curated catalogue, explicit comparison rules, and a cited matrix.

Data required: Part catalogues, equipment manuals, specification tables, and service bulletins for a narrow noncritical product category. Begin with fictional records.

## Workflow for the demonstration
1. Import manuals and catalogue records with source and revision metadata.
2. Extract part identifiers, units, and documented specifications into structured records.
3. Retrieve evidence for the original component and candidate replacements.
4. Compare required specifications with deterministic rules and label matches, conflicts, and unknowns.
5. Show a compatibility matrix with citations and a list of checks still required.

## Memorable demonstration
Two plausible replacements appear side by side; one conflicts on a required specification and another lacks documentation.

## Learning outcomes
Apply functions, classes, modular Python, API design, structured data, validation, exception handling, persistence, frontend/backend integration, and the category-specific AI workflow. Explain each module and show how failures are detected and handled.

## Evaluation criteria
Every comparison cites a specification; missing values remain unknown; a conflicting required value blocks a confirmed match.

Assess workflow correctness and failure handling alongside AI output quality. Document the actual checks performed and their limitations.

## Deliverables
- Source code organized into backend and frontend modules.
- Fictional sample records and reproducible setup instructions.
- A working minimum-scope demonstration and relevant verification results.
- An up-to-date README, detailed project/workflow document, and this proposal.

## Limitations and future work
A proposed alternative is not a certification of safe installation; restrict the demo to noncritical equipment and require technician verification.

Future extensions: More product families, revision tracking, and technician review records.

## Teacher selection record
- Selected for assignment: Yes — teacher approval reported by the user on 2026-11-16
- Requested changes: None reported yet
- Agreed scope: Pending
- Review date: Not specified; approval recorded on 2026-11-16

The portfolio includes four proposals in this category. The teacher-recommended project will be built first; the remaining projects stay planned for later development.

## Prototype availability — 2026-11-16
An isolated [DEMO proto](DEMO%20proto/README.md) now demonstrates the concept with fictional records and deterministic rules. It is not the full planned AI implementation. All prototype backend app, data, and tests are nested under its backend folder; the Node.js frontend is separate inside the same demo folder.

## Teacher prototype v2 — 2026-11-16
Color-coded comparison of documented specifications with side-by-side source passages. The interactive DEMO proto includes a guided walkthrough and remains deterministic with fictional records. This improvement does not change the agreed separation between prototype and full implementation.
