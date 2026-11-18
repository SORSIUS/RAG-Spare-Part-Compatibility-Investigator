import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pypdf import PdfWriter

from app.services.document_reader import read_document, read_pdf
from app.services.ingestion_service import IngestionService
from app.services.text_chunker import TextChunker


class IngestionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def test_unicode_text(self):
        path = self.directory / "manual.txt"
        path.write_text("Connector 2-pin. پنکھا", encoding="utf-8")
        self.assertIn("پنکھا", read_document(path)[0]["text"])

    def test_blank_pdf_page_numbers_and_warning(self):
        path = self.directory / "manual.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.add_blank_page(width=200, height=200)
        writer.write(path)
        self.assertEqual([page["page_number"] for page in read_pdf(str(path))], [1, 2])
        report = IngestionService().ingest_directory(self.directory)
        self.assertEqual(report["chunks"], [])
        self.assertEqual(report["documents"][0]["empty_pages"], [1, 2])
        self.assertTrue(report["documents"][0]["warnings"])

    def test_pdf_text_is_preserved(self):
        path = self.directory / "manual.pdf"
        path.touch()
        with patch("app.services.document_reader.PdfReader") as reader:
            page = Mock()
            page.extract_text.return_value = "12 V DC, 2-pin"
            reader.return_value.pages = [page]
            self.assertEqual(read_pdf(str(path))[0]["text"], "12 V DC, 2-pin")

    def test_overlap_and_exact_offsets(self):
        text = "one  two\nthree four five six seven"
        chunks = TextChunker(4, 1).chunk_page({"source": "manual", "page_number": 2, "text": text}, "hash")
        self.assertEqual([chunk.text.split() for chunk in chunks], [["one", "two", "three", "four"], ["four", "five", "six", "seven"]])
        for chunk in chunks:
            self.assertEqual(chunk.text, text[chunk.start_offset:chunk.end_offset])
            self.assertEqual(chunk.page_number, 2)

    def test_duplicate_names_have_distinct_sources_and_chunk_ids(self):
        for name in ["supplier_a", "supplier_b"]:
            folder = self.directory / name
            folder.mkdir()
            (folder / "manual.txt").write_text("12 V")
        chunks = IngestionService().ingest_directory(self.directory)["chunks"]
        self.assertEqual(len({chunk["source"] for chunk in chunks}), 2)
        self.assertEqual(len({chunk["chunk_id"] for chunk in chunks}), 2)

    def test_bad_pdf_does_not_drop_good_documents(self):
        (self.directory / "broken.pdf").write_bytes(b"not a PDF")
        (self.directory / "valid.txt").write_text("FAN-12: 12 V")
        report = IngestionService().ingest_directory(self.directory)
        self.assertEqual(len(report["errors"]), 1)
        self.assertEqual(len(report["documents"]), 1)
        self.assertEqual(report["chunks"][0]["text"], "FAN-12: 12 V")

    def test_stable_ids_and_changed_content(self):
        path = self.directory / "manual.txt"
        path.write_text("12 V")
        service = IngestionService()
        first = service.ingest_directory(self.directory)["chunks"]
        self.assertEqual(first, service.ingest_directory(self.directory)["chunks"])
        path.write_text("24 V")
        self.assertNotEqual(first[0]["document_id"], service.ingest_directory(self.directory)["chunks"][0]["document_id"])

    def test_invalid_settings_and_paths(self):
        for size, overlap in [(0, 0), (3, 3), (3, -1)]:
            with self.assertRaises(ValueError):
                TextChunker(size, overlap)
        with self.assertRaises(FileNotFoundError):
            read_pdf(str(self.directory / "missing.pdf"))
        with self.assertRaises(ValueError):
            read_document(self.directory / "manual.csv")

    def test_cli_report_and_empty_input_preserves_output(self):
        inputs = self.directory / "inputs"
        inputs.mkdir()
        output = self.directory / "report.json"
        command = [sys.executable, "-m", "app.ingest", "--input-dir", str(inputs), "--output", str(output)]
        output.write_text("previous output")
        process = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(output.read_text(), "previous output")
        (inputs / "manual.txt").write_text("FAN-12 is 12 V")
        process = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(output.read_text())["chunks"][0]["source"], "manual.txt")


if __name__ == "__main__":
    unittest.main()
