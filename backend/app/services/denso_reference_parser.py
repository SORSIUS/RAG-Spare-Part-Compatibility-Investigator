"""Column-bounded OEM -> standard DENSO references for one reviewed revision.

Skip annotated, wrapped, missing or ambiguous cells rather than guessing. The
Iridium upgrade columns are intentionally not interpreted as direct substitutes.
"""
import hashlib
import re

SOURCE_SHA = "212028e9de007768f021c7691013eaf1e3b40b1fa270ab543e7e4b5f567d3891"
SOURCE_URL = "https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_6_others_2025.pdf"
SCHEMA = "denso-oem-standard-2025-v2"
CAUTION = "Published spark-plug cross-reference only. Check the vehicle application table, engine, production range and market before choosing a plug; this chart alone does not establish vehicle fitment."


def cell_lines(page, bounds):
    lines = {}
    left, top_bound, right, bottom = bounds
    for word in page.extract_words(x_tolerance=1, y_tolerance=2):
        if word["top"] < top_bound or word["bottom"] > bottom or word["x1"] <= left or word["x0"] >= right:
            continue
        top = round(word["top"])
        key = next((y for y in lines if abs(y - top) <= 2), top)
        lines.setdefault(key, []).append(word["text"] if word["x0"] >= left and word["x1"] <= right else "[AMBIGUOUS]")
    return {y: " ".join(words).strip() for y, words in lines.items()}


def parse_cells(originals, alternatives, source, page_number):
    records, brand = [], None
    for y, original in sorted(originals.items()):
        paired = [text for top, text in alternatives.items() if abs(top - y) <= 2]
        if len(paired) != 1:
            continue
        alternative = paired[0]
        if alternative == "DENSO":
            brand = original.title() if re.fullmatch(r"[A-Z][A-Z &.-]{1,30}", original) else None
            continue
        if not brand or not re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", original) or not any(c.isdigit() for c in original):
            continue
        if not re.fullmatch(r"[A-Z][A-Z0-9]*\d[A-Z0-9]*(?:-[A-Z0-9]+)*", alternative):
            continue
        identifier = hashlib.sha256(f"{SOURCE_SHA}:{page_number}:{y}:{brand}:{original}:{alternative}".encode()).hexdigest()
        records.append({"id": identifier, "original_brand": brand, "original_part": re.sub(r"[^A-Z0-9]", "", original),
                        "original_printed": original, "brand": "DENSO", "part_number": alternative,
                        "component": "spark_plug", "axle": "", "make": brand, "model": "Vehicle application must be checked",
                        "vehicle_label": "Vehicle application must be checked", "period": "Not specified in this cross-reference",
                        "application": CAUTION, "oem_group": [original], "source": source,
                        "source_sha256": SOURCE_SHA, "page_number": page_number,
                        "raw_row": {"original_cell": original, "standard_denso_cell": alternative},
                        "relationship": "published_oem_cross_reference", "reference_only": True})
    return records


def extract_references(path, source):
    import pdfplumber
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError("Unreviewed DENSO reference revision.")
    records = []
    with pdfplumber.open(path) as pdf:
        for index in range(17, 30):
            page = pdf.pages[index]
            for block in range(3):
                shift = block * 173.74
                originals = cell_lines(page, (74 + shift, 65, 143 + shift, 859))
                alternatives = cell_lines(page, (143 + shift, 65, 187 + shift, 859))
                records.extend(parse_cells(originals, alternatives, source, index + 1))
    return records
