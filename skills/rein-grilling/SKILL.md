---
name: rein-grilling
description: "Interviews the user about a plan, idea or decision until every choice in it is settled by them, and ends with the list of decisions before anything is built. Use when the user types /rein-grilling to stress-test a plan, a design, a feature idea or a business call, even when the idea is still vague. Not for analyzing a requirement document against code (rein-analyzing-requirements) or writing a skill (rein-writing-skills)."
disable-model-invocation: true
license: MIT
metadata:
  author: rockychang7
  version: "0.1.0"
---

# Grilling

The interview is there to get the user's own decisions out of a loose idea, not the agent's opinion of it.

Reply in Chinese by default, in plain words someone outside the field could follow. When the user asks for another
language, use that one, the template labels below included.

## Done when

- Every question that came up was decided by the user, or the user said to leave it open.
- The decision list in [Output](#output) was shown, and the user confirmed it matches what they meant.
- Nothing was built, written or changed before that confirmation, except the list itself when they ask to save it.

## Steps

1. **Look up the facts first.** Whatever the code, the files, the tools or the web can answer, find out yourself;
   ask the user only for decisions. A lookup that takes a while holds back only the questions that depend on it.
2. **Ask a round**, in the format below: at most 5 questions, none of which depends on the answer to another in the
   same round; the rest wait for a later round.
3. **Ask the next round** from the answers. An answer can open new questions or change old ones; when it changes a
   question already settled, ask that one again.
4. **Stop asking** when nothing is left to decide, or when the user says to stop ("先这样", "enough"). Show the
   decision list and wait for their confirmation.
5. **Save the list only when asked**, as a Markdown file in the project's `docs/process/`.

### The round

```
**Q1 · <标题>**：<问题；有选项时写成 A / B / C>

➡️ 推荐：<你的答案>，因为<一句理由>。按推荐来吗？

---

**Q2 · ...**
```

Word every question so it ends in "按推荐来吗？": the user answers each by number with 同意, 不同意, or
"改成……". A question worded the other way round makes "yes" reject the recommendation.

## When to stop and ask

- Every decision belongs to the user, even one whose answer looks obvious. Put it in a round and wait.
- A question about how something looks or feels cannot be settled by talking. Say so, suggest making a rough
  version to look at first, and leave it open until they have.
- When the first round shows the subject is too big for one session (more than a handful of rounds ahead), stop
  and suggest splitting it into parts to grill one at a time.

## Pitfalls

| Situation | What to do |
| --- | --- |
| A decision seems obvious, so the agent answers it itself and moves on | Ask it. An interview the user did not answer only records the agent's opinion |
| The questions run out and the agent starts building | Show the decision list and wait. Running out of questions is not the user's go-ahead |
| Asking the user something a file or a command could answer | Look it up, and use what you found in the recommendation |
| The user answers "I don't know" | Mark it open with what would settle it. Do not pick for them |

## Output

The decision list:

```
## 已定

1. <决定>：<选了什么>，因为<用户给的理由，有就写>

## 还没定

1. <问题>：<卡在哪>，<怎样才能定下来>
```

Leave out "还没定" when nothing is open. Then ask whether it matches what they meant.
