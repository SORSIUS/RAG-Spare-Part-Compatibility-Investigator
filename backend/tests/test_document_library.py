import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.core.settings import Settings
from app.main import create_app
from app.repositories.document_library import DocumentLibrary
from app.services.hybrid_retrieval import retrieve_sources
from app.services.rag_retriever import RagRetriever
from test_rag import FixtureRepository, fixture_snapshot
from app.models.chat import ChatRequest
from app.repositories.conversations import ConversationRepository
from app.services.answer_service import AnswerService
from app.services.vehicle_questions import needs_vehicle_details


class FakeEmbeddings:
    def split(self, text):
        return [text] if text.strip() else []


class FakeVectors:
    def __init__(self):
        self.embeddings = FakeEmbeddings()
        self.entries = {}
        self.writes = 0

    def add(self, document_id, chunks, progress):
        for chunk in chunks:
            if chunk["id"] not in self.entries:
                self.writes += 1
            self.entries[chunk["id"]] = chunk
        progress(len(chunks), len(chunks))

    def search(self, query, ready_ids, limit=12, **kwargs):
        return []


class DocumentLibraryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.vectors = FakeVectors()
        self.library = DocumentLibrary(self.root, self.vectors)

    def add_text(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return self.library.register(path, name)

    def test_duplicate_content_reuses_index_even_with_different_name(self):
        first = self.add_text("first.txt", "The original shock has a lower mounting bracket.")
        self.library.process(first["id"])
        writes = self.vectors.writes
        duplicate = self.add_text("renamed.txt", "The original shock has a lower mounting bracket.")
        self.library.process(duplicate["id"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(len(self.library.list()), 1)
        self.assertEqual(self.vectors.writes, writes)
        self.assertEqual(self.library.get(first["id"])["status"], "ready")

    def test_named_file_scopes_vectors_and_removes_filename_from_query(self):
        first = self.add_text("toyota_specs.txt", "Front suspension uses a MacPherson strut.")
        second = self.add_text("other.txt", "A separate unrelated catalogue.")
        self.library.process(first["id"])
        self.library.process(second["id"])
        with patch.object(self.vectors, "search", return_value=[{"content": "MacPherson strut"}]) as search:
            result = self.library.search("According to TOYOTA_SPECS.TXT, what is the suspension?")
        self.assertEqual(search.call_args.args[1], [first["id"]])
        self.assertNotIn("toyota_specs.txt", search.call_args.args[0].lower())
        self.assertEqual(result[0]["retrieval_scope"], "named_document")

    def test_named_file_without_relevant_hits_does_not_use_other_catalogues(self):
        document = self.add_text("toyota_specs.txt", "Front suspension uses a MacPherson strut.")
        self.library.process(document["id"])
        lexical = RagRetriever(fixture_snapshot())
        result = retrieve_sources(lexical, self.library, "toyota_specs.txt DCF002K", 8)
        self.assertEqual(result, [])

    def test_second_document_does_not_reparse_existing_document(self):
        first = self.add_text("first.txt", "The first reference document.")
        self.library.process(first["id"])
        cache = self.library.root / (first["id"][:24] + "-chunks.json")
        before = cache.stat().st_mtime_ns
        second = self.add_text("second.txt", "The second independent reference document.")
        self.library.run_pending()
        self.assertEqual(cache.stat().st_mtime_ns, before)
        self.assertEqual(self.library.get(second["id"])["status"], "ready")

    def test_interrupted_document_reuses_saved_chunks(self):
        document = self.add_text("resume.txt", "Saved extraction can be reused after interruption.")
        self.library.process(document["id"])
        self.library.update(document["id"], status="indexing")
        with patch("app.repositories.document_library.read_library_document", side_effect=AssertionError("Do not parse again")):
            self.library.process(document["id"])
        self.assertEqual(self.library.get(document["id"])["status"], "ready")

    def test_state_persists_when_library_reopens(self):
        document = self.add_text("persistent.txt", "A persistent document history.")
        self.library.process(document["id"])
        reopened = DocumentLibrary(self.root, self.vectors)
        self.assertEqual(reopened.get(document["id"])["status"], "ready")
        self.assertEqual(reopened.get(document["id"])["indexed"], 1)

    def test_blank_pdf_is_marked_needs_ocr(self):
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        path = self.root / "blank.pdf"
        writer.write(path)
        document = self.library.register(path, path.name)
        self.library.process(document["id"])
        self.assertEqual(self.library.get(document["id"])["status"], "needs_ocr")

    def test_damaged_file_failure_is_local_to_that_document(self):
        good = self.add_text("good.txt", "A valid reference.")
        bad_path = self.root / "broken.pdf"
        bad_path.write_bytes(b"%PDF-damaged")
        bad = self.library.register(bad_path, bad_path.name)
        self.library.run_pending()
        self.assertEqual(self.library.get(good["id"])["status"], "ready")
        self.assertEqual(self.library.get(bad["id"])["status"], "failed")

    def test_paths_are_not_exposed_and_filename_is_sanitized(self):
        path = self.root / "source.txt"
        path.write_text("A harmless source.")
        document = self.library.register(path, "../../private/source.txt")
        self.assertEqual(document["name"], "source.txt")
        self.assertNotIn("path", document)
        self.assertNotIn("schema", document)


class UploadApiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.library = DocumentLibrary(self.root / "data/runtime", FakeVectors())
        self.library.start = lambda: None
        self.client = self.enterContext(TestClient(create_app(lambda: Settings(self.root), FixtureRepository(fixture_snapshot()), document_library=self.library)))

    def test_upload_returns_queued_before_indexing_and_deduplicates(self):
        body = b"Each vehicle must have its correct shock absorber."
        response = self.client.post("/api/documents/upload", files={"file": ("notes.txt", body, "text/plain")})
        self.assertEqual(response.status_code, 202)
        document = response.json()
        self.assertEqual(document["status"], "queued")
        self.assertEqual(document["indexed"], 0)
        self.library.process(document["id"])
        second = self.client.post("/api/documents/upload", files={"file": ("renamed.txt", body, "text/plain")}).json()
        self.assertTrue(second["duplicate"])
        self.assertEqual(second["status"], "ready")

    def test_upload_rejects_unsupported_empty_and_fake_pdf(self):
        for name, data, expected in [("x.exe", b"anything", 415), ("x.pdf", b"not pdf", 415), ("x.txt", b"", 422)]:
            self.assertEqual(self.client.post("/api/documents/upload", files={"file": (name, data)}).status_code, expected)

    def test_document_route_checks_source_revision_and_missing_ids(self):
        document = self.client.post("/api/documents/upload", files={"file": ("notes.txt", b"Original reference")}).json()
        url = "/api/documents/" + document["id"] + "/pdf"
        self.assertEqual(self.client.get(url).content, b"Original reference")
        self.library.path(document["id"]).write_bytes(b"Changed")
        self.assertEqual(self.client.get(url).status_code, 409)
        self.assertEqual(self.client.get("/api/documents/" + "a" * 64 + "/pdf").status_code, 404)

    def test_retry_only_changes_failed_document(self):
        document = self.client.post("/api/documents/upload", files={"file": ("notes.txt", b"Reference")}).json()
        self.library.update(document["id"], status="failed")
        response = self.client.post("/api/documents/" + document["id"] + "/retry")
        self.assertEqual(response.json()["status"], "queued")
        self.assertEqual(self.client.post("/api/documents/" + "a" * 64 + "/retry").status_code, 404)


class HybridTests(unittest.TestCase):
    def setUp(self):
        self.lexical = RagRetriever(fixture_snapshot())

    def test_unknown_identifier_is_not_replaced_by_semantic_neighbor(self):
        class Library:
            def search(self, *args):
                raise AssertionError("Unknown identifiers must fail closed.")
        self.assertEqual(retrieve_sources(self.lexical, Library(), "What size is DCF999P?", 8), [])

    def test_semantic_passage_can_answer_without_literal_overlap(self):
        class Library:
            def search(self, *args):
                return [{"source": "guide.pdf", "page_number": 1, "content": "Dampers limit oscillation after road impacts.", "cosine_distance": .3, "pdf_url": "/api/documents/" + "a" * 64 + "/pdf#page=1"}]
        sources = retrieve_sources(self.lexical, Library(), "Why does my vehicle keep bouncing?", 8)
        self.assertEqual(sources[0]["retrieval_method"], "semantic")

    def test_suspension_question_does_not_use_filter_records(self):
        class Library:
            def search(self, *args):
                return []
        self.assertEqual(retrieve_sources(self.lexical, Library(), "Can I use CITY suspensions with this car?", 8), [])

    def test_exact_comparison_keeps_both_dimension_records(self):
        class Library:
            def search(self, *args):
                return []
        sources = retrieve_sources(self.lexical, Library(), "Compare dimensions of DCF901P and DCF902P", 2)
        self.assertTrue(any("DCF901P" in source["content"] for source in sources))
        self.assertTrue(any("DCF902P" in source["content"] for source in sources))

    def test_new_part_in_uploaded_document_can_be_retrieved(self):
        class Library:
            def lookup_identifier(self, identifier):
                return [{"source": "new.pdf", "page_number": 1, "content": "DCF999P is documented in this new reference.", "retrieval_method": "exact/document"}]
            def search(self, *args):
                return []
        sources = retrieve_sources(self.lexical, Library(), "DCF999P dimensions", 8)
        self.assertEqual(sources[0]["retrieval_method"], "exact/document")

    def test_owner_swap_needs_years_and_collects_them_in_context(self):
        self.assertTrue(needs_vehicle_details("Can Corolla suspension fit a Honda City?"))
        self.assertFalse(needs_vehicle_details("Can 2012 Corolla suspension fit a 2016 Honda City?"))
        self.assertFalse(needs_vehicle_details("Why should I replace shock absorbers in pairs?"))

    def test_upload_only_chat_does_not_require_the_denso_pdf(self):
        class Library:
            def search(self, *args):
                return [{"title": "Uploaded note", "content": "An uploaded reference document.", "source": "note.pdf", "page_number": 1, "raw_excerpt": "An uploaded reference document.", "pdf_url": "/api/documents/" + "a" * 64 + "/pdf#page=1"}]
        class MissingRepository:
            library = Library()
            def load(self):
                raise FileNotFoundError()
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(Path(directory))
            service = AnswerService(MissingRepository(), ConversationRepository(Path(directory) / "chat.sqlite3"))
            result = service.ask(ChatRequest(question="Explain this reference", mode="evidence"), settings)
            self.assertEqual(result["status"], "evidence_only")
            self.assertEqual(result["sources"][0]["id"], "S1")

    def test_numerical_comparison_uses_catalogue_rules_without_llm(self):
        class NoModel:
            def __init__(self, settings):
                raise AssertionError("Do not generate documented numerical comparisons.")
        with tempfile.TemporaryDirectory() as directory:
            settings = Settings(Path(directory))
            service = AnswerService(FixtureRepository(fixture_snapshot()), ConversationRepository(Path(directory) / "chat.sqlite3"), NoModel)
            result = service.ask(ChatRequest(question="Compare the dimensions of DCF901P and DCF902P."), settings)
            self.assertEqual(result["answer_method"], "catalogue_rules")
            self.assertEqual(result["status"], "answered")
            self.assertIn("length conflict", result["claims"][-1]["text"])
            self.assertIsNone(result["model"])


if __name__ == "__main__":
    unittest.main()
