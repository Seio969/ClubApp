---
description: Create and switch to a new branch following this repo's naming convention
argument-hint: <type> <short-description>
---

Create a new git branch and switch to it.

Arguments: `$ARGUMENTS` — expected as `<type> <short-description>`, e.g. `fix quick-bugs-plan-section-2` or `feat transaction-dialog`.

Steps:
1. Run `git status` to confirm there's nothing uncommitted that would be inconvenient to carry onto the new branch. If there are uncommitted changes, tell the user what they are and ask whether to proceed (they'll come along onto the new branch), stash them, or abort — don't decide silently.
2. Determine the base branch: use the current branch unless the user's request implies branching from `main` (e.g. they say "from main" or the current branch is unrelated to the new work) — if ambiguous, ask.
3. Build the branch name as `<type>/<short-description>` in kebab-case, matching existing branches in this repo (`fix/quick-bugs-plan-section-1`, `docs/plan-and-ui-proposal`). Common types: `fix`, `feat`, `docs`, `refactor`, `chore`.
4. Run `git checkout -b <type>/<short-description>` (from the chosen base, pulling/fetching first only if the user asked to branch from an up-to-date `main`).
5. Confirm the new branch name and that it's checked out.

Do not push the new branch or create a PR as part of this command — that's a separate step (`/push`).
