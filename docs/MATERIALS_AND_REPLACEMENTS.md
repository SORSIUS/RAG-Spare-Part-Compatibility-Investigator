# Materials, vehicle coverage and replacement evidence

## What to collect next

| Material | Where to get it | How it helps |
| --- | --- | --- |
| Toyota owner manuals | [Toyota Indus Pakistan](https://toyota-indus.com/owner-manual/) | Controls, maintenance and model-specific operation. The portal requests model/year, frame details and phone verification. These are not replacement-parts cross-reference catalogues. |
| Toyota parts catalogue and repair information | [Toyota Tech subscription plans](https://www.toyota-tech.eu/subscription-plans) | Original numbers, diagrams, repair procedures and application details. Access depends on the plan; check market coverage. There is no verified free universal Toyota PDF in this project. |
| DENSO spark-plug catalogues | [Official regional downloads](https://am.denso.com/plug-global/model-search/catalog/) | Download the regional application sections and product information. Asia 2025 and product information are already indexed here; other regions broaden evidence. |
| OEM spark-plug references | [DENSO vehicle-manufacturer number search](https://am.denso.com/search/plug-global/genuine_parts/list.cgi) | Original-number references. DENSO explicitly requires checking the vehicle application table; a cross-reference alone is not a vehicle-fit guarantee. |
| Suspension catalogues | [KYB MEA catalogue portal](https://kybme.com/our-catalogues/) | Vehicle applications, positions, mounting/protection kits and OEM cells. The reviewed MEA accessories PDF is already imported. The portal timed out during this research, so download availability should be checked manually. |

For broad coverage, collect multiple makes and regional editions rather than assuming one country's Corolla data applies everywhere. Keep the original filename, publisher, edition/year, download URL and market. Prefer searchable PDFs with application tables and original/aftermarket number columns. Large scans may require OCR. Upload accepts files up to 25 MB; use official regional sections when available.

## What your new materials do

- Body parts/functions article: component names, locations and purposes.
- Engine parts/functions article: engine terminology and component explanations.
- Malla Reddy Automobile Engineering course PDF: systems and introductory engineering explanations.
- MASTERPARTS fourth-edition catalogue: product-group overview. Its introduction says the full part-number range cannot be listed; do not treat every pictured part as a replacement reference.

These four files are user-supplied; their original download URLs were not provided. All four were registered and indexed without rebuilding older documents. The registry sanitizes some filename characters, so the displayed names may contain underscores.

## Two linked retrieval paths

1. Vehicle → application/production conditions → component/axle → manufacturer part → PDF row.
2. Original brand + original number → explicitly aligned replacement cell → application/production conditions → PDF row.

The first path has 3,814 KYB application associations across 14 makes. The second currently has 345 application references, covering 144 distinct original-brand/number combinations; 168 references concern Toyota applications. Multiple vehicle rows can describe the same replacement pair, so these are not 345 unique replacement products.

The replacement index lives in the existing local `fitments.sqlite3` database (`replacement_links` and `replacement_builds` tables). A composite brand/original-number index avoids a full document search. Sources are rebuilt only after their import changes. Chroma still handles ordinary document questions. Uploading a new PDF indexes its text; it does not automatically create trusted structured replacement edges.

## Try it

In the frontend, expand **Have an original part number?** and enter Toyota / 48609-12500. Expect KYB SM7210 with five printed applications, including Corolla, Blade and Prius listings; each has its own conditions and PDF page.

```text
GET /api/replacements?brand=Toyota&part=48609-12500
```

The same evidence is accessible through the existing read-only MCP `search_catalogue` tool:

```json
{"query":"Replacement for Toyota 48609-12500?","limit":6}
```

An unknown number returns `not_documented`, which means the imported evidence does not establish a link. It does not mean the parts are incompatible.

No reverse links, transitive links, or Cartesian pairings of grouped cells are generated. A shared part number does not establish that two complete suspension assemblies can be swapped. Exact chassis, engine, axle, production month, steering side and market still matter. For installation-critical systems, use the correct repair procedure and qualified inspection.
