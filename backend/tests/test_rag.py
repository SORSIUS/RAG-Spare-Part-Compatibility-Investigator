import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.core.settings import Settings
from app.integrations.groq_client import GroqClient, ProviderError
from app.main import create_app
from app.models.chat import ChatRequest, GeneratedAnswer
from app.repositories.catalogue import CatalogueSnapshot
from app.repositories.conversations import ConversationRepository
from app.services.answer_service import AnswerService, CitationError, validate_citations
from app.services.rag_retriever import RagRetriever


def fixture_snapshot(fingerprint="a" * 64):
    def evidence(page, section, text):
        return {"source": "fixture.pdf", "page_number": page, "section": section, "quote": text}
    catalogue = {
        "page_count": 141, "warnings": [],
        "dimensions": [
            {"part_number": "DCF901P", "dimensions_mm": {"length": 100, "width": 200, "height": 30}, "evidence": evidence(97, "photo_guide", "DCF901P: Length 100mm Width 200mm Height 30mm")},
            {"part_number": "DCF902P", "dimensions_mm": {"length": 120, "width": 200, "height": 30}, "evidence": evidence(98, "photo_guide", "DCF902P: Length 120mm Width 200mm Height 30mm")},
        ],
        "cross_references": [{"brand": "EXAMPLE BRAND", "external_part": "ABC-001", "denso_part": "DCF901P", "evidence": evidence(68, "cross_reference", "ABC-001  DCF901P")}],
        "applications": [{"make": "EXAMPLE", "vehicle": "CITY (10-15)", "production_range": "01/10-12/15", "qualifiers": "RHD | + AC", "parts": ["DCF901P"], "evidence": evidence(4, "application", "CITY (10-15) RHD + AC DCF901P")}],
    }
    return CatalogueSnapshot(fingerprint, catalogue, [])


class FixtureRepository:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def load(self, force=False):
        return self.snapshot


class ValidClient:
    calls = 0

    def __init__(self, settings):
        pass

    def generate(self, question, sources, history):
        type(self).calls += 1
        source = sources[0]
        answer = GeneratedAnswer.model_validate({"insufficient_evidence": False, "claims": [{"text": "The retrieved record documents " + source["title"] + ".", "citations": [{"source_id": source["id"], "quote": source["content"]}]}], "unknowns": ["Exact-vehicle suitability has not been verified."], "follow_up_questions": []})
        return answer, {"total_tokens": 100}


class BadCitationClient(ValidClient):
    def generate(self, question, sources, history):
        answer, usage = super().generate(question, sources, history)
        answer.claims[0].citations[0].source_id = "S999"
        return answer, usage


class RagTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.settings = Settings(self.directory, "test-key-not-real")
        self.snapshot = fixture_snapshot()
        self.sources = RagRetriever(self.snapshot).retrieve("DCF901P dimensions")

    def test_dimension_intent_prioritizes_exact_part_dimensions(self):
        self.assertEqual(self.sources[0]["section"], "photo_guide")
        self.assertIn("DCF901P", self.sources[0]["content"])
        self.assertIn("100 mm", self.sources[0]["content"])

    def test_comparison_balances_both_part_numbers(self):
        sources = RagRetriever(self.snapshot).retrieve("Compare dimensions of DCF901P and DCF902P", 2)
        self.assertTrue(any("DCF901P" in source["content"] for source in sources))
        self.assertTrue(any("DCF902P" in source["content"] for source in sources))

    def test_unknown_part_and_unrelated_question_retrieve_nothing(self):
        retriever = RagRetriever(self.snapshot)
        self.assertEqual(retriever.retrieve("What size is DCF999P?"), [])
        self.assertEqual(retriever.retrieve("quantum banana recipe"), [])

    def test_reference_intent_returns_named_brand(self):
        sources = RagRetriever(self.snapshot).retrieve("What is the replacement for ABC-001?")
        self.assertEqual(sources[0]["section"], "cross_reference")
        self.assertIn("EXAMPLE BRAND", sources[0]["content"])

    def test_source_links_are_bound_to_source_fingerprint_and_page(self):
        self.assertEqual(self.sources[0]["pdf_url"], "/api/catalogue/pdf?version=" + "a" * 64 + "#page=97")

    def test_missing_and_fabricated_citations_are_rejected(self):
        answer, usage = ValidClient(self.settings).generate("question", self.sources, [])
        validate_citations(answer, self.sources)
        answer.claims[0].citations[0].source_id = "S999"
        with self.assertRaises(CitationError):
            validate_citations(answer, self.sources)
        answer.claims[0].citations[0].source_id = "S1"
        answer.claims[0].citations[0].quote = "a fabricated supporting quote"
        with self.assertRaises(CitationError):
            validate_citations(answer, self.sources)

    def test_uncited_claim_numbers_and_part_numbers_are_rejected(self):
        answer, usage = ValidClient(self.settings).generate("question", self.sources, [])
        answer.claims[0].text = "The length is 9999 mm."
        with self.assertRaises(CitationError):
            validate_citations(answer, self.sources)
        answer.claims[0].text = "This is DCF999P."
        with self.assertRaises(CitationError):
            validate_citations(answer, self.sources)

    def test_application_quotes_cannot_skip_fields_or_expand_dates(self):
        content = "vehicle COROLLA (_E12_) (01-07); production range 01/01-12/07; qualifiers: + AC, JPN; listed DENSO parts: DCF383P"
        sources = [{"id": "S1", "content": content}]
        answer = GeneratedAnswer.model_validate({"insufficient_evidence": False, "claims": [{"text": "COROLLA (_E12_) (01-07); production range 01/01-12/07; + AC, JPN; DCF383P", "citations": [{"source_id": "S1", "quote": content}]}], "unknowns": [], "follow_up_questions": []})
        validate_citations(answer, sources)
        answer.claims[0].citations[0].quote = "vehicle COROLLA (_E12_) (01-07); qualifiers: + AC, JPN"
        with self.assertRaises(CitationError):
            validate_citations(answer, sources)
        answer.claims[0].citations[0].quote = content
        answer.claims[0].text = "The production dates are 2001 to 2007."
        with self.assertRaises(CitationError):
            validate_citations(answer, sources)

    def test_unverified_model_answer_is_withheld_but_sources_remain(self):
        repository = ConversationRepository(self.directory / "chat.sqlite3")
        service = AnswerService(FixtureRepository(self.snapshot), repository, BadCitationClient)
        result = service.ask(ChatRequest(question="DCF901P dimensions"), self.settings)
        self.assertEqual(result["status"], "unverified_response")
        self.assertEqual(result["claims"], [])
        self.assertTrue(result["sources"])

    def test_no_evidence_avoids_model_calls(self):
        ValidClient.calls = 0
        service = AnswerService(FixtureRepository(self.snapshot), ConversationRepository(self.directory / "chat.sqlite3"), ValidClient)
        result = service.ask(ChatRequest(question="quantum banana"), self.settings)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(ValidClient.calls, 0)

    def test_evidence_mode_needs_no_api_key(self):
        service = AnswerService(FixtureRepository(self.snapshot), ConversationRepository(self.directory / "chat.sqlite3"))
        result = service.ask(ChatRequest(question="DCF901P size", mode="evidence"), Settings(self.directory))
        self.assertEqual(result["status"], "evidence_only")

    def test_partial_answer_keeps_checked_facts_and_gives_next_step(self):
        class PartialClient(ValidClient):
            def generate(self, question, sources, history):
                answer, usage = super().generate(question, sources, history)
                answer.insufficient_evidence = True
                return answer, usage
        service = AnswerService(FixtureRepository(self.snapshot), ConversationRepository(self.directory / "partial.sqlite3"), PartialClient)
        result = service.ask(ChatRequest(question="Explain DCF901P"), self.settings)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertTrue(result["claims"])
        self.assertTrue(result["follow_up_questions"])
        self.assertIn("sources", result["assistant_text"])

    def test_conversation_persists_and_follow_up_retrieves_previous_part(self):
        path = self.directory / "chat.sqlite3"
        service = AnswerService(FixtureRepository(self.snapshot), ConversationRepository(path), ValidClient)
        first = service.ask(ChatRequest(question="DCF901P dimensions"), self.settings)
        second = service.ask(ChatRequest(question="What about its width?", conversation_id=first["conversation_id"]), self.settings)
        self.assertEqual(second["status"], "answered")
        self.assertEqual(len(ConversationRepository(path).get(first["conversation_id"])["messages"]), 2)

    def test_secret_is_absent_from_settings_repr(self):
        self.assertNotIn("test-key-not-real", repr(self.settings))


