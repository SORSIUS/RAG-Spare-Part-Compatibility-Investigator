import json
import tempfile
import unittest
from pathlib import Path
from shutil import copytree
from app.repository import Repository
from app.service import DemoService
from app.comparison import compare_parts

class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.data=Path(temporary.name)/'data';copytree(Path(__file__).resolve().parents[1]/'data'/'sample',self.data/'sample')
        self.repo=Repository(self.data);self.service=DemoService(self.repo,{})

    def test_three_distinct_verdicts(self):
        self.assertEqual([c['verdict'] for c in self.service.run({})['candidates']],['match','conflict','unknown'])

    def test_voltage_conflict_contains_real_values_and_source(self):
        candidate=self.service.run({})['candidates'][1]
        check=next(c for c in candidate['checks'] if c['key']=='voltage')
        self.assertEqual((check['actual'],check['required'],check['status'],check['source']),('24 V','12 V','conflict','CAT-03'))

    def test_missing_connector_remains_unknown(self):
        check=self.service.run({})['candidates'][2]['checks'][2]
        self.assertEqual(check['status'],'unknown');self.assertEqual(check['actual'],'Not documented')

    def test_bulletin_resolves_only_the_documented_field(self):
        result=self.service.run({'bulletin':True})
        candidate=result['candidates'][2]
        self.assertEqual(candidate['verdict'],'match');self.assertEqual(candidate['checks'][2]['source'],'SB-05')
        self.assertEqual(candidate['checks'][0]['source'],'CAT-04')

    def test_airflow_is_minimum_not_exact_match(self):
        sample=self.repo.sample
        sample['parts'][1]['airflow']=29
        result=compare_parts(sample,'FAN-12')
        self.assertEqual(result['candidates'][0]['checks'][3]['status'],'conflict')

    def test_source_absence_cannot_create_a_confirmed_match(self):
        self.repo.sample['documents']=[d for d in self.repo.sample['documents'] if d['id']!='CAT-02']
        self.assertEqual(self.service.run({})['candidates'][0]['verdict'],'unknown')

    def test_all_sources_resolve(self):
        result=self.service.run({'bulletin':True});ids={d['id'] for d in result['documents']}
        self.assertTrue(all(c['source'] in ids and c['original_source'] in ids for item in result['candidates'] for c in item['checks']))

    def test_investigation_does_not_mutate_sample_or_write_state(self):
        before=json.dumps(self.repo.sample,sort_keys=True)
        self.service.run({'bulletin':True})
        self.assertEqual(json.dumps(self.repo.sample,sort_keys=True),before)
        self.assertEqual(self.service.run({})['candidates'][2]['verdict'],'unknown')
        self.assertEqual(self.repo.snapshot()['commits'],[])

    def test_invalid_inputs_and_installation_confirmation(self):
        for payload in [[],{'query':'UNKNOWN'},{'bulletin':'yes'},{'query':4}]:
            with self.assertRaises(ValueError):self.service.run(payload)
        with self.assertRaises(ValueError):self.service.confirm('anything')

if __name__=='__main__':unittest.main()
