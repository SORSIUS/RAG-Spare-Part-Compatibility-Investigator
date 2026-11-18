import re
from decimal import Decimal, InvalidOperation

from app.services.evidence_retriever import EvidenceRetriever


def normalize(value: str) -> str:
    return " ".join(value.casefold().split())


class CompatibilityService:
    def __init__(self, retriever: EvidenceRetriever, rules: list[dict]):
        if not rules or len({rule["field"] for rule in rules}) != len(rules):
            raise ValueError("Provide nonempty comparison rules with unique fields.")
        for rule in rules:
            if rule.get("operator") not in {"exact", "minimum"} or not rule.get("label"):
                raise ValueError("Each rule needs a label and an exact or minimum operator.")
        self.retriever = retriever
        self.rules = rules

    def observations(self, evidence: list[dict], label: str) -> list[dict]:
        observations = []
        seen = set()
        pattern = re.compile(r"^" + re.escape(label) + r":[ \t]*([^\r\n]+)", re.MULTILINE | re.IGNORECASE)
        for hit in evidence:
            for match in pattern.finditer(hit["record_text"]):
                value = match.group(1).strip()
                if normalize(value) in {"unknown", "not documented", "unspecified", "n/a"}:
                    continue
                identity = (hit["source"], hit["page_number"], match.group(0))
                if identity not in seen:
                    seen.add(identity)
                    observations.append({"value": value, "source": hit["source"], "page_number": hit["page_number"], "chunk_id": hit["chunk_id"], "quote": match.group(0)})
        return observations

    def compare(self, original: str, candidate: str) -> dict:
        original_evidence = self.retriever.part_evidence(original)
        candidate_evidence = self.retriever.part_evidence(candidate)
        checks = []
        for rule in self.rules:
            requirements = self.observations(original_evidence, rule["label"])
            alternatives = self.observations(candidate_evidence, rule["label"])
            required_values = {normalize(hit["value"]) for hit in requirements}
            actual_values = {normalize(hit["value"]) for hit in alternatives}
            status = "unknown"
            reason = "Missing documented requirement or candidate value."
            if len(required_values) > 1 or len(actual_values) > 1:
                reason = "Conflicting source values; a person must resolve the document revision or scope."
            elif required_values and actual_values:
                required = next(iter(required_values))
                actual = next(iter(actual_values))
                if rule["operator"] == "exact":
                    status = "match" if actual == required else "conflict"
                    reason = "Exact agreement required, including the unit named in the label."
                else:
                    try:
                        required_number, actual_number = Decimal(required), Decimal(actual)
                        if not required_number.is_finite() or not actual_number.is_finite():
                            raise InvalidOperation
                        status = "match" if actual_number >= required_number else "conflict"
                        reason = "Candidate must meet or exceed the documented minimum."
                    except InvalidOperation:
                        reason = "Expected numeric values in the label's unit; no unit conversion was inferred."
            checks.append({**rule, "status": status, "reason": reason, "requirements": requirements, "candidate_evidence": alternatives})

        statuses = {check["status"] for check in checks}
        verdict = "conflict" if "conflict" in statuses else "unknown" if "unknown" in statuses else "match"
        return {
            "original": original,
            "candidate": candidate,
            "verdict": verdict,
            "checks": checks,
            "explanation": {
                "match": "All configured fields match the recorded requirements. This is not installation approval.",
                "conflict": "At least one documented field conflicts with the requirements.",
                "unknown": "The documents do not establish agreement for every configured field.",
            }[verdict],
            "limits": "Explicit labelled records only. No automatic vehicle-fitment inference, revision selection, or safety certification.",
        }
