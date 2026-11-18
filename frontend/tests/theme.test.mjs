import test from 'node:test';
import assert from 'node:assert/strict';
import {readTheme, initializeTheme} from '../src/services/theme.js';

test('theme persists across page initialization and handles blocked storage', () => {
  const data = new Map();
  const storage = {getItem: key => data.get(key), setItem: (key, value) => data.set(key, value)};
  const button = {setAttribute() {}}, root = {dataset: {}};
  initializeTheme(button, root, storage);
  assert.equal(root.dataset.theme, 'light');
  button.onclick();
  assert.equal(root.dataset.theme, 'dark');
  const restored = {dataset: {}};
  initializeTheme({setAttribute() {}}, restored, storage);
  assert.equal(restored.dataset.theme, 'dark');
  assert.equal(readTheme({getItem() {throw Error('blocked');}}, true), 'dark');
  assert.equal(readTheme({getItem: () => 'invalid'}, false), 'light');
});
