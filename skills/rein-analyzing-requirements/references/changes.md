# When the requirement changes

The analysis follows one stored version of the document (`meta.source_v`).
Every `src` names a section of that version, and the pages show its text. A
newer document changes nothing until you take it in, and you take it in only
after the user agreed to what it does to the analysis.

## The document changed

The product owner sends a new version: a file, a link, or pasted text.

1. **Get the whole new version as one Markdown file**, as for a new
   requirement. A version you could only read in part: stop and ask for an
   export. Comparing half a document reports the other half as removed.
2. **Store it and list the changes.**
   `req.py refresh --req <name> --doc <file>`. It lists every section added,
   removed, changed (`was` and `now` lines) or moved (renumbered) since the
   version the analysis follows, and per section what cites it: `cited_by`
   (where, with a line of text), `items` (the features, flows, questions,
   release items they belong to) and `apis` (the APIs of those features).
   Run it without `--doc` to list the same changes again, for example in a
   new session.
   - `stored` is false and nothing changed: the document is the same; say so.
   - Only `head` changed (title, version line): set `meta.doc_version`,
     raise `meta.source_v`, `check`, `render`. No need to ask.
3. **Find code already written.** For each item and API, check the working
   branch for code that implements it (routes, services, tables). Only read.
   Code that the change makes wrong is part of the impact.
4. **Tell the user and wait** (`refresh.impact`). In plain words, one line
   per change, grouped by section:
   - what changed in the document: before → after;
   - what it affects, by name, not only by ID: features, flow steps,
     questions, APIs, and code files to redo;
   - what you would do: rewrite a rule, drop a feature, add a question, …;
   - added sections nothing cites yet: what they bring.

   For example:

   ```text
   原文第 2 版改了 5 处：
   - §2.3 导出报名名单：删了 → B03 导出功能、B3 导出接口不做了（标删除）
   - §3.4 取消报名：截止以后也能取消了 → C04 的规则要改；Q01 正好被原文答了
   - §3.6 候补报名：新增 → 要加功能、流程分支和接口；补位要不要游客确认没说，提成问题
   已经写了的代码：ActivitySignupController.cancel() 的截止判断要改
   ```

   Wait for a go-ahead. The product owner may have changed the document by
   mistake, or the team may push back on part of it.
5. **Update the analysis**, after the go-ahead:
   - A rule, step or question citing a changed section: make it match the new
     text.
   - A removed section: items that only it supports get `removed` with the
     reason ("§2.3 removed in document version 2"); never delete them. Items
     that also cite other sections lose only that citation.
   - A moved section: change its number in every `src` that cites it. Miss
     one and that `src` points at another section without any error.
   - An added section: write it in like a new requirement (features, rules,
     flows, APIs, questions), or list it in `skipped_sections` with why.
   - What the new text leaves unclear or contradicts: a new question. Never
     decide it yourself.
   - A question the new text answers: record the answer with `by` the
     document and `note` naming the section, then apply it like any answer.
   - The version line changed: `meta.doc_version`.
   - One `changes` entry per change, at the top: `src` the section, `refs`
     every ID you touched.
   - `meta.source_v`: the new version (`doc_v` in the refresh result).
6. **Check and render**, then tell the user what changed in the analysis and
   which pages were regenerated.

Rendering before the analysis takes the new version in is allowed (to record
an answer, say): pages stay on the version the analysis follows, and
`status` keeps reporting the newer document until `meta.source_v` is raised.
