# Automotive source documents

## DENSO cabin air filter catalogue

- Publisher: DENSO Aftermarket Europe.
- Source: https://assets.denso-am.eu/production/attachments/Cabin-Air-Filters-Product-Catalogue-2026.pdf
- Downloaded: 2026-11-17.
- Local path: backend/data/sources/automotive/denso_cabin_air_filters_2026.pdf
- Verified metadata: 141 pages, 5,872,957 bytes, not encrypted.
- SHA-256: 4a853e38eb3a2295c7652ee951051a949a29090867876fbcdc6abd8e0ce6a474
- Status: Downloaded, metadata checked, and processed with the source-specific parser. Representative application/reference/dimension layouts were visually inspected; 5 local-source integration checks passed. Exact-vehicle compatibility validation remains pending.
- Redistribution: Not established. Downloaded source files are excluded by the root .gitignore; do not publish this manufacturer's PDF without reviewing permission and terms.

The catalogue remains separate from fictional sample fixtures. The new DensoParser handles this edition's layout; the earlier sample label parser remains a separate workflow. Local extraction produced 345 dimension records, 7,798 cross-reference rows, and 3,704 application rows. Counts do not establish completeness or real-world fitment accuracy. See AUTOMOTIVE_WORKFLOW.md for scope and limitations.

## Main app usage — 2026-11-18

The main app builds ignored structured-record and page-chunk caches from this PDF. Search sources stays local. Ask Groq sends selected extracted excerpts together with the question and bounded recent dialogue to Groq; it does not upload the complete PDF. A project key is still required for live model verification.

The response's source desk distinguishes normalized source records from extracted excerpts. Links reference physical PDF pages and include the document hash. Old links are rejected if the local source changes. The full manufacturer PDF and derived full indexes remain outside Git.

## Additional suspension source — downloaded 2026-11-18

- Publisher/source: KYB South Africa; https://kyb.co.za/wp-content/uploads/2023/09/KYB-catalogue-2023.pdf.
- Local file: backend/data/sources/extra/kyb_shocks_2023.pdf.
- Edition: 2023 regional catalogue, not a current global fitment source.
- Verified: 160 PDF pages, 16,983,101 bytes.
- SHA-256: 4b9d7d42c3be79739a348838c3273bbc67c137124c590feacbbd56ec8ef27c50.
- Extraction: physical page 153 exceeded the PDF reader's parsing budget. It was skipped; 1,148 token windows from readable text were indexed in Chroma. The limitation is retained in the document registry and UI.
- Use: document-grounded suspension reference questions. No new structured KYB interchange/fitment parser was created.
- Redistribution: not established; original and derived indexes remain local and ignored by Git.

Attempted additional official URLs returned HTTP 403 and were not downloaded: DENSO Cabin-Air-Filter-Product-Information-Catalogue.pdf and KYB's 2026 installer-guide PDF. The exact URLs and HTTP outcomes are saved in ignored backend/data/runtime/reference_downloads.json.

User uploads retain their filename, content SHA-256, physical page numbers, and immutable document links. Uploaded documents are reference data, not instructions. Text-only/scanned-PDF limitations apply. The fictional verification_training_reference.pdf is excluded from ordinary answers after integration checks.
