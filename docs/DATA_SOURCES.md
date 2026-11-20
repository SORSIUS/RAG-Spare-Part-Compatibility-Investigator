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

## KYB MEA linked suspension applications — 2026-11-20

Downloaded the official 174-page [KYB accessories catalogue V.3](https://kybme.com/new/wp-content/uploads/2025/11/accessory-catalogue-KYB.pdf), SHA256 `0315864b4689f878207671bc29ea3a83d01768130d3b7b987c2a813c7abe16be`. The reviewed column-aware adapter imported 3,814 associations across 14 makes and 178 model groups from 59 supported application pages. Toyota Corolla has 395 associations. It preserves production codes, application conditions, axle/component, part number, OEM cell group and original PDF page. Coverage is partial and not a Pakistan-specific interchange guarantee.

The local PDF is `backend/data/sources/extra/kyb_mea_accessories.pdf`; the SQLite index is `backend/data/runtime/fitments.sqlite3`. Both remain ignored. Setup, extraction limits, source revision history, visual spot check and design research are documented in [FITMENT_INDEX.md](FITMENT_INDEX.md). Earlier entries above describe the state before this structured adapter existed.
# Additional official DENSO coverage — 2026-11-20

Downloaded and indexed directly from the [official DENSO catalogue download page](https://am.denso.com/plug-global/model-search/catalog/):

| Local file | Official PDF | Pages | SHA-256 |
| --- | --- | --- | --- |
| denso_spark_plug_japan_2025.pdf | [Japan](https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_4_japan_2025.pdf) | 53 | 84d5c4529999eb8f0fc7681e4dea91d1610857fb68c71df4dcada957c76f933e |
| denso_spark_plug_europe_2025.pdf | [Europe/USA](https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_5_europe_2025.pdf) | 61 | e7bef24dc32728bfd93788b108b3abc3b597e02316f4fb68fbb3275bbccf8d7c |
| denso_spark_plug_references_2025.pdf | [Others/cross-references](https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_6_others_2025.pdf) | 65 | 212028e9de007768f021c7691013eaf1e3b40b1fa270ab543e7e4b5f567d3891 |

Three new documents add 3,217 embedding windows. The existing Asia and product-information documents were hash-deduplicated. The ignored runtime download manifest records URLs, hashes, page counts and sizes. Third-party Toyota manuals requiring registration or payment were not bypassed.

The new parser reads only the reviewed PDF's OEM-reference pages 18–30, using three bounded original/standard-DENSO column pairs. It skips annotations, absent entries, boundary-crossing words, unmatched rows and unrecognized headers. The Iridium upgrade columns are not imported. Physical page 29 was rendered and inspected to check the Toyota layout and sample pair 90919-01095 → W16ETR-S.

Output: 1,341 number-reference rows across 18 named original-number brands, including 137 Toyota rows. Some brands are service brands or cover non-car equipment; these counts are not vehicle counts. This evidence does not establish a vehicle's suitability. DENSO's chart requires checking its application tables.

## Reviewed vehicle application subset

The existing Asia PDF now also supplies 60 Toyota Taiwan vehicle/engine/year/standard-plug application rows from physical pages 99–100. Both pages were rendered and reviewed; extraction is hash-locked and rejects ambiguous or engine-less rows. Complete original model labels, production ranges, market, OEM number and physical page are retained. A normalized model family supports owner questions; it does not imply interchangeability between variants. Other regional application tables remain ordinary document-search sources until a reviewed adapter is added.
