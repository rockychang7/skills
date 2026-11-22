#!/usr/bin/env node
// docs.mjs — helper for the rein-managing-project-docs skill: setup / where / init / check / group
// No dependencies, Node 18+. It ships inside the skill and is replaced when the skill is upgraded,
// so it holds nothing of any one person. A person's own data lives outside the skill:
//   config file: ~/.config/rein-managing-project-docs/config.json, {"store": "<path>"} or {"store": null}
//   registry:    <store>/projects.json when there is a store (it travels with the store to other computers);
//                otherwise projects.json next to the config file
//   RMPD_HOME replaces the config folder, RMPD_STORE the store, and RMPD_RULES_HOME the home folder setup installs
//   the global rules under (all three for tests)
// The conventions are in ../references/conventions.md. This script only does what a program can judge.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const SKILL_NAME = 'rein-managing-project-docs';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const SKILL_DIR = path.resolve(HERE, '..');
const CONFIG_DIR = path.resolve(process.env.RMPD_HOME || path.join(os.homedir(), '.config', SKILL_NAME));
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');
const CONFIG = (() => { try { return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8')); } catch { return null; } })();
const storeSetting = process.env.RMPD_STORE || CONFIG?.store || null;
// The store is optional. Without one, the four types can only go in the project repository.
const STORE = storeSetting ? canon(storeSetting) : null;
const REGISTRY = STORE ? path.join(STORE, 'projects.json') : path.join(CONFIG_DIR, 'projects.json');
const NO_STORE = `This computer has no private store yet. To keep documents outside the project repository, create one first: its name and location are the user's to choose; ask if they have not said (skill ${SKILL_NAME}, section 1). Then run docs.mjs setup --store <path> --apply`;

// The four types these conventions place per project. Key = folder name: under docs/ in the project
// repository, under projects/<project>/ in the store.
const TYPES = {
  internals: 'internal docs',
  decisions: 'decision records',
  work: 'work folders',
  notes: 'notes',
};
const DATED = /^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*$/;
const KEBAB = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const HAS_DATE = /^\d{4}-?\d{2}-?\d{2}[-_]/;
const VERSIONY = /(?:[-_. ](?:v\d+|final|new|old|copy|bak|backup|draft\d*)|\(\d+\))$/i;
// Names that working documents usually get when an agent drops them at the project root or the root of docs/
const STRAY_PREFIX = /^(?:plan|plans|todo|todos|notes?|summary|design|spec|specs|tasks|report|analysis|decision|decisions|progress|handoff|implementation|proposal|research|findings|review|scratch|draft)(?:[-_ .].*)?\.md$/i;
const STRAY_SUFFIX = /[-_ .](?:plan|summary|design|spec|proposal|notes|report|analysis|todo|tasks|decision|findings|handoff|progress)\.md$/i;
const WORK_STATUS = ['active', 'done', 'dropped'];
const DECISION_STATUS = ['accepted', 'superseded'];
const ACTIVE_DAYS = 30;
// Tools with a document home of their own: their folders belong to the tool and are skipped.
// The config file's toolDirs can add more.
const TOOL_DIRS = ['.rein/', '.kiro/', '.specify/', 'openspec/', ...((CONFIG && CONFIG.toolDirs) || [])].map((d) => (d.endsWith('/') ? d : d + '/'));
const toolOwned = (rel) => TOOL_DIRS.some((d) => rel.startsWith(d));

/* ---------- helpers ---------- */

const posix = (p) => p.split(path.sep).join('/');
const show = (p) => posix(p);
const list = (items) => items.join(', ');

function git(args, cwd) {
  try {
    return execFileSync('git', args, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], maxBuffer: 256 * 1024 * 1024 }).replace(/\r?\n$/, '');
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

function loadRegistry() {
  if (!fs.existsSync(REGISTRY)) return { version: 1, projects: {} };
  const data = JSON.parse(fs.readFileSync(REGISTRY, 'utf8'));
  data.projects ??= {};
  return data;
}

function saveRegistry(data) {
  fs.mkdirSync(path.dirname(REGISTRY), { recursive: true });
  fs.writeFileSync(REGISTRY, JSON.stringify(data, null, 2) + '\n');
}

// "all", "none", "decisions,notes" or an array → a list of types, or { error }
function parseArrangement(value) {
  if (Array.isArray(value)) {
    const unknown = value.filter((t) => !TYPES[t]);
    return unknown.length ? { error: `unknown types: ${list(unknown)}` } : [...new Set(value)];
  }
  const words = String(value).split(',').map((w) => w.trim().toLowerCase()).filter(Boolean);
  if (words.length === 1 && words[0] === 'all') return Object.keys(TYPES);
  if (words.length === 1 && words[0] === 'none') return [];
  const unknown = words.filter((t) => !TYPES[t]);
  if (unknown.length || !words.length) return { error: `--in-repo takes all, none, or some of ${list(Object.keys(TYPES))} separated by commas; not understood: ${unknown.join(',') || '(empty)'}` };
  return [...new Set(words)];
}

function describeRule(rule, i) {
  return `group rule ${i + 1} (${rule.remote ? `remote ${rule.remote}` : `folder ${rule.folder}`})`;
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

// Which project the current folder belongs to, and how its documents are arranged.
// Order: the project's own registry entry → the first matching group rule → defaults.in_repo → not decided.
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

  let chosen = null;
  let skip = false;
  let source = null;
  if (registered && entry.skip) { skip = true; source = 'its registry entry'; }
  else if (registered && Array.isArray(entry.in_repo)) { chosen = entry.in_repo; source = 'its registry entry'; }
  else {
    const hit = matchGroup(registry, base, remotes);
    if (hit) {
      source = describeRule(hit.rule, hit.i);
      if (hit.rule.skip) skip = true;
      else {
        const parsed = parseArrangement(hit.rule.in_repo ?? []);
        chosen = parsed.error ? null : parsed;
        if (parsed.error) source = `${source}, which is invalid: ${parsed.error}`;
      }
    } else if (Array.isArray(registry.defaults?.in_repo)) {
      chosen = registry.defaults.in_repo;
      source = 'defaults.in_repo in the registry';
    }
  }
  const inRepo = new Set((chosen || []).filter((t) => TYPES[t]));
  return {
    id, registered, root, base, folder, remotes, inRepo, skip, source, decided: Boolean(chosen),
    // Tools with a document home of their own, judged by whether their folder exists now
    tools: root ? TOOL_DIRS.filter((d) => fs.existsSync(path.join(root, d))) : [],
    allow: new Set((entry.allow || []).map((p) => posix(p))),
    // This project's folder in the store; null without a store
    storeDir: STORE ? path.join(STORE, 'projects', id) : null,
  };
}

function frontMatter(file) {
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch { return null; }
  const m = text.match(/^﻿?---\r?\n([\s\S]*?)\r?\n---/);
  if (!m) return null;
  const data = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (kv) data[kv[1]] = kv[2].replace(/\s+#.*$/, '').replace(/^["']|["']$/g, '').trim();
  }
  return data;
}

function contentHash(file) {
  try {
    const stat = fs.statSync(file);
    if (!stat.isFile() || stat.size < 40 || stat.size > 5 * 1024 * 1024) return null;
    const buf = fs.readFileSync(file);
    const isText = !buf.subarray(0, 8000).includes(0);
    const data = isText ? Buffer.from(buf.toString('utf8').replace(/\r\n/g, '\n').trim()) : buf;
    if (data.length < 40) return null;
    return crypto.createHash('sha1').update(data).digest('hex');
  } catch {
    return null;
  }
}

function walk(dir, out = []) {
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const e of entries) {
    if (e.name === '.git') continue;
    const full = path.join(dir, e.name);
    if (e.isSymbolicLink()) continue;
    if (e.isDirectory()) walk(full, out);
    else if (e.isFile()) out.push(full);
  }
  return out;
}

function daysSince(dateText) {
  const t = Date.parse(dateText);
  return Number.isNaN(t) ? null : Math.floor((Date.now() - t) / 86400000);
}

/* ---------- rules: is a path in the right place, with the right name ---------- */

// rel: path relative to a document root (docs/ in the project repository, projects/<project>/ in the store), forward slashes.
// Looks at names and places only, never at content. Returns [{ level, code, msg }].
function checkDocPath(rel) {
  const parts = rel.split('/');
  const type = parts[0];
  const issues = [];
  const bad = (code, msg) => issues.push({ level: 'error', code, msg });
  if (!TYPES[type] || parts.length < 2) return issues;
  const name = parts[1];
  const stem = name.replace(/\.md$/i, '');
  if (type === 'internals') {
    if (parts.length === 2 && /\.md$/i.test(name)) {
      if (HAS_DATE.test(name)) bad('wrong-name', `internal docs describe how things are now; no date in the file name: ${name}`);
      else if (VERSIONY.test(stem)) bad('wrong-name', `keep one internal doc per topic and edit it in place; no v2, final and the like: ${name}`);
      else if (!KEBAB.test(stem) || name !== name.toLowerCase()) bad('wrong-name', `file names are lowercase English words joined by hyphens: ${name}`);
    }
  } else if (type === 'decisions' || type === 'notes') {
    if (parts.length === 2) {
      if (name === '.gitkeep' || name === 'README.md') return issues;
      if (!/\.md$/.test(name) || !DATED.test(stem)) bad('wrong-name', `${TYPES[type]} are named YYYY-MM-DD-short-name.md: ${name}`);
    }
  } else if (type === 'work') {
    const folder = name === 'archive' ? parts[2] : name;
    if (name === '.gitkeep' || (name === 'archive' && (!folder || folder === '.gitkeep'))) return issues;
    const depth = name === 'archive' ? 3 : 2;
    if (parts.length === depth) bad('wrong-place', `work/ holds one folder per piece of work; put files in work/YYYY-MM-DD-short-name/: ${rel}`);
    else if (!DATED.test(folder)) bad('wrong-name', `work folders are named YYYY-MM-DD-short-name: ${folder}`);
  }
  return issues;
}

/* ---------- where ---------- */

// What to ask the user when a project's arrangement is not decided. Offer the options; never pick one for the user.
const ARRANGEMENTS = [
  '  --in-repo all         all four in the project repository: a private project whose docs should follow the code',
  '  --in-repo none        all four in the store: a project that is or may become public, or a repository that is not the user\'s to add files to',
  '  --in-repo decisions   only decision records in the repository, the rest in the store: an open-source project that wants contributors to see why',
  '  or any set of types separated by commas, e.g. --in-repo internals,decisions',
];
const ASK = [
  'This project\'s document arrangement is not decided. Ask the user: internal docs, decision records, work folders, notes — which go in the project repository and which in the private store?',
  'Common choices (list them for the user; do not pick one for them):',
  ...ARRANGEMENTS,
  'When the user has chosen: docs.mjs init --in-repo <their choice>',
  ...(STORE ? [] : ['Note: this computer has no private store yet. If the user picks the store for any type, create the store first (name and location as the user says; ask if not said), then register.']),
].join('\n');

function cmdWhere(args) {
  const json = args.includes('--json');
  if (STORE && isInside(process.cwd(), STORE)) {
    if (json) console.log(JSON.stringify({ store: show(STORE), insideStore: true }, null, 2));
    else console.log(`This is the private store itself (${show(STORE)}). Each project's documents are under projects/<project>/; check the whole store with docs.mjs check --store.`);
    return 0;
  }
  const p = resolveProject(process.cwd());
  const types = Object.keys(TYPES);
  const inRepo = types.filter((t) => p.inRepo.has(t));
  const inStore = types.filter((t) => !p.inRepo.has(t));
  if (json) {
    console.log(JSON.stringify({
      id: p.id, registered: p.registered, managed: !p.skip, decided: p.decided, source: p.source,
      repo: p.root && show(p.root), store: STORE && show(STORE), storeDir: p.storeDir && show(p.storeDir),
      config: show(CONFIG_FILE), configured: Boolean(CONFIG),
      inRepo: p.decided ? inRepo : null, inStore: p.decided ? inStore : null, tools: p.tools,
    }, null, 2));
    return 0;
  }
  console.log(`Project: ${p.id}${p.registered ? ' (registered)' : ' (not registered)'}`);
  console.log(`Repository: ${p.root ? show(p.root) : '(the current folder is not in a git repository)'}`);
  console.log(`Store: ${STORE ? show(STORE) : 'none'}${CONFIG ? '' : ` (this computer is not set up: ${show(CONFIG_FILE)} does not exist)`}`);
  if (p.skip) {
    console.log(`Not managed: ${p.source} marks this project as following its own rules. Write documents the way its own rule files (AGENTS.md, CLAUDE.md, README) say; do not ask the user about the arrangement and do not run init.`);
    return 0;
  }
  if (!p.decided) {
    if (p.source) console.log(`Arrangement: ${p.source}.`);
    console.log(ASK);
  } else {
    console.log(`Arrangement: from ${p.source}.`);
    console.log(`In the project repository under docs/: user-facing docs${inRepo.map((t) => `, ${TYPES[t]} docs/${t}/`).join('')}`);
    if (inStore.length && !STORE) console.log(`Meant for the store: ${list(inStore.map((t) => TYPES[t]))}. ${NO_STORE}`);
    else if (!inStore.length) console.log('In the store: nothing');
    else console.log(`In the store under ${show(p.storeDir)}/: ${list(inStore.map((t) => `${TYPES[t]} ${t}/`))}`);
    if (!p.registered) console.log('Not registered yet: before writing the first of these documents here, run docs.mjs init. It records this arrangement; no need to ask the user.');
  }
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
    const base = path.join(STORE, 'projects');
    const ids = fs.existsSync(base) ? fs.readdirSync(base, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name) : [];
    for (const id of ids) checkStoreSide(path.join(base, id), `projects/${id}`, add);
    checkStoreGit(add);
    return report(issues, { quiet, title: `store ${show(STORE)} (${ids.length} projects)` });
  }

  if (STORE && isInside(process.cwd(), STORE)) {
    console.error('This is the store itself. Check it with check --store.');
    return 1;
  }
  const p = resolveProject(process.cwd());
  if (!p.root) {
    console.error('The current folder is not in a git repository. To check the whole store, use check --store.');
    return 1;
  }
  if (p.skip) {
    if (!quiet) console.log(`Check: project ${p.id} is not managed (${p.source}); nothing to check.`);
    return 0;
  }
  if (STORE && isInside(STORE, p.root)) add('error', 'private-in-repo', show(STORE), 'the store is inside this project repository; one git add would commit the private documents', 'move the store outside every project');
  if (p.decided && !STORE && Object.keys(TYPES).some((t) => !p.inRepo.has(t))) add('warn', 'no-store', p.id, 'this project puts some types in the store, but this computer has no store, so they have nowhere to go', NO_STORE);
  if (!p.decided) add('warn', 'undecided', p.id, 'this project\'s arrangement is not decided, so whether documents are in the right place cannot be checked (names still are)', 'ask the user how to arrange it, then docs.mjs init --in-repo …');

  // 1. Files in the project repository: tracked, plus untracked and not ignored (the next git add -A takes them)
  const listed = staged
    ? (git(['diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'], p.root) || '')
    : (git(['ls-files', '--cached', '--others', '--exclude-standard', '-z'], p.root) || '');
  const files = [...new Set(listed.split('\0').filter(Boolean))];
  const storeHashes = new Map();
  if (p.storeDir && fs.existsSync(p.storeDir)) {
    for (const f of walk(p.storeDir)) {
      const rel = posix(path.relative(p.storeDir, f));
      if (p.inRepo.has(rel.split('/')[0])) continue;
      const h = contentHash(f);
      if (h) storeHashes.set(h, rel);
    }
  }
  for (const rel of files) {
    if (p.allow.has(rel) || toolOwned(rel)) continue;
    const name = rel.split('/').pop();
    checkRepoPath(p, rel, (level, code, msg, fix) => add(level, code, rel, msg, fix));
    if (storeHashes.size && /\.(md|txt|png|jpe?g|webp|json|csv|log|sql|ya?ml|sh|mjs|js|py)$/i.test(name)) {
      const h = contentHash(path.join(p.root, rel));
      if (h && storeHashes.has(h)) add('error', 'private-in-repo', rel, `same content as ${storeHashes.get(h)} in the store: a copy of a private document`, 'delete this copy from the project repository (if it was already pushed somewhere others can see, treat it as public)');
    }
  }

  // New documents this commit adds: the script cannot judge content, so it only points them out
  if (staged) {
    const flagged = new Set(issues.map((i) => i.file));
    const fresh = (git(['diff', '--cached', '--name-only', '--diff-filter=A', '-z'], p.root) || '').split('\0').filter(Boolean);
    for (const rel of fresh) {
      if (flagged.has(rel) || p.allow.has(rel) || !/\.md$/i.test(rel)) continue;
      const parts = rel.split('/');
      if (parts.length === 1 ? /^(readme|changelog|contributing|license|security|code_of_conduct|agents|claude)\b/i.test(rel) : parts[0] !== 'docs') continue;
      if (parts[0] === 'docs' && p.inRepo.has(parts[1])) continue;
      add('note', 'new-doc', rel, 'this commit adds a new document to the project repository, which holds only docs for users and contributors', 'fine if it is a user-facing doc; if it is a plan, decision or internal doc, move it where this project\'s arrangement says (docs.mjs where) before committing');
    }
  }

  // 2. Links from the project to the store (junctions, symlinks): once an ignore rule fails, private documents get committed
  if (!staged) {
    for (const dir of [p.root, path.join(p.root, 'docs')]) {
      let entries = [];
      try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { /* no docs/ */ }
      for (const e of entries) {
        if (!e.isSymbolicLink()) continue;
        let target = null;
        try { target = fs.realpathSync(path.join(dir, e.name)); } catch { /* broken link */ }
        if (target && STORE && isInside(target, STORE)) {
          add('error', 'private-in-repo', posix(path.relative(p.root, path.join(dir, e.name))), 'a link into the store; git treats it as a plain folder, and when an ignore rule fails the private documents get committed', 'delete the link; agents read and write the store at its own path');
        }
      }
    }
  }

  // 3. This project's half in the store
  if (!staged) {
    if (p.storeDir) checkStoreSide(p.storeDir, `(store) projects/${p.id}`, add);
    for (const t of Object.keys(TYPES)) if (p.inRepo.has(t) || !p.decided) checkTypeDir(path.join(p.root, 'docs', t), `docs/${t}`, t, add);
  }

  return report(issues, { quiet, title: `project ${p.id}${p.registered ? '' : ' (not registered)'}${staged ? ', staged files only' : ''}` });
}

// One path in the project repository: is it in the right place
function checkRepoPath(p, rel, add) {
  const parts = rel.split('/');
  const name = parts[parts.length - 1];
  // Where a type goes for this project: docs/ in the repository, or this project's folder in the store
  const dest = (sub) => (p.inRepo.has(sub.split('/')[0]) ? `docs/${sub}` : p.storeDir ? show(path.join(p.storeDir, sub)) : `the store's projects/${p.id}/${sub} (this computer has no store yet; create one first)`);
  const whereThree = p.decided
    ? `plans go to ${dest('work/YYYY-MM-DD-short-name/plan.md')}, decisions to ${dest('decisions/')}, notes to ${dest('notes/')}`
    : 'plans go to work/YYYY-MM-DD-short-name/plan.md, decisions to decisions/, notes to notes/ (whether under docs/ or in the store is not decided for this project yet; ask the user)';
  if (parts[0] === 'docs' && TYPES[parts[1]] && parts.length > 2) {
    const type = parts[1];
    const sub = parts.slice(1).join('/');
    if (name === '.gitkeep') return;
    if (p.decided && !p.inRepo.has(type)) {
      add('error', 'private-in-repo', `this project keeps ${TYPES[type]} in the store`, `move it to ${dest(sub)}; if the user wants this one file in the repository, add it to allow in this project's registry entry; to move the whole type into the repository, ask the user, then add "${type}" to in_repo`);
    } else {
      for (const i of checkDocPath(sub)) add(i.level, i.code, i.msg, 'rename it by the conventions');
    }
    return;
  }
  if (!/\.md$/i.test(name)) return;
  const atRoot = parts.length === 1;
  const atDocsRoot = parts.length === 2 && parts[0] === 'docs';
  if ((atRoot || atDocsRoot) && STRAY_PREFIX.test(name)) {
    add('error', 'wrong-place', `${name} looks like a working document (plan, summary, to-do) and should not sit at ${atRoot ? 'the project root' : 'the root of docs/'}`, `${whereThree}; if it is a user-facing doc, give it a name that says what it covers`);
  } else if (atDocsRoot && (STRAY_SUFFIX.test(name) || VERSIONY.test(name.replace(/\.md$/i, '')))) {
    add('warn', 'wrong-place', `${name} is named like a working document or carries a version suffix`, 'keep it if it is a user-facing doc (it can be listed in allow in the registry); if it is a plan or summary, move it into work/ or notes/ as this project\'s arrangement says');
  }
}

function checkStoreSide(dir, label, add) {
  if (!fs.existsSync(dir)) return;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === 'README.md' || e.name === '.gitkeep') continue;
    if (!e.isDirectory() || !TYPES[e.name]) {
      add('warn', 'wrong-place', `${label}/${e.name}`, 'a project folder holds only internals/, decisions/, work/, notes/ and a README.md', 'move it into the matching folder');
      continue;
    }
    checkTypeDir(path.join(dir, e.name), `${label}/${e.name}`, e.name, add);
  }
}

