import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from mcp import Client

from app.core.settings import Settings
from app.main import create_app
from app.mcp_server import create_mcp_server
from app.models.chat import ChatRequest
from app.repositories.conversations import ConversationRepository
from app.services.answer_service import AnswerService
from app.services.catalogue_tools import CatalogueTools
from test_rag import fixture_snapshot, FixtureRepository


class AgentFeatureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.settings = Settings(Path(temporary.name))
        self.repository = FixtureRepository(fixture_snapshot())
        self.tools = CatalogueTools(self.repository)
        self.client = self.enterContext(TestClient(create_app(lambda: self.settings, self.repository)))

    def test_comparison_matrix_matches_domain_rules_and_has_page_links(self):
        result = self.client.post("/api/catalogue/compare", json={"original": "DCF901P", "candidate": "DCF902P"})
        self.assertEqual(result.status_code, 200)
        body = result.json()
        self.assertEqual(body["status"], "conflict")
        self.assertEqual([check["status"] for check in body["dimension_checks"]], ["conflict", "match", "match"])
        self.assertIn("#page=97", body["dimension_checks"][0]["evidence"][0]["pdf_url"])
        self.assertEqual(body["vehicle_fitment"], "unknown")
        self.assertFalse(body["llm_used"])

    def test_direct_reference_and_unknown_are_not_installation_approval(self):
        direct = self.tools.compare("ABC-001", "DCF901P", "EXAMPLE BRAND")
        self.assertEqual(direct["status"], "documented_reference")
        self.assertEqual(direct["dimension_checks"][0]["status"], "unknown")
        self.assertEqual(self.tools.compare("DOES-NOT-EXIST", "DCF901P")["status"], "unknown")
        self.assertEqual(self.tools.compare("DCF901P", "DCF901P")["status"], "unknown")

    def test_agent_search_is_read_only_and_lookup_is_bounded(self):
        response = self.client.post("/api/catalogue/search", json={"query": "DCF901P dimensions", "limit": 1})
        self.assertEqual(len(response.json()["sources"]), 1)
        lookup = self.client.post("/api/catalogue/lookup", json={"part": "DCF901P", "limit": 1}).json()
        self.assertEqual(lookup["status"], "found")
        self.assertEqual(lookup["record_counts"]["dimensions"], 1)
        self.assertIn("pdf_url", lookup["dimensions"][0]["evidence"])
        self.assertEqual(self.client.get("/api/conversations").json()["conversations"], [])

    def test_invalid_identifiers_limits_and_extra_fields_are_rejected(self):
        cases = [("compare", {"original": " ", "candidate": "DCF901P"}), ("compare", {"original": "DCF901P", "candidate": "not-denso"}), ("search", {"query": "x", "limit": 13}), ("search", {"query": " "}), ("lookup", {"part": "x", "limit": 0}), ("lookup", {"part": "x", "limit": True}), ("compare", {"original": "DCF901P", "candidate": "DCF902P", "secret": "not-allowed"})]
        for operation, body in cases:
            with self.subTest(operation=operation, body=body):
                self.assertEqual(self.client.post("/api/catalogue/" + operation, json=body).status_code, 422)

    def test_exports_preserve_evidence_and_do_not_call_model(self):
        message = self.client.post("/api/chat", json={"question": "DCF901P size", "mode": "evidence"}).json()
        base = "/api/conversations/" + message["conversation_id"] + "/export"
        markdown = self.client.get(base)
        self.assertEqual(markdown.status_code, 200)
        self.assertIn("PDF page 97", markdown.text)
        self.assertIn("Source IDs are scoped", markdown.text)
        self.assertIn("attachment; filename=", markdown.headers["content-disposition"])
        data = self.client.get(base + "?format=json").json()
        self.assertEqual(data["messages"][0]["sources"], message["sources"])
        self.assertEqual(self.client.get(base + "?format=html").status_code, 422)
        self.assertEqual(self.client.get("/api/conversations/" + "a" * 32 + "/export").status_code, 404)

    def test_repeated_pronouns_preserve_original_part(self):
        history = ConversationRepository(self.settings.runtime_dir / "follow-ups.sqlite3")
        service = AnswerService(self.repository, history)
        first = service.ask(ChatRequest(question="DCF901P dimensions", mode="evidence"), self.settings)
        for question in ["What about its width?", "And its height?", "Does it have a reference?"]:
            result = service.ask(ChatRequest(question=question, mode="evidence", conversation_id=first["conversation_id"]), self.settings)
            self.assertIn("DCF901P", result["retrieval_query"])
            self.assertTrue(result["sources"])
            self.assertTrue(all("DCF901P" in source["content"] for source in result["sources"]))

    def test_openapi_exposes_typed_agent_operations(self):
        schema = self.client.get("/openapi.json").json()
        for path in ["/api/catalogue/compare", "/api/catalogue/search", "/api/catalogue/lookup"]:
            self.assertIn("requestBody", schema["paths"][path]["post"])

    def test_mcp_protocol_discovery_calls_resources_and_invalid_input(self):
        async def verify():
            async with Client(create_mcp_server(lambda: self.tools)) as client:
                listed = await client.list_tools()
                self.assertEqual({tool.name for tool in listed.tools}, {"catalogue_info", "search_catalogue", "lookup_part", "compare_parts"})
                self.assertTrue(all(tool.annotations.read_only_hint for tool in listed.tools))
                result = await client.call_tool("compare_parts", {"original": "DCF901P", "candidate": "DCF902P"})
                self.assertFalse(result.is_error)
                self.assertEqual(result.structured_content["status"], "conflict")
                result = await client.call_tool("search_catalogue", {"query": "DCF901P dimensions", "limit": 1})
                self.assertEqual(len(result.structured_content["sources"]), 1)
                result = await client.call_tool("lookup_part", {"part": "ABC-001", "brand": "EXAMPLE BRAND"})
                self.assertEqual(result.structured_content["denso_parts"], ["DCF901P"])
                resource = await client.read_resource("catalogue://metadata")
                self.assertEqual(json.loads(resource.contents[0].text)["source_sha256"], "a" * 64)
                invalid = await client.call_tool("compare_parts", {"original": "DCF901P", "candidate": "not-denso"})
                self.assertTrue(invalid.is_error)
                invalid = await client.call_tool("search_catalogue", {"query": "x", "limit": 99})
                self.assertTrue(invalid.is_error)
        asyncio.run(verify())

    def test_mcp_rejects_untrusted_browser_origin(self):
        response = self.client.post("http://127.0.0.1:8000/mcp", headers={"Accept": "application/json, text/event-stream", "Origin": "https://example.com"}, json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
