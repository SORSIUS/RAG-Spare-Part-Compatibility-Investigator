import tempfile
import unittest
from pathlib import Path

from app.services.compatibility_service import CompatibilityService
from app.services.evidence_retriever import EvidenceRetriever
from app.services.ingestion_service import IngestionService
from scripts.create_sample_pdf import create_sample_pdf


RULES = [
    {"field": "voltage", "label": "Supply voltage (V DC)", "operator": "exact"},
    {"field": "width", "label": "Frame width (mm)", "operator": "exact"},
    {"field": "connector", "label": "Connector", "operator": "exact"},
    {"field": "airflow", "label": "Airflow (CFM)", "operator": "minimum"},
]


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        create_sample_pdf(self.directory / "manual.pdf")
        self.report = IngestionService().ingest_directory(self.directory)
        self.retriever = EvidenceRetriever(self.report["chunks"])
        self.service = CompatibilityService(self.retriever, RULES)

    def test_real_text_pdf_produces_four_source_pages(self):
        self.assertEqual(self.report["errors"], [])
        self.assertEqual([chunk["page_number"] for chunk in self.report["chunks"]], [1, 2, 3, 4])

    def test_three_verdicts_from_actual_pdf(self):
        self.assertEqual([self.service.compare("FAN-12", part)["verdict"] for part in ["ALT-A", "ALT-B", "ALT-C"]], ["match", "conflict", "unknown"])

    def test_conflict_cites_different_pdf_pages(self):
        check = self.service.compare("FAN-12", "ALT-B")["checks"][0]
        self.assertEqual(check["requirements"][0]["page_number"], 1)
        self.assertEqual(check["candidate_evidence"][0]["page_number"], 3)
        self.assertIn("24", check["candidate_evidence"][0]["quote"])

    def test_quotes_are_present_in_their_cited_chunks(self):
        chunks = {chunk["chunk_id"]: chunk for chunk in self.report["chunks"]}
        for check in self.service.compare("FAN-12", "ALT-A")["checks"]:
            for evidence in check["requirements"] + check["candidate_evidence"]:
                self.assertIn(evidence["quote"], chunks[evidence["chunk_id"]]["text"])

    def test_no_candidate_or_original_is_unknown(self):
        self.assertEqual(self.service.compare("FAN-12", "MISSING")["verdict"], "unknown")
        self.assertEqual(self.service.compare("MISSING", "ALT-A")["verdict"], "unknown")

    def test_search_does_not_match_partial_part_identifiers(self):
        self.assertEqual(self.retriever.search("ALT-AB"), [])
        self.assertTrue(self.retriever.search("ALT-B voltage"))
        self.assertEqual(self.retriever.part_evidence("ALT"), [])

    def test_conflicting_documents_are_not_silently_resolved(self):
        (self.directory / "conflicting.txt").write_text("Part number: ALT-A\nSupply voltage (V DC): 48\n")
        report = IngestionService().ingest_directory(self.directory)
        service = CompatibilityService(EvidenceRetriever(report["chunks"]), RULES)
        self.assertEqual(service.compare("FAN-12", "ALT-A")["checks"][0]["status"], "unknown")

    def test_numeric_unit_mismatch_stays_unknown(self):
        (self.directory / "numbers.txt").write_text("Part number: OTHER\nAirflow (CFM): 100 m3/h\n")
        report = IngestionService().ingest_directory(self.directory)
        service = CompatibilityService(EvidenceRetriever(report["chunks"]), RULES)
        self.assertEqual(service.compare("FAN-12", "OTHER")["checks"][3]["status"], "unknown")

    def test_multiple_parts_in_one_chunk_do_not_mix_values(self):
        chunks = [{"text": "Part number: ONE\nConnector: A\nPart number: TWO\nConnector: B", "source": "records.txt", "page_number": 1, "chunk_id": "test"}]
        service = CompatibilityService(EvidenceRetriever(chunks), [{"field": "connector", "label": "Connector", "operator": "exact"}])
        self.assertEqual(service.compare("ONE", "TWO")["verdict"], "conflict")


if __name__ == "__main__":
    unittest.main()