// One type folder: names, plus the status at the top of each file
function checkTypeDir(dir, label, type, add) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const nameIssue = (rel, file) => { for (const i of checkDocPath(rel)) add(i.level, i.code, file, i.msg, 'rename it by the conventions'); };
  if (type === 'internals') {
    for (const e of entries) if (e.isFile()) nameIssue(`internals/${e.name}`, `${label}/${e.name}`);
  } else if (type === 'decisions') {
    const names = new Set(entries.map((e) => e.name));
    for (const e of entries) {
      if (!e.isFile() || e.name === '.gitkeep' || e.name === 'README.md') continue;
      const file = `${label}/${e.name}`;
      nameIssue(`decisions/${e.name}`, file);
      const fm = frontMatter(path.join(dir, e.name));
      if (!fm || !DECISION_STATUS.includes(fm.status)) add('error', 'bad-status', file, `a decision record starts with status: ${DECISION_STATUS.join(' / ')}`, 'add it');
      else if (fm.status === 'superseded') {
        if (!fm.superseded_by) add('error', 'bad-status', file, 'a superseded decision names the one that replaced it in superseded_by', 'add it');
        else if (!names.has(path.basename(fm.superseded_by))) add('warn', 'bad-status', file, `superseded_by points to ${fm.superseded_by}, which is not in this folder`, 'check it (the newer one may be on the other side)');
      }
    }
  } else if (type === 'notes') {
    for (const e of entries) if (e.isFile()) nameIssue(`notes/${e.name}`, `${label}/${e.name}`);
  } else if (type === 'work') {
    const one = (folderDir, folderLabel, name, archived) => {
      if (!DATED.test(name)) { add('error', 'wrong-name', folderLabel, `work folders are named YYYY-MM-DD-short-name: ${name}`, 'rename it by the conventions'); return; }
      const main = ['plan.md', 'test.md'].map((f) => path.join(folderDir, f)).find((f) => fs.existsSync(f));
      if (!main) { add('error', 'bad-status', folderLabel, 'a work folder has a plan.md (the plan) or a test.md (the test record), with the status at its top', 'add one'); return; }
      const st = frontMatter(main)?.status;
      if (!WORK_STATUS.includes(st)) { add('error', 'bad-status', `${folderLabel}/${path.basename(main)}`, `starts with status: ${WORK_STATUS.join(' / ')}`, 'add it'); return; }
      if (archived && st === 'active') add('warn', 'stale', folderLabel, 'already in archive/ but still active', 'set it to done or dropped');
      if (!archived && st !== 'active') add('warn', 'stale', folderLabel, `status is ${st} but it is not archived`, 'first keep what matters (decisions, internal docs, real tests), then move the whole folder into work/archive/');
      if (!archived && st === 'active') {
        const age = daysSince(name.slice(0, 10));
        if (age !== null && age > ACTIVE_DAYS) add('warn', 'stale', folderLabel, `still active after ${age} days`, 'archive it when done; mark it dropped when abandoned');
      }
    };
    for (const e of entries) {
      if (e.name === '.gitkeep') continue;
      if (e.isFile()) { add('error', 'wrong-place', `${label}/${e.name}`, 'work/ holds one folder per piece of work; files go inside a YYYY-MM-DD-short-name/ folder', 'move it into its work folder'); continue; }
      if (!e.isDirectory()) continue;
      if (e.name === 'archive') {
        for (const a of fs.readdirSync(path.join(dir, 'archive'), { withFileTypes: true })) {
          if (a.isDirectory()) one(path.join(dir, 'archive', a.name), `${label}/archive/${a.name}`, a.name, true);
        }
      } else one(path.join(dir, e.name), `${label}/${e.name}`, e.name, false);
    }
  }
}

