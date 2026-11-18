import test from 'node:test';
import assert from 'node:assert/strict';
import {comparisonMarkdown, dimensionValue} from '../src/components/comparison.js';
import {request} from '../src/services/api.js';

test('dimension cells distinguish missing and conflicting source values', () => {
  assert.equal(dimensionValue([]), 'Not documented');
  assert.equal(dimensionValue([238.5]), '238.5 mm');
  assert.equal(dimensionValue([100, 120]), '100 mm / 120 mm');
});

test('comparison report preserves evidence, hash, unknowns, and fitment limit', () => {
  const evidence = {source: 'fixture.pdf', page_number: 97, quote: 'DCF901P length 100mm', pdf_url: '/api/catalogue/pdf?version=' + 'a'.repeat(64) + '#page=97'};
  const result = {original: 'DCF901P', candidate: 'DCF902P', brand: null, status: 'unknown', explanation: 'Insufficient evidence.', source_sha256: 'a'.repeat(64), created_at: '2026-11-18', dimension_checks: [{field: 'length_mm', status: 'unknown', original_values: [100], candidate_values: [], evidence: [evidence, evidence]}], cross_reference_evidence: [], cross_reference_status: 'unknown', vehicle_fitment: 'unknown', notice: 'Catalogue evidence is not installation approval.'};
  const report = comparisonMarkdown(result);
  assert.match(report, /Not documented/); assert.match(report, /PDF page 97/); assert.ok(report.includes('a'.repeat(64)));
  assert.equal(report.split(evidence.quote).length - 1, 1); assert.match(report, /not installation approval/);
});

test('comparison rejects a stale or malformed backend contract', async () => {
  await assert.rejects(request('catalogue/compare', {}, async () => ({ok: true, json: async () => ({status: 'old'})})), /comparison response is incompatible/);
});
