# “Can This Part Replace That?” — Spare-Part Compatibility Investigator

Status: Full application remains planned. An isolated, rules-based teacher prototype is available in [DEMO proto](DEMO%20proto/README.md).
Teacher selection: Approved, as reported by the user on 2026-11-16. Priority: Build this category’s assignment project first.
Last updated: 2026-11-16

Repair staff struggle to compare unavailable parts against inconsistent specifications and replacement documentation.

## Read these first
- [Project concept, architecture, and workflow](PROJECT_README.md)
- [Teacher proposal](PROPOSAL_README.md)
- [Category overview](../README.md)
- [Full portfolio plan](../../../PROJECT_PORTFOLIO_README.md)

## Current structure
- `backend/`: Planned Python/FastAPI application, with `app/api`, `app/models`, `app/services`, `app/repositories`, `app/integrations`, and `app/core`.
- `frontend/`: Planned Node.js-based React/Vite frontend, with `src/components`, `src/pages`, `src/services`, and `src/state`.
- `data/sample/`: Fictional demonstration data to create during implementation.
- `docs/`: Design notes and later diagrams.
- `tests/`: Meaningful backend, frontend, and workflow checks added during implementation.
- Middleware: Add a folder only when a concrete authentication, logging, or request-processing need is identified. FastAPI middleware can remain inside the backend.

## Next actions
1. Review the proposal with the teacher and record selection.
2. Agree on the smallest demo and create the fictional data.
3. Implement and validate the backend workflow, then connect the frontend.
4. Demonstrate the acceptance scenario in PROJECT_README.md.

## Documentation maintenance
Update this README whenever code, structure, setup, configuration, or behavior changes. Record what changed and what was actually checked. Update PROJECT_README.md for architecture and workflow changes, and PROPOSAL_README.md when agreed scope changes. Keep planned features separate from working features.

## Change log
- 2026-11-16: Created the concept, proposal, and empty implementation folders. Checked scaffold structure and document links only; application behavior has not been tested.

## Isolated demonstration
All runnable prototype code, sample data, and backend tests live inside `DEMO proto/`. See its README for setup, limitations, and verification. The full-application scaffold remains separate.

- 2026-11-16: Added the isolated Python/Node teacher-demo prototype; no live LLM integration.

Prototype v2 verification: 9 Python tests, JavaScript syntax, and the project-specific browser walkthrough passed. See [demo verification](DEMO%20proto/docs/VERIFICATION.md) for scope and limits.

- 2026-11-16: Recorded teacher approval and assigned prototype port 3101; use DEMO proto/START_DEMO.cmd.

- 2026-11-16: Upgraded the isolated DEMO proto: Color-coded comparison of documented specifications with side-by-side source passages. See its README and verification notes for the current walkthrough.
