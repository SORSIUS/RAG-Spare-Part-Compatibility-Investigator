import tempfile
import unittest
from pathlib import Path

from app.repositories.replacements import ReplacementRepository
from app.services.denso_reference_parser import parse_cells, cell_lines, SOURCE_SHA, SCHEMA
from app.services.fitment_answer import fitment_answer
from app.services.answer_service import validate_citations, CitationError


class DensoReferenceTests(unittest.TestCase):
    def records(self):
        return parse_cells({68: "TOYOTA", 82: "90919-01095"}, {68: "DENSO", 82: "W16ETR-S"}, "reference.pdf", 29)

    def test_headers_are_local_and_annotated_or_missing_cells_are_skipped(self):
        self.assertEqual(len(self.records()), 1)
        self.assertEqual(parse_cells({82: "90919-01095"}, {82: "W16ETR-S"}, "r.pdf", 29), [])
        for original, alternative in [("90919-01095(BPR5EK)", "W16ETR-S"), ("90919-01095", "-"), ("90919-01095", "W16ETR-S(*1)")]:
            self.assertEqual(parse_cells({68: "TOYOTA", 82: original}, {68: "DENSO", 82: alternative}, "r.pdf", 29), [])

    def test_clipped_words_are_never_accepted_as_identifiers(self):
        class Page:
            def extract_words(self, **kwargs):
                return [{"text": "90919-01095", "x0": 75, "x1": 145, "top": 82, "bottom": 89}]
        self.assertIn("[AMBIGUOUS]", cell_lines(Page(), (74, 65, 143, 859))[82])

    def test_import_is_idempotent_and_lookup_and_checked_answer_keep_limits(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = ReplacementRepository(Path(folder))
            for _ in range(2):
                repo.replace_external_source(SOURCE_SHA, SCHEMA, self.records())
            result = repo.search("Toyota", "90919-01095")
            self.assertEqual(result["total"], 1)
            self.assertTrue(result["records"][0]["reference_only"])
            sources = [{**source, "id": "S1"} for source in repo.question_sources("Toyota 90919-01095 replacement?", 6)]
            answer = fitment_answer(sources)
            validate_citations(answer, sources)
            self.assertIn("vehicle application", answer.claims[0].text)
            answer.claims[0].text = "DENSO W99ETR-S fits."
            with self.assertRaises(CitationError):
                validate_citations(answer, sources)
            unknown = repo.search("Toyota", "UNLISTED")
            self.assertEqual(unknown["status"], "not_documented")
            self.assertIn("model", unknown["message"])
            self.assertTrue(unknown["next_steps"])


if __name__ == "__main__":
    unittest.main()
