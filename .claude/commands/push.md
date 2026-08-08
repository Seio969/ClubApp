---
description: Push the current branch to origin, setting upstream if needed
argument-hint: [optional PR title/notes]
---

Push the current branch to `origin`.

Arguments: `$ARGUMENTS` — optional. If non-empty, after pushing also open a PR against `main` using `gh pr create`, using the argument text as guidance for the title/body; otherwise just push, no PR.

Steps:
1. Run `git status` and `git branch --show-current` to confirm the branch and that there's nothing uncommitted left behind (uncommitted changes won't be pushed — flag them, don't silently ignore).
2. Refuse to push directly to `main`/`master` without explicit confirmation from the user.
3. Push: `git push -u origin <branch>` if the branch has no upstream yet, otherwise plain `git push`. Never force-push (`--force`/`-f`) unless the user explicitly asked for it in this same request, and never force-push to `main`.
4. If `$ARGUMENTS` was provided (PR requested): gather context via `git log main..HEAD` and `git diff main...HEAD`, then run `gh pr create --title "..." --body "$(cat <<'EOF' ... EOF)"` per the repo's usual PR body shape (Summary + Test plan). Return the PR URL.
5. If no PR was requested, just confirm the push succeeded and report the branch/remote state.
