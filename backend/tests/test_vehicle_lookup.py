import tempfile
import unittest
from pathlib import Path

from app.core.settings import Settings
from app.models.chat import ChatRequest
from app.repositories.conversations import ConversationRepository
from app.repositories.fitments import FitmentRepository
from app.services.answer_service import AnswerService
from app.services.kyb_fitment_parser import parse_rows
from app.services.denso_vehicle_parser import parse_rows as parse_denso, SCHEMA, SOURCE_SHA
from app.services.vehicle_lookup import owner_query
from test_rag import FixtureRepository, fixture_snapshot


class VehicleLookupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.fitments = FitmentRepository(self.path)
        rows = [["COROLLA"] + [""] * 11,
                ["07/10-On", "NZE151,ZRE151,ZRE152 1.8 L EFI", "NST5387R NST5387L", "", "", "4860912500", "SM7210", "349035", "", "", "", ""]]
        records = parse_rows(rows, "TOYOTA", 96, "kyb.pdf", "a" * 64)
        self.fitments.replace_source("a" * 64, "kyb.pdf", "test", "", 1, records)
        denso = parse_denso([["TOYOTA"] + [""] * 6, ["COROLLA ALTIS 1.8L", "1800", "-", "1ZZ-FE", "2001-", "K16R-U11", "9091901164"]], 99, "asia.pdf")
        self.fitments.replace_source(SOURCE_SHA, "asia.pdf", SCHEMA, "", 1, denso)

    def test_filters_keep_component_year_engine_and_market(self):
        result = self.fitments.search("Toyota", "Corolla", 2012, engine="1.8", axle="front", component="shock_absorber")
        self.assertEqual({r["part_number"] for r in result["records"]}, {"NST5387L", "NST5387R"})
        self.assertEqual(self.fitments.search("Toyota", "Corolla", 2012, engine="1.6")["total"], 0)
        self.assertEqual(self.fitments.search("Toyota", "Corolla", 2005, category="ignition", engine="1ZZFE", market="Taiwan")["total"], 1)
        self.assertEqual(self.fitments.search("Toyota", "Corolla", 2005, category="ignition", engine="1ZZFE", market="Pakistan")["total"], 0)
        self.assertEqual(self.fitments.search("Toyota", "Corolla", 1999, category="ignition")["total"], 0)

    def test_owner_question_does_not_confuse_fit_verb_or_two_vehicles(self):
        vehicles = [{"make": "Toyota", "model": "Corolla"}, {"make": "Honda", "model": "Fit"}, {"make": "Honda", "model": "City"}]
        context = owner_query("Which suspension can fit my Corolla 2012 1.8?", vehicles)
        self.assertEqual(context["model"], "Corolla")
        self.assertEqual(context["engine"], "1.8")
        self.assertEqual(owner_query("Corolla 2012 2L suspension", vehicles)["engine"], "2")
        self.assertEqual(owner_query("Corolla 2005 1.8 1ZZ-FE spark plugs", vehicles)["engine"], "1ZZ-FE")
        self.assertIsNone(owner_query("Can Toyota Corolla suspension fit a City?", vehicles))

    def test_follow_up_flow_needs_no_part_number_or_llm_call(self):
        fitments = self.fitments
        class Library:
            def __init__(self):
                self.fitments = fitments
            def linked_sources(self, query, limit):
                return fitments.question_sources(query, limit)
            def names_document(self, query):
                return False
            def search(self, query, limit):
                return []
        class NoLLM:
            def __init__(self, settings):
                raise AssertionError("This structured lookup must not call the LLM.")
        repository = FixtureRepository(fixture_snapshot())
        repository.library = Library()
        service = AnswerService(repository, ConversationRepository(self.path / "chat.sqlite3"), NoLLM)
        settings = Settings(self.path)
        first = service.ask(ChatRequest(question="Which suspension fits my Corolla?"), settings)
        self.assertEqual(first["answer_method"], "vehicle_clarification")
        self.assertTrue(any("year" in q for q in first["follow_up_questions"]))
        second = service.ask(ChatRequest(question="2012", conversation_id=first["conversation_id"]), settings)
        self.assertEqual(len(second["follow_up_questions"]), 1)
        third = service.ask(ChatRequest(question="1.8 front", conversation_id=first["conversation_id"]), settings)
        self.assertEqual(third["answer_method"], "vehicle_catalogue")
        self.assertTrue(third["claims"])
        self.assertTrue(all("front" in s["content"] for s in third["sources"]))
        self.assertEqual(len(service.conversations.get(first["conversation_id"])["messages"]), 3)
        spark = service.ask(ChatRequest(question="Which spark plugs for Toyota Corolla 2005 1ZZ-FE Taiwan?"), settings)
        self.assertEqual(spark["answer_method"], "vehicle_catalogue")
        self.assertIn("DENSO K16R-U11", spark["claims"][0]["text"])

    def test_parser_skips_engine_missing_and_ambiguous_model(self):
        rows = [["TOYOTA"] + [""] * 6, ["[AMBIGUOUS]", "1800", "", "1ZZ-FE", "2001-", "K16R-U11", "9091901164"]]
        self.assertEqual(parse_denso(rows, 99, "asia.pdf"), [])
        rows[1][0] = "COROLLA ALTIS"
        rows[1][3] = ""
        self.assertEqual(parse_denso(rows, 99, "asia.pdf"), [])


if __name__ == "__main__":
    unittest.main()