function checkStoreGit(add) {
  if (!repoRoot(STORE) || !samePath(repoRoot(STORE), STORE)) {
    add('warn', 'not-synced', show(STORE), 'the store is not a git repository: nothing protects it from a lost disk or a slip', 'git init it and push it to a private remote');
    return;
  }
  const dirty = (git(['status', '--porcelain'], STORE) || '').split(/\r?\n/).filter(Boolean).length;
  if (dirty) add('warn', 'not-synced', show(STORE), `${dirty} uncommitted changes in the store`, 'commit them in the store');
  const ahead = git(['rev-list', '--count', '@{u}..HEAD'], STORE);
  if (ahead === null) add('warn', 'not-synced', show(STORE), 'the store has no remote (or its branch has no upstream)', 'push it to a private remote');
  else if (Number(ahead) > 0) add('warn', 'not-synced', show(STORE), `${ahead} commits in the store are not pushed`, 'git push in the store');
}

function report(issues, { quiet, title }) {
  const errors = issues.filter((i) => i.level === 'error');
  const warns = issues.filter((i) => i.level === 'warn');
  const notes = issues.filter((i) => i.level === 'note');
  const print = quiet ? [...errors, ...notes] : issues;
  if (!quiet || print.length) console.log(`Check: ${title}`);
  for (const i of print) {
    console.log(`${i.level === 'error' ? '✗' : i.level === 'warn' ? '!' : '·'} [${i.code}] ${i.file}`);
    console.log(`    ${i.msg}`);
    if (i.fix) console.log(`    fix: ${i.fix}`);
  }
  if (!quiet || errors.length) console.log(errors.length || warns.length ? `Result: ${errors.length} problems, ${warns.length} warnings` : 'Result: no problems');
  return errors.length ? 1 : 0;
}

