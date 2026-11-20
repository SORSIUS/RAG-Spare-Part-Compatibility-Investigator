import tempfile
import unittest
from pathlib import Path

from app.repositories.fitments import FitmentRepository
from app.repositories.replacements import ReplacementRepository
from app.services.kyb_fitment_parser import parse_rows, SCHEMA


class ReplacementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runtime = Path(self.temp.name)
        self.fitments = FitmentRepository(self.runtime)
        self.rows = [
            ["COROLLA"] + [""] * 11,
            ["07/10-On", "NZE151,ZRE151,ZRE152 1.8 L EFI", "NST5387R NST5387L",
             "4833112220 4815742030", "SB2015 SB5176", "4860912500", "SM7210",
             "349035", "", "", "", ""]]
        self.records = parse_rows(self.rows, "TOYOTA", 96, "catalogue.pdf", "a" * 64)
        self.fitments.replace_source("a" * 64, "catalogue.pdf", SCHEMA, "https://example.test", 1, self.records)
        self.repo = ReplacementRepository(self.runtime)

    def test_direct_reference_preserves_application_and_evidence(self):
        result = self.repo.search("toyota", "48609-12500")
        self.assertEqual(result["total"], 1)
        record = result["records"][0]
        self.assertEqual(record["part_number"], "SM7210")
        self.assertEqual(record["period"], "07/10-On")
        self.assertIn("ZRE152", record["application"])
        self.assertTrue(record["pdf_url"].endswith("#page=96"))

    def test_groups_reverse_and_wrong_brand_are_not_inferred(self):
        for brand, number in [("Toyota", "4833112220"), ("Toyota", "SM7210"), ("Honda", "4860912500")]:
            self.assertEqual(self.repo.search(brand, number)["status"], "not_documented")

    def test_reimport_invalidates_cached_links_and_unknown_adapters_cannot_publish(self):
        self.assertEqual(self.repo.search("Toyota", "4860912500")["total"], 1)
        self.fitments.replace_source("a" * 64, "catalogue.pdf", "unreviewed", "", 1, self.records)
        self.assertEqual(self.repo.search("Toyota", "4860912500")["total"], 0)

    def test_question_fast_path_requires_explicit_brand_and_original_number(self):
        sources = self.repo.question_sources("Replacement for Toyota 48609-12500?", 8)
        self.assertEqual(len(sources), 1)
        self.assertIn("SM7210", sources[0]["content"])
        self.assertEqual(self.repo.question_sources("Which suspension for Corolla?", 8), [])

    def test_checked_fallback_keeps_original_number_and_validates_citations(self):
        from app.services.fitment_answer import fitment_answer
        from app.services.answer_service import validate_citations
        sources = [{**s, "id": "S1"} for s in self.repo.question_sources("Toyota 4860912500 replacement?", 1)]
        answer = fitment_answer(sources)
        self.assertIn("4860912500", answer.claims[0].text)
        validate_citations(answer, sources)


if __name__ == "__main__":
    unittest.main()
