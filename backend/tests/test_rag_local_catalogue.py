import unittest

from app.core.settings import Settings
from app.repositories.catalogue import CatalogueRepository
from app.services.rag_retriever import RagRetriever


@unittest.skipUnless(Settings().pdf_path.is_file(), "Local DENSO PDF is required for retrieval integration checks.")
class RealRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = CatalogueRepository(Settings()).load()
        cls.retriever = RagRetriever(cls.snapshot)

    def test_real_dimension_record_ranks_first(self):
        source = self.retriever.retrieve("What are the dimensions of DCF002K?")[0]
        self.assertEqual(source["section"], "photo_guide")
        self.assertEqual(source["page_number"], 97)
        self.assertIn("282 mm", source["content"])
        self.assertIn("206 mm", source["content"])
        self.assertIn("30 mm", source["content"])

    def test_real_vehicle_question_retrieves_model_mentions(self):
        sources = self.retriever.retrieve("Which cabin filters are listed for Toyota Corolla?")
        self.assertTrue(sources)
        self.assertEqual(sources[0]["section"], "application")
        self.assertIn("TOYOTA", sources[0]["content"])
        self.assertIn("COROLLA", sources[0]["content"])

    def test_comparison_retrieves_both_dimension_records(self):
        sources = self.retriever.retrieve("Compare the dimensions of DCF009P and DCF031P.")
        self.assertTrue(any(source["section"] == "photo_guide" and "DCF009P" in source["content"] for source in sources))
        self.assertTrue(any(source["section"] == "photo_guide" and "DCF031P" in source["content"] for source in sources))

    def test_reference_and_all_page_links_are_real(self):
        sources = self.retriever.retrieve("Does the catalogue cross-reference C30001 to DCF357P?")
        self.assertEqual(sources[0]["section"], "cross_reference")
        self.assertIn("C30001", sources[0]["content"])
        self.assertIn("DCF357P", sources[0]["content"])
        for source in sources:
            self.assertTrue(1 <= source["page_number"] <= self.snapshot.catalogue["page_count"])
            self.assertIn(self.snapshot.fingerprint, source["pdf_url"])

    def test_out_of_catalogue_question_is_not_forced_into_an_answer(self):
        self.assertEqual(self.retriever.retrieve("quantum banana lasagna recipe"), [])


if __name__ == "__main__":
    unittest.main()
