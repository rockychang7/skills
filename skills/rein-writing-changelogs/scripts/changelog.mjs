#!/usr/bin/env node
// changelog.mjs: check the format of CHANGELOG.md and print one version's notes.
// Node.js 18+, standard library only. Run `node changelog.mjs --help`.

import { existsSync, readFileSync } from "node:fs";

const HELP = `Usage: node changelog.mjs <command> [options]

Commands:
  check [file] [--all]     Check the newest version's entry (every version with --all).
                           file defaults to CHANGELOG.md in the current folder.
  print <version> [file]   Print one version's notes without its heading, for the GitHub Release text.

Format checked:
  # Changelog                       the first line
  ## 1.4.0 - 2026-11-24             version and release date, newest first
  ### Breaking Changes              then, in this order and only when they have items:
  ### Added                           Breaking Changes, Added, Fixed, Changed, Verification
  ### Fixed                         or, for an entry in Chinese:
  ### Changed                         不兼容改动, 新增, 修复, 调整, 验证
  ### Verification
Also: no text before the first section, no empty section, no commit hashes.

Exit codes: 0 no problems / printed, 1 problems found / version not found, 2 wrong usage or no file.
Examples:
  node changelog.mjs check
  node changelog.mjs check docs/CHANGELOG.md --all
  node changelog.mjs print 1.4.0 > release-notes.md`;

