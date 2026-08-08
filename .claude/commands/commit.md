---
description: Stage and commit changes following this repo's commit message convention
argument-hint: [optional message override]
---

Create a git commit for the current changes, following this repo's established style.

Arguments: `$ARGUMENTS` — optional. If provided, use it as guidance for (or the literal) commit message. If empty, derive the message entirely from the diff.

Steps:
1. Run in parallel: `git status`, `git diff` (unstaged) and `git diff --cached` (staged), and `git log -5 --format='%B---'` to refresh the message style (subject line `type: summary` under ~70 chars, body explaining *why* not *what*, wrapped prose).
2. Stage relevant files by name (never `git add -A`/`git add .`). Skip anything that looks like a secret, credential, or build artifact — flag it to the user instead of staging it.
3. After staging, run `git status` again to confirm exactly what's staged before committing.
4. Draft a commit message matching this repo's real convention (see recent log): a `type: short summary` subject (`fix`, `feat`, `docs`, `refactor`, `chore`), then a body paragraph explaining the motivation/why, then a blank line, then:
   ```
   Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
   ```
5. Commit via heredoc (`git commit -m "$(cat <<'EOF' ... EOF)"`), never `--no-verify`/`--no-gpg-sign` unless explicitly asked.
6. If a pre-commit hook fails, fix the underlying issue, re-stage, and make a **new** commit — never `--amend` to paper over a failed hook.
7. Run `git status` once more to confirm the commit succeeded and report the resulting commit summary to the user.

Do not push as part of this command — that's `/push`. Only commit when there are real changes; don't create an empty commit.
