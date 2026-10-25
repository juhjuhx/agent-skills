---
name: github-workflow
description: "Complete GitHub workflow: auth, PRs, issues, code review, repo management. Use when: GitHub, git, PR, pull request, issue, code review, repository, clone, fork, release, CI/CD."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Git, Pull-Requests, Issues, Code-Review, Repositories, CI/CD, Authentication, gh-cli]
    related_skills: [hermes-agent, cross-agent-memory]
---

# GitHub Workflow

Complete guide for working with GitHub — authentication, pull requests, issues, code review, and repository management. Every section shows `gh` CLI first, then `git` + `curl` fallback for machines without `gh`.

## Prerequisites

- Git installed
- GitHub account
- Optional: `gh` CLI (`brew install gh` or `apt install gh`)

## Auth Detection (use at the start of any GitHub workflow)

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi
```

Extract owner/repo from git remote:
```bash
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

---

## Section 1: Authentication

### HTTPS with Personal Access Token (Recommended)

1. Create token at https://github.com/settings/tokens (scopes: `repo`, `workflow`, `read:org`)
2. Configure git: `git config --global credential.helper store`
3. Test: `git ls-remote https://github.com/<user>/<repo>.git`

### SSH Key Authentication

```bash
ssh-keygen -t ed25519 -C "email@example.com" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub  # Add to https://github.com/settings/keys
ssh -T git@github.com
```

### gh CLI Authentication

```bash
gh auth login  # Interactive browser login
# Or headless: echo "$TOKEN" | gh auth login --with-token
gh auth setup-git
gh auth status
```

### API Access Without gh

```bash
export GITHUB_TOKEN="<token>"
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

**Full details:** See `scripts/gh-env.sh` for the complete auth detection script.

---

## Section 2: Pull Request Workflow

### Branch Creation

```bash
git fetch origin
git checkout main && git pull origin main
git checkout -b feat/description
```

Branch naming: `feat/`, `fix/`, `refactor/`, `docs/`, `ci/`

### Making Commits

```bash
git add src/file.py
git commit -m "feat: add feature

Detailed description. Wrap at 72 characters."
```

Format: `type(scope): description` — Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`

### Creating a PR

**With gh:**
```bash
gh pr create --title "feat: add feature" --body "## Summary\n..." --draft --reviewer user1
```

**With curl:**
```bash
BRANCH=$(git branch --show-current)
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{\"title\":\"feat: add feature\",\"body\":\"...\",\"head\":\"$BRANCH\",\"base\":\"main\"}"
```

### Monitoring CI

**With gh:** `gh pr checks` / `gh pr checks --watch`

**With curl:**
```bash
SHA=$(git rev-parse HEAD)
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status
```

### Auto-Fixing CI Failures

```bash
gh run list --branch $(git branch --show-current) --limit 5
gh run view <RUN_ID> --log-failed
# Fix code, then:
git add . && git commit -m "fix: resolve CI failure" && git push
```

### Merging

```bash
gh pr merge --squash --delete-branch
# Or auto-merge when checks pass:
gh pr merge --auto --squash --delete-branch
```

**Full details:** See `references/ci-troubleshooting.md` and `references/conventional-commits.md` for CI debugging and commit conventions. See `templates/pr-body-bugfix.md` and `templates/pr-body-feature.md` for PR body templates.

---

## Section 3: Code Review

### Reviewing Local Changes (Pre-Push)

```bash
git diff main...HEAD --stat          # Scope
git diff main...HEAD                 # Full diff
git diff main...HEAD | grep -n "print(\|console\.log\|TODO\|FIXME"  # Find issues
```

### Reviewing a PR

**With gh:**
```bash
gh pr view 123
gh pr diff 123
gh pr checkout 123
```

**With curl:**
```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/123/files
```

### Posting Review Comments

**Inline comment with gh:**
```bash
gh api repos/$OWNER/$REPO/pulls/123/comments \
  --method POST -f body="Suggestion" -f path="src/file.py" -f commit_id="$SHA" -f line=45 -f side="RIGHT"
```

**Formal review:**
```bash
gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --request-changes --body "See inline comments."
```

