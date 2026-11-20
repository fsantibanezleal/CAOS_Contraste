// The chunk-size gate (BL-102): every application JS chunk of a build is under the template's 500 KB target.
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { test } from 'node:test';
import { checkChunkSizes, LIMIT_BYTES } from './check-chunk-sizes.mjs';

function dist(t, files) {
  const temp = process.env.CAOS_TEMP_ROOT || tmpdir();
  mkdirSync(temp, { recursive: true });
  const base = mkdtempSync(join(resolve(temp), 'chunk-fixture-'));
  t.after(() => rmSync(base, { recursive: true, force: true }));
  mkdirSync(join(base, 'assets'));
  for (const [name, size] of Object.entries(files)) writeFileSync(join(base, 'assets', name), Buffer.alloc(size, 97));
  return base;
}

test('the limit is 500 KB (500,000 bytes)', () => assert.equal(LIMIT_BYTES, 500_000));

test('passes when every .js chunk is under the limit and ignores other files', (t) => {
  const r = checkChunkSizes(dist(t, { 'a-1.js': 499_999, 'b-2.js': 10, 'font.woff2': 900_000 }));
  assert.equal(r.failures.length, 0);
  assert.equal(r.chunks.length, 2);
});

test('fails each chunk at or over the limit, naming it, largest first in the list', (t) => {
  const r = checkChunkSizes(dist(t, { 'Workbench-1.js': 500_000, 'ok-2.js': 5, 'Methodology-3.js': 913_096 }));
  assert.deepEqual(r.failures.map((f) => f.name), ['Methodology-3.js', 'Workbench-1.js']);
  assert.equal(r.chunks[0].name, 'Methodology-3.js');
});

test('fails a dist without assets', (t) => {
  const base = mkdtempSync(join(resolve(process.env.CAOS_TEMP_ROOT || tmpdir()), 'chunk-empty-'));
  t.after(() => rmSync(base, { recursive: true, force: true }));
  assert.throws(() => checkChunkSizes(base), /assets/);
});
