# Linked vehicle and part evidence

## What changed

The app now combines a relational fitment index with the existing document RAG library. A car owner can select a vehicle and see catalogue-listed candidates without waiting for generation. Questions that match imported vehicle/suspension records retrieve their source rows before broad text/vector search. Other questions retain the ordinary RAG workflow.

```text
Reviewed manufacturer PDF
  -> column-aware table adapter
  -> vehicle + production range + application qualifications
  -> axle + component + aftermarket number + OEM cell group
  -> row ID + source SHA256 + physical PDF page
  -> indexed SQLite lookup
  -> part cards, REST API, or cited RAG context
```

Every association has an immutable source hash and deterministic row/column/part ID. This ID identifies the linked evidence unit. Generic Chroma text windows are a separate representation; their IDs are not misrepresented as the table row IDs.

## Actual dataset and provenance — 2026-11-20

- Official source: [KYB MEA accessories catalogue V.3](https://kybme.com/new/wp-content/uploads/2025/11/accessory-catalogue-KYB.pdf).
- Local PDF: `backend/data/sources/extra/kyb_mea_accessories.pdf`; 174 physical pages.
- Reviewed source hash: `0315864b4689f878207671bc29ea3a83d01768130d3b7b987c2a813c7abe16be`.
- Current adapter: `kyb-mea-accessories-v3`; 59 supported application pages inspected, 3,814 vehicle/part associations, 14 makes, 178 model groups. Toyota Corolla has 395 associations. These counts do not mean 3,814 unique products.
- The PDF's production column is headed YY/MM. The app preserves its literal codes, such as `07/10-On`, instead of relying on LLM date expansion. Year filtering interprets the first field as year; it cannot decide an exact production-month boundary from a year alone.
- The catalogue is published through KYB Middle East/Africa, with application qualifiers for multiple markets. It is not a verified Pakistan-only database. Chassis, engine, steering side and regional conditions are preserved and must be checked.
- Raw PDFs and derived runtime data remain local and ignored. Download availability does not establish redistribution permission; the repository includes the importer and provenance, not the source PDF or derived full database.

The existing DENSO cabin-air-filter catalogue, KYB South Africa 2023 catalogue and Toyota brochure/specification documents remain available. A vehicle specification brochure is not itself a replacement-part compatibility catalogue.

## Setup and repeatability

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/import_kyb_fitments.py
```

The script downloads the official PDF only if absent, verifies the reviewed edition's hash, and imports tables only when the source/schema pair has not been imported. It commits a source revision atomically. A second run was verified to report `Cached fitment index reused; no PDF extraction.` The normal worker prepares semantic windows separately. Uploading these exact PDF bytes through the browser can also activate the reviewed adapter in the background; an unrelated PDF is not treated as a fitment table merely because it has a similar filename.

Storage: `backend/data/runtime/fitments.sqlite3`. Import summary: `backend/data/runtime/fitment_import.json`. Both are ignored local artifacts. SQLite indexes cover vehicle/category/year, part and source. SQL parameters handle user filter values; chassis filtering uses token boundaries, avoiding a substring such as ZRE15 matching ZRE152.

## Table interpretation and limits

The adapter uses pdfplumber's table grid, not a flat text split. It removes duplicate overprinted characters, reconstructs split model headings, keeps models containing digits, and skips unrecognized headers, unsupported makes/tables and ambiguous page-leading continuation rows. Its import is deliberately partial rather than guessed.

Front and rear remain separate, as do shock absorbers, protection kits and mounting kits. Several OEM numbers in one cell remain an **OEM cell group**. They are not converted into individual interchangeable-part pairs. Product-series colour coding, inventory, prices, left/right orientation absent an explicit field, VIN decoding and market-wide completeness are not inferred. Component drawings are labelled illustrations, not product photographs.

Generic PDF upload does not automatically build this structured index for every manufacturer. New catalogue layouts need another reviewed adapter. The SHA256 guard deliberately stops the importer if the publisher replaces the PDF edition; review and version the parser before accepting changed columns.

## API and RAG use

```text
GET /api/fitments/options
GET /api/fitments?make=Toyota&model=Corolla&year=2012&axle=front&chassis=ZRE152
```

Responses include total, limit, offset, elapsed_ms, catalogue qualifications and original PDF URLs. There are nine associations in the tested filter, from physical PDF page 96. Different engine/application rows remain separate; the same part number can appear more than once. Unknown chassis values return zero listings and do not imply incompatibility.

The linked retrieval path skips both broad lexical retrieval and Chroma search when it has matching evidence. The LLM sees a bounded set of normalized application rows, not the entire PDF. Every row explicitly carries the catalogue-candidate limitation. A two-car swap question must still establish the actual relationship and vehicle conditions; shared part names or a broad model match cannot approve a swap.

The live part-card explanation initially failed numeric checks when the model expanded a production code incorrectly. The generated text was withheld. The app now falls back to checked catalogue wording for these structured links and runs that wording through the same citation validator. The UI discloses that fallback. Quote/number/identifier membership checks still do not prove semantic entailment; review the original table.

## Frontend research

- [Autostore](https://www.autostore.pk/): vehicle/brand browsing and category navigation.
- [SehgalMotors spare parts](https://sehgalmotors.pk/collections/auto-spare-parts): product/category presentation and filterable listings.
- [Partfinder](https://www.thepartfinder.pk/): make/model/year/part-first selection.
- [PartSouq Toyota catalogues](https://partsouq.com/en/catalog/genuine/locate?c=Toyota): vehicle/part catalogue organization.
- [AUTODOC car parts](https://www.autodoc.co.uk/car-parts): vehicle finder and part-category organization.

These influenced the original frontend structure. No retailer catalogue was scraped into the fitment database, and no retailer availability/price was invented.

## Observed verification

- Source page 96 was rendered and visually checked against extracted cells. Selected front/rear, shock, mounting and protection entries agreed with the table. This is a spot check, not a full manual audit of every imported association.
- Cached import performed no PDF extraction. Twenty indexed Corolla lookups measured median 6.17 ms and maximum 6.68 ms locally; this excludes HTTP/browser and LLM latency.
- API returned nine filtered Corolla records, zero for an unknown chassis, and HTTP 200 application/pdf for the fingerprinted source.
- Browser tested at 1280x900 and 390x844: vehicle filter, nine cards, original source URLs, part-to-question action, explicit no-result message, saved-history access, light/dark layout, no horizontal overflow at the mobile test size. Temporary viewport overrides were reset.
- A live generated explanation failed guardrails; retesting displayed the checked catalogue fallback with source S1. This limitation is retained rather than counted as a successful generated answer.
- Screenshots: `storefront-desktop.jpg`, `storefront-parts.jpg`, `storefront-mobile.jpg` in docs/.
