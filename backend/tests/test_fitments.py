import tempfile
import unittest
from pathlib import Path

from app.repositories.fitments import FitmentRepository
from app.services.kyb_fitment_parser import parse_rows
from app.services.fitment_answer import fitment_answer
from app.services.answer_service import validate_citations, CitationError
from app.services.hybrid_retrieval import retrieve_sources


class FitmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = FitmentRepository(Path(self.temp.name))
        self.sha = 'a' * 64
        self.rows = [
            ['COROLLA S', 'EDAN / COROLLA HATCH', 'BACK / AUR', 'IS'] + [''] * 8,
            ['07/10-On', 'NZE151,ZRE151,ZRE152 1.8 L EFI', 'NST5387R\nNST5387L', '4833112220\n4815742030', 'SB2015\nSB5176', '4860912500', 'SM7210', '349035', '4834112220', '', '4875512100', ''],
            ['RAV4'] + [''] * 11,
            ['12/10-18/12', 'ACA40 2.0L', '3350001', '', '', '', '', '349024', '', '', '', '']]
        self.records = parse_rows(self.rows, 'TOYOTA', 96, 'catalogue.pdf', self.sha)
        self.repo.replace_source(self.sha, 'catalogue.pdf', 'test', 'https://example.test/catalogue.pdf', 1, self.records)

    def test_columns_do_not_turn_oem_groups_into_individual_pairs(self):
        records = self.repo.search('Toyota', 'Corolla')['records']
        self.assertEqual(len(records), 6)
        kit = next(r for r in records if r['part_number'] == 'SB2015')
        self.assertEqual(kit['axle'], 'front')
        self.assertEqual(kit['oem_group'], ['4833112220', '4815742030'])
        self.assertEqual(next(r for r in records if r['part_number'] == '349035')['axle'], 'rear')

    def test_numeric_model_heading_cannot_leak_previous_vehicle(self):
        self.assertEqual(self.repo.search('Toyota', 'Corolla', part='3350001')['total'], 0)
        self.assertEqual(self.repo.search('Toyota', 'Rav4', part='3350001')['total'], 1)

    def test_no_substring_chassis_or_preproduction_year_match(self):
        self.assertEqual(self.repo.search('Toyota', 'Corolla', year=2006)['total'], 0)
        self.assertEqual(self.repo.search('Toyota', 'Corolla', chassis='ZRE15')['total'], 0)
        self.assertEqual(self.repo.search('Toyota', 'Corolla', year=2012, chassis='ZRE152')['total'], 6)

    def test_index_reimport_is_idempotent_and_evidence_keeps_hash(self):
        self.repo.replace_source(self.sha, 'catalogue.pdf', 'test', 'https://example.test/catalogue.pdf', 1, self.records)
        self.assertEqual(self.repo.options()['record_count'], len(self.records))
        record = self.repo.search('Toyota', 'Corolla', limit=1)['records'][0]
        evidence = self.repo.evidence(record)
        self.assertIn(self.sha, evidence['pdf_url'])
        self.assertIn('not installation approval', evidence['content'])
        self.assertIn('columns', evidence['raw_excerpt'])

    def test_duplicate_header_and_ambiguous_page_continuation_are_skipped(self):
        rows = [['YYYeeeaaarr', 'AAApppllliiicccaaatttiiiooonnn'] + [''] * 10, self.rows[1]]
        self.assertEqual(parse_rows(rows, 'TOYOTA', 97, 'catalogue.pdf', self.sha), [])

    def test_question_lookup_is_vehicle_specific_and_avoids_two_car_swap(self):
        result = self.repo.question_sources('Which front suspension parts for Toyota Corolla 2012 ZRE152?', 8)
        self.assertTrue(result)
        self.assertTrue(all('front' in source['content'] for source in result))
        self.assertEqual(self.repo.question_sources('Can I swap Corolla suspension into a City?', 8), [])
        self.assertEqual(self.repo.question_sources('quantum banana recipe', 8), [])

    def test_checked_fallback_preserves_printed_dates_and_citation_checks(self):
        sources = [{**source, 'id': 'S' + str(i + 1)} for i, source in enumerate(self.repo.question_sources('Toyota Corolla front suspension KYB NST5387L', 8))]
        answer = fitment_answer(sources)
        validate_citations(answer, sources)
        self.assertIn('07/10-On', answer.claims[0].text)
        self.assertNotIn('2010', answer.claims[0].text)
        self.assertIsNone(fitment_answer([{'section': 'document_passage'}]))

    def test_linked_fast_path_never_runs_broad_document_search(self):
        repo = self.repo
        class Library:
            def linked_sources(self, query, limit):
                return repo.question_sources(query, limit)
            def search(self, *args):
                raise AssertionError('Broad semantic search should not run')
        class Lexical:
            def retrieve(self, *args):
                raise AssertionError('Broad lexical search should not run')
        result = retrieve_sources(Lexical(), Library(), 'Toyota Corolla front suspension 2012 ZRE152', 8)
        self.assertTrue(result)
        self.assertEqual(result[0]['retrieval_method'], 'indexed vehicle-part link')

    def test_fabricated_kyb_identifier_is_rejected(self):
        sources = [{**source, 'id': 'S' + str(i + 1)} for i, source in enumerate(self.repo.question_sources('Toyota Corolla front suspension KYB NST5387L', 8))]
        answer = fitment_answer(sources)
        answer.claims[0].text = answer.claims[0].text.replace('NST5387L', 'NST9999L')
        with self.assertRaises(CitationError):
            validate_citations(answer, sources)


    def test_pakistan_candidates_are_retained_without_claiming_market_fit(self):
        sources=self.repo.question_sources('Toyota Corolla 2012 1.8 Pakistan front suspension',8)
        self.assertTrue(sources)
        self.assertTrue(all(source['market_unconfirmed'] for source in sources))
        self.assertTrue(all(source['requested_market']=='Pakistan' for source in sources))
        self.assertTrue(all('front' in source['content'] for source in sources))

if __name__ == '__main__':
    unittest.main()