const SECTIONS = {
  en: ["Breaking Changes", "Added", "Fixed", "Changed", "Verification"],
  zh: ["不兼容改动", "新增", "修复", "调整", "验证"],
};
const VERSION_HEADING = /^## (\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?) - (\d{4}-\d{2}-\d{2})$/;
const ANY_VERSION = /^#{1,2}\s+\[?v?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)\]?/;
const HASH = /(?<![0-9A-Za-z#])(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}(?![0-9A-Za-z])/;

function readLines(file) {
  if (!existsSync(file)) {
    console.error(`${file}: no such file. Pass the changelog's path, or run from the folder that has CHANGELOG.md.`);
    process.exit(2);
  }
  return readFileSync(file, "utf8").replace(/^﻿/, "").split(/\r?\n/);
}

// Headings outside fenced code blocks: { level, text, line (0-based) }
function headings(lines) {
  const out = [];
  let fence = null;
  lines.forEach((l, i) => {
    const f = l.match(/^\s*(```|~~~)/);
    if (f) { fence = fence === f[1] ? null : fence ?? f[1]; return; }
    if (fence) return;
    const h = l.match(/^(#{1,6})\s+(.*?)\s*#*\s*$/);
    if (h) out.push({ level: h[1].length, text: h[2], raw: l, line: i });
  });
  return out;
}

// Version entries: a level-2 heading, or an old-style level-1 version heading; ends at the next one.
function entries(lines) {
  const hs = headings(lines);
  const starts = hs.filter((h) => h.level === 2 || (h.level === 1 && ANY_VERSION.test(h.raw)));
  return starts.map((h, k) => {
    const end = k + 1 < starts.length ? starts[k + 1].line : lines.length;
    const v = h.raw.match(ANY_VERSION);
    return { heading: h, start: h.line, end, version: v ? v[1] : null, inner: hs.filter((x) => x.line > h.line && x.line < end) };
  });
}

function cmpSemver(a, b) {
  const split = (v) => (v.includes("-") ? [v.slice(0, v.indexOf("-")), v.slice(v.indexOf("-") + 1)] : [v, null]);
  const [ma, pa] = split(a);
  const [mb, pb] = split(b);
  const na = ma.split(".").map(Number), nb = mb.split(".").map(Number);
  for (let i = 0; i < 3; i++) if (na[i] !== nb[i]) return na[i] - nb[i];
  if (pa === pb) return 0;
  if (pa === null) return 1;
  if (pb === null) return -1;
  const xa = pa.split("."), xb = pb.split(".");
  for (let i = 0; i < Math.max(xa.length, xb.length); i++) {
    if (xa[i] === undefined) return -1;
    if (xb[i] === undefined) return 1;
    const da = /^\d+$/.test(xa[i]), db = /^\d+$/.test(xb[i]);
    if (da && db && Number(xa[i]) !== Number(xb[i])) return Number(xa[i]) - Number(xb[i]);
    if (da !== db) return da ? -1 : 1;
    if (xa[i] !== xb[i]) return xa[i] < xb[i] ? -1 : 1;
  }
  return 0;
}

function validDate(s) {
  const d = new Date(`${s}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s;
}

function checkEntry(lines, e, add) {
  const at = e.start + 1;
  const m = e.heading.raw.match(VERSION_HEADING);
  if (!m) {
    add(at, `the version heading "${e.heading.raw}" is not "## <version> - <YYYY-MM-DD>". Write it like "## 1.4.0 - 2026-11-24".`);
  } else if (!validDate(m[2])) {
    add(at, `${m[2]} is not a real date. Write the release date as YYYY-MM-DD.`);
  }

  const secs = e.inner.filter((h) => h.level === 3);
  for (const h of e.inner.filter((h) => h.level < 3)) {
    add(h.line + 1, `"${h.raw}" splits the entry. Use one of the ### sections, or move it out of the changelog.`);
  }
  if (secs.length === 0) {
    add(at, "the entry has no sections. Put each change under ### Breaking Changes, Added, Fixed, Changed or Verification.");
  }

  const firstSec = secs.length ? secs[0].line : e.end;
  for (let i = e.start + 1; i < firstSec; i++) {
    if (lines[i].trim()) { add(i + 1, "text before the first section. Move it under one of the ### sections, or remove it."); break; }
  }

  const lang = secs.length && SECTIONS.zh.includes(secs[0].text) ? "zh" : "en";
  const names = SECTIONS[lang];
  let last = -1;
  const seen = new Set();
  secs.forEach((h, k) => {
    const idx = names.indexOf(h.text);
    if (idx < 0) {
      const other = SECTIONS[lang === "en" ? "zh" : "en"].includes(h.text);
      add(h.line + 1, other
        ? `"${h.text}" mixes languages in one entry. Use ${names.join(", ")}.`
        : `"### ${h.text}" is not a section name. Use one of: ${names.join(", ")}.`);
      return;
    }
    if (seen.has(h.text)) add(h.line + 1, `"### ${h.text}" appears twice. Merge the two into one.`);
    else if (idx < last) add(h.line + 1, `"### ${h.text}" is out of order. The order is: ${names.join(", ")}.`);
    seen.add(h.text);
    last = Math.max(last, idx);
    const end = k + 1 < secs.length ? secs[k + 1].line : e.end;
    if (!lines.slice(h.line + 1, end).some((l) => l.trim())) {
      add(h.line + 1, `"### ${h.text}" is empty. Remove the section when it has nothing.`);
    }
  });

  let fence = false;
  for (let i = e.start + 1; i < e.end; i++) {
    if (/^\s*(```|~~~)/.test(lines[i])) { fence = !fence; continue; }
    if (fence) continue;
    const text = lines[i].replace(/`[^`]*`/g, "").replace(/\]\([^)]*\)/g, "]");
    const h = text.match(HASH);
    if (h) add(i + 1, `"${h[0]}" looks like a commit hash. Say what changed for the user instead.`);
  }
}

function check(file, all) {
  const lines = readLines(file);
  const problems = [];
  const add = (line, msg) => problems.push({ line, msg });

  const first = lines.findIndex((l) => l.trim());
  if (first < 0 || lines[first].trim() !== "# Changelog") {
    add(first < 0 ? 1 : first + 1, 'the file does not start with "# Changelog". Put that heading on the first line.');
  }

  const es = entries(lines);
  if (es.length === 0) {
    add(1, 'no version entries. Add one like "## 1.0.0 - 2026-11-24" below "# Changelog".');
  } else {
    for (const e of all ? es : [es[0]]) checkEntry(lines, e, add);
    // Without --all: the newest entry against every other. With --all: each entry against the next, and duplicates.
    const pairs = [];
    if (all) {
      const seenAt = new Map();
      for (const e of es) {
        if (!e.version) continue;
        if (seenAt.has(e.version)) add(e.start + 1, `version ${e.version} appears twice (line ${seenAt.get(e.version)} too). Keep one entry per version.`);
        else seenAt.set(e.version, e.start + 1);
      }
      const vs = es.filter((e) => e.version);
      for (let k = 0; k + 1 < vs.length; k++) pairs.push([vs[k], vs[k + 1], false]);
    } else if (es[0].version) {
      // compare with the highest older version only, so one misplaced entry gives one problem
      const top = es.slice(1).filter((b) => b.version).sort((x, y) => cmpSemver(y.version, x.version))[0];
      if (top) pairs.push([es[0], top, true]);
    }
    for (const [a, b, dup] of pairs) {
      const c = cmpSemver(a.version, b.version);
      if (c === 0 && dup) add(a.start + 1, `version ${a.version} already has an entry at line ${b.start + 1}. Keep one entry per version.`);
      else if (c < 0) add(a.start + 1, `${a.version} is above ${b.version} (line ${b.start + 1}). Newest versions go first.`);
    }
  }

  problems.sort((x, y) => x.line - y.line);
  for (const p of problems) console.log(`${file}:${p.line}: ${p.msg}`);
  const scope = all ? "all versions" : es.length ? `version ${es[0].version ?? "(unreadable)"}` : "the file";
  console.log(problems.length ? `${problems.length} problem(s) in ${scope}.` : `No problems in ${scope}.`);
  return problems.length ? 1 : 0;
}

function print(version, file) {
  const lines = readLines(file);
  const want = version.replace(/^v/, "");
  const e = entries(lines).find((x) => x.version === want);
  if (!e) {
    console.error(`${file}: no entry for version ${want}. Versions found: ${entries(lines).map((x) => x.version).filter(Boolean).join(", ") || "none"}.`);
    return 1;
  }
  console.log(lines.slice(e.start + 1, e.end).join("\n").trim());
  return 0;
}

function main(argv) {
  if (argv.length === 0 || argv.includes("--help") || argv.includes("-h")) {
    console.log(HELP);
    return argv.length === 0 ? 2 : 0;
  }
  const [cmd, ...rest] = argv;
  const flags = rest.filter((a) => a.startsWith("--"));
  const args = rest.filter((a) => !a.startsWith("--"));
  const bad = flags.filter((f) => !(cmd === "check" && f === "--all"));
  if (bad.length) { console.error(`unknown option ${bad[0]}. Run with --help.`); return 2; }
  if (cmd === "check") {
    if (args.length > 1) { console.error("check takes one file. Run with --help."); return 2; }
    return check(args[0] ?? "CHANGELOG.md", flags.includes("--all"));
  }
  if (cmd === "print") {
    if (args.length < 1 || args.length > 2) { console.error("print needs a version, like: print 1.4.0 [file]"); return 2; }
    return print(args[0], args[1] ?? "CHANGELOG.md");
  }
  console.error(`unknown command "${cmd}". Use check or print; run with --help.`);
  return 2;
}

process.exitCode = main(process.argv.slice(2));
