---
description: Work through one PLAN.md chunk end-to-end - branch, one item at a time, docs update, PR draft
argument-hint: [which PLAN.md item(s) or section to work on this chunk]
---

Work through a chunk of PLAN.md, one item at a time, with a check-in after each before continuing.

Arguments: `$ARGUMENTS` — which PLAN.md item(s)/section to work on. If empty, ask which item(s) before starting rather than guessing.

Steps:
1. Read PLAN.md in full before doing anything else — it's the source of truth for what's broken, what's missing, and what's already been decided (see its "Decisions" section). Treat anything marked "Decided" there as settled; don't re-ask about it. Ask only about product/business-rule calls that aren't already covered there.
2. Before writing any code, create a feature branch for this chunk (use `/branch`) — `main` is protected on GitHub, no direct pushes. Do NOT commit or push — the user commits and pushes everything themselves.
3. Work through the item(s) in `$ARGUMENTS` ONE at a time. After each one, stop and report back before starting the next — don't chain multiple fixes together without checking in.
4. Once everything in this chunk is done and approved, update PLAN.md and CLAUDE.md so PLAN.md stays lean for the next session to read in full — do this *before* drafting the PR, since both files land on this same branch and the PR description should describe the branch's final contents:
   - Delete this chunk's task description(s) from PLAN.md entirely (no strikethrough — the code is now the source of truth for how it works). Replace each with a single compact line in a short "Completed" log, e.g. `- [x] on_refresh indentation fixed (PR #N)` — just enough for a quick "did we already do X" check, not the original problem writeup.
   - If an item carried a decision that outlives the task itself (a business rule, a "why we chose X over Y", anything future work would need and can't infer from the code alone) — migrate that decision into the right doc: CLAUDE.md's "Key invariants & durable decisions" if it's a cross-cutting rule likely to matter on most tasks, or ARCHITECTURE.md's matching per-file section if it's file/module-specific detail. Don't leave decisions parked in PLAN.md once their task is done — PLAN.md is a shrinking todo list; CLAUDE.md/ARCHITECTURE.md are the durable reference.
   - Leave the doc updates uncommitted — the user commits and pushes everything themselves.
5. As the final step, give a draft: a suggested PR title, and a body with a "## Summary" (bullet points of what changed and why, including the doc updates alongside the code) and a "## Test plan" section with concrete, numbered manual-test steps (not just a checkbox), formatted the same way this repo's existing PRs are written, so the user can commit, push, and open the PR themselves. Then STOP — don't continue to any other PLAN.md section.