### Review Checklist

- **Correctness:** Edge cases, error handling
- **Security:** No hardcoded secrets, input validation, SQL injection, XSS
- **Quality:** Clear naming, DRY, single responsibility
- **Testing:** New code paths tested, happy + error cases
- **Performance:** No N+1 queries, appropriate caching
- **Documentation:** Public APIs documented, non-obvious logic explained

**Full details:** See `references/review-output-template.md` for the structured review output format.

---

## Section 4: Issues Management

### Viewing Issues

```bash
gh issue list --state open --label "bug"
gh issue view 42
```

### Creating Issues

```bash
gh issue create \
  --title "Login redirect ignores ?next= parameter" \
  --body "## Description\n..." \
  --label "bug,backend" \
  --assignee "username"
```

### Managing Issues

```bash
gh issue edit 42 --add-label "priority:high"
gh issue edit 42 --add-assignee @me
gh issue comment 42 --body "Investigated — root cause found"
gh issue close 42 --reason "completed"
```

### Issue Triage Workflow

1. List untriaged: `gh issue list --label "needs-triage"`
2. Read and categorize each issue
3. Apply labels and priority
4. Assign if owner is clear
5. Comment with triage notes if needed

**Full details:** See `templates/bug-report.md` and `templates/feature-request.md` for issue templates.

---

## Section 5: Repository Management

### Cloning

```bash
git clone https://github.com/owner/repo.git
git clone --depth 1 https://github.com/owner/repo.git  # Shallow
gh repo clone owner/repo
```

### Creating Repos

```bash
gh repo create my-project --public --clone
gh repo create my-org/my-project --private --description "A tool" --license MIT
```

### Forking

```bash
gh repo fork owner/repo --clone
git remote add upstream https://github.com/owner/repo.git
git fetch upstream && git merge upstream/main
```

### Repository Settings

```bash
gh repo edit --description "Updated" --visibility public
gh repo edit --enable-auto-merge
```

### Releases

```bash
gh release create v1.0.0 --title "v1.0.0" --generate-notes
gh release list
gh release download v1.0.0 --dir ./downloads
```

### GitHub Actions

```bash
gh workflow list
gh run list --limit 10
gh run view <RUN_ID> --log-failed
gh run rerun <RUN_ID> --failed
gh workflow run ci.yml --ref main
```

### Secrets Management

```bash
gh secret set API_KEY --body "value"
gh secret list
gh secret delete API_KEY
```

**Full details:** See `references/github-api-cheatsheet.md` for the complete API reference.

---

## Quick Reference Table

| Action | gh | git + curl |
|--------|-----|-----------|
| Clone | `gh repo clone o/r` | `git clone https://github.com/o/r.git` |
| Create PR | `gh pr create ...` | `curl POST /repos/o/r/pulls` |
| Review PR | `gh pr review N --approve` | `curl POST /repos/o/r/pulls/N/reviews` |
| List issues | `gh issue list` | `curl GET /repos/o/r/issues` |
| Create issue | `gh issue create ...` | `curl POST /repos/o/r/issues` |
| Create release | `gh release create v1.0` | `curl POST /repos/o/r/releases` |
| Set secret | `gh secret set KEY` | `curl PUT /repos/o/r/actions/secrets/KEY` |

---

## Common Pitfalls

1. **GitHub disabled password auth** — Use personal access token or SSH key
2. **Token lacks scopes** — Regenerate with `repo`, `workflow`, `read:org`
3. **Multiple GitHub accounts** — Use SSH with different keys per host alias
4. **CI fails silently** — Check `gh pr checks --watch` for real-time status
5. **Merge conflicts** — Always pull latest main before creating PR
6. **Stale credentials** — Run `git credential reject` then re-authenticate

## Verification Checklist

- [ ] Auth working: `gh auth status` or `git ls-remote` succeeds
- [ ] Git identity set: `git config user.name` and `user.email`
- [ ] PR creates successfully: `gh pr create --draft`
- [ ] CI checks visible: `gh pr checks`
- [ ] Issues accessible: `gh issue list`
