# Current work checkpoint — 2026-11-20

Newest work: model/year/engine/component-aware retrieval and owner clarification are implemented. The existing 3,814 KYB application rows now support engine/component filtering; 60 Toyota Taiwan spark-plug application rows add explicit engine/period/OEM/standard-plug links. Multi-turn owner lookup, history and real MCP retrieval passed without LLM calls. Final checks: 120 backend and 13 frontend tests, plus syntax/live API checks.

Coverage remains bounded: other regional spark-plug tables and additional vehicle makes need reviewed adapters. Source market, production qualifiers and exact chassis still matter. The new engine input has not had a fresh browser visual walkthrough.

Latest coverage expansion: three additional official DENSO PDFs are downloaded and ready. The reviewed OEM-reference adapter adds 1,341 standard-DENSO number references, including 137 Toyota rows, separate from KYB's 345 application-specific links. Empty replies now provide next steps and chat continuation; partial answers preserve checked cited facts. Final backend 116 / frontend 13 tests and live API/MCP checks passed without LLM calls.

Remaining scope: add reviewed adapters for vehicle/engine application tables to join exact vehicle conditions to spark-plug references. The new regional PDFs are searchable, but their application tables are not yet fully normalized into structured vehicle links. Do not claim every vehicle/part is covered or that an OEM cross-reference proves installation fitment.

Latest addition: directed original-part replacement lookup is implemented in the API, expandable frontend form and existing MCP search. The reviewed KYB catalogue supplies 345 application-specific references across 14 makes; this is limited coverage, not every part/model. Four newly supplied PDFs are ready for ordinary document questions. See `MATERIALS_AND_REPLACEMENTS.md` for materials, provenance and limits.

Next coverage work: collect official regional application/cross-reference catalogues, add and review a dedicated adapter per format, and test representative original-number pairs. Generic upload alone does not publish trusted replacement links. Existing browser-visual-check limitations still apply; this update has HTTP/asset and automated checks.

## Latest handoff — gradients, PDFs and chat recovery

Implemented gradients and an original illustrative hero image (`frontend/assets/automotive-hero.png`), conversational message layout, pending user bubble, bottom composer and retry messages. Provider failures preserve source references in a saved assistant reply; Markdown exports include it. Two official DENSO 2025 PDFs were downloaded and registered: Asia applications (122 pages) and product information (41 pages). See ignored `additional_reference_pdfs.json` for source URLs and hashes.

Final checks passed: 107 backend tests, 13 frontend tests, JS syntax, full Node/Python HTTP integration and MCP HTTP/stdio. The integration check disabled LLM calls and passed history, follow-up, source route, comparisons, exports, missing-key recovery and auto-reload. App restarted at http://127.0.0.1:3201/ (command session 10632).

Only fresh visual browser verification remains blocked: computer-use stopped because the current browser URL could not be determined confidently for policy enforcement. Do not claim the new gradient/chat layout passed visual QA. Previous storefront screenshots verify only the earlier iteration. No more browser retries, LLM calls or image generation were made during the low-usage verification pass. README is updated. No commit/push.

The previous task was partially implemented before the user's usage question. Its remaining automated checks and documentation are now finished; visual QA is explicitly outstanding.

## Latest completed work

- Vehicle-first automotive interface with make/model/year/position/chassis filters, part cards, original-PDF links, saved investigations, catalogue drawer and both themes.
- Official KYB MEA accessories catalogue and reviewed column-aware adapter: 3,814 associations, 14 makes, 178 model groups, 395 Corolla associations; 59 supported application pages in the 174-page PDF.
- Indexed SQLite vehicle/application/part/source links used before broad lexical/Chroma search. Hash/schema caching avoids repeated PDF extraction. Other layouts retain generic document RAG and need their own reviewed adapter.
- Checked catalogue fallback when generated wording fails date/quote checks; fabricated KYB/chassis identifier rejection. Original guardrails retained.
- README setup, FITMENT_INDEX.md, source provenance and detailed change history updated.

## Latest verification and limits

107 backend tests, 12 frontend tests and JS syntax passed. API returned nine filtered Corolla rows, zero for an unknown chassis and HTTP 200 application/pdf for the fingerprinted source. Cached import reused without extraction. Twenty local indexed queries: median 6.17 ms, max 6.68 ms (not HTTP/LLM latency).

Browser checked at 1280x900 and 390x844: vehicle filters, cards, part-to-question action, empty-result message, saved history and both themes. No mobile page overflow. Viewport overrides reset. Screenshots: storefront-desktop.jpg, storefront-parts.jpg, storefront-mobile.jpg.

The live LLM explanation changed a production code and was rejected. The retest displayed the checked source-linked fallback; do not call it a successful generated answer. Duplicate PDF headers and digit-containing model boundaries were corrected during import. Source page 96 was visually spot checked; not every imported row is manually audited. Coverage is partial and not Pakistan-specific installation approval. Exact production month, chassis, engine, steering and market still matter. OCR, VIN decoding, prices/stock and production authentication remain outside the implemented scope.

App: http://127.0.0.1:3201/ (command session 55976), retained browser tab 1 in browser 2. Source PDFs, databases and embeddings remain ignored. Unrelated untracked .vscode and the oddly named user file were preserved. No demo edits or Git commit/push in this update. Keep backend/.env private. Optional next work: review additional catalogue adapters/pages and improve generated wording reliability for structured rows.

# Previous checkpoint — 2026-11-18

## Completed

- Natural, short owner-friendly LLM answers; evidence restrictions and server-side citation validation retained.
- Enter button; source-only search moved to source desk; normal provider branding and Local workspace wording removed.
- White/emerald light theme and green/black dark theme, saved per browser; readable cards and source passages.
- Active saved-chat indicator, empty state, mobile History control; a loading error no longer detaches the selected chat.
- Current setup-focused README and dedicated docs/CHANGELOG.md preserving the old detailed change entries.

## Verified

98 backend tests, 12 frontend tests, JS syntax checks. Live Groq Toyota answer produced two concise cited claims. Browser opened an older chat, restored the new chat, and retained its answer/citations/export URL/selection after reload. Both themes survived reload. No provider branding appeared in normal visible text; no horizontal page overflow at the tested browser size. Screenshots: interface-light.jpg and interface-dark.jpg in docs/.

## Issue fixed

New theme CSS/JS initially returned 404 because Node serves an explicit allowlist. Added both routes, restarted the project server, and verified successful app initialization. App currently runs at http://127.0.0.1:3201/ (command session 15903). Browser tab 4 in browser 2 is retained as the deliverable.

## Remaining limits / optional next work

Dedicated mobile viewport walkthrough has not been run; mobile History control is implemented. Citation membership checks do not prove semantic correctness. Scanned PDFs still need external OCR. Production authentication/hosting is not implemented. These are existing limitations, not claims of completed features.

No unfinished required code changes identified in this update. Continue from this checkpoint if further visual refinements are requested. No demo changes; no Git commit or push. Keep backend/.env private.