class GroqTests(unittest.TestCase):
    def setUp(self):
        self.settings = Settings(api_key="test-key-not-real")
        self.sources = [{"id": "S1", "content": "Part DCF901P length is 100 mm."}]

    def test_request_uses_groq_structured_output_and_data_is_not_system_prompt(self):
        def transport(request):
            self.assertEqual(str(request.url), GroqClient.endpoint)
            self.assertEqual(request.headers["authorization"], "Bearer test-key-not-real")
            body = json.loads(request.content)
            self.assertTrue(body["response_format"]["json_schema"]["strict"])
            self.assertNotIn("injected-document-marker", body["messages"][0]["content"])
            self.assertIn("injected-document-marker", body["messages"][1]["content"])
            content = {"insufficient_evidence": True, "claims": [], "unknowns": ["Missing evidence"], "follow_up_questions": []}
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(content)}}], "usage": {"total_tokens": 9}})
        answer, usage = GroqClient(self.settings, httpx.MockTransport(transport)).generate("injected-document-marker", self.sources, [])
        self.assertTrue(answer.insufficient_evidence)
        self.assertEqual(usage["total_tokens"], 9)

    def test_rate_limit_auth_and_malformed_responses_are_sanitized(self):
        for status, body, code in [(429, {"secret": "test-key-not-real"}, "provider_rate_limit"), (401, {}, "provider_auth"), (200, {}, "provider_response")]:
            client = GroqClient(self.settings, httpx.MockTransport(lambda request: httpx.Response(status, json=body)))
            with self.assertRaises(ProviderError) as caught:
                client.generate("question", self.sources, [])
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn("test-key-not-real", str(caught.exception))

    def test_missing_key_and_timeout(self):
        with self.assertRaises(ProviderError) as caught:
            GroqClient(Settings()).generate("question", self.sources, [])
        self.assertEqual(caught.exception.code, "configuration_missing")
        def timeout(request):
            raise httpx.ReadTimeout("timeout")
        with self.assertRaises(ProviderError) as caught:
            GroqClient(self.settings, httpx.MockTransport(timeout)).generate("question", self.sources, [])
        self.assertEqual(caught.exception.status_code, 504)


class ApiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.settings = Settings(self.directory, "test-key-not-real")
        self.settings.pdf_path.parent.mkdir(parents=True)
        self.settings.pdf_path.write_bytes(b"%PDF-1.7 controlled test fixture")
        fingerprint = hashlib.sha256(self.settings.pdf_path.read_bytes()).hexdigest()
        self.app = create_app(lambda: self.settings, FixtureRepository(fixture_snapshot(fingerprint)), ValidClient)
        self.client = self.enterContext(TestClient(self.app))

    def test_health_and_status_do_not_leak_credentials(self):
        self.assertEqual(self.client.get("/api/health").json()["contract_version"], 3)
        response = self.client.get("/api/status")
        self.assertTrue(response.json()["llm_configured"])
        self.assertNotIn("test-key-not-real", response.text)

    def test_chat_response_citations_history_and_pdf_route(self):
        response = self.client.post("/api/chat", json={"question": "DCF901P dimensions"})
        self.assertEqual(response.status_code, 200, response.text)
        message = response.json()
        self.assertEqual(message["status"], "answered")
        self.assertTrue(message["claims"][0]["citations"])
        self.assertEqual(len(self.client.get("/api/conversations").json()["conversations"]), 1)
        history = self.client.get("/api/conversations/" + message["conversation_id"]).json()
        self.assertEqual(len(history["messages"]), 1)
        pdf = self.client.get(message["sources"][0]["pdf_url"].split("#")[0])
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_stale_pdf_citation_is_rejected(self):
        response = self.client.get("/api/catalogue/pdf?version=" + "0" * 64)
        self.assertEqual(response.status_code, 409)

    def test_validation_and_unknown_conversation(self):
        for payload in [{"question": " "}, {"question": "x" * 2001}, {"question": "hello", "unexpected": 1}, {"question": "hello", "mode": "unsafe"}]:
            self.assertEqual(self.client.post("/api/chat", json=payload).status_code, 422)
        self.assertEqual(self.client.post("/api/chat", json={"question": "DCF901P", "conversation_id": "a" * 32}).status_code, 404)

    def test_provider_error_saves_honest_chat_recovery_with_sources(self):
        class FailureClient:
            def __init__(self, settings):
                pass
            def generate(self, *args):
                raise ProviderError("provider_auth", "Check the local key", 503)
        self.app.state.answers.client_factory = FailureClient
        response = self.client.post("/api/chat", json={"question": "DCF901P size"})
        self.assertEqual(response.status_code, 200)
        message = response.json()
        self.assertEqual(message['status'], 'provider_unavailable')
        self.assertEqual(message['provider_issue'], 'provider_auth')
        self.assertTrue(message['sources'])
        self.assertFalse(message['claims'])
        self.assertIn('authenticate', message['assistant_text'])
        saved = self.client.get('/api/conversations/' + message['conversation_id']).json()
        self.assertEqual(saved['messages'][0]['assistant_text'], message['assistant_text'])

    def test_no_credentials_is_usable_in_evidence_mode(self):
        self.settings = Settings(self.directory)
        response = self.client.post("/api/chat", json={"question": "DCF901P size", "mode": "evidence"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "evidence_only")


if __name__ == "__main__":
    unittest.main()
