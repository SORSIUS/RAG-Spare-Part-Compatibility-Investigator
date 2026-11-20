"""Reviewed Toyota Taiwan application rows, physical pages 99–100, Asia 2025."""
import hashlib
import re

from app.services.kyb_fitment_parser import family

SOURCE_SHA = "9743fa42b26b7ecae877cf163534422766b7909fe7961993f61386715b8cba25"
SOURCE_URL = "https://am.denso.com/plug-global/wp-content/uploads/sites/23/catalog_3_asia_2025.pdf"
SCHEMA = "denso-toyota-taiwan-2025-v4"


def model_family(label):
    label = re.sub(r"^NEW\s+", "", label).replace("RAV 4", "RAV4")
    for name in ("ALPHARD", "AURIS", "C-HR", "LAND CRUISE PRADO", "PREVIA", "RAV4", "SIENNA", "SIENTA", "TOWNACE", "WISH", "ZACE"):
        if re.match(re.escape(name) + r"\b", label):
            return name.title()
    return family(label)


def parse_rows(rows, page, source):
    records, model, toyota = [], None, False
    for index, row in enumerate(rows):
        label, cc, chassis, engine, period, part, original = row
        if label == "TOYOTA":
            toyota, model = True, None
            continue
        if label in {"VOLVO", "VOLKSWAGEN", "TOBE", "YAMAHA", "SUBARU", "SUZUKI"}:
            toyota, model = False, None
        if not toyota:
            continue
        if "[AMBIGUOUS]" in label:
            model = None
            continue
        if label:
            model = label
        dates = re.fullmatch(r"((?:19|20)\d{2})(?:\.\d{1,2})?-((?:19|20)\d{2}(?:\.\d{1,2})?)?", period)
        if not model or not dates or not re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", engine) or not any(c.isalpha() for c in engine) or not any(c.isdigit() for c in engine):
            continue
        if not re.fullmatch(r"[A-Z]+\d[A-Z0-9]*(?:-[A-Z0-9]+)*", part) or not re.fullmatch(r"\d{10}", original):
            continue
        identity = hashlib.sha256(f"{SOURCE_SHA}:{page}:{index}:{part}:{model}".encode()).hexdigest()
        application = f"Market: Taiwan; engine {engine}; " + (f"{cc} cc; " if cc.isdigit() else "") + (f"vehicle code {chassis}; " if chassis and chassis != "-" else "") + f"model {model}"
        records.append({"id": identity, "make": "Toyota", "model": model_family(model),
                        "vehicle_label": model, "start_year": int(dates[1]), "end_year": int(dates[2][:4]) if dates[2] else None,
                        "period": period, "application": application, "category": "ignition", "component": "spark_plug",
                        "axle": "", "brand": "DENSO", "part_number": part, "engine": engine,
                        "engine_cc": int(cc) if cc.isdigit() else None, "market": "Taiwan", "oem_group": [original],
                        "source": source, "source_sha256": SOURCE_SHA, "page_number": page,
                        "raw_row": {"columns": row}})
    return records


def extract_applications(path):
    import pdfplumber
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError("Unreviewed DENSO application revision.")
    records = []
    bounds = [(35, 147), (147, 180), (180, 208), (208, 234), (234, 281), (281, 338), (338, 388)]
    with pdfplumber.open(path) as pdf:
        for index in (98, 99):
            page = pdf.pages[index]
            shift = 2.8 if index == 99 else 0
            lines = {}
            for word in page.extract_words(x_tolerance=1, y_tolerance=2):
                if word["top"] < 40 or word["top"] > 815:
                    continue
                y = round(word["top"])
                key = next((v for v in lines if abs(y-v) <= 2), y)
                cells = lines.setdefault(key, [[] for _ in bounds])
                for col, (left, right) in enumerate(bounds):
                    left, right = left + shift, right + shift
                    if left <= word["x0"] < right:
                        cells[col].append(word["text"] if word["x1"] <= right else "[AMBIGUOUS]")
                        break
            records.extend(parse_rows([[" ".join(c) for c in cells] for _, cells in sorted(lines.items())], index+1, path.name))
    return records
