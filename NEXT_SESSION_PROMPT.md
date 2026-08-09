# Next-session implementation prompt

Reusable template for starting a fresh Claude Code session to implement one
chunk of `PLAN.md`. Copy the block below as the session's first message,
replacing the bracketed `[...]` section with the specific `PLAN.md` item(s)
you want done in that session, following the recommended order in `PLAN.md`
§5 (e.g. minimal testing infrastructure, then `§2.3` real member search,
`§2.4` transactions). One session = one chunk = one branch = one PR
draft — see `PLAN.md` for the recommended order and `UI_PROPOSAL.md` for the
UI direction (not needed until PLAN.md §4.5 / order-of-work step 11).

---

```
Read PLAN.md and UI_PROPOSAL.md in full before doing anything else — they're the
source of truth for what's broken, what's missing, and what's already been
decided (see PLAN.md §6 "Decisions"). Treat anything marked "Decided" there as
settled; don't re-ask me about it.

Before writing any code, create a feature branch for this chunk of work (main
is protected on GitHub — no direct pushes, PR required). Do NOT commit, push,
or open a pull request yourself — I'll handle all git operations (commits,
pushes, PR) manually.

Work through ONE item at a time, then stop and report back to me before
starting the next one — don't chain multiple fixes together without checking
in. I want to review each step before you move on.

Once everything in this chunk is done and I've approved it, update PLAN.md and
CLAUDE.md so PLAN.md stays lean for the next session to read in full — do this
*before* drafting the PR, since both files land on this same branch and the PR
description should describe the branch's final contents, not just the code:
  - Delete this chunk's task description(s) from PLAN.md entirely (no
    strikethrough — the code is now the source of truth for how it works).
    Replace each with a single compact line in a short "Completed" log,
    e.g. "- [x] on_refresh indentation fixed (PR #N)" — just enough for a
    quick "did we already do X" check, not the original problem writeup.
  - If an item carried a decision that outlives the task itself (a business
    rule, a "why we chose X over Y", anything future work would need to
    know and can't infer from the code alone) — migrate that specific
    decision into CLAUDE.md, in whichever file-by-file section it belongs
    to. Don't leave decisions parked in PLAN.md once their task is done;
    PLAN.md is a shrinking todo list, CLAUDE.md is the durable
    architecture/decisions reference.
Leave PLAN.md/CLAUDE.md changes uncommitted — I'll commit and push everything
myself.

As the final step, give me a draft: a suggested PR title, and a body with a
"## Summary" (bullet points of what changed and why, including the PLAN.md/
CLAUDE.md updates alongside the code) and a "## Test plan" section, formatted
the same way this repo's existing PRs are written — so I can commit, push,
and open the PR myself. Then STOP — don't continue on to any other PLAN.md
section. I'll start a fresh session for the next chunk myself.

Ask me before making any product/business-rule call that isn't already covered
in PLAN.md §6 — but don't ask about anything already decided there.

```


Read PLAN.md in full before doing anything else — they're the
source of truth for what's broken, what's missing, and what's already been
decided (see PLAN.md §6 "Decisions"). Treat anything marked "Decided" there as
settled; don't re-ask me about it.

Before writing any code, create a feature branch for this chunk of work (main
is protected on GitHub — no direct pushes, PR required). Do NOT commit, push,
or open a pull request yourself — I'll handle all git operations (commits,
pushes, PR) manually.

Work through ONE item at a time, then stop and report back to me before
starting the next one — don't chain multiple fixes together without checking
in. I want to review each step before you move on.

Once everything in this chunk is done and I've approved it, update PLAN.md and
CLAUDE.md so PLAN.md stays lean for the next session to read in full — do this
*before* drafting the PR, since both files land on this same branch and the PR
description should describe the branch's final contents, not just the code:
  - Delete this chunk's task description(s) from PLAN.md entirely (no
    strikethrough — the code is now the source of truth for how it works).
    Replace each with a single compact line in a short "Completed" log,
    e.g. "- [x] on_refresh indentation fixed (PR #N)" — just enough for a
    quick "did we already do X" check, not the original problem writeup.
  - If an item carried a decision that outlives the task itself (a business
    rule, a "why we chose X over Y", anything future work would need to
    know and can't infer from the code alone) — migrate that specific
    decision into CLAUDE.md, in whichever file-by-file section it belongs
    to. Don't leave decisions parked in PLAN.md once their task is done;
    PLAN.md is a shrinking todo list, CLAUDE.md is the durable
    architecture/decisions reference.
Leave PLAN.md/CLAUDE.md changes uncommitted — I'll commit and push everything
myself.

As the final step, give me a draft: a suggested PR title, and a body with a
"## Summary" (bullet points of what changed and why, including the PLAN.md/
CLAUDE.md updates alongside the code) and a "## Test plan" section, formatted
the same way this repo's existing PRs are written — so I can commit, push,
and open the PR myself. Then STOP — don't continue on to any other PLAN.md
section. I'll start a fresh session for the next chunk myself.

Ask me before making any product/business-rule call that isn't already covered
in PLAN.md §6 — but don't ask about anything already decided there.