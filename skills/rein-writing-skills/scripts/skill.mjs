#!/usr/bin/env node
// skill.mjs: check, run and trigger-test agent skills (folders with a SKILL.md).
// Node.js 18+, standard library only. Run `node skill.mjs --help`.

import { spawn, spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import {
  appendFileSync, cpSync, existsSync, mkdirSync, readFileSync, readdirSync, realpathSync, statSync, writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SELF = fileURLToPath(import.meta.url);
const WIN = process.platform === "win32";

const HELP = {
  main: `Usage: node skill.mjs <command> [options]

Commands:
  check <skill folder>...    Check structure and wording. Free; changes nothing.
  run <case folder>...       Run test cases in throwaway folders with Claude Code. Costs money.
  triggers <prompts.json>    Say each prompt in fresh sessions and report whether the skill loaded. Costs money.

Run \`node skill.mjs <command> --help\` for the options of one command.
Exit codes: 0 done (check: no errors), 1 problems found or a run failed, 2 wrong usage.`,

  check: `Usage: node skill.mjs check <skill folder>... [--json] [--strict]

Checks each folder's SKILL.md and the files it points to. Every problem names the file, the line and what to do.
  errors    the --- block does not parse; name missing, malformed, over 64 characters or not the folder's
            name; description missing or over 1024 characters; compatibility over 500 characters; a path
            in SKILL.md that does not exist.
  warnings  the description never says when to use the skill or what it is not for; no section for
            done-when, stop-and-ask or output; shouted words (MUST, NEVER, 务必...); fields only Claude
            Code reads; references that SKILL.md never points to, that point to other references, or that
            are long with no contents list; a body over 300 lines (over 500 is past the specification).
  --json    print one JSON object instead of lines
  --strict  exit 1 on warnings too
Example: node skill.mjs check skills/writing-release-notes`,

  run: `Usage: node skill.mjs run <case folder>... (--skill <skill folder> | --without) [options]

Runs each test case in a new Claude Code session, in a throwaway project under --out. A case folder holds
prompt.md (settings block, then what the user says), case.yaml (name, expected_outcome), graders/*.md (one
statement each), and optionally files/ (copied into the project) and followups.md (what the user says next,
one reply per turn, replies separated by a line with only ---). Each run costs money.

  --skill <folder>       the skill to test; it is copied beside the project and added with --add-dir
  --without              run with no skill: the baseline
  --label <text>         the run folder is <out>/<case>-<label> (default: the skill's name, or "none")
  --out <folder>         where run folders go (default: <system temp>/skill-runs)
  --model <model>        passed to claude
  --effort <level>       passed to claude
  --max-budget-usd <n>   passed to claude, per turn
  --jobs <n>             cases run at once (default 1)
  --scaffold             run case.yaml's context.scaffold_script with bash instead of copying files/

The session sees none of your own skills, plugins, settings or MCP servers; your CLAUDE.md is still read.
It runs with full permissions inside the throwaway project. A hook blocks writing files outside the run
folder, shell commands that name your home folder or a path outside the run folder, and starting more
sessions. Tools that reach outside (notifications, schedules, remote triggers) are turned off.
Each run folder gets project/, trace.jsonl (every step), run.json (summary), reply.md (the conversation)
and grade.md (the graders, to mark PASS or FAIL with evidence).
Example: node skill.mjs run tests/evals/new-skill --skill skills/my-skill --out runs`,

  triggers: `Usage: node skill.mjs triggers <prompts.json> --skill <skill folder> [options]

Says each prompt in fresh, read-only Claude Code sessions (6 turns at most) and records whether the skill
was loaded. A prompt triggers when more than half of its runs loaded the skill, and passes when that
matches its "trigger". Costs money: one session per prompt and run.

prompts.json: {"fixture": "<folder copied as the project; optional; relative to this file>",
               "prompts": [{"prompt": "...", "trigger": true, "group": "tune"}, ...]}
  --runs <n>             sessions per prompt (default 3)
  --group <name>         only the prompts of this group
  --description <text>   try another description; the skill folder is not changed
  --label <text>         the results folder is <out>/triggers-<label> (default: the skill's name)
  --out <folder>         default: <system temp>/skill-runs
  --model, --effort, --max-budget-usd    passed to claude
  --jobs <n>             sessions at once (default 4)
Writes results.json there and prints one line per prompt.`,
};

class UsageError extends Error {}

// ---------------------------------------------------------------- arguments

function parseArgs(argv, flags, values) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--help" || a === "-h") { out.help = true; continue; }
    if (a.startsWith("--")) {
      const eq = a.indexOf("=");
      const key = eq > 0 ? a.slice(2, eq) : a.slice(2);
      if (flags.includes(key)) { out[key] = true; continue; }
      if (values.includes(key)) {
        const v = eq > 0 ? a.slice(eq + 1) : argv[++i];
        if (v === undefined) throw new UsageError(`--${key} needs a value.`);
        out[key] = v;
        continue;
      }
      throw new UsageError(`Unknown option ${a}.`);
    }
    out._.push(a);
  }
  return out;
}

function positiveInt(v, name, fallback) {
  if (v === undefined) return fallback;
  const n = Number(v);
  if (!Number.isInteger(n) || n < 1) throw new UsageError(`--${name} must be a whole number of 1 or more, not "${v}".`);
  return n;
}

// ---------------------------------------------------------------- frontmatter

function splitFrontmatter(text) {
  const lines = text.replace(/^﻿/, "").split(/\r?\n/);
  if (lines[0].trim() !== "---") return null;
  const end = lines.findIndex((l, i) => i > 0 && l.trim() === "---");
  if (end < 0) return { unclosed: true, lines };
  return { lines, head: lines.slice(1, end), body: lines.slice(end + 1), bodyStart: end + 2 };
}

function closedDouble(t) {
  return t.length > 1 && /(^|[^\\])(\\\\)*"$/.test(t);
}

