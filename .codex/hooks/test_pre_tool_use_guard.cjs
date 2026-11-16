'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync, execFileSync } = require('node:child_process');
const guard = path.join(__dirname, 'pre_tool_use_guard.cjs');
function event(command, cwd = process.cwd(), tool_name = 'Bash') {
  const result = spawnSync(process.execPath, [guard], { input: JSON.stringify({ tool_name, tool_input: { command }, cwd }), encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout ? JSON.parse(result.stdout).hookSpecificOutput : null;
}
test('blocks hard reset, bulk clean, and force push', () => {
  assert.match(event('git reset --hard').permissionDecisionReason, /Hard reset/);
  assert.match(event('git clean -fdx').permissionDecisionReason, /Bulk git clean/);
  assert.match(event('git clean -dfx').permissionDecisionReason, /Bulk git clean/);
  assert.match(event('git push --force-with-lease origin main').permissionDecisionReason, /Force-push/);
});
test('blocks environment dumps and secret-bearing env reads without printing values', () => {
  assert.match(event('Get-ChildItem Env:').permissionDecisionReason, /environment/);
  assert.match(event('Get-Content .env').permissionDecisionReason, /\.env/);
  assert.match(event('type .env.local').permissionDecisionReason, /\.env/);
  assert.equal(event('Get-Content .env.example'), null);
});
test('blocks unbounded large file reads and permits bounded reads', (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-guard-read-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const file = path.join(dir, 'large.txt');
  fs.writeFileSync(file, Array.from({ length: 351 }, (_, i) => `line ${i}`).join('\n'));
  assert.match(event(`Get-Content -Raw "${file}"`, dir).permissionDecisionReason, /351 lines/);
  assert.equal(event(`Get-Content -TotalCount 20 "${file}"`, dir), null);
});
test('blocks staged synthetic credentials without revealing the value', (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-guard-secret-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  execFileSync('git', ['init', '-q'], { cwd: dir });
  const fake = 'ghp_' + '0'.repeat(36);
  fs.writeFileSync(path.join(dir, 'fixture.txt'), `token = "${fake}"\n`);
  execFileSync('git', ['add', 'fixture.txt'], { cwd: dir });
  const result = event('git commit -m "fixture"', dir);
  assert.equal(result.permissionDecision, 'deny');
  assert.match(result.permissionDecisionReason, /value redacted/);
  assert.equal(result.permissionDecisionReason.includes(fake), false);
});
test('allows staged placeholders and normal status commands', (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'codex-guard-safe-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  execFileSync('git', ['init', '-q'], { cwd: dir });
  fs.writeFileSync(path.join(dir, 'fixture.txt'), 'api_key = "REPLACE_ME_EXAMPLE"\n');
  execFileSync('git', ['add', 'fixture.txt'], { cwd: dir });
  assert.equal(event('git commit -m "fixture"', dir), null);
  assert.equal(event('git status --short', dir), null);
});
