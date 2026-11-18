import test from 'node:test';
import assert from 'node:assert/strict';
import {request} from '../src/services/api.js';
import {safePdfUrl, sourceLabel} from '../src/components/sources.js';

test('status contract rejects a stale backend', async () => {
  await assert.rejects(request('status', undefined, async () => ({ok: true, json: async () => ({status: 'old'})})), /older backend/);
});
test('API preserves the question and conversation fields', async () => {
  const body = {question: 'DCF002K size?', conversation_id: null, mode: 'evidence'};
  await request('chat', body, async (url, options) => { assert.equal(url, '/api/chat'); assert.deepEqual(JSON.parse(options.body), body); return {ok: true, json: async () => ({claims: [], sources: []})}; });
});
test('provider errors are readable', async () => {
  await assert.rejects(request('chat', {}, async () => ({ok: false, json: async () => ({error: {message: 'Groq rate limit reached'}})})), /rate limit/);
});
test('unreadable upstream response produces a useful error', async () => {
  await assert.rejects(request('status', undefined, async () => ({ok: true, json: async () => { throw new Error('html'); }})), /unreadable response/);
});
test('chat rejects responses missing the sources contract', async () => {
  await assert.rejects(request('chat', {}, async () => ({ok: true, json: async () => ({text: 'old version'})})), /does not match/);
});
test('only locally served fingerprinted PDF page links are accepted', () => {
  assert.ok(safePdfUrl('/api/catalogue/pdf?version=' + 'a'.repeat(64) + '#page=97'));
  for (const value of ['javascript:alert(1)', 'https://example.com/file.pdf', '/api/catalogue/pdf#page=0', '/api/catalogue/pdf?version=invalid#page=1', undefined]) assert.equal(safePdfUrl(value), null);
});
test('source label keeps page numbering explicit', () => {
  assert.equal(sourceLabel({id: 'S1', page_number: 97}), 'S1 · PDF page 97');
  assert.equal(sourceLabel({id: 'S1', page_number: 0}), 'Source page unavailable');
});

test('uploaded document links require a hash and positive page', () => {
  assert.ok(safePdfUrl('/api/documents/' + 'a'.repeat(64) + '/pdf#page=2'));
  for (const value of ['/api/documents/../../.env/pdf#page=1', '/api/documents/' + 'a'.repeat(64) + '/pdf#page=0', 'https://example.com/api/documents/' + 'a'.repeat(64) + '/pdf#page=1']) assert.equal(safePdfUrl(value), null);
});
