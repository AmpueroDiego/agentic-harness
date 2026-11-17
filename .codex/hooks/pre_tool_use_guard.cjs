'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

function deny(reason) {
  process.stdout.write(JSON.stringify({ hookSpecificOutput: {
    hookEventName: 'PreToolUse', permissionDecision: 'deny', permissionDecisionReason: reason
  } }));
}
function runGit(args, cwd, maxBuffer = 16 * 1024 * 1024) {
  return spawnSync('git', args, { cwd, encoding: null, maxBuffer, windowsHide: true });
}
function targetCwd(command, cwd) {
  const match = command.match(/\bgit(?:\.exe)?\s+-C\s+(?:"([^"]+)"|'([^']+)'|(\S+))/i);
  if (!match) return cwd;
  const target = match[1] || match[2] || match[3];
  return path.resolve(cwd, target);
}
function hasSensitiveStagedContent(command, cwd) {
  const repo = targetCwd(command, cwd);
  const root = runGit(['rev-parse', '--show-toplevel'], repo, 1024 * 1024);
  if (root.error || root.status !== 0) return null; // Not a repository; Git itself will reject the commit.
  const gitRoot = root.stdout.toString('utf8').trim();
  const listed = runGit(['diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'], gitRoot);
  if (listed.error || listed.status !== 0) return 'Could not inspect the staged files safely; commit blocked.';
  const files = listed.stdout.toString('utf8').split('\0').filter(Boolean);
  const binaryExt = /\.(?:png|jpe?g|gif|ico|pdf|zip|7z|rar|gz|woff2?|ttf|eot|dll|exe|pdb|so|pyc|class|jar|mp4|webm)$/i;
  const signatures = [
    /-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----/,
    /\bAKIA[0-9A-Z]{16}\b/,
    /\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b/,
    /\bxox[baprs]-[A-Za-z0-9-]{10,}\b/,
    /(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd|secret)\s*[:=]\s*["']([^"'\r\n]{12,})["']/i
  ];
  const placeholder = /^(?:example|placeholder|replace[_ -]?me(?:[_ -]?example)?|change[_ -]?me|dummy|fake|test)$/i;
  for (const file of files) {
    if (binaryExt.test(file)) continue;
    const blob = runGit(['show', `:${file}`], gitRoot, 8 * 1024 * 1024);
    if (blob.error || blob.status !== 0) return `Could not inspect staged file ${file}; commit blocked.`;
    if (blob.stdout.length >= 8 * 1024 * 1024) return `Staged file ${file} is too large to scan safely; commit blocked.`;
    if (blob.stdout.includes(0)) continue;
    const text = blob.stdout.toString('utf8');
    for (const signature of signatures) {
      const scan = new RegExp(signature.source, `${signature.flags}g`);
      for (const match of text.matchAll(scan)) {
        const value = match[1] || match[0];
        if (placeholder.test(value)) continue;
        return `Staged file ${file} matches a secret pattern (${signature.source.includes('PRIVATE KEY') ? 'private key' : 'credential-like value'}); value redacted, commit blocked.`;
      }
    }
  }
  return null;
}
function unboundedRead(command, cwd) {
  const match = command.match(/\b(?:cat|type|Get-Content|gc)\b(?:\s+-(?:Raw|LiteralPath|Path)\b)*\s+(?:"([^"]+)"|'([^']+)'|([^\s;&|]+))/i);
  if (!match) return null;
  const segmentEnd = command.slice(match.index).search(/[;&|]/);
  const readSegment = segmentEnd < 0 ? command.slice(match.index) : command.slice(match.index, match.index + segmentEnd);
  if (!/\b-Raw\b/i.test(readSegment) && /-(?:TotalCount|First|Skip)\b/i.test(readSegment)) return null;
  const file = match[1] || match[2] || match[3];
  if (!file || file.startsWith('-') || /(?:^|[\\/])\.env(?:\.(?:example|sample|template))?$/i.test(file)) return null;
  const absolute = path.resolve(cwd, file);
  try {
    if (!fs.statSync(absolute).isFile()) return null;
    const input = fs.readFileSync(absolute, 'utf8');
    const lines = input.split(/\r?\n/).length;
    return lines > 350 ? `Unbounded full read blocked: ${file} has ${lines} lines. Use rg or a bounded read (offset/limit, Select-Object -First, or sed -n).` : null;
  } catch (_) { return null; }
}

let event;
try { event = JSON.parse(fs.readFileSync(0, 'utf8')); }
catch (_) { deny('Could not parse the hook request; refusing this shell action.'); process.exit(0); }
if ((event.tool_name || '') !== 'Bash') process.exit(0);
const command = String((event.tool_input || {}).command || '');
const cwd = String(event.cwd || process.cwd());
const destructive = [
  [/\bgit(?:\.exe)?(?:\s+-C\s+(?:"[^"]+"|'[^']+'|\S+))?\s+push\b[^\r\n;&|]*--force(?:-with-lease)?\b/i, 'Force-push is blocked by workspace policy.'],
  [/\bgit(?:\.exe)?(?:\s+-C\s+(?:"[^"]+"|'[^']+'|\S+))?\s+reset\b[^\r\n;&|]*--hard\b/i, 'Hard reset is blocked because it discards work. Use a reversible recovery plan.'],

  [/^\s*(?:printenv|env|set)\s*$/im, 'Dumping the full environment is blocked to avoid exposing credentials.'],
  [/\b(?:Get-ChildItem|gci)\s+Env:/i, 'Dumping the full environment is blocked to avoid exposing credentials.'],
  [/\b(?:cat|type|Get-Content|gc)\b[^\r\n;&|]*(?:^|[\\\/\s"'])\.env(?:\.(?:local|production|development|staging|test))?(?=$|[\\\/\s"'])/i, 'Reading secret-bearing .env files through shell is blocked. Use the project\'s documented secret manager without printing values.']
];
for (const [pattern, reason] of destructive) if (pattern.test(command)) { deny(reason); process.exit(0); }
const cleanCommand = command.match(/\bgit(?:\.exe)?(?:\s+-C\s+(?:"[^"]+"|'[^']+'|\S+))?\s+clean\b([^\r\n;&|]*)/i);
if (cleanCommand) {
  const options = cleanCommand[1].match(/(?:^|\s)-[a-z]+/ig) || [];
  const flags = options.join('').toLowerCase();
  if (flags.includes('f') && flags.includes('d') && flags.includes('x') || /--(?:force|dir|ignored)\b/i.test(cleanCommand[1])) {
    deny('Bulk git clean is blocked by workspace policy.'); process.exit(0);
  }
}
const readBlock = unboundedRead(command, cwd);
if (readBlock) { deny(readBlock); process.exit(0); }
if (/\bgit(?:\.exe)?(?:\s+-C\s+(?:"[^"]+"|'[^']+'|\S+))?\s+commit\b/i.test(command)) {
  const secretBlock = hasSensitiveStagedContent(command, cwd);
  if (secretBlock) { deny(secretBlock); process.exit(0); }
}
process.exit(0);
