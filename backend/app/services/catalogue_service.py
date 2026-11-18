import re

from app.services.denso_parser import normalize_identifier, PART_PATTERN


class CatalogueService:
    def __init__(self, catalogue: dict):
        self.catalogue = catalogue

    def lookup(self, part: str, brand: str | None = None) -> dict:
        identifier = normalize_identifier(part)
        references = [record for record in self.catalogue["cross_references"] if (normalize_identifier(record["external_part"]) == identifier or record["denso_part"] == identifier) and (brand is None or normalize_identifier(record["brand"]) == normalize_identifier(brand))]
        denso_parts = {identifier} if re.fullmatch(PART_PATTERN, identifier) else {record["denso_part"] for record in references}
        external_brands = {normalize_identifier(record["brand"]) for record in references}
        ambiguous = not re.fullmatch(PART_PATTERN, identifier) and brand is None and len(external_brands) > 1
        return {
            "query": identifier,
            "brand": brand,
            "status": "ambiguous_brand" if ambiguous else "found" if references or any(record["part_number"] in denso_parts for record in self.catalogue["dimensions"]) or any(set(record["parts"]) & denso_parts for record in self.catalogue["applications"]) else "not_found",
            "denso_parts": sorted(denso_parts),
            "cross_references": references,
            "dimensions": [record for record in self.catalogue["dimensions"] if record["part_number"] in denso_parts],
            "applications": [record for record in self.catalogue["applications"] if set(record["parts"]) & denso_parts],
            "fitment_status": "unknown; confirm the exact vehicle, production date, region, and all qualifiers",
        }

    def search(self, query: str, limit: int = 8) -> list[dict]:
        if limit < 1 or not query.strip():
            raise ValueError("Provide a nonempty query and a positive limit.")
        terms = set(re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", query.lower()))
        matches = []
        for record in self.catalogue["applications"]:
            text = " ".join([record["make"], record["vehicle"], record["qualifiers"], record["production_range"], *record["parts"]])
            words = set(re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", text.lower()))
            if terms and terms <= words:
                matches.append(record)
        return matches[:limit]

    def compare(self, original: str, candidate: str, brand: str | None = None) -> dict:
        original_lookup = self.lookup(original, brand)
        candidate_id = normalize_identifier(candidate)
        if not re.fullmatch(PART_PATTERN, candidate_id):
            raise ValueError("Choose an explicit DENSO candidate number, such as DCF357P.")
        original_id = normalize_identifier(original)
        direct_records = [record for record in original_lookup["cross_references"] if normalize_identifier(record["external_part"]) == original_id and record["denso_part"] == candidate_id]
        if original_lookup["status"] == "ambiguous_brand":
            direct_records = []
        original_dimensions = [record for record in self.catalogue["dimensions"] if record["part_number"] == original_id]
        candidate_dimensions = [record for record in self.catalogue["dimensions"] if record["part_number"] == candidate_id]
        checks = []
        for axis in ["length", "width", "height"]:
            before = {record["dimensions_mm"][axis] for record in original_dimensions}
            after = {record["dimensions_mm"][axis] for record in candidate_dimensions}
            status = "unknown"
            if len(before) == len(after) == 1:
                status = "match" if before == after else "conflict"
            checks.append({"field": axis + "_mm", "status": status, "original_values": sorted(before), "candidate_values": sorted(after), "evidence": [record["evidence"] for record in original_dimensions + candidate_dimensions]})
        verdict = "conflict" if any(check["status"] == "conflict" for check in checks) else "documented_reference" if direct_records else "unknown"
        return {
            "original": original_id,
            "candidate": candidate_id,
            "status": verdict,
            "cross_reference_status": "documented" if direct_records else "unknown",
            "cross_reference_evidence": [record["evidence"] for record in direct_records],
            "dimension_checks": checks,
            "vehicle_fitment": "unknown",
            "explanation": {
                "conflict": "At least one documented dimension differs. Do not treat these as an established dimensional match.",
                "documented_reference": "The catalogue directly links this brand/part number to the DENSO candidate. Vehicle suitability and any missing specifications still need verification.",
                "unknown": "The catalogue checks do not establish interchangeability. Equal dimensions, absent rows, or shared vehicle mentions are insufficient proof.",
            }[verdict],
        }
