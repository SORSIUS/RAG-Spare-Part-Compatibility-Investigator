"""Column-aware adapter for KYB's 12-column MEA accessories catalogue.

Only application tables are accepted. Index pages and ambiguous continuations
are skipped. OEM numbers are a cell group, never invented one-to-one mappings.
"""
import hashlib
import re

SCHEMA = "kyb-mea-accessories-v3"
SOURCE_URL = "https://kybme.com/new/wp-content/uploads/2025/11/accessory-catalogue-KYB.pdf"
SOURCE_SHA = "0315864b4689f878207671bc29ea3a83d01768130d3b7b987c2a813c7abe16be"
COLUMNS = [(2, "front", "shock_absorber", None), (4, "front", "protection_kit", 3),
           (6, "front", "mounting_kit", 5), (7, "rear", "shock_absorber", None),
           (9, "rear", "protection_kit", 8), (11, "rear", "mounting_kit", 10)]
MAKES = {"TOYOTA", "HONDA", "SUZUKI", "NISSAN", "MAZDA", "MITSUBISHI", "DAIHATSU", "SUBARU", "LEXUS", "ISUZU", "HYUNDAI", "KIA", "FORD", "CHEVROLET"}


def family(label):
    for name in ("COROLLA CROSS", "COROLLA VERSO", "COROLLA", "CITY", "CIVIC", "SWIFT", "YARIS", "VIOS", "HILUX", "CAMRY", "PRIUS", "VITZ", "ALTO", "WAGON R", "JAZZ", "FIT", "CR-V", "CRV"):
        if re.match(re.escape(name) + r"(?:\b|/)", label):
            return name.title()
    return label.split(" / ")[0].strip().title()


def period_years(value):
    match = re.fullmatch(r"(\d{2})(?:/\d{2})?-(On|\d{2}(?:/\d{2})?)", value, re.I)
    if not match:
        return None
    def year(v):
        y = int(v[:2])
        return 2000 + y if y < 50 else 1900 + y
    return year(match[1]), None if match[2].lower() == "on" else year(match[2])


def parse_rows(rows, make, page, source, fingerprint):
    model = None
    records = []
    for row_number, row in enumerate(rows):
        if len(row) != 12:
            continue
        cells = [" ".join((cell or "").split()) for cell in row]
        years = period_years(cells[0])
        if years is None:
            # Headings are split across cells by the table grid. Join fragments
            # without assuming the first cell is a complete vehicle name.
            heading = "".join(cells).strip()
            compact = re.sub(r"(.)\1+", r"\1", heading.lower())
            if any(label in compact for label in ("year", "aplication", "y/m")):
                model = None
                continue
            if re.match(r"[A-Z]", cells[0]) and not re.search(r"year|yy/mm|application", heading, re.I):
                model = heading
            continue
        if not model or not cells[1]:
            continue
        raw = {"make": make, "model": model, "period": cells[0], "application": cells[1], "columns": cells[2:]}
        for column, axle, component, oem_column in COLUMNS:
            for part in cells[column].split():
                if not re.fullmatch(r"[A-Z0-9][A-Z0-9-]{2,19}", part) or not re.search(r"\d", part):
                    continue
                identity = f"{fingerprint}:{page}:{row_number}:{column}:{part}"
                records.append({"id": hashlib.sha256(identity.encode()).hexdigest(), "make": make.title(), "model": family(model), "vehicle_label": model,
                                "start_year": years[0], "end_year": years[1], "period": cells[0], "application": cells[1], "category": "suspension", "component": component,
                                "axle": axle, "brand": "KYB", "part_number": part, "oem_group": cells[oem_column].split() if oem_column else [],
                                "source": source, "source_sha256": fingerprint, "page_number": page, "raw_row": raw})
    return records


def extract_catalogue(path, fingerprint, progress=lambda page: None):
    import pdfplumber
    records, inspected = [], 0
    with pdfplumber.open(path) as pdf:
        for index, page in enumerate(pdf.pages):
            page = page.dedupe_chars()
            header = page.crop((0, 0, page.width, 70)).extract_text() or ""
            make = next((name for name in MAKES if re.search(r"\b" + name + r"\b", header)), None)
            if not make or "Accessories list" not in header:
                continue
            for table in page.extract_tables():
                records.extend(parse_rows(table, make, index + 1, path.name, fingerprint))
            inspected += 1
            progress(index + 1)
            page.close()
    return records, inspected
