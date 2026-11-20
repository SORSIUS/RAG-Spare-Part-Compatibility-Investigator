import test from 'node:test';
import assert from 'node:assert/strict';
import {recoveryText} from '../src/components/chat-feedback.js';
import {ApiError} from '../src/services/api.js';

test('chat recovery offers a next step for limits and transport errors', () => {
  assert.match(recoveryText(new ApiError('limit', 429, 'provider_rate_limit')), /moment/);
  assert.match(recoveryText(new Error('The request timed out.')), /shorter question/);
  assert.match(recoveryText(new TypeError('Failed to fetch')), /kept your question/);
  assert.match(recoveryText(new ApiError('missing chat', 404, 'missing')), /new conversation/);
});