function scalar(raw) {
  raw = raw.trim();
  if (raw.startsWith("'")) {
    return raw.length > 1 && raw.endsWith("'")
      ? { value: raw.slice(1, -1).replace(/''/g, "'"), style: "single" }
      : { value: raw, style: "broken" };
  }
  if (raw.startsWith('"')) {
    try { return { value: JSON.parse(raw), style: "double" }; } catch { return { value: raw, style: "broken" }; }
  }
  if (raw.startsWith("[") && raw.endsWith("]")) {
    return { value: raw.slice(1, -1).split(",").map((s) => s.trim()).filter(Boolean).map((s) => scalar(s).value), style: "list" };
  }
  return { value: raw.replace(/\s+#.*$/, ""), style: "plain" };
}

// Reads the small YAML subset skill files use: top-level key: value, quoted strings, block scalars (| and >),
// flow lists ([a, b]), and one level of nested map or list. Reports what real YAML would choke on.
function readYaml(lines, firstLine = 1) {
  const fields = {};
  const problems = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim() || /^\s*#/.test(line)) continue;
    const at = firstLine + i;
    const from = i;
    if (/^\s/.test(line)) {
      problems.push({ line: at, code: "frontmatter.indent", msg: "an indented line that belongs to no field. Indent only the lines under a field such as metadata:." });
      continue;
    }
    const m = line.match(/^([A-Za-z0-9_-]+):(?:[ \t]+(.*?))?[ \t]*$/);
    if (!m) {
      problems.push({ line: at, code: "frontmatter.line", msg: `cannot read "${line.trim().slice(0, 50)}". Write each field as key: value.` });
      continue;
    }
    const key = m[1];
    const raw = m[2] ?? "";
    const block = [];
    const take = () => {
      while (i + 1 < lines.length && (/^\s/.test(lines[i + 1]) || !lines[i + 1].trim())) block.push(lines[++i]);
      while (block.length && !block[block.length - 1].trim()) { block.pop(); i--; }
    };
    let value;
    let style;
    if (raw === "") {
      take();
      style = "map";
      if (block.length && block.every((b) => !b.trim() || /^\s+-(\s|$)/.test(b))) {
        value = block.filter((b) => b.trim()).map((b) => scalar(b.replace(/^\s+-\s*/, "")).value);
      } else {
        value = {};
        for (const b of block) {
          const mm = b.match(/^\s+([A-Za-z0-9_-]+):(?:[ \t]+(.*?))?[ \t]*$/);
          if (mm) value[mm[1]] = scalar(mm[2] ?? "").value;
        }
      }
    } else if (/^[|>][+-]?\d*$/.test(raw)) {
      take();
      style = "block";
      const used = block.filter((b) => b.trim());
      const indent = used.length ? Math.min(...used.map((b) => b.match(/^\s*/)[0].length)) : 0;
      const parts = block.map((b) => b.slice(indent));
      value = raw[0] === "|" ? parts.join("\n") : parts.join(" ").replace(/\s+/g, " ").trim();
    } else if (raw.startsWith('"')) {
      let t = raw;
      while (!closedDouble(t) && i + 1 < lines.length && /^\s/.test(lines[i + 1])) t += " " + lines[++i].trim();
      try {
        value = JSON.parse(t);
        style = "double";
      } catch {
        value = t.replace(/^"|"$/g, "");
        style = "broken";
        problems.push({ line: at, code: `${key}.quotes`, msg: `${key} is in double quotes but does not parse. Write each " inside it as \\" and each \\ as \\\\.` });
      }
    } else {
      ({ value, style } = scalar(raw));
      if (style === "broken") {
        problems.push({ line: at, code: `${key}.quotes`, msg: `${key} opens a single quote it never closes. Write each ' inside it as ''.` });
      } else if (style === "plain") {
        if (/:\s|:$/.test(raw)) {
          problems.push({ line: at, code: `${key}.colon`, msg: `${key} has ": " in a value without quotes, which breaks YAML: the skill then loads with no ${key}. Put the value in double quotes.` });
        } else if (/\s#/.test(raw)) {
          problems.push({ line: at, code: `${key}.comment`, msg: `" #" in a value without quotes starts a comment and cuts ${key} there. Put the value in double quotes.` });
        } else if (/^[{*&!%@`]|^[?-]\s/.test(raw)) {
          problems.push({ line: at, code: `${key}.indicator`, msg: `${key} starts with a character YAML reads specially. Put the value in double quotes.` });
        }
      }
    }
    if (fields[key]) problems.push({ line: at, code: "frontmatter.duplicate", msg: `${key} appears twice; tools keep only one. Remove the other.` });
    fields[key] = { value, line: at, style, from, to: i };
  }
  return { fields, problems };
}

function plainFields(fields) {
  return Object.fromEntries(Object.entries(fields).map(([k, f]) => [k, f.value]));
}

// ---------------------------------------------------------------- check

const SPEC_KEYS = new Set(["name", "description", "license", "compatibility", "metadata", "allowed-tools"]);
const CLAUDE_KEYS = new Set([
  "when_to_use", "argument-hint", "arguments", "disable-model-invocation", "user-invocable", "disallowed-tools",
  "model", "effort", "context", "agent", "background", "hooks", "paths", "shell",
]);
const USE_WHEN = /\buse (?:it |this(?: skill)? )?(?:when|whenever|for)\b|\bwhen (?:the )?user\b|用于|使用场景|什么时候用|时使用/i;
const NOT_FOR = /\bnot for\b|\bnot when\b|\bdo not use\b|\bdon'?t use\b|不用于|不适用|不要用/i;
const HEADINGS = [
  ["done", /done when|definition of done|complet|finished when|完成标准|做到什么算完|算完成|验收/i,
    "no section says when the work is done. Add a 'Done when' list the agent can check, near the top."],
  ["stop", /\bstop\b|\bask\b|停下|问用户|什么时候问|要问/i,
    "no section says when to stop and ask the user. Add one if any step needs the user's decision."],
  ["output", /\boutput\b|hand ?over|deliver|\breport\b|输出|交付|交给用户|回复/i,
    "no section says what the agent hands over. Add an 'Output' section: what the reply or the files look like."],
];
const SHOUT = /\b(?:MUST|NEVER|ALWAYS|CRITICAL|IMPORTANT|REQUIRED)\b|务必|硬性要求|绝对不|一定要|严禁/g;
const PATH_REF = /(?<![\w./\\-])((?:references|scripts|assets|agents)\/[^\s`'"()<>[\]{},;:*|]+)/g;
const MD_LINK = /\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;

function walk(dir) {
  const out = [];
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) out.push(...walk(p));
    else out.push(p);
  }
  return out.sort();
}

function tokens(text) {
  let ascii = 0;
  let other = 0;
  for (const ch of text) (ch.charCodeAt(0) < 128 ? ascii++ : other++);
  return Math.round(ascii / 4 + other);
}

function checkSkill(target) {
  let dir = resolve(target);
  if (existsSync(dir) && statSync(dir).isFile()) dir = dirname(dir);
  const report = { dir: target, name: null, errors: [], warnings: [], stats: {} };
  const add = (level, file, line, code, message) =>
    report[level === "error" ? "errors" : "warnings"].push({ file, line, code, message });
  const file = join(dir, "SKILL.md");
  if (!existsSync(file)) {
    add("error", "SKILL.md", 0, "skill.missing", "no SKILL.md in this folder. A skill is a folder with a SKILL.md at its top.");
    return report;
  }
  const text = readFileSync(file, "utf8");
  const fm = splitFrontmatter(text);
  if (!fm) {
    add("error", "SKILL.md", 1, "frontmatter.missing", "line 1 is not ---. Start the file with a --- block holding name and description; without it, tools read the whole file as the body.");
    return report;
  }
  if (fm.unclosed) {
    add("error", "SKILL.md", 1, "frontmatter.unclosed", "the --- block at the top is never closed. Add a line with only --- after the last field.");
    return report;
  }
  const { fields, problems } = readYaml(fm.head, 2);
  for (const p of problems) add("error", "SKILL.md", p.line, p.code, p.msg);

  const folder = basename(dir);
  const name = fields.name?.value;
  if (typeof name !== "string" || !name) {
    add("error", "SKILL.md", fields.name?.line || 1, "name.missing", `no name. Add name: ${folder} (the folder's name).`);
  } else {
    report.name = name;
    const at = fields.name.line;
    if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(name)) add("error", "SKILL.md", at, "name.format", `name "${name}" may use only lowercase letters, digits and single hyphens, not at either end.`);
    if (name.length > 64) add("error", "SKILL.md", at, "name.long", `name has ${name.length} characters; the limit is 64.`);
    if (name !== folder) add("error", "SKILL.md", at, "name.folder", `name "${name}" differs from the folder "${folder}". Make them the same: tools find a skill by its folder and show it by its name.`);
    if (/anthropic|claude/.test(name)) add("warning", "SKILL.md", at, "name.reserved", `the name contains "anthropic" or "claude"; claude.ai and the Skills API refuse such names.`);
  }

  const d = fields.description;
  const desc = typeof d?.value === "string" ? d.value.trim() : "";
  if (!desc) {
    add("error", "SKILL.md", d?.line || 1, "description.missing", "no description. Add one: what the skill does, when to use it, what it is not for. Agents decide from it whether to load the skill.");
  } else {
    const at = d.line;
    if (desc.length > 1024) add("error", "SKILL.md", at, "description.long", `the description has ${desc.length} characters; the limit is 1024. Cut summaries of the steps or rules first: they belong in the body.`);
    const extra = typeof fields.when_to_use?.value === "string" ? fields.when_to_use.value.length : 0;
    if (desc.length + extra > 1536) add("warning", "SKILL.md", at, "description.listing", `description and when_to_use have ${desc.length + extra} characters together; Claude Code cuts the listing at 1536.`);
    // A CJK character carries about as much as two Latin letters.
    const width = [...desc].reduce((n, ch) => n + (ch.charCodeAt(0) > 0x2e7f ? 2 : 1), 0);
    if (width < 50) add("warning", "SKILL.md", at, "description.short", `the description has only ${desc.length} characters. Say when to use the skill, in the words a user would say.`);
    if (!USE_WHEN.test(desc)) add("warning", "SKILL.md", at, "description.use-when", `the description never says when to use the skill. Add "Use when ..." with the situations and the words a user would say.`);
    if (!NOT_FOR.test(desc)) add("warning", "SKILL.md", at, "description.not-for", `the description never says what the skill is not for. Add "Not for ..." naming the nearest tasks or skills, so a similar request goes elsewhere.`);
    if (/[<>]/.test(desc)) add("warning", "SKILL.md", at, "description.angle", "the description has < or >; Claude Code shows them as &lt; and &gt;.");
  }
  const compat = fields.compatibility?.value;
  if (typeof compat === "string" && compat.length > 500) add("error", "SKILL.md", fields.compatibility.line, "compatibility.long", `compatibility has ${compat.length} characters; the limit is 500.`);
  for (const [k, f] of Object.entries(fields)) {
    if (SPEC_KEYS.has(k)) continue;
    if (CLAUDE_KEYS.has(k)) add("warning", "SKILL.md", f.line, "field.claude-only", `${k} is read only by Claude Code: Codex ignores it, and the claude.ai upload and the Skills API refuse it. Keep it only if the skill is for Claude Code alone.`);
    else add("warning", "SKILL.md", f.line, "field.unknown", `no tool reads "${k}". Move it under metadata, or remove it.`);
  }

  const body = fm.body;
  let last = body.length;
  while (last > 0 && !body[last - 1].trim()) last--;
  const bodyLines = last;
  if (bodyLines > 500) add("warning", "SKILL.md", fm.bodyStart, "body.long", `the body has ${bodyLines} lines, over the 500 the specification recommends. Move what only some runs need into references/ and say when to read each file.`);
  else if (bodyLines > 300) add("warning", "SKILL.md", fm.bodyStart, "body.long", `the body has ${bodyLines} lines. Every line is read each time the skill loads; move what only some runs need into references/.`);

  const headings = [];
  const shouts = [];
  const seen = new Set();
  let fence = false;
  body.forEach((line, i) => {
    const at = fm.bodyStart + i;
    if (/^\s*(```|~~~)/.test(line)) { fence = !fence; return; }
    if (fence) return;
    const h = line.match(/^#{1,6}\s+(.*)$/);
    if (h) headings.push(h[1]);
    const prose = line.replace(/`[^`]*`/g, "");
    const s = prose.match(SHOUT);
    if (s) shouts.push({ at, words: s });
    if (/(?:references|scripts|assets)\\\w/.test(line)) add("warning", "SKILL.md", at, "path.backslash", "a path written with backslashes. Use forward slashes: they work on every system.");
    const refs = [];
    for (const m of line.matchAll(MD_LINK)) {
      const t = m[1];
      if (/^[a-z][a-z0-9+.-]*:/i.test(t) || t.startsWith("#")) continue;
      let p = t.split("#")[0];
      try { p = decodeURI(p); } catch { /* keep as written */ }
      if (p) refs.push(p);
    }
    for (const m of line.matchAll(PATH_REF)) refs.push(m[1].replace(/[.)]+$/, ""));
    for (const p of refs) {
      if (seen.has(p)) continue;
      seen.add(p);
      if (!existsSync(join(dir, p))) add("error", "SKILL.md", at, "link.missing", `${p} does not exist in the skill folder. Fix the path, or create the file.`);
    }
  });
  for (const [key, re, msg] of HEADINGS) {
    if (!headings.some((h) => re.test(h))) add("warning", "SKILL.md", 0, "body." + key, msg);
  }
  const shouted = shouts.reduce((n, s) => n + s.words.length, 0);
  if (shouted >= 3) {
    const words = [...new Set(shouts.flatMap((s) => s.words))].join(", ");
    add("warning", "SKILL.md", shouts[0].at, "body.shouting", `${shouted} shouted words (${words}) on lines ${shouts.map((s) => s.at).join(", ")}. Say why in a clause instead; keep a hard word only for a rule agents break under pressure.`);
  }

  const refDir = join(dir, "references");
  if (existsSync(refDir) && statSync(refDir).isDirectory()) {
    for (const f of walk(refDir)) {
      const rel = "references/" + relative(refDir, f).replace(/\\/g, "/");
      if (!text.includes(rel)) add("warning", rel, 0, "reference.unlinked", `SKILL.md never points to ${rel}. Say when to read it ("When ..., read ${rel}"), or delete it.`);
      if (!/\.(md|markdown|txt)$/i.test(f)) continue;
      const t = readFileSync(f, "utf8");
      const lines = t.split(/\r?\n/);
      const inner = lines.findIndex((l) => [...l.matchAll(PATH_REF)].some((m) => m[1].startsWith("references/") && m[1] !== rel));
      if (inner >= 0) add("warning", rel, inner + 1, "reference.nested", `${rel} points to another file in references/. Point to every reference from SKILL.md instead: an agent may read only the start of a file it reaches through another.`);
      if (lines.length > 100 && !/^#{1,3}\s*(contents|table of contents|目录)\s*$/im.test(t)) add("warning", rel, 1, "reference.contents", `${rel} has ${lines.length} lines and no contents list. Put a "## Contents" list near the top, so an agent that reads only the start knows what is there.`);
    }
  }

  report.stats = { descChars: desc.length, bodyLines, tokens: tokens(body.slice(0, last).join("\n")) };
  return report;
}

function cmdCheck(argv) {
  const a = parseArgs(argv, ["json", "strict"], []);
  if (a.help) return console.log(HELP.check), 0;
  if (!a._.length) throw new UsageError("Name at least one skill folder.");
  const reports = a._.map(checkSkill);
  const errors = reports.reduce((n, r) => n + r.errors.length, 0);
  const warnings = reports.reduce((n, r) => n + r.warnings.length, 0);
  if (a.json) {
    console.log(JSON.stringify({ skills: reports, errors, warnings }, null, 2));
  } else {
    for (const r of reports) {
      const s = r.stats;
      const size = s.bodyLines === undefined ? "" : ` · description ${s.descChars} characters · body ${s.bodyLines} lines, about ${s.tokens} tokens`;
      console.log(`${r.dir}: ${r.errors.length} error(s), ${r.warnings.length} warning(s)${size}`);
      for (const [level, list] of [["error", r.errors], ["warning", r.warnings]]) {
        for (const p of list) console.log(`  ${p.file}${p.line ? ":" + p.line : ""}: ${level} ${p.code}: ${p.message}`);
      }
    }
  }
  return errors || (a.strict && warnings) ? 1 : 0;
}

// ---------------------------------------------------------------- sessions

const OUTWARD = [
  "Artifact", "ArtifactComments", "ArtifactData", "CronCreate", "CronDelete", "DesignSync", "EnterWorktree",
  "ExitWorktree", "PushNotification", "RemoteTrigger", "ScheduleWakeup", "SendMessage",
];
const KEEP_ENV = new Set(["CLAUDE_CODE_GIT_BASH_PATH", "CLAUDE_CONFIG_DIR"]);
const BLOCKED = "Blocked by the test run";

function findClaude() {
  const bin = process.env.CLAUDE_BIN;
  if (bin) return /\.(m?js|cjs)$/i.test(bin) ? [process.execPath, bin] : [bin];
  const names = WIN ? ["claude.exe", "claude.cmd"] : ["claude"];
  for (const d of (process.env.PATH || "").split(WIN ? ";" : ":")) {
    for (const n of names) {
      const p = join(d, n);
      if (!existsSync(p)) continue;
      if (n === "claude.cmd") {
        const exe = join(d, "node_modules", "@anthropic-ai", "claude-code", "bin", "claude.exe");
        if (existsSync(exe)) return [exe];
        continue;
      }
      return [p];
    }
  }
  throw new Error("Claude Code not found. Put claude on PATH, or set CLAUDE_BIN to its path.");
}

function sessionEnv() {
  const env = {};
  for (const [k, v] of Object.entries(process.env)) {
    if ((k.startsWith("CLAUDE") || k.startsWith("AI_AGENT")) && !KEEP_ENV.has(k)) continue;
    env[k] = v;
  }
  env.ENABLE_CLAUDEAI_MCP_SERVERS = "false";
  return env;
}

function killTree(child) {
  if (WIN) spawnSync("taskkill", ["/T", "/F", "/PID", String(child.pid)], { windowsHide: true });
  else child.kill("SIGKILL");
}

// One `claude -p` turn; every event is appended to `trace`. Resolves with the exit code and the result event.
function runClaude(cmd, args, { cwd, input, timeoutMs, trace, marker }) {
  appendFileSync(trace, JSON.stringify({ type: "runner", ...marker }) + "\n");
  return new Promise((done) => {
    let child;
    try {
      child = spawn(cmd[0], [...cmd.slice(1), ...args], { cwd, env: sessionEnv(), windowsHide: true });
    } catch (e) {
      done({ exit: null, result: null, timedOut: false, stderr: String(e) });
      return;
    }
    let buf = "";
    let err = "";
    let result = null;
    let timedOut = false;
    let finished = false;
    const take = (line) => {
      if (!line.trim()) return;
      let ev;
      try { ev = JSON.parse(line); } catch { ev = { type: "runner", unparsed: line }; }
      appendFileSync(trace, JSON.stringify(ev) + "\n");
      if (ev.type === "result") result = ev;
    };
    const timer = setTimeout(() => { timedOut = true; killTree(child); }, timeoutMs);
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (d) => {
      buf += d;
      let k;
      while ((k = buf.indexOf("\n")) >= 0) { take(buf.slice(0, k)); buf = buf.slice(k + 1); }
    });
    child.stderr.on("data", (d) => { err += d; });
    const finish = (code) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      take(buf);
      done({ exit: code, result, timedOut, stderr: err.slice(-4000) });
    };
    child.on("error", (e) => { err += String(e); finish(null); });
    child.on("close", finish);
    child.stdin.on("error", () => {});
    child.stdin.end(input);
  });
}

function readEvents(file) {
  if (!existsSync(file)) return [];
  return readFileSync(file, "utf8").split("\n").filter((l) => l.trim()).map((l) => {
    try { return JSON.parse(l); } catch { return {}; }
  });
}

function toolCalls(events) {
  const calls = [];
  for (const e of events) {
    if (e.type !== "assistant") continue;
    for (const b of e.message?.content || []) if (b?.type === "tool_use") calls.push({ name: String(b.name), input: b.input || {} });
  }
  return calls;
}

function blockedCount(events) {
  let n = 0;
  for (const e of events) {
    if (e.type !== "user") continue;
    for (const b of e.message?.content || []) {
      if (b?.type !== "tool_result") continue;
      const c = typeof b.content === "string" ? b.content : JSON.stringify(b.content || "");
      if (c.includes(BLOCKED)) n++;
    }
  }
  return n;
}

const SKILL_FILE = /[\\/]([\w.-]+)[\\/]SKILL\.md\b/gi;

function loadedSkills(calls) {
  const found = [];
  const add = (n) => { if (n && !found.includes(n)) found.push(n); };
  for (const { name, input } of calls) {
    if (name === "Skill") add(String(input.skill || input.command || "").split(":").pop());
    else if (name === "Read") for (const m of String(input.file_path || "").matchAll(SKILL_FILE)) add(m[1]);
    else if (name === "Bash" || name === "PowerShell") for (const m of String(input.command || "").matchAll(SKILL_FILE)) add(m[1]);
  }
  return found;
}

function git(cwd, ...args) {
  const r = spawnSync("git", ["-c", "user.name=skill-test", "-c", "user.email=skill-test@example.invalid", "-c", "core.autocrlf=false", ...args], { cwd, encoding: "utf8", windowsHide: true });
  if (r.status !== 0) throw new Error(`git ${args.join(" ")} failed in ${cwd}: ${(r.stderr || r.error || "").toString().trim()}`);
  return r.stdout;
}

function newProject(project, from) {
  mkdirSync(project, { recursive: true });
  if (from && existsSync(from)) cpSync(from, project, { recursive: true });
  git(project, "init", "-q");
  git(project, "add", "-A");
  git(project, "commit", "-q", "--allow-empty", "-m", "test case files");
}

const SKIP_COPY = new Set([".git", "node_modules", "__pycache__"]);

function skillName(dir) {
  const fm = splitFrontmatter(readFileSync(join(dir, "SKILL.md"), "utf8"));
  const n = fm && !fm.unclosed ? readYaml(fm.head).fields.name?.value : null;
  return typeof n === "string" && n ? n : basename(resolve(dir));
}

// Copies the skill to <home>/.claude/skills/<name>; returns the name.
function installSkill(dir, home, description) {
  if (!existsSync(join(dir, "SKILL.md"))) throw new UsageError(`${dir} has no SKILL.md.`);
  const name = skillName(dir);
  const dest = join(home, ".claude", "skills", name);
  cpSync(dir, dest, { recursive: true, filter: (src) => !SKIP_COPY.has(basename(src)) });
  if (description !== undefined) {
    const file = join(dest, "SKILL.md");
    const fm = splitFrontmatter(readFileSync(file, "utf8"));
    const f = readYaml(fm.head).fields.description;
    const line = "description: " + JSON.stringify(description);
    const lines = fm.lines.slice();
    if (f) lines.splice(1 + f.from, f.to - f.from + 1, line);
    else lines.splice(1, 0, line);
    writeFileSync(file, lines.join("\n"), "utf8");
  }
  return name;
}

function canonical(p) {
  let cur = resolve(p);
  const rest = [];
  while (!existsSync(cur)) {
    const up = dirname(cur);
    if (up === cur) break;
    rest.unshift(basename(cur));
    cur = up;
  }
  let real = cur;
  try { real = realpathSync.native(cur); } catch { /* keep */ }
  return join(real, ...rest);
}

function norm(p) {
  let s = resolve(p).replace(/\\/g, "/").replace(/\/+$/, "");
  if (WIN) s = s.toLowerCase();
  return s;
}

function inside(root, p) {
  const a = norm(root);
  const b = norm(p);
  return b === a || b.startsWith(a + "/");
}

function settingsFor(root, guard) {
  const settings = { autoMemoryDirectory: join(root, "auto-memory").replace(/\\/g, "/") };
  if (guard) {
    const node = process.execPath.replace(/\\/g, "/");
    settings.hooks = {
      PreToolUse: [{
        matcher: [...WRITE_TOOLS, ...SHELL_TOOLS].join("|"),
        hooks: [{ type: "command", command: `"${node}" "${SELF.replace(/\\/g, "/")}" guard "${root.replace(/\\/g, "/")}"` }],
      }],
    };
  }
  const file = join(root, "settings.json");
  writeFileSync(file, JSON.stringify(settings, null, 2) + "\n", "utf8");
  return file;
}

function modelArgs(a) {
  const out = [];
  if (a.model) out.push("--model", a.model);
  if (a.effort) out.push("--effort", a.effort);
  if (a["max-budget-usd"]) out.push("--max-budget-usd", a["max-budget-usd"]);
  return out;
}

async function pool(items, jobs, fn) {
  const out = new Array(items.length);
  let next = 0;
  const worker = async () => {
    while (next < items.length) {
      const k = next++;
      out[k] = await fn(items[k], k);
    }
  };
  await Promise.all(Array.from({ length: Math.min(jobs, items.length) }, worker));
  return out;
}

const money = (n) => "$" + (n || 0).toFixed(2);

// ---------------------------------------------------------------- run

function readCase(dir) {
  const promptFile = join(dir, "prompt.md");
  if (!existsSync(promptFile)) throw new UsageError(`${dir} has no prompt.md. A case folder holds prompt.md, case.yaml and graders/.`);
  const raw = readFileSync(promptFile, "utf8");
  const fm = splitFrontmatter(raw);
  const settings = fm && !fm.unclosed ? plainFields(readYaml(fm.head).fields) : {};
  const prompt = (fm && !fm.unclosed ? fm.body.join("\n") : raw).trim();
  if (!prompt) throw new UsageError(`${promptFile} has no prompt after its settings block.`);
  const yamlFile = join(dir, "case.yaml");
  const meta = existsSync(yamlFile) ? plainFields(readYaml(readFileSync(yamlFile, "utf8").split(/\r?\n/)).fields) : {};
  const gdir = join(dir, "graders");
  const graders = existsSync(gdir)
    ? readdirSync(gdir).filter((f) => f.endsWith(".md")).sort().map((f) => {
      const g = splitFrontmatter(readFileSync(join(gdir, f), "utf8"));
      const text = (g && !g.unclosed ? g.body.join("\n") : readFileSync(join(gdir, f), "utf8")).trim();
      return { name: f.replace(/\.md$/, ""), text };
    })
    : [];
  const fu = join(dir, "followups.md");
  const followups = existsSync(fu) ? readFileSync(fu, "utf8").split(/^---[ \t]*$/m).map((s) => s.trim()).filter(Boolean) : [];
  let tools = Array.isArray(settings.allowed_tools) ? settings.allowed_tools.map((t) => String(t).replace(/\(.*$/, "").trim()) : ["Write", "Edit", "Bash"];
  tools = [...new Set(["Read", "Glob", "Grep", "Skill", ...tools])].filter((t) => t && !OUTWARD.includes(t));
  return {
    dir,
    name: String(meta.name || basename(resolve(dir))),
    prompt,
    followups,
    maxTurns: Number(settings.max_turns) || 30,
    timeout: Number(settings.timeout_seconds) || 900,
    tools,
    expected: String(meta.expected_outcome || "").trim(),
    scaffold: meta.context && typeof meta.context === "object" ? meta.context.scaffold_script : undefined,
    graders,
  };
}

async function runCase(c, a, claude) {
  const label = a.label;
  const folder = resolve(a.out, `${c.name}-${label}`);
  mkdirSync(folder, { recursive: true });
  const root = canonical(folder);
  const project = join(root, "project");
  if (a.scaffold && c.scaffold) {
    mkdirSync(project, { recursive: true });
    const r = spawnSync("bash", [resolve(c.dir, c.scaffold).replace(/\\/g, "/")], { cwd: project, encoding: "utf8", windowsHide: true });
    if (r.status !== 0) throw new Error(`${c.name}: ${c.scaffold} failed: ${(r.stderr || r.error || "").toString().trim()}`);
  } else {
    newProject(project, join(c.dir, "files"));
  }
  let name = null;
  const args = [
    "-p", "--output-format", "stream-json", "--verbose", "--setting-sources", "project,local",
    "--settings", settingsFor(root, true), "--strict-mcp-config", "--dangerously-skip-permissions",
    "--tools", c.tools.join(","), "--disallowedTools", OUTWARD.join(","), "--max-turns", String(c.maxTurns),
    ...modelArgs(a),
  ];
  if (a.skill) {
    name = installSkill(a.skill, join(root, "skill-home"));
    args.push("--add-dir", join(root, "skill-home"));
  }
  const trace = join(root, "trace.jsonl");
  const session = randomUUID();
  const said = [c.prompt, ...c.followups];
  const turns = [];
  for (let k = 0; k < said.length; k++) {
    const extra = k === 0 ? ["--session-id", session] : ["--resume", session];
    const started = Date.now();
    const t = await runClaude(claude, [...args, ...extra], { cwd: project, input: said[k], timeoutMs: c.timeout * 1000, trace, marker: { turn: k + 1, said: said[k] } });
    const r = t.result || {};
    turns.push({
      said: said[k], exit: t.exit, timedOut: t.timedOut, seconds: Math.round((Date.now() - started) / 1000),
      cost: r.total_cost_usd || 0, numTurns: r.num_turns, error: Boolean(r.is_error) || !t.result || t.timedOut,
      reply: r.result || "", stderr: t.result ? undefined : t.stderr,
    });
    if (turns[k].error) break;
  }
  const events = readEvents(trace);
  const init = events.find((e) => e.type === "system" && e.subtype === "init") || {};
  const calls = toolCalls(events);
  let changed = [];
  try { changed = git(project, "status", "--porcelain", "-uall").split("\n").filter((l) => l.trim()); } catch { /* project may be gone */ }
  const summary = {
    case: c.name, label, skill: name, skillSource: a.skill ? resolve(a.skill) : null,
    model: init.model || a.model || null, claude: init.claude_code_version || null,
    cost: +turns.reduce((n, t) => n + t.cost, 0).toFixed(4), seconds: turns.reduce((n, t) => n + t.seconds, 0),
    failed: turns.some((t) => t.error) || turns.length < said.length,
    skillsLoaded: loadedSkills(calls), tools: calls.map((x) => x.name), blocked: blockedCount(events), changed,
    turns: turns.map(({ reply, ...rest }) => rest), folder: root,
  };
  writeFileSync(join(root, "run.json"), JSON.stringify(summary, null, 2) + "\n", "utf8");
  writeFileSync(join(root, "reply.md"), turns.map((t, k) =>
    `## Turn ${k + 1}: the user\n\n${t.said}\n\n## Turn ${k + 1}: the agent\n\n${t.reply || "(no reply" + (t.timedOut ? ": timed out" : "") + ")"}\n`).join("\n"), "utf8");
  writeFileSync(join(root, "grade.md"), [
    `# ${c.name} · ${label}`, "",
    `Expected: ${c.expected || "(case.yaml has no expected_outcome)"}`, "",
    "Mark each grader PASS or FAIL from what the run did, not from what the reply says it did: read the tool calls",
    "in trace.jsonl and the files in project/. Give the evidence in one line.", "",
    "| Grader | PASS / FAIL | Evidence |", "| --- | --- | --- |",
    ...c.graders.map((g) => `| ${g.name}: ${g.text.replace(/\s*\n\s*/g, " ").replace(/\|/g, "\\|")} | | |`), "",
  ].join("\n"), "utf8");
  return summary;
}

async function cmdRun(argv) {
  const a = parseArgs(argv, ["without", "scaffold"], ["skill", "label", "out", "model", "effort", "max-budget-usd", "jobs"]);
  if (a.help) return console.log(HELP.run), 0;
  if (!a._.length) throw new UsageError("Name at least one case folder.");
  if (!a.skill === !a.without) throw new UsageError("Give either --skill <folder> or --without.");
  if (a.skill && !existsSync(join(a.skill, "SKILL.md"))) throw new UsageError(`${a.skill} has no SKILL.md.`);
  const jobs = positiveInt(a.jobs, "jobs", 1);
  a.label = a.label || (a.skill ? skillName(a.skill) : "none");
  a.out = a.out || join(tmpdir(), "skill-runs");
  const cases = a._.map(readCase);
  for (const c of cases) {
    const folder = resolve(a.out, `${c.name}-${a.label}`);
    if (existsSync(folder)) throw new UsageError(`${folder} already exists. Give this run another --label; old runs are never overwritten.`);
  }
  const claude = findClaude();
  let failed = 0;
  await pool(cases, jobs, async (c) => {
    let s;
    try {
      s = await runCase(c, a, claude);
    } catch (e) {
      failed++;
      console.log(`${c.name}-${a.label}: could not run: ${e.message}`);
      return;
    }
    if (s.failed) failed++;
    const err = s.turns.find((t) => t.error);
    console.log([
      `${c.name}-${a.label}: ${s.failed ? "FAILED" : "done"} · ${s.turns.length} turn(s), ${money(s.cost)}, ${s.seconds}s · model ${s.model || "?"}`,
      `  skills loaded: ${s.skillsLoaded.join(", ") || "none"} · files changed: ${s.changed.length} · blocked: ${s.blocked}`,
      err ? `  ${err.timedOut ? "timed out" : "error"}: ${(err.stderr || err.reply || "no result event").toString().trim().slice(0, 300)}` : null,
      `  ${s.folder}  (grade it in grade.md)`,
    ].filter(Boolean).join("\n"));
  });
  return failed ? 1 : 0;
}

// ---------------------------------------------------------------- triggers

async function cmdTriggers(argv) {
  const a = parseArgs(argv, [], ["skill", "runs", "group", "description", "label", "out", "model", "effort", "max-budget-usd", "jobs"]);
  if (a.help) return console.log(HELP.triggers), 0;
  if (a._.length !== 1) throw new UsageError("Name one prompts file.");
  if (!a.skill) throw new UsageError("Give --skill <folder>.");
  if (!existsSync(join(a.skill, "SKILL.md"))) throw new UsageError(`${a.skill} has no SKILL.md.`);
  const file = a._[0];
  let spec;
  try { spec = JSON.parse(readFileSync(file, "utf8")); } catch (e) { throw new UsageError(`${file} is not readable JSON: ${e.message}`); }
  if (!Array.isArray(spec.prompts)) throw new UsageError(`${file} needs a "prompts" list.`);
  const prompts = spec.prompts.filter((p) => !a.group || p.group === a.group);
  if (!prompts.length) throw new UsageError(a.group ? `No prompt has group "${a.group}".` : "The prompts list is empty.");
  for (const [k, p] of prompts.entries()) {
    if (typeof p.prompt !== "string" || typeof p.trigger !== "boolean") throw new UsageError(`Prompt ${k + 1} needs "prompt" (text) and "trigger" (true or false).`);
  }
  const runs = positiveInt(a.runs, "runs", 3);
  const jobs = positiveInt(a.jobs, "jobs", 4);
  const label = a.label || skillName(a.skill);
  const base = resolve(a.out || join(tmpdir(), "skill-runs"), `triggers-${label}`);
  if (existsSync(base)) throw new UsageError(`${base} already exists. Give this run another --label; old runs are never overwritten.`);
  const fixture = spec.fixture ? resolve(dirname(file), spec.fixture) : null;
  if (fixture && !existsSync(fixture)) throw new UsageError(`The fixture ${fixture} does not exist.`);
  mkdirSync(base, { recursive: true });
  const root = canonical(base);
  const name = installSkill(a.skill, join(root, "skill-home"), a.description);
  const claude = findClaude();
  const jobsList = prompts.flatMap((p, i) => Array.from({ length: runs }, (_, r) => ({ p, i, r })));
  const results = await pool(jobsList, jobs, async ({ p, i, r }) => {
    const dir = join(root, `${i + 1}-${r + 1}`);
    newProject(join(dir, "project"), fixture);
    const args = [
      "-p", "--output-format", "stream-json", "--verbose", "--setting-sources", "project,local",
      "--settings", settingsFor(dir, false), "--strict-mcp-config", "--tools", "Read,Glob,Grep,Skill",
      "--max-turns", "6", "--add-dir", join(root, "skill-home"), ...modelArgs(a),
    ];
    const trace = join(dir, "trace.jsonl");
    const t = await runClaude(claude, args, { cwd: join(dir, "project"), input: p.prompt, timeoutMs: 300000, trace, marker: { prompt: i + 1, run: r + 1 } });
    const loaded = loadedSkills(toolCalls(readEvents(trace)));
    return { i, hit: loaded.includes(name), others: loaded.filter((n) => n !== name), cost: t.result?.total_cost_usd || 0, error: !t.result };
  });
  const init = readEvents(join(root, "1-1", "trace.jsonl")).find((e) => e.subtype === "init") || {};
  const rows = prompts.map((p, i) => {
    const mine = results.filter((x) => x.i === i);
    const loaded = mine.filter((x) => x.hit).length;
    const triggered = loaded * 2 > runs;
    return {
      prompt: p.prompt, trigger: p.trigger, group: p.group || null, loaded, runs, triggered,
      pass: triggered === p.trigger, errors: mine.filter((x) => x.error).length,
      others: [...new Set(mine.flatMap((x) => x.others))],
    };
  });
  const cost = results.reduce((n, x) => n + x.cost, 0);
  const out = {
    skill: name, description: a.description ?? null, model: init.model || a.model || null,
    claude: init.claude_code_version || null, runs, cost: +cost.toFixed(4),
    passed: rows.filter((x) => x.pass).length, of: rows.length, prompts: rows,
  };
  writeFileSync(join(root, "results.json"), JSON.stringify(out, null, 2) + "\n", "utf8");
  for (const x of rows) {
    const what = x.trigger ? "should load " : "should not  ";
    const note = [x.others.length ? `also loaded: ${x.others.join(", ")}` : "", x.errors ? `${x.errors} run(s) failed` : ""].filter(Boolean).join("; ");
    console.log(`${x.pass ? "PASS" : "FAIL"}  ${x.loaded}/${x.runs}  ${what} ${(x.group || "").padEnd(5)}  ${x.prompt.replace(/\s+/g, " ").slice(0, 70)}${note ? "  (" + note + ")" : ""}`);
  }
  const groups = [...new Set(rows.map((x) => x.group || "all"))];
  console.log(`\n${out.passed} of ${out.of} passed` + (groups.length > 1 ? " (" + groups.map((g) => {
    const gs = rows.filter((x) => (x.group || "all") === g);
    return `${g} ${gs.filter((x) => x.pass).length}/${gs.length}`;
  }).join(", ") + ")" : "") + ` · ${money(cost)} · model ${out.model || "?"} · ${join(root, "results.json")}`);
  return rows.some((x) => x.errors) ? 1 : 0;
}

// ---------------------------------------------------------------- guard (the PreToolUse hook of `run`)

const HOME_REF = /(^|[\s"'=(])~(?=[\\/\s"']|$)|\$\{?HOME\}?(?![\w])|%USERPROFILE%|%HOMEPATH%|\$env:(?:USERPROFILE|HOME)\b/i;
const NULL_DEVICES = new Set(["/dev/null", "/dev/stdout", "/dev/stderr", "nul"]);
const WRITE_TOOLS = new Set(["Write", "Edit", "MultiEdit", "NotebookEdit"]);
const SHELL_TOOLS = new Set(["Bash", "PowerShell"]);

function absolutePaths(command) {
  const found = [];
  for (const part of command.split(/&&|\|\||[;&|\n]/)) {
    const words = part.match(/"[^"]*"|'[^']*'|[^\s<>]+/g) || [];
    words.forEach((w, k) => {
      let t = w.replace(/^["']|["']$/g, "");
      if (k === 0) return; // the program itself
      t = t.replace(/^-{1,2}[\w-]+=/, "").replace(/^\d?>>?/, "");
      if (NULL_DEVICES.has(t.toLowerCase())) return;
      if (WIN && /^\/[a-zA-Z]\//.test(t)) t = `${t[1].toUpperCase()}:/${t.slice(3)}`;
      if (/^[a-zA-Z]:[\\/]/.test(t) || /^\\\\/.test(t) || (!WIN && t.startsWith("/"))) found.push(t);
    });
  }
  return found;
}

function startsSession(command) {
  if (/skill\.mjs["']?\s+(?:run|triggers)\b/.test(command)) return true;
  return command.split(/&&|\|\||[;&|\n]/).some((part) => {
    const first = (part.trim().match(/^"[^"]*"|^'[^']*'|^\S+/) || [""])[0].replace(/^["']|["']$/g, "");
    return /^(?:claude|codex)(?:\.exe|\.cmd)?$/i.test(basename(first));
  });
}

async function cmdGuard(argv) {
  const rootArg = argv[0];
  if (!rootArg) throw new UsageError("guard needs the run folder.");
  let raw = "";
  for await (const chunk of process.stdin) raw += chunk;
  let ev;
  try { ev = JSON.parse(raw); } catch { return 0; }
  const root = canonical(rootArg);
  const input = ev.tool_input || {};
  const block = (why) => {
    process.stderr.write(`${BLOCKED}: ${why} Work inside the run folder ${root}.\n`);
    return 2;
  };
  const tool = String(ev.tool_name || "");
  const target = input.file_path || input.notebook_path;
  if (WRITE_TOOLS.has(tool) && typeof target === "string" && target) {
    const abs = canonical(resolve(ev.cwd || process.cwd(), target));
    return inside(root, abs) ? 0 : block(`${abs} is outside the run folder.`);
  }
  const command = input.command;
  if (SHELL_TOOLS.has(tool) && typeof command === "string") {
    if (startsSession(command)) return block("a test run does not start more agent sessions.");
    if (HOME_REF.test(command)) return block("the command names the home folder.");
    for (const p of absolutePaths(command)) if (!inside(root, canonical(p))) return block(`${p} is outside the run folder.`);
  }
  return 0;
}

// ---------------------------------------------------------------- main

async function main(argv) {
  const [command, ...rest] = argv;
  try {
    if (!command || command === "--help" || command === "-h" || command === "help") {
      console.log(HELP.main);
      return command ? 0 : 2;
    }
    if (command === "check") return cmdCheck(rest);
    if (command === "run") return await cmdRun(rest);
    if (command === "triggers") return await cmdTriggers(rest);
    if (command === "guard") return await cmdGuard(rest);
    throw new UsageError(`Unknown command "${command}".`);
  } catch (e) {
    if (e instanceof UsageError) {
      console.error(`${e.message}\nRun \`node skill.mjs ${HELP[command] ? command + " " : ""}--help\` for usage.`);
      return 2;
    }
    console.error(e.message || String(e));
    return 1;
  }
}

process.exitCode = await main(process.argv.slice(2));
