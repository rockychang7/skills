#!/usr/bin/env node
// docs.mjs — helper for the rein-managing-project-docs skill: setup / where / init / check / backup / restore / group
// No dependencies, Node 18+. It ships inside the skill and is replaced when the skill is upgraded,
// so it holds nothing of any one person. A person's own data lives outside the skill:
//   config file: ~/.config/rein-managing-project-docs/config.json, {"store": "<path>"} or {"store": null}
//   registry:    <store>/projects.json when there is a store (it travels with the store to other computers);
//                otherwise projects.json next to the config file
//   this computer: local.json next to the config file: where each project sits here and its last backup
//   RMPD_HOME replaces the config folder, RMPD_STORE the store, and RMPD_RULES_HOME the home folder setup installs
//   the global rules under (all three for tests)
// The conventions are in ../references/conventions.md. This script only does what a program can judge.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const SKILL_NAME = 'rein-managing-project-docs';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const SKILL_DIR = path.resolve(HERE, '..');
const CONFIG_DIR = canon(process.env.RMPD_HOME || path.join(os.homedir(), '.config', SKILL_NAME));
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');
const LOCAL_FILE = path.join(CONFIG_DIR, 'local.json');
const CONFIG = (() => { try { return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8')); } catch { return null; } })();
const storeSetting = process.env.RMPD_STORE || CONFIG?.store || null;
// The store is optional: it only backs up documents that are not committed.
const STORE = storeSetting ? canon(storeSetting) : null;
const REGISTRY = STORE ? path.join(STORE, 'projects.json') : path.join(CONFIG_DIR, 'projects.json');
const NO_STORE = `This computer has no store, so documents that are not committed have no backup. If the user wants one, create it first: its name and location are the user's to choose; ask if they have not said (skill ${SKILL_NAME}, section 1). Then run docs.mjs setup --store <path> --apply`;

// Documents made while working with an agent live in docs/process/; the project's own documents sit at fixed places (OWN).
const DOCS = 'docs/process';
const TYPES = {
  work: 'work folders',
  decisions: 'decision records',
  notes: 'notes',
  explain: 'explainers',
};
// Folders in docs/process/ that another skill keeps; nothing inside them is checked
const OWNED = {
  requirements: 'the requirements skill (rein-analyzing-requirements) keeps its own folder here',
};
// The project's own documents: this skill fixes their names and places; their content is the project's.
const OWN = [
  { path: 'AGENTS.md', what: 'rules for agents' },
  { path: 'CLAUDE.md', what: 'only the line @AGENTS.md' },
  { path: 'docs/ARCHITECTURE.md', what: 'code map' },
  { path: 'docs/CONVENTION.md', alt: 'docs/conventions', what: 'coding conventions' },
  { path: 'docs/CONTEXT.md', what: 'business terms (optional)' },
];
// The same documents under other names: where each belongs
const OWN_ALIASES = [
  { re: /^(?:architecture|arch)(?:[-_ .][^/]*)?\.md$/i, to: 'docs/ARCHITECTURE.md', what: 'code map' },
  { re: /^conventions?(?:[-_ .][^/]*)?\.md$/i, to: 'docs/CONVENTION.md', what: 'coding conventions' },
  { re: /^(?:context|glossary)(?:[-_ .][^/]*)?\.md$/i, to: 'docs/CONTEXT.md', what: 'business terms' },
];
// AGENTS.md keeps a short "where documents are" section between these markers
const MAP_BEGIN = `<!-- ${SKILL_NAME}:docs-map -->`;
const MAP_END = `<!-- /${SKILL_NAME}:docs-map -->`;
const RULES_MAX_LINES = 200;
// Version 0.1 kept four types under docs/ or in the store, type by type
const LEGACY_TYPES = ['internals', 'decisions', 'work', 'notes'];
const DATED = /^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$/;
const KEBAB = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const HAS_DATE = /^\d{4}-?\d{2}-?\d{2}[-_]/;
const VERSIONY = /(?:[-_. ](?:v\d+|final|new|old|copy|bak|backup|draft\d*)|\(\d+\))$/i;
// Names that working documents usually get when an agent drops them at the project root or the root of docs/
const DOC_EXT = '(?:md|markdown|html?|txt)';
const STRAY_PREFIX = new RegExp(`^(?:plan|plans|todo|todos|notes?|summary|design|spec|specs|tasks|report|analysis|decision|decisions|progress|handoff|implementation|proposal|research|findings|review|scratch|draft|explainer)(?:[-_ .].*)?\\.${DOC_EXT}$`, 'i');
const STRAY_SUFFIX = new RegExp(`[-_ .](?:plan|summary|design|spec|proposal|notes|report|analysis|todo|tasks|decision|findings|handoff|progress)\\.${DOC_EXT}$`, 'i');
const IS_DOC = new RegExp(`\\.${DOC_EXT}$`, 'i');
const ACTIVE_DAYS = 30;
const MAX_BACKUP_BYTES = 20 * 1024 * 1024;
// Tools with a document home of their own: their folders belong to the tool and are skipped.
// The config file's toolDirs can add more.
const TOOL_DIRS = ['.rein/', '.kiro/', '.specify/', 'openspec/', ...((CONFIG && CONFIG.toolDirs) || [])].map((d) => (d.endsWith('/') ? d : d + '/'));
const toolOwned = (rel) => TOOL_DIRS.some((d) => rel.startsWith(d));

/* ---------- helpers ---------- */

const posix = (p) => p.split(path.sep).join('/');
const show = (p) => posix(p);
const list = (items) => items.join(', ');
const indent = (text) => text.split('\n').map((l) => `    ${l}`).join('\n');
// Hidden and system files: never checked, never backed up (a .env in a scripts/ folder stays on this computer)
const isClutter = (name) => name.startsWith('.') || ['Thumbs.db', 'desktop.ini'].includes(name);
// The part of a name before its first dot: names are checked without their extension, whatever the format
const stemOf = (name) => name.replace(/^([^.]+)\..*$/, '$1');

function git(args, cwd) {
  try {
    return execFileSync('git', args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], maxBuffer: 256 * 1024 * 1024 }).replace(/\r?\n$/, '');
  } catch {
    return null;
  }
}

function gitBuf(args, cwd) {
  try {
    return execFileSync('git', args, { cwd, stdio: ['ignore', 'pipe', 'ignore'], maxBuffer: 256 * 1024 * 1024 });
  } catch {
    return null;
  }
}

function repoRoot(dir) {
  const out = git(['rev-parse', '--show-toplevel'], dir);
  return out ? path.resolve(out) : null;
}

// Worktrees share one project name: use the main repository's folder
function mainRoot(dir) {
  const common = git(['rev-parse', '--path-format=absolute', '--git-common-dir'], dir);
  if (common && path.basename(common) === '.git') return path.dirname(path.resolve(common));
  return repoRoot(dir);
}

function normRemote(url) {
  return String(url).trim().toLowerCase()
    .replace(/^[a-z+]+:\/\//, '')
    .replace(/^[^@/]+@/, '')
    .replace(':', '/')
    .replace(/\.git$/, '')
    .replace(/\/+$/, '');
}

function slug(name) {
  return String(name).trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'project';
}

// Windows writes one path two ways (a short 8.3 name such as LONGNA~1 and the long name) and ignores case; resolve the real path before comparing
function canon(p) {
  let base = path.resolve(p);
  const rest = [];
  while (!fs.existsSync(base) && path.dirname(base) !== base) { rest.unshift(path.basename(base)); base = path.dirname(base); }
  try { base = fs.realpathSync.native(base); } catch { /* keep it as it is */ }
  return path.join(base, ...rest);
}

function isInside(child, parent) {
  const rel = path.relative(canon(parent), canon(child));
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
}

function samePath(a, b) {
  const norm = (p) => (process.platform === 'win32' ? canon(p).toLowerCase() : canon(p));
  return norm(a) === norm(b);
}

function readOr(file) {
  try { return fs.readFileSync(file); } catch { return null; }
}

// Same content, ignoring CRLF against LF in text (git on Windows may check text files out with CRLF)
function sameBuf(a, b) {
  if (!a || !b) return a === b;
  if (a.equals(b)) return true;
  const norm = (buf) => (buf.subarray(0, 8000).includes(0) ? buf : Buffer.from(buf.toString('utf8').replace(/\r\n/g, '\n')));
  return norm(a).equals(norm(b));
}

// Every file under dir, as paths relative to it with forward slashes
function listFiles(dir) {
  const out = [];
  const walk = (d, prefix) => {
    let entries;
    try { entries = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (e.name === '.git' || e.isSymbolicLink()) continue;
      const rel = prefix ? `${prefix}/${e.name}` : e.name;
      if (e.isDirectory()) walk(path.join(d, e.name), rel);
      else if (e.isFile()) out.push(rel);
    }
  };
  walk(dir, '');
  return out.sort();
}

function daysSince(dateText) {
  const t = Date.parse(dateText);
  return Number.isNaN(t) ? null : Math.floor((Date.now() - t) / 86400000);
}

function option(args, name) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : null;
}

/* ---------- registry and this computer's state ---------- */

// Version 0.1 said, type by type, whether it went in the repository (in_repo); now one switch says whether docs/process/ is committed.
function legacyCommit(value) {
  if (value === 'all') return true;
  if (value === 'none') return false;
  const types = Array.isArray(value) ? value : typeof value === 'string' ? value.split(',').map((s) => s.trim()).filter(Boolean) : null;
  if (!types) return null;
  if (!types.length) return false;
  if (LEGACY_TYPES.every((t) => types.includes(t))) return true;
  return null; // some types in the repository and some in the store: that no longer exists, so it needs a new decision
}

function upgradeRegistry(data) {
  const fix = (o) => {
    if (!o || !('in_repo' in o)) return;
    const c = legacyCommit(o.in_repo);
    if (c === null) o.legacy_in_repo = o.in_repo;
    else o.commit = c;
    delete o.in_repo;
  };
  for (const entry of Object.values(data.projects)) fix(entry);
  for (const rule of Array.isArray(data.groups) ? data.groups : []) fix(rule);
  if (data.defaults) {
    fix(data.defaults);
    if (data.defaults.legacy_in_repo !== undefined) delete data.defaults.legacy_in_repo;
  }
  data.version = 2;
  return data;
}

function loadRegistry() {
  if (!fs.existsSync(REGISTRY)) return { version: 2, projects: {} };
  const data = JSON.parse(fs.readFileSync(REGISTRY, 'utf8'));
  data.projects ??= {};
  return data.version === 2 ? data : upgradeRegistry(data);
}

// Saved in the store, the registry is committed there at once (never pushed), so the store stays clean
function saveRegistry(data, message) {
  fs.mkdirSync(path.dirname(REGISTRY), { recursive: true });
  fs.writeFileSync(REGISTRY, JSON.stringify({ ...data, version: 2 }, null, 2) + '\n');
  if (!STORE || !repoRoot(STORE) || !samePath(repoRoot(STORE), STORE)) return true;
  if (!git(['status', '--porcelain', '--', 'projects.json'], STORE)) return true;
  return git(['add', '--', 'projects.json'], STORE) !== null && git(['commit', '-q', '-m', message || 'Update the registry', '--', 'projects.json'], STORE) !== null;
}

// This computer only (paths differ from computer to computer): where each project sits, and its last backup
function loadLocal() {
  try {
    const data = JSON.parse(fs.readFileSync(LOCAL_FILE, 'utf8'));
    data.projects ??= {};
    return data;
  } catch {
    return { projects: {} };
  }
}

function saveLocal(data) {
  fs.mkdirSync(CONFIG_DIR, { recursive: true });
  fs.writeFileSync(LOCAL_FILE, JSON.stringify(data, null, 2) + '\n');
}

function remember(local, p, backup) {
  const prev = local.projects[p.id] || {};
  local.projects[p.id] = { ...prev, path: show(p.base), ...(backup ? { backup } : {}) };
}

function describeRule(rule, i) {
  return `group rule ${i + 1} (${rule.remote ? `remote ${rule.remote}` : `folder ${rule.folder}`})`;
}

function switchText(commit) {
  return commit
    ? 'commit docs/process/ with the code'
    : 'do not commit docs/process/ (ignored on this computer, backed up to the store)';
}

// The first group rule that matches: by the start of a remote URL, or by the folder the project sits in
function matchGroup(registry, base, remotes) {
  const groups = Array.isArray(registry.groups) ? registry.groups : [];
  for (let i = 0; i < groups.length; i++) {
    const rule = groups[i];
    if (rule.remote) {
      const pre = normRemote(rule.remote);
      if (pre && remotes.some((r) => r === pre || r.startsWith(pre + '/'))) return { rule, i };
    } else if (rule.folder && base && isInside(base, rule.folder)) {
      return { rule, i };
    }
  }
  return null;
}

// Which project the current folder belongs to, and whether it commits docs/process/.
// Order: the project's own registry entry → the first matching group rule → defaults.commit → not decided.
function resolveProject(cwd) {
  const root = repoRoot(cwd);
  const base = root ? mainRoot(cwd) : path.resolve(cwd);
  const folder = path.basename(base);
  const remotes = root
    ? [...new Set((git(['remote', '-v'], root) || '').split(/\r?\n/).map((l) => l.split(/\s+/)[1]).filter(Boolean).map(normRemote))]
    : [];
  const registry = loadRegistry();
  let id = null;
  for (const [key, entry] of Object.entries(registry.projects)) {
    const match = (entry.match || []).map((m) => String(m));
    if (match.some((m) => remotes.includes(normRemote(m)))) { id = key; break; }
  }
  if (!id) {
    for (const [key, entry] of Object.entries(registry.projects)) {
      const names = [key, ...(entry.match || [])].map((m) => String(m).toLowerCase());
      if (names.includes(folder.toLowerCase())) { id = key; break; }
    }
  }
  const registered = Boolean(id);
  id ??= slug(folder);
  const entry = registry.projects[id] || {};

  let commit = null;
  let skip = false;
  let source = null;
  const notes = [];
  if (registered && entry.skip) { skip = true; source = 'its registry entry'; }
  else if (registered && typeof entry.commit === 'boolean') { commit = entry.commit; source = 'its registry entry'; }
  else {
    if (registered && entry.legacy_in_repo !== undefined) notes.push(`Its registry entry comes from version 0.1 and split the types between the repository and the store (in_repo ${JSON.stringify(entry.legacy_in_repo)}). That no longer exists, so it needs a new decision.`);
    const hit = matchGroup(registry, base, remotes);
    if (hit) {
      source = describeRule(hit.rule, hit.i);
      if (hit.rule.skip) skip = true;
      else if (typeof hit.rule.commit === 'boolean') commit = hit.rule.commit;
      else { notes.push(`${source} comes from version 0.1 and split the types between the repository and the store; it no longer decides anything.`); source = null; }
    } else if (typeof registry.defaults?.commit === 'boolean') {
      commit = registry.defaults.commit;
      source = 'defaults.commit in the registry';
    }
  }
  // Committed documents follow the branch, so a worktree has its own docs/process/. Documents that are not committed
  // exist once per repository, in the main folder; a worktree does not get them.
  const docsRoot = root && commit === true ? root : base;
  return {
    id, registered, root, base, folder, remotes, commit, skip, source, notes, decided: commit !== null,
    docsRoot, docsDir: path.join(docsRoot, DOCS), worktree: Boolean(root) && !samePath(root, base),
    tools: root ? TOOL_DIRS.filter((d) => fs.existsSync(path.join(root, d))) : [],
    allow: new Set((entry.allow || []).map((p) => posix(p))),
    // This project's backup in the store; null without a store
    storeDir: STORE ? path.join(STORE, 'projects', id) : null,
  };
}

// Is docs/process/ ignored by git on this computer (by any ignore file). Asked about a file inside it: asked about
// "docs/process/" itself, git can report a blank line of a .gitignore as the match.
function isIgnored(p) {
  return Boolean(p.root) && git(['check-ignore', '-q', '--no-index', `${DOCS}/probe-${SKILL_NAME}`], p.docsRoot) !== null;
}

function trackedDocs(p) {
  return p.root ? (git(['ls-files', '-z', '--', `${DOCS}/`], p.root) || '').split('\0').filter(Boolean) : [];
}

// What a backup takes: the files under docs/process/ that git ignores (all of them when the project does not commit
// docs/process/; single files kept out by hand when it does), less raw logs, hidden files and very large files
function backupSet(p) {
  const out = { files: [], raw: 0, big: [] };
  if (!p.root || !fs.existsSync(p.docsDir)) return out;
  const listed = git(['ls-files', '-z', '--others', '--ignored', '--exclude-standard', '--', `${DOCS}/`], p.docsRoot) || '';
  for (const full of listed.split('\0').filter(Boolean)) {
    const rel = full.slice(DOCS.length + 1);
    if (rel.split('/').some(isClutter)) continue;
    if (/(?:^|\/)evidence\/raw\//.test(rel)) { out.raw++; continue; }
    let size = 0;
    try { size = fs.statSync(path.join(p.docsDir, rel)).size; } catch { continue; }
    if (size > MAX_BACKUP_BYTES) { out.big.push(rel); continue; }
    out.files.push(rel);
  }
  out.files.sort();
  return out;
}

// What copying srcRels from srcDir over destDir would change, so that destDir ends up the same as the source
function mirrorPlan(srcDir, srcRels, destDir) {
  const want = new Set(srcRels);
  const have = listFiles(destDir);
  const haveSet = new Set(have);
  const added = [];
  const changed = [];
  const removed = have.filter((rel) => !want.has(rel));
  for (const rel of srcRels) {
    if (!haveSet.has(rel)) added.push(rel);
    else if (!sameBuf(readOr(path.join(srcDir, rel)), readOr(path.join(destDir, rel)))) changed.push(rel);
  }
  return { added, changed, removed, count: added.length + changed.length + removed.length };
}

function applyMirror(plan, srcDir, destDir) {
  // Removals first: on Windows a rename that only changes case would otherwise delete the file it just copied
  for (const rel of plan.removed) {
    fs.rmSync(path.join(destDir, rel), { force: true });
    pruneEmpty(path.dirname(path.join(destDir, rel)), destDir);
  }
  for (const rel of [...plan.added, ...plan.changed]) {
    const dest = path.join(destDir, rel);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(path.join(srcDir, rel), dest);
  }
}

function pruneEmpty(dir, stop) {
  while (isInside(dir, stop) && !samePath(dir, stop)) {
    try {
      if (fs.readdirSync(dir).length) return;
      fs.rmdirSync(dir);
    } catch {
      return;
    }
    dir = path.dirname(dir);
  }
}

function changeText(plan) {
  return [
    plan.added.length && `${plan.added.length} added`,
    plan.changed.length && `${plan.changed.length} changed`,
    plan.removed.length && `${plan.removed.length} removed`,
  ].filter(Boolean).join(', ');
}

function storeHead() {
  return git(['rev-parse', '--verify', '-q', 'HEAD'], STORE);
}

// The store commit this computer last backed up or restored this project at, if the store still has it
function lastSync(local, id) {
  const state = local.projects[id]?.backup;
  return state?.commit && git(['cat-file', '-e', `${state.commit}^{commit}`], STORE) !== null ? state : null;
}

// How far the store's copy is behind docs/process/ here
function backupState(p, local) {
  if (!STORE || !p.root) return null;
  const set = backupSet(p);
  const plan = mirrorPlan(p.docsDir, set.files, p.storeDir);
  const storeFiles = listFiles(p.storeDir).length;
  // Nothing here but a backup in the store: a new computer or a wiped folder, to restore, not changes to back up
  const restorable = !set.files.length && storeFiles > 0;
  return { files: set.files.length, pending: restorable ? 0 : plan.count, restorable, last: local.projects[p.id]?.backup?.at || null, storeFiles };
}

function when(iso) {
  if (!iso) return 'never';
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/* ---------- rules: is a path in the right place, with the right name ---------- */

// rel: a path relative to docs/process/, forward slashes. Looks at names and places only, never at content.
// Any format is fine: names are checked without their extension. Returns [{ level, code, msg }].
function checkDocPath(rel) {
  const parts = rel.split('/');
  const issues = [];
  const bad = (code, msg, level = 'error') => issues.push({ level, code, msg });
  if (parts.some(isClutter)) return issues;
  const [type, name] = parts;
  if (OWNED[type]) return issues;
  if (!TYPES[type]) {
    if (parts.length === 1 && type.toLowerCase() === 'readme.md') return issues;
    bad('wrong-place', `${DOCS}/ holds only ${list([...Object.keys(TYPES), ...Object.keys(OWNED)].map((t) => `${t}/`))} (and a README.md): ${rel}`, 'warn');
    return issues;
  }
  if (!name) return issues;
  const stem = stemOf(name);
  if (type === 'work') {
    const archived = name === 'archive';
    const folder = archived ? parts[2] : name;
    const depth = archived ? 3 : 2;
    if (!folder) return issues;
    if (parts.length === depth) bad('wrong-place', `work/ holds one folder per piece of work; put files in work/YYYY-MM-DD-short-name/: ${rel}`);
    else if (!DATED.test(folder)) bad('wrong-name', `work folders are named YYYY-MM-DD-short-name: ${folder}`);
  } else if (type === 'decisions' || type === 'notes') {
    if (!DATED.test(stem)) bad('wrong-name', `${TYPES[type]} are named YYYY-MM-DD-short-name, any format (.md, .html, …): ${name}`);
  } else if (type === 'explain') {
    if (HAS_DATE.test(name)) bad('wrong-name', `explainers describe how things are now and are edited in place; no date in the name: ${name}`);
    else if (VERSIONY.test(stem)) bad('wrong-name', `keep one explainer per topic and edit it in place; no v2, final and the like: ${name}`);
    else if (!KEBAB.test(stem) || name !== name.toLowerCase()) bad('wrong-name', `names are lowercase English words joined by hyphens: ${name}`);
  }
  return issues;
}

/* ---------- where ---------- */

const ASK = [
  'Not decided whether this project commits docs/process/. Ask the user once, offering both (do not pick one for them):',
  '  --commit      docs/process/ goes into the repository with the code: a private project whose documents should follow the code',
  '  --no-commit   docs/process/ stays out of the repository (ignored on this computer only; no file in the project changes) and is backed up to the private store: a company repository, or a project that is or may become public',
  'When the user has chosen: docs.mjs init --commit or docs.mjs init --no-commit',
  ...(STORE ? [] : ['Note: this computer has no store, so with --no-commit the documents would have no backup. If the user wants one, create the store first (skill section 1).']),
].join('\n');

function legacyLayout(p) {
  return p.root ? LEGACY_TYPES.filter((t) => fs.existsSync(path.join(p.root, 'docs', t))).map((t) => `docs/${t}/`) : [];
}

/* ---------- the project's own documents ---------- */

// Exact-case existence: on Windows, fs.existsSync('docs/architecture.md') is true for docs/ARCHITECTURE.md
function exactExists(base, rel) {
  let dir = base;
  for (const part of rel.split('/').filter(Boolean)) {
    let names;
    try { names = fs.readdirSync(dir); } catch { return false; }
    if (!names.includes(part)) return false;
    dir = path.join(dir, part);
  }
  return true;
}

function ownDocs(p) {
  return OWN.map((o) => {
    const at = exactExists(p.root, o.path) ? o.path : o.alt && exactExists(p.root, o.alt) ? `${o.alt}/` : null;
    return { ...o, at };
  });
}

// Names and places only; what the documents say is the project's business
function checkOwnDocs(p, add) {
  const root = p.root;
  const read = (rel) => { try { return fs.readFileSync(path.join(root, rel), 'utf8'); } catch { return null; } };
  const own = ownDocs(p);
  const agents = own[0].at ? read('AGENTS.md') : null;
  const claude = own[1].at ? read('CLAUDE.md') : null;
  const imports = claude !== null && /^\s*@AGENTS\.md\s*$/m.test(claude);
  if (claude !== null && !imports) {
    add('warn', 'own-docs', 'CLAUDE.md', agents !== null
      ? 'CLAUDE.md does not import AGENTS.md, so the rules for agents live in two files that drift apart'
      : 'the rules for agents are in CLAUDE.md only; Codex and other tools read AGENTS.md',
    'ask the user, then move the rules into AGENTS.md and leave CLAUDE.md as the line @AGENTS.md (Claude-only additions may follow it)');
  }
  // The same documents under other names or places
  for (const dir of ['', 'docs']) {
    let entries = [];
    try { entries = fs.readdirSync(path.join(root, dir), { withFileTypes: true }); } catch { /* no docs/ */ }
    for (const e of entries) {
      if (!e.isFile()) continue;
      const rel = dir ? `${dir}/${e.name}` : e.name;
      const hit = OWN_ALIASES.find((a) => a.re.test(e.name));
      if (!hit || rel === hit.to || p.allow.has(rel)) continue;
      add('warn', 'own-docs-name', rel, `the project's ${hit.what} has a fixed name and place: ${hit.to}`, `ask the user, then rename it to ${hit.to} and fix every line that points at it (AGENTS.md, CLAUDE.md, README)`);
    }
  }
  const conv = own[3].at === 'docs/CONVENTION.md' ? read('docs/CONVENTION.md') : null;
  const lines = conv ? conv.split('\n').length : 0;
  if (lines > RULES_MAX_LINES) add('warn', 'long-rules', 'docs/CONVENTION.md', `${lines} lines; agents read a file this long partly or not at all`, 'ask the user, then split it by topic into docs/conventions/ with a README.md index (move sections, do not rewrite them) and point AGENTS.md at the index');
  // AGENTS.md says where the documents are
  if (agents === null) return;
  const expected = [...own.slice(2).filter((o) => o.at).map((o) => o.at), ...(fs.existsSync(p.docsDir) ? [`${DOCS}/`] : [])];
  const a = agents.indexOf(MAP_BEGIN);
  const b = agents.indexOf(MAP_END);
  if (a < 0 || b < a) {
    if (expected.length) add('warn', 'docs-map', 'AGENTS.md', `AGENTS.md has no "where documents are" section, so agents may not find ${list(expected)}`, `add one between ${MAP_BEGIN} and ${MAP_END}: one line per document, in the user's language (skill section 7)`);
    return;
  }
  const map = agents.slice(a, b);
  const missing = expected.filter((x) => !map.includes(x.replace(/\/$/, '')));
  if (missing.length) add('warn', 'docs-map', 'AGENTS.md', `the "where documents are" section does not mention ${list(missing)}`, 'add a line for each');
  const named = [...map.matchAll(/`([^`\s]+)`/g)].map((m) => m[1]).filter((x) => x.includes('/') || /\.md$/i.test(x));
  const stale = named.filter((x) => !x.startsWith(DOCS) && !exactExists(root, x.replace(/\/$/, '')));
  if (stale.length) add('warn', 'docs-map', 'AGENTS.md', `the "where documents are" section points at ${list(stale)}, which do not exist`, 'fix or remove those lines');
}

function cmdWhere(args) {
  const json = args.includes('--json');
  if (STORE && isInside(process.cwd(), STORE)) {
    if (json) console.log(JSON.stringify({ store: show(STORE), insideStore: true }, null, 2));
    else console.log(`This is the store itself (${show(STORE)}): backup copies of each project's docs/process/ under projects/<project>/. Do not edit them here; change the project's own docs/process/ and run docs.mjs backup there.`);
    return 0;
  }
  const p = resolveProject(process.cwd());
  const local = loadLocal();
  const ignored = isIgnored(p);
  const backup = p.decided && !p.skip ? backupState(p, local) : null;
  const legacy = legacyLayout(p);
  if (json) {
    console.log(JSON.stringify({
      id: p.id, registered: p.registered, managed: !p.skip, decided: p.decided, commit: p.commit, source: p.source,
      repo: p.root && show(p.root), docs: show(p.docsDir), docsExists: fs.existsSync(p.docsDir), ignored, worktree: p.worktree,
      store: STORE && show(STORE), storeDir: p.storeDir && show(p.storeDir), backup,
      config: show(CONFIG_FILE), configured: Boolean(CONFIG), tools: p.tools, legacyLayout: legacy, notes: p.notes,
      ownDocs: p.root ? Object.fromEntries(ownDocs(p).map((o) => [o.path, o.at])) : null,
    }, null, 2));
    return 0;
  }
  console.log(`Project: ${p.id}${p.registered ? ' (registered)' : ' (not registered)'}`);
  console.log(`Repository: ${p.root ? show(p.root) : '(the current folder is not in a git repository)'}`);
  if (!CONFIG) console.log(`This computer is not set up: ${show(CONFIG_FILE)} does not exist (skill ${SKILL_NAME}, section 1).`);
  if (p.skip) {
    console.log(`Not managed: ${p.source} marks this project as following its own rules. Write documents the way its own rule files (AGENTS.md, CLAUDE.md, README) say; do not ask the user and do not run init.`);
    return 0;
  }
  for (const n of p.notes) console.log(n);
  if (!p.decided) {
    console.log(ASK);
    return 0;
  }
  console.log(`Documents: ${show(p.docsDir)}/${fs.existsSync(p.docsDir) ? '' : ' (does not exist yet)'}`);
  console.log(`Switch: ${switchText(p.commit)} (from ${p.source})`);
  if (p.worktree && !p.commit) console.log('This is a worktree: documents that are not committed live in the main folder, above; write them there.');
  if (!p.registered) console.log('Not registered yet: before writing the first document, run docs.mjs init. It records this switch; no need to ask the user.');
  else if (!p.commit && !ignored) console.log('docs/process/ is not ignored on this computer yet: before writing, run docs.mjs init (no need to ask the user).');
  else if (p.commit && ignored) console.log(`docs/process/ is ignored on this computer although this project commits it; see which line ignores it: git check-ignore -v --no-index ${DOCS}/x`);
  if (!p.commit || backup?.files || backup?.storeFiles) {
    if (!STORE) console.log(`Backup: none. ${NO_STORE}`);
    else if (backup) {
      const parts = [`last backup ${when(backup.last)}`];
      if (backup.pending) parts.push(`${backup.pending} changes not backed up yet (docs.mjs backup)`);
      console.log(`Backup: ${show(p.storeDir)}/ · ${list(parts)}`);
      if (backup.restorable) console.log(`docs/process/ is empty here but the store holds ${backup.storeFiles} files of this project: docs.mjs restore brings them back.`);
    }
  }
  if (p.root) {
    const own = ownDocs(p);
    console.log(`Project's own documents (names and places fixed, content the project's): ${own.map((o) => (o.at ? o.at : `${o.path} (none)`)).join(', ')}`);
  }
  if (legacy.length) console.log(`Old layout found: ${list(legacy)} (version 0.1 kept documents under docs/). They now go in docs/process/; move them by skill section 6.`);
  if (p.tools.length) console.log(`Tools with their own document home: ${list(p.tools)} (requirements, specs, tasks and acceptance go through that tool's own commands; do not write its files by hand)`);
  return 0;
}

/* ---------- check ---------- */

function cmdCheck(args) {
  const staged = args.includes('--staged');
  const storeAll = args.includes('--store');
  const quiet = args.includes('--quiet');
  const issues = [];
  const add = (level, code, file, msg, fix) => issues.push({ level, code, file, msg, fix });

  if (storeAll) {
    if (!STORE) { console.error(NO_STORE); return 1; }
    checkStore(add);
    return report(issues, { quiet, title: `store ${show(STORE)}` });
  }

  if (STORE && isInside(process.cwd(), STORE)) {
    console.error('This is the store itself. Check it with check --store.');
    return 1;
  }
  const p = resolveProject(process.cwd());
  if (!p.root) {
    console.error('The current folder is not in a git repository. To check the store, use check --store.');
    return 1;
  }
  if (p.skip) {
    if (!quiet) console.log(`Check: project ${p.id} is not managed (${p.source}); nothing to check.`);
    return 0;
  }
  if (STORE && isInside(STORE, p.root)) add('error', 'private-in-repo', show(STORE), 'the store is inside this project repository; one git add would commit the backups', 'move the store outside every project');
  if (!p.decided) add('warn', 'undecided', p.id, 'whether this project commits docs/process/ is not decided', 'ask the user, then docs.mjs init --commit or --no-commit');

  // docs/process/ and git (the pre-commit check looks only at what is being committed, below)
  if (!staged && p.commit === false) {
    const tracked = trackedDocs(p);
    if (tracked.length) add('error', 'private-in-repo', `${DOCS}/`, `${tracked.length} files under ${DOCS}/ are tracked by git, although this project does not commit ${DOCS}/`, `ask the user; to stop committing them: git rm -r --cached ${DOCS}/ (the files stay on disk). If they were pushed where others can see, see skill section 4`);
    if (!isIgnored(p)) add('error', 'not-ignored', `${DOCS}/`, `${DOCS}/ is not ignored on this computer; one git add -A would commit it`, 'docs.mjs init');
    if (!STORE) add('warn', 'no-backup', `${DOCS}/`, 'documents that are not committed have no backup: this computer has no store', NO_STORE);
  } else if (!staged && p.commit === true && isIgnored(p)) {
    add('warn', 'ignored', `${DOCS}/`, `${DOCS}/ is ignored although this project commits it`, `see which line ignores it: git check-ignore -v --no-index ${DOCS}/x`);
  }

  if (staged) {
    const files = (git(['diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'], p.root) || '').split('\0').filter(Boolean);
    for (const rel of files) {
      if (p.allow.has(rel) || toolOwned(rel)) continue;
      if (rel.startsWith(`${DOCS}/`)) {
        if (p.commit === false) add('error', 'private-in-repo', rel, `this project does not commit ${DOCS}/`, `unstage it: git restore --staged ${rel}`);
        else for (const i of checkDocPath(rel.slice(DOCS.length + 1))) add(i.level, i.code, rel, i.msg, 'rename it by the conventions');
        continue;
      }
      checkRepoPath(rel, (level, code, msg, fix) => add(level, code, rel, msg, fix));
    }
    return report(issues, { quiet, title: `project ${p.id}, staged files only` });
  }

  // Files in the project repository: tracked, plus untracked and not ignored (the next git add -A takes them)
  const files = (git(['ls-files', '--cached', '--others', '--exclude-standard', '-z'], p.root) || '').split('\0').filter(Boolean);
  for (const rel of new Set(files)) {
    if (rel.startsWith(`${DOCS}/`) || p.allow.has(rel) || toolOwned(rel)) continue;
    checkRepoPath(rel, (level, code, msg, fix) => add(level, code, rel, msg, fix));
  }
  for (const old of legacyLayout(p)) add('warn', 'old-layout', old, `version 0.1 kept documents under docs/; they now go in ${DOCS}/`, 'move them by skill section 6');
  checkOwnDocs(p, add);
  checkDocsTree(p.docsDir, samePath(p.docsRoot, p.root) ? DOCS : show(p.docsDir), add);
  if (p.decided && STORE && (p.commit === false || backupSet(p).files.length)) {
    const b = backupState(p, loadLocal());
    if (b?.pending) add('warn', 'not-backed-up', `${DOCS}/`, `${b.pending} changes since the last backup (${when(b.last)})`, 'docs.mjs backup');
    if (b?.restorable) add('warn', 'restorable', `${DOCS}/`, `empty here, but the store holds ${b.storeFiles} files of this project`, 'docs.mjs restore');
  }
  return report(issues, { quiet, title: `project ${p.id}${p.registered ? '' : ' (not registered)'}` });
}

// One path in the project repository, outside docs/process/: is it a working document left where it does not belong
function checkRepoPath(rel, add) {
  const parts = rel.split('/');
  const name = parts[parts.length - 1];
  if (!IS_DOC.test(name)) return;
  const atRoot = parts.length === 1;
  const atDocsRoot = parts.length === 2 && parts[0] === 'docs';
  const where = `plans and test records go in ${DOCS}/work/YYYY-MM-DD-short-name/, decisions in ${DOCS}/decisions/, notes in ${DOCS}/notes/, explainer pages in ${DOCS}/explain/`;
  if ((atRoot || atDocsRoot) && STRAY_PREFIX.test(name)) {
    add('error', 'wrong-place', `${name} looks like a working document (plan, summary, to-do) and should not sit at ${atRoot ? 'the project root' : 'the root of docs/'}`, `${where}. If it is a user-facing doc, give it a name that says what it covers; if the project's own rule files use it, add it to allow in the registry`);
  } else if (atDocsRoot && (STRAY_SUFFIX.test(name) || VERSIONY.test(stemOf(name)))) {
    add('warn', 'wrong-place', `${name} is named like a working document or carries a version suffix`, `keep it if it is a user-facing doc (it can be listed in allow in the registry); if it is a plan or summary: ${where}`);
  }
}

// docs/process/: only the four type folders; names; work left open for long
function checkDocsTree(dir, label, add) {
  if (!fs.existsSync(dir)) return;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (isClutter(e.name) || (e.isDirectory() && OWNED[e.name])) continue;
    if (!e.isDirectory() || !TYPES[e.name]) {
      for (const i of checkDocPath(e.name)) add(i.level, i.code, `${label}/${e.name}`, i.msg, 'move it into the matching folder');
      continue;
    }
    const typeDir = path.join(dir, e.name);
    for (const f of fs.readdirSync(typeDir, { withFileTypes: true })) {
      if (isClutter(f.name)) continue;
      const file = `${label}/${e.name}/${f.name}`;
      if (e.name === 'work' && f.isDirectory()) {
        if (f.name === 'archive') {
          for (const a of fs.readdirSync(path.join(typeDir, 'archive'), { withFileTypes: true })) {
            if (isClutter(a.name)) continue;
            const rel = `work/archive/${a.name}${a.isDirectory() ? '/x' : ''}`;
            for (const i of checkDocPath(rel)) add(i.level, i.code, `${file}/${a.name}`, i.msg, 'rename or move it by the conventions');
          }
          continue;
        }
        const issuesHere = checkDocPath(`work/${f.name}/x`);
        for (const i of issuesHere) add(i.level, i.code, file, i.msg, 'rename it by the conventions');
        if (!issuesHere.length) {
          const age = daysSince(f.name.slice(0, 10));
          if (age !== null && age > ACTIVE_DAYS) add('warn', 'stale', file, `in work/ for ${age} days`, 'when it is done or dropped, keep what matters, then move the whole folder into work/archive/ (skill section 5)');
        }
        continue;
      }
      for (const i of checkDocPath(`${e.name}/${f.name}`)) add(i.level, i.code, file, i.msg, 'rename it by the conventions');
    }
  }
}

function checkStore(add) {
  if (!repoRoot(STORE) || !samePath(repoRoot(STORE), STORE)) {
    add('warn', 'not-synced', show(STORE), 'the store is not a git repository: the backups have no history', 'git init it and push it to a private remote');
  } else {
    const dirty = (git(['status', '--porcelain'], STORE) || '').split(/\r?\n/).filter(Boolean).length;
    if (dirty) add('warn', 'not-synced', show(STORE), `${dirty} uncommitted changes in the store`, 'backups commit on their own; changes made by hand in the store get overwritten by the next backup. Ask the user before committing or discarding them');
    const ahead = git(['rev-list', '--count', '@{u}..HEAD'], STORE);
    if (ahead === null) add('warn', 'not-synced', show(STORE), 'the store has no remote (or its branch has no upstream): a lost disk loses the backups', 'push it to a private remote');
    else if (Number(ahead) > 0) add('warn', 'not-synced', show(STORE), `${ahead} commits in the store are not pushed`, 'the user pushes when they like: git push in the store');
  }
  const registry = loadRegistry();
  const base = path.join(STORE, 'projects');
  const ids = fs.existsSync(base) ? fs.readdirSync(base, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name) : [];
  for (const id of ids) if (!registry.projects[id]) add('warn', 'unknown-project', `projects/${id}`, 'a backup with no project of that name in the registry', 'register the project (docs.mjs init --id <name> in it), or ask the user whether to delete this folder');
  const local = loadLocal();
  for (const [id, v] of Object.entries(local.projects)) {
    if (!v.path || !fs.existsSync(v.path)) continue;
    const p = resolveProject(v.path);
    if (p.skip || !p.decided) continue;
    const b = backupState(p, local);
    if (b?.pending) add('warn', 'not-backed-up', id, `${b.pending} changes in ${show(p.docsDir)}/ since the last backup (${when(b.last)})`, 'docs.mjs backup --all');
    if (b?.restorable) add('warn', 'restorable', id, `${show(p.docsDir)}/ is empty, but the store holds ${b.storeFiles} files of this project`, `docs.mjs restore in ${show(p.base)}`);
  }
}

function report(issues, { quiet, title }) {
  const errors = issues.filter((i) => i.level === 'error');
  const warns = issues.filter((i) => i.level === 'warn');
  const print = quiet ? errors : issues;
  if (!quiet || print.length) console.log(`Check: ${title}`);
  for (const i of print) {
    console.log(`${i.level === 'error' ? '✗' : '!'} [${i.code}] ${i.file}`);
    console.log(`    ${i.msg}`);
    if (i.fix) console.log(`    fix: ${i.fix}`);
  }
  if (!quiet || errors.length) console.log(errors.length || warns.length ? `Result: ${errors.length} problems, ${warns.length} warnings` : 'Result: no problems');
  return errors.length ? 1 : 0;
}

/* ---------- init: register a project ---------- */

function cmdInit(args) {
  const dry = args.includes('--dry-run');
  const noHook = args.includes('--no-hook');
  const force = args.includes('--force');
  const markSkip = args.includes('--skip');
  if (args.includes('--commit') && args.includes('--no-commit')) { console.error('Give one of --commit or --no-commit.'); return 1; }
  const commitArg = args.includes('--commit') ? true : args.includes('--no-commit') ? false : null;
  const root = repoRoot(process.cwd());
  if (!root) { console.error('The current folder is not in a git repository. git init first, or run this inside the project.'); return 1; }
  if (STORE && isInside(root, STORE)) { console.error('This is the store itself; it is not registered.'); return 1; }
  const registry = loadRegistry();
  const current = resolveProject(process.cwd());
  const id = slug(option(args, '--id') || current.id);
  const existing = registry.projects[id];
  if (existing && !current.registered && !force) {
    console.error(`The registry already has a project named ${id} that does not match this repository (different remote and folder). Pick another name: init --id <name>`);
    return 1;
  }
  if (current.skip && !markSkip && !force) {
    console.error(`This project is not managed: ${current.source} marks it as following its own rules. Do nothing here. Only if the user says it should follow these conventions, run init again with --force and --commit or --no-commit.`);
    return 1;
  }

  const entry = { ...(existing || {}) };
  const match = new Set([...(entry.match || []), ...current.remotes]);
  if (!current.remotes.length) match.add(current.folder);
  entry.match = [...match];
  entry.added ??= new Date().toISOString().slice(0, 10);
  delete entry.in_repo;

  if (markSkip) {
    entry.skip = true;
    delete entry.commit;
    delete entry.legacy_in_repo;
    if (!dry) { registry.projects[id] = entry; saveRegistry(registry, `Register ${id}: not managed`); }
    console.log(`${dry ? '(Preview, nothing written) Would mark' : 'Marked'} ${id} as not managed: agents follow its own rules there, and check skips it.`);
    return 0;
  }

  // The switch is whatever the user decided: --commit / --no-commit now, the registry entry, or a group rule / defaults they wrote
  const commit = commitArg ?? current.commit;
  if (commit === null) {
    if (dry) console.log('(Preview, nothing written)');
    console.error(ASK);
    return 1;
  }
  delete entry.skip;
  delete entry.legacy_in_repo;
  entry.commit = commit;
  const allowArg = option(args, '--allow');
  if (allowArg) entry.allow = [...new Set([...(entry.allow || []), ...allowArg.split(',').map((s) => posix(s.trim())).filter(Boolean)])];
  entry.tools = current.tools;
  const via = commitArg === null && current.source && !current.registered ? ` (from ${current.source})` : '';
  const p = { ...current, id, commit, docsRoot: commit ? current.root : current.base };
  p.docsDir = path.join(p.docsRoot, DOCS);

  const steps = [];
  const notes = [];
  const failed = [];
  const act = (text, fn) => {
    steps.push(text);
    if (dry) return;
    try { fn(); } catch (err) { failed.push(`${text} (${err.code || err.message})`); }
  };
  act(`registry ${show(REGISTRY)}: ${existing ? 'update' : 'add'} ${id} (${switchText(commit)}${via}${entry.tools.length ? `; tools with their own document home: ${list(entry.tools)}` : ''}${entry.allow?.length ? `; let through: ${list(entry.allow)}` : ''})`, () => {
    registry.projects[id] = entry;
    if (!saveRegistry(registry, `Register ${id}: ${commit ? 'commits docs/process/' : 'docs/process/ not committed'}`)) throw new Error('written, but committing it in the store failed');
  });

  // The local ignore list: .git/info/exclude, shared by all worktrees, never part of the repository
  const excludeFile = git(['rev-parse', '--path-format=absolute', '--git-path', 'info/exclude'], current.base);
  if (excludeFile) {
    const text = fs.existsSync(excludeFile) ? fs.readFileSync(excludeFile, 'utf8') : '';
    const isOurs = (x) => x.trim() === `${DOCS}/` || x.trim() === DOCS;
    const has = (line) => text.split(/\r?\n/).some((x) => x.trim() === line || x.trim() === line.replace(/\/$/, ''));
    const add = ['.scratch/'].filter((l) => !has(l));
    if (!commit && !has(`${DOCS}/`) && !isIgnored(p)) add.push(`${DOCS}/`);
    const drop = commit && text.split(/\r?\n/).some(isOurs);
    if (add.length || drop) {
      const what = [add.length && `add ${list(add)}`, drop && `remove ${DOCS}/ (this project commits it now)`].filter(Boolean).join('; ');
      act(`local ignore list .git/info/exclude: ${what} (no file in the project changes)`, () => {
        let next = drop ? text.split(/\r?\n/).filter((x) => !isOurs(x)).join('\n') : text;
        if (add.length) next = `${next}${next && !next.endsWith('\n') ? '\n' : ''}${add.join('\n')}\n`;
        fs.mkdirSync(path.dirname(excludeFile), { recursive: true });
        fs.writeFileSync(excludeFile, next);
      });
    }
  }
  if (commit && !dry && isIgnored(p)) notes.push(`${DOCS}/ is still ignored by another ignore file; see which: git check-ignore -v --no-index ${DOCS}/x`);
  if (!commit) {
    const tracked = trackedDocs(p);
    if (tracked.length) notes.push(`${tracked.length} files under ${DOCS}/ are already tracked by git; ignoring does not untrack them. To stop committing them, ask the user, then: git rm -r --cached ${DOCS}/ (skill section 4).`);
    if (!STORE) notes.push(`No backup: ${NO_STORE}`);
  }
  if (!fs.existsSync(p.docsDir)) act(`create ${show(p.docsDir)}/`, () => fs.mkdirSync(p.docsDir, { recursive: true }));
  act(`this computer's list ${show(LOCAL_FILE)}: ${id} sits at ${show(current.base)}`, () => {
    const local = loadLocal();
    remember(local, { id, base: current.base });
    saveLocal(local);
  });

  if (!noHook) {
    const hooksPath = git(['config', '--get', 'core.hooksPath'], root);
    const hookFile = git(['rev-parse', '--path-format=absolute', '--git-path', 'hooks/pre-commit'], root);
    const line = `node "${show(path.join(HERE, 'docs.mjs'))}" check --staged --quiet`;
    if (hooksPath) {
      steps.push(`(not installed) this project uses its own hooks folder ${hooksPath}; left alone. To check before each commit, add this line to its pre-commit: ${line}`);
    } else if (hookFile && fs.existsSync(hookFile) && !fs.readFileSync(hookFile, 'utf8').includes(SKILL_NAME)) {
      steps.push(`(not installed) the project already has its own pre-commit; not overwritten. To check before each commit, add this line to it: ${line}`);
    } else if (hookFile && !fs.existsSync(hookFile)) {
      act('install a pre-commit check in .git/hooks/pre-commit (this computer only, not part of the repository; delete the file to remove it)', () => {
        fs.mkdirSync(path.dirname(hookFile), { recursive: true });
        fs.writeFileSync(hookFile, [
          '#!/bin/sh',
          `# ${SKILL_NAME}: stop commits that put documents in the wrong place. Installed by docs.mjs init; delete this file to remove it.`,
          `TOOL="${show(path.join(HERE, 'docs.mjs'))}"`,
          '[ -f "$TOOL" ] || exit 0',
          'command -v node >/dev/null 2>&1 || exit 0',
          'node "$TOOL" check --staged --quiet && exit 0',
          `echo "${SKILL_NAME}: the document problems above stopped this commit. If they are fine, commit with git commit --no-verify." >&2`,
          'exit 1',
          '',
        ].join('\n'), { mode: 0o755 });
      });
    }
  }
  console.log(dry ? `(Preview, nothing written) ${steps.length} steps:` : failed.length ? `Project ${id} is partly registered:` : `Project ${id} is registered:`);
  for (const step of steps) console.log(`- ${step}`);
  for (const n of notes) console.log(`Note: ${n}`);
  if (failed.length) {
    console.log('\nThese steps failed (usually because the current tool may not change files in .git/). Tell the user and ask them to run the same init in a terminal:');
    for (const f of failed) console.log(`- ${f}`);
  }
  if (!dry && !failed.length) {
    if (!commit && STORE && p.storeDir && listFiles(p.storeDir).length && !listFiles(p.docsDir).length) console.log(`The store holds a backup of this project: docs.mjs restore brings it into ${DOCS}/.`);
    console.log('See the result: docs.mjs where');
  }
  return failed.length ? 1 : 0;
}

/* ---------- backup and restore ---------- */

// Copy docs/process/ (what git ignores of it) over the project's folder in the store, then commit there. One direction
// only: the project's copy is the original. Stops instead of overwriting when the store's copy changed elsewhere.
function backupOne(p, { dry, force }, local) {
  if (p.skip) return { level: 'skip', text: `${p.id}: not managed (${p.source}); nothing to back up` };
  if (!p.root) return { level: 'skip', text: `${p.id}: not in a git repository` };
  if (!p.decided) return { level: 'skip', text: `${p.id}: whether it commits ${DOCS}/ is not decided; nothing to back up` };
  const rel = `projects/${p.id}`;
  const set = backupSet(p);
  const storeFiles = listFiles(p.storeDir);
  if (!set.files.length && !storeFiles.length) return { level: 'skip', text: `${p.id}: nothing to back up${p.commit ? ` (this project commits ${DOCS}/; only files kept out of it by hand get backed up)` : ''}` };
  const plan = mirrorPlan(p.docsDir, set.files, p.storeDir);
  const extra = [];
  if (set.raw) extra.push(`${set.raw} files under evidence/raw/ left out`);
  if (set.big.length) extra.push(`left out as larger than 20 MB: ${list(set.big)}`);
  const stop = (why) => ({ level: 'stop', text: `${p.id}: stopped, nothing copied. ${why}`, extra });
  if (!force) {
    const dirty = git(['status', '--porcelain', '--', rel], STORE);
    if (dirty) return stop(`The store's copy has changes that are not committed (edited by hand in the store?):\n${indent(dirty)}\n  Ask the user which side to keep; commit or discard them in the store, then back up again.`);
    const last = lastSync(local, p.id);
    if (last) {
      const since = git(['log', '--format=%h %ad %s', '--date=short', `${last.commit}..HEAD`, '--', rel], STORE);
      if (since) return stop(`The store's copy changed after this computer last backed it up (another computer's backup, pulled in?):\n${indent(since)}\n  Run docs.mjs restore first to bring those changes here, then back up.`);
    } else if (plan.count && storeFiles.length) {
      return stop(`The store already holds a copy of this project (${storeFiles.length} files) that this computer has never backed up or restored, and it differs from ${DOCS}/ here. Run docs.mjs restore to bring it here first. To replace it with this computer's copy instead (the old one stays in the store's history), the user says so and you run backup --force.`);
    }
    if (!set.files.length) return stop(`${DOCS}/ has nothing to back up here, but the store holds ${storeFiles.length} files of this project. If the folder was wiped, run docs.mjs restore; if the user really removed everything, backup --force.`);
  }
  if (!plan.count) {
    if (!dry) remember(local, p, { commit: storeHead(), at: new Date().toISOString() });
    return { level: 'ok', text: `${p.id}: up to date (${set.files.length} files)`, extra };
  }
  const summary = changeText(plan);
  if (dry) return { level: 'ok', text: `${p.id}: would back up (${summary}) into ${show(p.storeDir)}/`, extra };
  applyMirror(plan, p.docsDir, p.storeDir);
  const message = `backup ${p.id}: ${summary}`;
  const failed = { level: 'fail', text: `${p.id}: copied into ${show(p.storeDir)}/ but committing in the store failed (some tools may not change .git/). Tell the user and ask them to run in a terminal: git -C "${show(STORE)}" add -A -- ${rel} && git -C "${show(STORE)}" commit -m "${message}"`, extra };
  if (git(['add', '-A', '--', rel], STORE) === null) return failed;
  // git may see no change where the bytes differed only in line endings
  const changed = git(['status', '--porcelain', '--', rel], STORE);
  if (changed === null) return failed;
  if (changed && git(['commit', '-q', '-m', message, '--', rel], STORE) === null) return failed;
  remember(local, p, { commit: storeHead(), at: new Date().toISOString() });
  if (!changed) return { level: 'ok', text: `${p.id}: up to date (${set.files.length} files)`, extra };
  return { level: 'ok', text: `${p.id}: backed up (${summary}) into ${show(p.storeDir)}/`, extra, committed: true };
}

function storeReady() {
  if (!STORE) { console.error(NO_STORE); return false; }
  if (!repoRoot(STORE) || !samePath(repoRoot(STORE), STORE)) { console.error(`The store ${show(STORE)} is not a git repository, so backups would have no history. git init it first (skill section 1).`); return false; }
  return true;
}

function cmdBackup(args) {
  const dry = args.includes('--dry-run');
  const force = args.includes('--force');
  const all = args.includes('--all');
  if (!storeReady()) return 1;
  const local = loadLocal();
  const results = [];
  if (all) {
    const entries = Object.entries(local.projects);
    if (!entries.length) console.log(`No projects are listed for this computer in ${show(LOCAL_FILE)}; docs.mjs init or backup inside a project adds it.`);
    for (const [id, v] of entries) {
      if (!v.path || !fs.existsSync(v.path)) { results.push({ level: 'skip', text: `${id}: ${v.path || '(no folder recorded)'} not found on this computer` }); continue; }
      results.push(backupOne(resolveProject(v.path), { dry, force }, local));
    }
  } else {
    if (isInside(process.cwd(), STORE)) { console.error('This is the store itself. Run backup inside a project, or backup --all.'); return 1; }
    const p = resolveProject(process.cwd());
    if (!p.registered && p.decided && !dry) results.push({ level: 'stop', text: `${p.id}: not registered yet; run docs.mjs init first (no need to ask the user).` });
    else results.push(backupOne(p, { dry, force }, local));
  }
  if (!dry) saveLocal(local);
  for (const r of results) {
    console.log(`${r.level === 'ok' ? '✓' : r.level === 'skip' ? '·' : '✗'} ${r.text}`);
    for (const e of r.extra || []) console.log(`    ${e}`);
  }
  if (results.some((r) => r.committed)) console.log(`Committed in the store, not pushed. The user pushes when they like: git -C "${show(STORE)}" push`);
  return results.some((r) => r.level === 'stop' || r.level === 'fail') ? 1 : 0;
}

// Bring the store's copy into docs/process/: on a new computer, or after another computer's backup was pulled into the store.
// A file changed on both sides since this computer's last backup is left alone and listed.
function cmdRestore(args) {
  const dry = args.includes('--dry-run');
  if (!storeReady()) return 1;
  if (isInside(process.cwd(), STORE)) { console.error('This is the store itself. Run restore inside the project.'); return 1; }
  const p = resolveProject(process.cwd());
  if (!p.root) { console.error('The current folder is not in a git repository.'); return 1; }
  if (p.skip) { console.log(`Project ${p.id} is not managed (${p.source}); nothing to restore.`); return 0; }
  if (!p.decided) { console.error(ASK); return 1; }
  if (!p.registered || (p.commit === false && !isIgnored(p))) { console.error(`Run docs.mjs init first (no need to ask the user): ${p.registered ? `${DOCS}/ is not ignored on this computer yet` : 'this project is not registered'}. Then restore.`); return 1; }
  const src = p.storeDir;
  const storeFiles = listFiles(src);
  if (!storeFiles.length) { console.log(`The store holds nothing for ${p.id} (${show(src)}/). Nothing to restore.`); return 0; }
  const local = loadLocal();
  const last = lastSync(local, p.id);
  const rel = `projects/${p.id}`;
  const baseFiles = new Set(last ? (git(['ls-tree', '-r', '-z', '--name-only', last.commit, '--', `${rel}/`], STORE) || '').split('\0').filter(Boolean).map((f) => f.slice(rel.length + 1)) : []);
  const baseOf = (f) => (baseFiles.has(f) ? gitBuf(['show', `${last.commit}:${rel}/${f}`], STORE) : null);
  const here = backupSet(p).files;
  // Nothing here at all (a new computer, a wiped folder): bring everything back
  const wiped = !here.length;
  const copy = [];
  const remove = [];
  const keep = [];
  const conflicts = [];
  for (const f of storeFiles) {
    const S = readOr(path.join(src, f));
    const L = readOr(path.join(p.docsDir, f));
    if (L && sameBuf(L, S)) continue;
    const B = baseOf(f);
    if (!L) { if (!wiped && B && sameBuf(S, B)) keep.push(f); else copy.push(f); continue; } // removed here after the last backup: stays removed
    if (B && sameBuf(L, B)) copy.push(f);
    else if (B && sameBuf(S, B)) keep.push(f);
    else conflicts.push(f);
  }
  const inStore = new Set(storeFiles);
  for (const f of here) {
    if (inStore.has(f)) continue;
    const B = baseOf(f);
    if (B && sameBuf(readOr(path.join(p.docsDir, f)), B)) remove.push(f); // removed in the store since, unchanged here
    else keep.push(f);
  }
  console.log(`${dry ? '(Preview, nothing written) ' : ''}Restore ${p.id} from ${show(src)}/ into ${show(p.docsDir)}/:`);
  if (!copy.length && !remove.length && !conflicts.length) console.log('- nothing to bring over; this computer already has the store\'s copy');
  if (copy.length) console.log(`- copy from the store: ${list(copy)}`);
  if (remove.length) console.log(`- remove (removed in the store, unchanged here): ${list(remove)}`);
  if (keep.length) console.log(`- keep as they are here (changed only here; the next backup takes them): ${list(keep)}`);
  if (conflicts.length) console.log(`- changed both here and in the store${last ? ' since this computer\'s last backup' : ''}; left as they are here: ${list(conflicts)}`);
  if (dry) return conflicts.length ? 1 : 0;
  for (const f of remove) { fs.rmSync(path.join(p.docsDir, f), { force: true }); pruneEmpty(path.dirname(path.join(p.docsDir, f)), p.docsDir); }
  for (const f of copy) {
    const dest = path.join(p.docsDir, f);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(path.join(src, f), dest);
  }
  if (conflicts.length) {
    remember(local, p);
    saveLocal(local);
    console.log(`The store's versions are under ${show(src)}/. Ask the user which to keep for each; put the chosen content in ${DOCS}/ here, then run docs.mjs backup --force.`);
    return 1;
  }
  remember(local, p, { commit: storeHead(), at: new Date().toISOString() });
  saveLocal(local);
  if (keep.length) console.log('Then run docs.mjs backup so the store gets the changes made here.');
  return 0;
}

/* ---------- group: one switch for a whole group of projects ---------- */

function cmdGroup(args) {
  const [sub, ...rest] = args;
  const registry = loadRegistry();
  const groups = Array.isArray(registry.groups) ? registry.groups : [];
  const describe = (rule, i) => `${i + 1}. ${rule.remote ? `remote ${rule.remote}` : `folder ${rule.folder}`} → ${rule.skip ? 'not managed (follows its own rules)' : typeof rule.commit === 'boolean' ? switchText(rule.commit) : 'decides nothing (left from version 0.1; remove it and add it again)'}${rule.note ? `  (${rule.note})` : ''}`;

  if (!sub || sub === 'list') {
    if (!groups.length) console.log(`No group rules in ${show(REGISTRY)}. Projects not registered get asked about one by one.`);
    else {
      console.log(`Group rules in ${show(REGISTRY)} (the first match wins; a project's own registry entry beats them all):`);
      groups.forEach((rule, i) => console.log(describe(rule, i)));
    }
    return 0;
  }
  if (sub === 'add') {
    const remote = option(rest, '--remote');
    const folder = option(rest, '--folder');
    const choices = ['--commit', '--no-commit', '--skip'].filter((c) => rest.includes(c));
    const note = option(rest, '--note');
    if (Boolean(remote) === Boolean(folder)) { console.error('Give exactly one of --remote <start of the remote URL> or --folder <folder the projects sit in>.'); return 1; }
    if (choices.length !== 1) { console.error('Give exactly one of --commit, --no-commit or --skip.'); return 1; }
    const rule = {};
    if (remote) rule.remote = normRemote(remote);
    else rule.folder = show(canon(folder));
    if (choices[0] === '--skip') rule.skip = true;
    else rule.commit = choices[0] === '--commit';
    if (note) rule.note = note;
    const key = JSON.stringify(remote ? { remote: rule.remote } : { folder: rule.folder.toLowerCase() });
    if (groups.some((g) => JSON.stringify(g.remote ? { remote: g.remote } : { folder: String(g.folder).toLowerCase() }) === key)) {
      console.error('A rule for the same remote or folder already exists. Remove it first (group list, then group remove <number>).');
      return 1;
    }
    registry.groups = [...groups, rule];
    saveRegistry(registry, 'Add a group rule');
    console.log(`Added: ${describe(rule, registry.groups.length - 1)}`);
    if (folder && !fs.existsSync(folder)) console.log(`Note: ${rule.folder} does not exist on this computer.`);
    if (folder) console.log('Folder rules work only where that folder exists; on another computer with another layout they match nothing.');
    if (rule.commit === false && !STORE) console.log(`Note: ${NO_STORE}`);
    return 0;
  }
  if (sub === 'remove') {
    const n = Number(rest[0]);
    if (!Number.isInteger(n) || n < 1 || n > groups.length) { console.error(`Give the number of a rule (1 to ${groups.length}); see group list.`); return 1; }
    const [gone] = groups.splice(n - 1, 1);
    registry.groups = groups;
    saveRegistry(registry, 'Remove a group rule');
    console.log(`Removed: ${describe(gone, n - 1)}`);
    return 0;
  }
  console.error('Usage: group list | group add (--remote <prefix> | --folder <path>) (--commit | --no-commit | --skip) [--note <text>] | group remove <number>');
  return 1;
}

/* ---------- setup: once per computer; also to create or change the store later ---------- */
// Four things (a preview by default; --apply writes):
// 1. The store (only with --store): create it when the path is missing or an empty folder; connect to it when its root
//    has projects.json; refuse when it holds something else or sits inside another git repository.
//    The user chooses the name and place; the script never makes one up.
// 2. The config file: where this computer's store is (null without one). Other keys in it are kept.
// 3. The global rule: references/rule-template.md filled in with this computer's paths, installed for Claude Code and Codex.
// 4. Print the permissions to add to both tools' settings. The script does not edit settings files.

const RULE_MARK = new RegExp(`<!-- ${SKILL_NAME}:begin -->[\\s\\S]*?<!-- ${SKILL_NAME}:end -->`);

function nearestExisting(p) {
  let d = p;
  while (!fs.existsSync(d) && path.dirname(d) !== d) d = path.dirname(d);
  return d;
}

function cmdSetup(args) {
  const apply = args.includes('--apply');
  const home = path.resolve(option(args, '--home') || process.env.RMPD_RULES_HOME || os.homedir());
  const storeArg = option(args, '--store');
  const store = args.includes('--no-store') ? null : (storeArg ? path.resolve(storeArg) : STORE);
  const steps = [];
  const notes = [];
  const act = (text, fn) => { steps.push(text); if (apply) fn(); };

  // 1. The store
  if (store) {
    const outer = repoRoot(nearestExisting(store));
    const exists = fs.existsSync(store);
    const entries = exists ? fs.readdirSync(store).filter((n) => n !== '.git') : [];
    const isStore = exists && fs.existsSync(path.join(store, 'projects.json'));
    if (outer && !samePath(outer, store)) {
      console.error(`The store cannot sit inside another git repository: ${show(store)} is inside ${show(outer)}. One git add would commit the backups to that repository. Pick a place outside every project.`);
      return 1;
    }
    if (isStore) {
      const count = Object.keys(JSON.parse(fs.readFileSync(path.join(store, 'projects.json'), 'utf8')).projects || {}).length;
      steps.push(`connect to the existing store ${show(store)} (${count} projects registered); nothing in it changes`);
    } else if (entries.length) {
      console.error(`${show(store)} exists and holds ${entries.length} items, but it is not a store (no projects.json at its root). Pick another place, or ask the user what this folder is for.`);
      return 1;
    } else {
      const localReg = path.join(CONFIG_DIR, 'projects.json');
      const carried = fs.existsSync(localReg) ? JSON.parse(fs.readFileSync(localReg, 'utf8')) : null;
      const n = carried ? Object.keys(carried.projects || {}).length : 0;
      act(`create the store ${show(store)}: git init, README.md, .gitignore, registry projects.json${n ? ` (moving in the ${n} projects already registered on this computer)` : ''}`, () => {
        fs.mkdirSync(path.join(store, 'projects'), { recursive: true });
        fs.writeFileSync(path.join(store, 'projects', '.gitkeep'), '');
        if (!repoRoot(store)) git(['init', '-q'], store);
        const tpl = (name) => fs.readFileSync(path.join(SKILL_DIR, 'assets', 'store', name), 'utf8');
        fs.writeFileSync(path.join(store, 'README.md'), tpl('README.md').replaceAll('__NAME__', path.basename(store)));
        fs.writeFileSync(path.join(store, '.gitignore'), tpl('gitignore.txt'));
        const reg = carried ? upgradeRegistry({ ...carried, projects: carried.projects || {} }) : { version: 2, projects: {} };
        fs.writeFileSync(path.join(store, 'projects.json'), JSON.stringify(reg, null, 2) + '\n');
        if (carried) fs.renameSync(localReg, localReg + '.moved');
      });
      notes.push('After the store is created: commit once in the store and push it to a private remote. The user pushes; neither the script nor the agent does.');
    }
  }

  // 2. The config file (other keys, such as toolDirs, are kept)
  act(`config file ${show(CONFIG_FILE)}: store = ${store ? show(store) : 'none'}`, () => {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
    fs.writeFileSync(CONFIG_FILE, JSON.stringify({ ...(CONFIG || {}), store: store ? show(store) : null }, null, 2) + '\n');
  });

  // 3. The global rule
  const template = fs.readFileSync(path.join(SKILL_DIR, 'references', 'rule-template.md'), 'utf8').match(RULE_MARK)?.[0];
  if (!template) { console.error(`references/rule-template.md has no section between ${SKILL_NAME}:begin and ${SKILL_NAME}:end.`); return 1; }
  const rule = template
    .replaceAll('__STORE__', store ? `\`${show(store)}\`` : `none (documents that are not committed have no backup; to have one, create a store with the skill ${SKILL_NAME})`)
    .replaceAll('__TOOL__', `\`node "${show(path.join(HERE, 'docs.mjs'))}"\``)
    .replaceAll('__TEMPLATES__', `\`${show(path.join(SKILL_DIR, 'assets', 'templates'))}/\``);
  const ccRule = path.join(home, '.claude', 'rules', `${SKILL_NAME}.md`);
  act(`Claude Code global rule: write ${show(ccRule)}`, () => { fs.mkdirSync(path.dirname(ccRule), { recursive: true }); fs.writeFileSync(ccRule, rule + '\n'); });
  const cxRule = path.join(home, '.codex', 'AGENTS.md');
  act(`Codex global rule: write the section between the two markers in ${show(cxRule)} (the rest of the file stays as it is)`, () => {
    fs.mkdirSync(path.dirname(cxRule), { recursive: true });
    const old = fs.existsSync(cxRule) ? fs.readFileSync(cxRule, 'utf8') : '';
    const next = RULE_MARK.test(old)
      ? old.replace(RULE_MARK, () => rule)
      : `${old}${old && !old.endsWith('\n') ? '\n' : ''}${old ? '\n' : ''}${rule}\n`;
    fs.writeFileSync(cxRule, next);
  });

  console.log(apply ? 'Done:' : '(Preview, nothing written; add --apply once the user agrees) Steps:');
  for (const st of steps) console.log(`- ${st}`);
  for (const n of notes) console.log(`\n${n}`);
  if (store) {
    console.log('\nTwo settings still need the store added (the script does not edit settings files, so it cannot break them; the agent can, once the user agrees):');
    console.log(`1. Claude Code, ~/.claude/settings.json: add "${show(store)}" to permissions.additionalDirectories.`);
    console.log(`2. Codex, ~/.codex/config.toml: add "${show(store)}" to writable_roots under [sandbox_workspace_write].`);
    console.log('Without them, an agent working in a sandbox may not be allowed to run docs.mjs backup, which writes to the store.');
  }
  console.log('\nThe global rule takes effect in new sessions.');
  return 0;
}

/* ---------- entry ---------- */

const [cmd, ...rest] = process.argv.slice(2);
const commands = { where: cmdWhere, check: cmdCheck, init: cmdInit, backup: cmdBackup, restore: cmdRestore, group: cmdGroup, setup: cmdSetup };
if (!commands[cmd]) {
  console.log([
    'Usage: node docs.mjs <command>',
    '  where [--json]             this project\'s name, whether it commits docs/process/ and who decided, the folder to write in, backup state',
    '  init [--commit | --no-commit] [--allow <paths>] [--id <name>] [--skip] [--force] [--no-hook] [--dry-run]',
    '                             register this project: record the switch, ignore docs/process/ (when not committed) and .scratch/ locally,',
    '                             create docs/process/, install a pre-commit check; --allow lets through files the project\'s own rules use',
    '                             (SPEC.md, TASKS.md); --skip marks it as following its own rules instead',
    '  check                      check this project: names, places, docs/process/ committed or ignored as decided, changes not backed up',
    '  check --staged --quiet     staged files only (the pre-commit check)',
    '  check --store              check the store: uncommitted or unpushed, projects with changes not backed up',
    '  backup [--all] [--dry-run] [--force]',
    '                             copy docs/process/ (what git ignores of it) into the store and commit there; never pushes;',
    '                             stops when the store\'s copy changed elsewhere (--force overwrites, only when the user says so)',
    '  restore [--dry-run]        bring the store\'s copy into docs/process/ (a new computer, or another computer\'s backup)',
    '  group list | add | remove  one switch for a group of projects, by remote prefix or folder',
    '  setup [--store <path> | --no-store] [--apply] [--home <folder>]',
    '                             once per computer: record the store (creating or connecting it) and install the global rule; previews by default',
  ].join('\n'));
  process.exit(cmd ? 1 : 0);
}
let code = 0;
try {
  code = commands[cmd](rest) ?? 0;
} catch (err) {
  console.error(`Error: ${err.message}`);
  code = 1;
}
process.exit(code);
