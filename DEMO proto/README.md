# Spare-Part Investigator — teacher prototype v2

Updated: 2026-11-16. Teacher-approved priority project. All runnable demo code lives in this isolated folder.

## What this demonstrates
Color-coded comparison of documented specifications with side-by-side source passages.

This is a fictional, deterministic concept prototype. The comparison reads structured sample specifications and curated manual passages; no embeddings, live LLM, document upload, or vector search is connected.

## Teacher walkthrough
1. Click **Inspect a voltage conflict**. ALT-B’s red cell shows 24 V against the original 12 V requirement.
2. Read the original manual and ALT-B catalogue side by side. The relevant values are highlighted in their passages.
3. Click any other colored matrix cell to inspect its specification, rule, and cited source.
4. Click **Investigate a missing detail**. ALT-C’s connector is unknown; it is not treated as compatible.
5. Tick **Add the missing service bulletin**. SB-05 supplies the 2-pin connector value for the documented sample revision, and the connector check changes to green.
6. Untick the bulletin to see the connector return to unknown. Select ALT-A to inspect the straightforward match.

Green means these four recorded fields match; red means a recorded conflict; amber means evidence is missing. These labels are also written in text and represented by symbols. Airflow is a minimum requirement; voltage, size, and connector require equality. No replacement is certified safe by this prototype.

## Existing local launch setup
Requires Node.js 18+ and Python 3.10+. No npm/pip installation or API keys are needed. START_DEMO.cmd retains port 3101. From a terminal inside this DEMO proto folder, run `./START_DEMO.cmd`, or run the Node frontend server from frontend with PORT set to 3101. The Python backend starts automatically on a private loopback port. Keep the terminal open.

After an update, stop the previous demo server with Ctrl+C and start it again; refreshing the browser alone does not reload Python code. If the old interface remains, use Ctrl+Shift+R. VS Code’s Run/Debug button does not execute a batch launcher. If `py -3` cannot start Python, set PYTHON_BIN to a working Python executable. Use one instance of this demo at a time because local records are shared.

## Structure and responsibilities
- backend/app/: comparison.py (specification checks, source references, bulletin evidence), service.py (read-only requests), repository.py (sample data), and api.py (routes).
- backend/data/sample/: Fictional records and project configuration.
- backend/data/runtime/: Local state created by reset or approval; ignored by Git.
- backend/tests/test_workflow.py: Focused domain tests using temporary repositories.
- frontend/server.mjs: Node static server, API proxy, and Python lifecycle.
- frontend/public/index.html: Project-specific interface.
- frontend/public/styles.css: Responsive interface styles.
- frontend/public/app.js: Browser interactions and API client.
- docs/WORKFLOW.md: Request and state flow.
- docs/VERIFICATION.md: Actual checks and saved screenshot.

## Verification
From backend: `py -3 -m unittest discover -s tests -v`.
From frontend: `npm run check`.

Assistant-run results: 9 domain tests and JavaScript syntax checks passed. The actual Node/Python browser walkthrough was checked, including voltage conflict, cited values, missing connector, bulletin resolution, and reversion. [Detailed verification](docs/VERIFICATION.md).

## Change log
- 2026-11-16: Replaced the generic prototype interface with color-coded comparison of documented specifications with side-by-side source passages. Updated domain modules, fictional records, tests, and documentation. The full application remains planned outside DEMO proto.

## Backend reload fix — 2026-11-16
The Node server now watches backend Python and sample configuration files and reloads its owned Python process when they change. Saved runtime records do not trigger a reload. During a reload, API calls return a clear retry message. This fix itself requires restarting an already-running old Node server once. Refresh the page for frontend edits. Kitchen Relay also validates response shape and explains an outdated-backend mismatch instead of failing with an undefined-map error.
