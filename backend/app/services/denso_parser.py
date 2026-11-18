import hashlib
import re
from pathlib import Path

from pypdf import PdfReader


PART_PATTERN = r"DCF\d{3}[PKA]"
DATE_PATTERN = r"\d{2}/\d{2}-(?:\d{2}/\d{2})?"


def normalize_identifier(value: str) -> str:
    return " ".join(value.upper().split())


class DensoParser:
    version = 3

    def __init__(self):
        self.warnings = []

    def evidence(self, source: str, page_number: int, section: str, quote: str) -> dict:
        return {"source": source, "page_number": page_number, "section": section, "quote": quote.strip()}

    def dimensions(self, text: str, source: str, page_number: int) -> list[dict]:
        records = []
        pending = []
        for line in text.splitlines():
            codes = list(re.finditer(r"\b" + PART_PATTERN + r"\b", line))
            if codes:
                pending = [match.group() for match in codes]
                continue
            values = list(re.finditer(r"Length:\s*([\d.,]+)\s*mm\s+Width:\s*([\d.,]+)\s*mm\s+Height:\s*([\d.,]+)\s*mm", line))
            if values:
                if len(values) != len(pending):
                    self.warnings.append(f"Page {page_number}: dimensions and part counts disagree; row skipped.")
                else:
                    for part, match in zip(pending, values):
                        records.append({"part_number": part, "dimensions_mm": dict(zip(["length", "width", "height"], [float(value.replace(",", ".")) for value in match.groups()])), "evidence": self.evidence(source, page_number, "photo_guide", part + "\n" + match.group())})
                pending = []
        return records

    def cross_references(self, text: str, source: str, page_number: int) -> list[dict]:
        lines = text.splitlines()
        header = next((line for line in lines if "DENSO" in line and not re.search(PART_PATTERN, line) and re.search(r"\S\s{2,}DENSO\b", line)), None)
        if header is None:
            self.warnings.append(f"Page {page_number}: cross-reference header not found; page skipped.")
            return []
        headings = list(re.finditer(r"(\S(?:.*?\S)?)\s{2,}DENSO\b", header))
        if not 1 <= len(headings) <= 4:
            self.warnings.append(f"Page {page_number}: column boundaries ambiguous; page skipped.")
            return []
        starts = [0] + [(headings[position - 1].end() + headings[position].start()) // 2 for position in range(1, len(headings))]
        brands = [None] * len(headings)
        records = []
        for line in lines:
            for column, start in enumerate(starts):
                cell = line[start:starts[column + 1] if column + 1 < len(starts) else None].strip()
                brand = re.fullmatch(r"(.+?)\s{2,}DENSO", cell)
                if brand:
                    brands[column] = brand.group(1).strip()
                    continue
                pair = re.fullmatch(r"(.+?)\s{2,}(" + PART_PATTERN + r")", cell)
                if pair:
                    if brands[column] is None:
                        self.warnings.append(f"Page {page_number}: cross-reference without brand; skipped.")
                        continue
                    records.append({"brand": brands[column], "external_part": pair.group(1).strip(), "denso_part": pair.group(2), "evidence": {**self.evidence(source, page_number, "cross_reference", cell), "brand_heading": brands[column]}})
                elif re.search(r"\b" + PART_PATTERN + r"\b", cell):
                    self.warnings.append(f"Page {page_number}: unparsed cross-reference cell; skipped.")
        return records

    def applications(self, text: str, source: str, page_number: int) -> list[dict]:
        records = []
        make = None
        pending = None
        for line in text.splitlines():
            stripped = line.strip()
            possible_make = re.sub(r"\s+continued$", "", stripped)
            indentation = len(line) - len(line.lstrip())
            if possible_make and indentation < 5 and possible_make.isupper() and all(character.isalpha() or character in " &./-" for character in possible_make):
                make = possible_make
                pending = None
                continue
            date = re.search(DATE_PATTERN, line)
            parts = re.findall(r"\b" + PART_PATTERN + r"\b", line)
            if date and parts:
                if not make:
                    self.warnings.append(f"Page {page_number}: application without a make heading; row skipped.")
                    pending = None
                    continue
                before_date = re.split(r"\s{3,}", line[:date.start()].strip())
                vehicle = before_date[0]
                qualifiers = " | ".join(before_date[1:])
                pending = {"make": make, "vehicle": vehicle, "qualifiers": qualifiers, "production_range": date.group(), "parts": parts, "fitment_verified": False, "evidence": self.evidence(source, page_number, "application", stripped)}
                records.append(pending)
            elif pending and stripped and not stripped.isdecimal() and not re.search(PART_PATTERN, stripped):
                if indentation < 5 and stripped.startswith("("):
                    pending["vehicle"] += " " + stripped
                    pending["evidence"]["quote"] += "\n" + stripped
                elif indentation > 20:
                    pending["qualifiers"] += (" | " if pending["qualifiers"] else "") + stripped
                    pending["evidence"]["quote"] += "\n" + stripped
        return records

    def parse(self, pdf_path: str | Path) -> dict:
        path = Path(pdf_path)
        if not path.is_file():
            raise FileNotFoundError(f"Catalogue not found: {path}")
        self.warnings = []
        report = {"parser": "denso_cabin_filters", "parser_version": self.version, "source": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "dimensions": [], "cross_references": [], "applications": []}
        with path.open("rb") as stream:
            reader = PdfReader(stream)
            report["page_count"] = len(reader.pages)
            for page_number, page in enumerate(reader.pages, start=1):
                text = page.extract_text(extraction_mode="layout")
                if "Application Tables" in text and "Cabin Air Filter" in text:
                    report["applications"].extend(self.applications(text, path.name, page_number))
                elif "Cross Reference Chart" in text and "Cabin Air Filter" in text:
                    report["cross_references"].extend(self.cross_references(text, path.name, page_number))
                elif "Photo Guide" in text and "Cabin Air Filter" in text:
                    report["dimensions"].extend(self.dimensions(text, path.name, page_number))
        report["warnings"] = sorted(set(self.warnings))
        report["limits"] = "Catalogue-specific extraction; not a complete fitment database. Application qualifiers are preserved as text, not interpreted. No installation approval."
        return report