/* ---------- init: register a project ---------- */

function option(args, name) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] && !args[i + 1].startsWith('--') ? args[i + 1] : null;
}

function cmdInit(args) {
  const dry = args.includes('--dry-run');
  const noHook = args.includes('--no-hook');
  const force = args.includes('--force');
  const markSkip = args.includes('--skip');
  const root = repoRoot(process.cwd());
  if (!root) { console.error('The current folder is not in a git repository. git init first, or run this inside the project.'); return 1; }
  if (STORE && isInside(root, STORE)) { console.error('This is the store itself; it is not registered.'); return 1; }
  const registry = loadRegistry();
  const current = resolveProject(root);
  const id = slug(option(args, '--id') || current.id);
  const existing = registry.projects[id];
  if (existing && !current.registered && !force) {
    console.error(`The registry already has a project named ${id} that does not match this repository (different remote and folder). Pick another name: init --id <name>`);
    return 1;
  }
  if (current.skip && !markSkip && !force) {
    console.error(`This project is not managed: ${current.source} marks it as following its own rules. Do nothing here. Only if the user says it should follow these conventions, run init again with --force and --in-repo.`);
    return 1;
  }

  const entry = { ...(existing || {}) };
  const match = new Set([...(entry.match || []), ...current.remotes]);
  if (!current.remotes.length) match.add(current.folder);
  entry.match = [...match];
  entry.added ??= new Date().toISOString().slice(0, 10);

  if (markSkip) {
    entry.skip = true;
    delete entry.in_repo;
    if (!dry) { registry.projects[id] = entry; saveRegistry(registry); }
    console.log(`${dry ? '(Preview, nothing written) Would mark' : 'Marked'} ${id} as not managed: agents follow its own rules there, and check skips it.`);
    return 0;
  }

  // The arrangement is whatever the user decided: --in-repo now, the registry entry, or a group rule / defaults they wrote
  const arg = option(args, '--in-repo');
  let inRepo = current.decided ? [...current.inRepo] : null;
  if (arg !== null) {
    const parsed = parseArrangement(arg);
    if (parsed.error) { console.error(parsed.error); return 1; }
    inRepo = parsed;
  }
  if (!inRepo && !dry) { console.error(ASK); return 1; }
  if (inRepo && !STORE && inRepo.length < Object.keys(TYPES).length && !dry) {
    console.error(`This arrangement keeps some types in the store (${list(Object.keys(TYPES).filter((t) => !inRepo.includes(t)).map((t) => TYPES[t]))}). ${NO_STORE}`);
    return 1;
  }
  delete entry.skip;
  if (inRepo) entry.in_repo = inRepo;
  const allowArg = option(args, '--allow');
  if (allowArg) entry.allow = [...new Set([...(entry.allow || []), ...allowArg.split(',').map((s) => posix(s.trim())).filter(Boolean)])];
  entry.tools = current.tools;
  const inStore = Object.keys(TYPES).filter((t) => !(inRepo || []).includes(t));
  const via = arg === null && inRepo && current.source && !current.registered ? ` (from ${current.source})` : '';

  const storeDir = STORE ? path.join(STORE, 'projects', id) : null;
  const steps = [];
  const failed = [];
  const act = (text, fn) => {
    steps.push(text);
    if (dry) return;
    try { fn(); } catch (err) { failed.push(`${text} (${err.code || err.message})`); }
  };
  const where = inRepo
    ? `repository: user-facing docs${inRepo.map((t) => ', ' + TYPES[t]).join('')}; store: ${list(inStore.map((t) => TYPES[t])) || 'nothing'}${via}`
    : 'arrangement not decided; ask the user first';
  act(`registry projects.json: ${existing ? 'update' : 'add'} ${id} (${where}${entry.tools.length ? `; tools with their own document home: ${list(entry.tools)}` : ''}${entry.allow?.length ? `; let through: ${list(entry.allow)}` : ''})`, () => {
    registry.projects[id] = entry;
    saveRegistry(registry);
  });
  if (inRepo && inStore.length && storeDir) {
    act(`create ${show(storeDir)}/ in the store (${list(inStore.map((t) => (t === 'work' ? 'work/archive' : t)))})`, () => {
      for (const t of inStore) {
        const d = path.join(storeDir, t === 'work' ? 'work/archive' : t);
        fs.mkdirSync(d, { recursive: true });
        if (!fs.readdirSync(d).length) fs.writeFileSync(path.join(d, '.gitkeep'), '');
      }
      const readme = path.join(storeDir, 'README.md');
      if (!fs.existsSync(readme)) {
        fs.writeFileSync(readme, `# ${id}: private documents\n\n- Project repository: ${current.remotes[0] || current.folder}\n- Registered: ${entry.added}\n- This folder holds the types this project keeps out of its repository. Conventions: skill ${SKILL_NAME}, references/conventions.md.\n`);
      }
    });
  }
  const excludeFile = git(['rev-parse', '--path-format=absolute', '--git-path', 'info/exclude'], root);
  if (excludeFile) {
    const text = fs.existsSync(excludeFile) ? fs.readFileSync(excludeFile, 'utf8') : '';
    if (!/^\.scratch\/?$/m.test(text)) {
      act('local ignore list .git/info/exclude: add .scratch/ (no file in the project changes)', () => {
        fs.mkdirSync(path.dirname(excludeFile), { recursive: true });
        fs.writeFileSync(excludeFile, `${text}${text && !text.endsWith('\n') ? '\n' : ''}.scratch/\n`);
      });
    }
  }
  if (!noHook) {
    const hooksPath = git(['config', '--get', 'core.hooksPath'], root);
    const hookFile = git(['rev-parse', '--path-format=absolute', '--git-path', 'hooks/pre-commit'], root);
    const line = `node "${show(path.join(HERE, 'docs.mjs'))}" check --staged --quiet`;
    if (hooksPath) {
      steps.push(`(not installed) this project uses its own hooks folder ${hooksPath}; left alone. To check before each commit, add this line to its pre-commit: ${line}`);
    } else if (hookFile && fs.existsSync(hookFile) && !fs.readFileSync(hookFile, 'utf8').includes(SKILL_NAME)) {
      steps.push(`(not installed) the project already has its own pre-commit; not overwritten. To check before each commit, add this line to it: ${line}`);
    } else if (hookFile) {
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
  if (dry && !inRepo) console.log(`\n${ASK}`);
  if (failed.length) {
    console.log('\nThese steps failed (usually because the current tool may not change files in .git/). Tell the user and ask them to run the same init in a terminal:');
    for (const f of failed) console.log(`- ${f}`);
  }
  if (!dry && !failed.length) console.log('See the result: docs.mjs where');
  return failed.length ? 1 : 0;
}

/* ---------- group: arrangements for a whole group of projects ---------- */

function cmdGroup(args) {
  const [sub, ...rest] = args;
  const registry = loadRegistry();
  const groups = Array.isArray(registry.groups) ? registry.groups : [];
  const describe = (rule, i) => `${i + 1}. ${rule.remote ? `remote ${rule.remote}` : `folder ${rule.folder}`} → ${rule.skip ? 'not managed (follows its own rules)' : arrangementText(rule.in_repo)}${rule.note ? `  (${rule.note})` : ''}`;

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
    const arg = option(rest, '--in-repo');
    const skip = rest.includes('--skip');
    const note = option(rest, '--note');
    if (Boolean(remote) === Boolean(folder)) { console.error('Give exactly one of --remote <start of the remote URL> or --folder <folder the projects sit in>.'); return 1; }
    if ((arg !== null) === skip) { console.error('Give exactly one of --in-repo all|none|<types> or --skip.'); return 1; }
    const rule = {};
    if (remote) rule.remote = normRemote(remote);
    else rule.folder = show(canon(folder));
    if (skip) rule.skip = true;
    else {
      const parsed = parseArrangement(arg);
      if (parsed.error) { console.error(parsed.error); return 1; }
      rule.in_repo = parsed.length === Object.keys(TYPES).length ? 'all' : parsed.length ? parsed : 'none';
    }
    if (note) rule.note = note;
    const key = JSON.stringify(remote ? { remote: rule.remote } : { folder: rule.folder.toLowerCase() });
    if (groups.some((g) => JSON.stringify(g.remote ? { remote: g.remote } : { folder: String(g.folder).toLowerCase() }) === key)) {
      console.error('A rule for the same remote or folder already exists. Remove it first (group list, then group remove <number>).');
      return 1;
    }
    registry.groups = [...groups, rule];
    saveRegistry(registry);
    console.log(`Added: ${describe(rule, registry.groups.length - 1)}`);
    if (folder && !fs.existsSync(folder)) console.log(`Note: ${rule.folder} does not exist on this computer.`);
    if (folder) console.log('Folder rules work only where that folder exists; on another computer with another layout they match nothing.');
    const needsStore = !skip && (rule.in_repo === 'none' || (Array.isArray(rule.in_repo) && rule.in_repo.length < Object.keys(TYPES).length));
    if (needsStore && !STORE) console.log(`Note: this rule keeps some types in the store. ${NO_STORE}`);
    return 0;
  }
  if (sub === 'remove') {
    const n = Number(rest[0]);
    if (!Number.isInteger(n) || n < 1 || n > groups.length) { console.error(`Give the number of a rule (1 to ${groups.length}); see group list.`); return 1; }
    const [gone] = groups.splice(n - 1, 1);
    registry.groups = groups;
    saveRegistry(registry);
    console.log(`Removed: ${describe(gone, n - 1)}`);
    return 0;
  }
  console.error('Usage: group list | group add (--remote <prefix> | --folder <path>) (--in-repo all|none|<types> | --skip) [--note <text>] | group remove <number>');
  return 1;
}

function arrangementText(value) {
  const parsed = parseArrangement(value ?? []);
  if (parsed.error) return `invalid (${parsed.error})`;
  const out = Object.keys(TYPES).filter((t) => !parsed.includes(t));
  if (!out.length) return 'all four in the repository';
  if (!parsed.length) return 'all four in the store';
  return `in the repository: ${list(parsed)}; in the store: ${list(out)}`;
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
      console.error(`The store cannot sit inside another git repository: ${show(store)} is inside ${show(outer)}. One git add would commit the private documents to that repository. Pick a place outside every project.`);
      return 1;
    }
    if (isStore) {
      const count = Object.keys(JSON.parse(fs.readFileSync(path.join(store, 'projects.json'), 'utf8')).projects || {}).length;
      steps.push(`connect to the existing store ${show(store)} (${count} projects registered); nothing in it changes`);
    } else if (entries.length) {
      console.error(`${show(store)} exists and holds ${entries.length} items, but it is not a store (no projects.json at its root). Pick another place, or ask the user what this folder is for.`);
      return 1;
    } else {
      const local = path.join(CONFIG_DIR, 'projects.json');
      const carried = fs.existsSync(local) ? JSON.parse(fs.readFileSync(local, 'utf8')) : null;
      const n = carried ? Object.keys(carried.projects || {}).length : 0;
      act(`create the store ${show(store)}: git init, README.md, .gitignore, registry projects.json${n ? ` (moving in the ${n} projects already registered on this computer)` : ''}`, () => {
        fs.mkdirSync(path.join(store, 'projects'), { recursive: true });
        fs.writeFileSync(path.join(store, 'projects', '.gitkeep'), '');
        if (!repoRoot(store)) git(['init', '-q'], store);
        const tpl = (name) => fs.readFileSync(path.join(SKILL_DIR, 'assets', 'store', name), 'utf8');
        fs.writeFileSync(path.join(store, 'README.md'), tpl('README.md').replaceAll('__NAME__', path.basename(store)));
        fs.writeFileSync(path.join(store, '.gitignore'), tpl('gitignore.txt'));
        fs.writeFileSync(path.join(store, 'projects.json'), JSON.stringify(carried || { version: 1, projects: {} }, null, 2) + '\n');
        if (carried) fs.renameSync(local, local + '.moved');
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
    .replaceAll('__STORE__', store ? `\`${show(store)}\`` : `none (the four types can only go in the project repository; to keep any outside it, create a store with the skill ${SKILL_NAME} first)`)
    .replaceAll('__TOOL__', `\`node "${show(path.join(HERE, 'docs.mjs'))}"\``);
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
    console.log('Without them, agents know a document belongs in the store but cannot read or write it.');
  }
  console.log('\nThe global rule takes effect in new sessions.');
  return 0;
}

/* ---------- entry ---------- */

const [cmd, ...rest] = process.argv.slice(2);
const commands = { where: cmdWhere, check: cmdCheck, init: cmdInit, group: cmdGroup, setup: cmdSetup };
if (!commands[cmd]) {
  console.log([
    'Usage: node docs.mjs <command>',
    '  where [--json]             this project\'s name, the store, whether its arrangement is decided, where each type goes',
    '  init [--in-repo all|none|<types>] [--allow <paths>] [--id <name>] [--skip] [--force] [--no-hook] [--dry-run]',
    '                             register this project: record its arrangement, create its store folder, ignore .scratch/ locally, install a pre-commit check;',
    '                             --allow lets through files the project rules use (SPEC.md, TASKS.md); --skip marks it as following its own rules instead',
    '  check                      check this project: wrong place, wrong name, private documents in the repository, work to archive',
    '  check --staged --quiet     staged files only (the pre-commit check)',
    '  check --store              check the whole store: names, status, uncommitted or unpushed changes',
    '  group list | add | remove  arrangements for groups of projects, by remote prefix or folder',
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
