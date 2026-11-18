import unittest

from app.services.catalogue_service import CatalogueService
from app.services.denso_parser import DensoParser


def reference(brand, external, denso):
    return {"brand": brand, "external_part": external, "denso_part": denso, "evidence": {"page_number": 4, "quote": external + " " + denso}}


def dimension(part, length=100):
    return {"part_number": part, "dimensions_mm": {"length": length, "width": 200, "height": 30}, "evidence": {"page_number": 5, "quote": part}}


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = DensoParser()

    def test_single_column_reference_preserves_leading_zero(self):
        records = self.parser.cross_references("BRAND       DENSO\n00123       DCF901P", "fixture.pdf", 4)
        self.assertEqual(records[0]["external_part"], "00123")
        self.assertEqual(records[0]["brand"], "BRAND")

    def test_brand_named_denso_and_four_columns(self):
        header = "".join(f"{brand:<14}DENSO".ljust(40) for brand in ["DENSO", "BRAND B", "BRAND C", "BRAND D"])
        data = "".join(f"{part:<14}{denso}".ljust(40) for part, denso in [("001", "DCF901P"), ("002", "DCF902P"), ("003", "DCF903P"), ("004", "DCF904P")])
        records = self.parser.cross_references(header + "\n" + data, "fixture.pdf", 4)
        self.assertEqual([record["external_part"] for record in records], ["001", "002", "003", "004"])
        self.assertEqual(records[0]["brand"], "DENSO")

    def test_shifted_heading_does_not_cut_first_part_character(self):
        header = f" {'BRAND A':<13}DENSO".ljust(40) + f"  {'BRAND B':<13}DENSO"
        data = f"{'123':<14}DCF901P".ljust(40) + f"{'0123':<14}DCF902P"
        self.assertEqual(self.parser.cross_references(header + "\n" + data, "fixture", 1)[1]["external_part"], "0123")

    def test_brand_transition_inside_column(self):
        text = "BRAND A       DENSO\n001           DCF901P\nBRAND B       DENSO\n001           DCF902P"
        self.assertEqual([record["brand"] for record in self.parser.cross_references(text, "fixture", 1)], ["BRAND A", "BRAND B"])

    def test_missing_header_fails_closed(self):
        self.assertEqual(self.parser.cross_references("001      DCF901P", "fixture", 1), [])
        self.assertTrue(self.parser.warnings)

    def test_decimal_comma_dimensions_and_column_pairing(self):
        text = "DCF901P                         DCF902K\nLength: 238,5mm Width: 200mm Height: 30mm     Length: 100mm Width: 90mm Height: 20mm"
        records = self.parser.dimensions(text, "fixture", 7)
        self.assertEqual(records[0]["dimensions_mm"]["length"], 238.5)
        self.assertEqual(records[1]["dimensions_mm"]["height"], 20)

    def test_mismatched_dimension_counts_are_skipped(self):
        records = self.parser.dimensions("DCF901P DCF902P\nLength: 100mm Width: 90mm Height: 20mm", "fixture", 7)
        self.assertEqual(records, [])
        self.assertTrue(self.parser.warnings)

    def test_unicode_make_continuation_and_wrapped_qualifier(self):
        text = " CITROËN      continued\n MODEL (18-)       + AC       For       04/18-       DCF901P\n                             left-/right-hand\n                             drive vehicles"
        record = self.parser.applications(text, "fixture", 8)[0]
        self.assertEqual(record["make"], "CITROËN")
        self.assertIn("left-/right-hand", record["qualifiers"])
        self.assertIn("drive vehicles", record["evidence"]["quote"])
        self.assertFalse(record["fitment_verified"])

    def test_wrapped_vehicle_label(self):
        record = self.parser.applications(" MAKE\n MODEL VAN        + AC       05/19-       DCF901P\n (18-)", "fixture", 8)[0]
        self.assertEqual(record["vehicle"], "MODEL VAN (18-)")

    def test_unscoped_application_is_not_guessed(self):
        self.assertEqual(self.parser.applications(" MODEL (18-)       04/18-       DCF901P", "fixture", 8), [])


class CatalogueTests(unittest.TestCase):
    def setUp(self):
        self.data = {"dimensions": [dimension("DCF901P"), dimension("DCF902P", 120), dimension("DCF903P")], "cross_references": [reference("A", "001", "DCF901P")], "applications": [{"make": "MAKE", "vehicle": "MODEL (18-)", "qualifiers": "RHD", "production_range": "04/18-", "parts": ["DCF901P"], "evidence": {"page_number": 9}}]}
        self.service = CatalogueService(self.data)

    def test_reference_is_not_vehicle_approval(self):
        result = self.service.compare("001", "DCF901P", "A")
        self.assertEqual(result["status"], "documented_reference")
        self.assertEqual(result["vehicle_fitment"], "unknown")

    def test_equal_dimensions_do_not_prove_interchangeability(self):
        result = self.service.compare("DCF901P", "DCF903P")
        self.assertEqual(result["status"], "unknown")
        self.assertTrue(all(check["status"] == "match" for check in result["dimension_checks"]))

    def test_different_dimensions_are_a_conflict(self):
        self.assertEqual(self.service.compare("DCF901P", "DCF902P")["status"], "conflict")

    def test_ambiguous_external_brand_needs_selection(self):
        self.data["cross_references"].append(reference("B", "001", "DCF902P"))
        self.assertEqual(self.service.lookup("001")["status"], "ambiguous_brand")
        self.assertEqual(self.service.compare("001", "DCF901P")["cross_reference_status"], "unknown")
        self.assertEqual(self.service.compare("001", "DCF901P", "A")["status"], "documented_reference")

    def test_missing_lookup_and_comparison_remain_unknown(self):
        self.assertEqual(self.service.lookup("NOT-HERE")["status"], "not_found")
        self.assertEqual(self.service.compare("NOT-HERE", "DCF999P")["status"], "unknown")

    def test_partial_part_identifier_cannot_match(self):
        self.assertEqual(self.service.lookup("00")["cross_references"], [])
        self.assertEqual(self.service.lookup("DCF901")["applications"], [])

    def test_search_requires_all_query_terms(self):
        self.assertEqual(len(self.service.search("MAKE MODEL")), 1)
        self.assertEqual(self.service.search("MAKE UNRELATED"), [])
        with self.assertRaises(ValueError):
            self.service.search(" ")

    def test_conflicting_dimension_records_stay_unknown(self):
        self.data["dimensions"].append(dimension("DCF901P", 121))
        self.assertEqual(self.service.compare("DCF901P", "DCF903P")["dimension_checks"][0]["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
