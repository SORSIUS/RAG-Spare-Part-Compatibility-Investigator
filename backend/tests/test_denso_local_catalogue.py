import hashlib
import json
import unittest
from pathlib import Path

from app.services.catalogue_service import CatalogueService
from app.services.denso_parser import DensoParser


BACKEND = Path(__file__).resolve().parents[1]
PDF = BACKEND / "data/sources/automotive/denso_cabin_air_filters_2026.pdf"


@unittest.skipUnless(PDF.is_file(), "Optional manufacturer PDF is local-only; download it to run integration checks.")
class LocalCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cached = BACKEND / "data/runtime/denso_catalogue.json"
        catalogue = json.loads(cached.read_text(encoding="utf-8")) if cached.exists() else {}
        fingerprint = hashlib.sha256(PDF.read_bytes()).hexdigest()
        if catalogue.get("sha256") != fingerprint or catalogue.get("parser_version") != DensoParser.version:
            catalogue = DensoParser().parse(PDF)
        cls.catalogue = catalogue
        cls.service = CatalogueService(catalogue)

    def test_section_coverage_and_no_reported_parse_anomalies(self):
        self.assertEqual(self.catalogue["page_count"], 141)
        self.assertGreaterEqual(len(self.catalogue["dimensions"]), 300)
        self.assertGreaterEqual(len(self.catalogue["cross_references"]), 7000)
        self.assertGreaterEqual(len(self.catalogue["applications"]), 3500)
        self.assertEqual(self.catalogue["warnings"], [])

    def test_visual_photo_guide_checks(self):
        by_part = {record["part_number"]: record for record in self.catalogue["dimensions"]}
        self.assertEqual(by_part["DCF002K"]["dimensions_mm"], {"length": 282, "width": 206, "height": 30})
        self.assertEqual(by_part["DCF002K"]["evidence"]["page_number"], 97)
        self.assertEqual(by_part["DCF414P"]["dimensions_mm"]["length"], 238.5)
        self.assertEqual(by_part["DCF414P"]["evidence"]["page_number"], 111)

    def test_reference_and_brand_column_boundaries(self):
        for brand, external, expected, page in [("1A FIRST AUTOMOTIVE", "C30001", "DCF357P", 68), ("FEBI BILSTEIN", "09430", "DCF031P", 76), ("DENSO", "014520-5230", "DCF382P", 75)]:
            references = self.service.lookup(external, brand)["cross_references"]
            self.assertTrue(any(record["denso_part"] == expected and record["evidence"]["page_number"] == page for record in references))

    def test_visual_application_row_preserves_qualifiers_and_date(self):
        matches = self.service.search("ABARTH GRANDE PUNTO")
        record = next(record for record in matches if record["production_range"] == "07/07-06/10")
        self.assertEqual(record["evidence"]["page_number"], 4)
        self.assertEqual(record["parts"], ["DCF488P", "DCF201K"])
        self.assertIn("+ AC", record["qualifiers"])
        self.assertFalse(record["fitment_verified"])

    def test_real_cross_reference_is_distinct_from_dimension_conflict(self):
        self.assertEqual(self.service.compare("C30001", "DCF357P", "1A FIRST AUTOMOTIVE")["status"], "documented_reference")
        result = self.service.compare("DCF009P", "DCF031P")
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["vehicle_fitment"], "unknown")


if __name__ == "__main__":
    unittest.main()
