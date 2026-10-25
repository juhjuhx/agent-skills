---
name: code-quality
description: "Code review, cleanup, and quality checks: parallel review, pre-commit gates, codebase inspection. Use when: code review, simplify, cleanup, refactor, code quality, pre-commit."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Code-Review, Cleanup, Refactor, Quality, Pre-Commit, Inspection]
    related_skills: [systematic-debugging, test-driven-development, github-workflow]
---

# Code Quality

Code review, cleanup, and quality inspection tools.

## Section 1: Simplify Code (Parallel Review)

Review recent code changes with three focused reviewers running in parallel, aggregate findings, and apply fixes.

### When to Use

Trigger when user says: "simplify", "review my code", "clean up my changes", "/simplify"

### The Process

**Phase 1 — Identify changes:**
```bash
git diff                    # Default: uncommitted changes
git diff HEAD               # Include staged
git diff main...HEAD        # This branch / PR
```

**Phase 2 — Launch three reviewers in parallel:**

Use `delegate_task` batch mode with three goals:

1. **Code Reuse** — Find duplicate functionality, existing utilities
2. **Code Quality** — Redundant state, parameter sprawl, copy-paste
3. **Efficiency** — Unnecessary work, missed concurrency, hot-path bloat

Give EVERY reviewer the COMPLETE diff plus repo path.

**Phase 3 — Aggregate and apply:**
1. Merge findings, dedup overlaps
2. Discard false positives
3. Resolve conflicts: correctness > user's focus > readability > micro-perf
4. Apply surviving fixes with `patch`
5. Verify: run targeted tests + linter

### Pitfalls

- Don't fan out wider than ~3 reviewers
- Give the WHOLE diff to each reviewer
- Apply ≠ rewrite — keep edits scoped to what the diff touched
- Respect project conventions (AGENTS.md, linter config)

## Section 2: Requesting Code Review (Subagent Dispatch)

Dispatch a code reviewer subagent to catch issues before they cascade. The reviewer gets precisely crafted context — never your session history.

### When to Request

**Mandatory:** After each task in subagent-driven development, after completing major features, before merge to main.
**Optional but valuable:** When stuck (fresh perspective), before refactoring (baseline check), after fixing complex bugs.

### How to Request

1. **Get git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

2. **Dispatch code reviewer subagent** with: description of changes, plan/requirements, base SHA, head SHA.

3. **Act on feedback:**
- Fix Critical issues immediately
- Fix Important issues before proceeding
- Note Minor issues for later
- Push back if reviewer is wrong (with technical reasoning)

### Red Flags
- Never skip review because "it's simple"
- Never ignore Critical issues
- Never proceed with unfixed Important issues

## Section 3: GitHub PR Review Pipeline

For formal PR reviews on GitHub, use this multi-agent pipeline:

1. **Pre-check** (haiku): Verify PR is open, not draft, not already reviewed by you
2. **Context gather** (haiku): Find relevant CLAUDE.md files for changed paths
3. **Summary** (sonnet): View PR and summarize changes
4. **Parallel review** (4 agents):
   - Agents 1+2: CLAUDE.md compliance (sonnet) — audit for rule violations
   - Agent 3: Bug scan (opus) — focus on diff only, flag significant bugs
   - Agent 4: Logic review (opus) — security, incorrect logic in changed code
5. **Validation** (parallel subagents): Each issue from step 4 gets independently validated
6. **Filter**: Only HIGH SIGNAL issues survive (syntax errors, definite logic errors, clear CLAUDE.md violations)
7. **Output**: Summary of findings; if `--comment` flag, post inline comments via `gh pr comment`

**False positive filter** — do NOT flag: pre-existing issues, pedantic nitpicks, linter-catchable issues, general quality concerns unless CLAUDE.md-required, issues silenced in code.

## Section 4: Specialized Review Agents

For comprehensive reviews, dispatch these focused agents:
- **code-reviewer**: General code quality and best practices
- **silent-failure-hunter**: Error handling gaps, swallowed errors, missing validation
- **code-simplifier**: Over-engineering and simplification opportunities
- **comment-analyzer**: Check if review comments were properly addressed
- **pr-test-analyzer**: Test coverage and quality evaluation
- **type-design-analyzer**: Type system design and API boundary review

## Section 5: Pre-commit Checklist

```bash
# Security scan
rg -n 'password|secret|api_key|token.*=|private_key' --type py
rg -n 'breakpoint\(\)|set_trace\(' --type py

# Quality checks
ruff check . --fix
mypy . --ignore-missing-imports
pytest tests/ -q

# Git checks
git diff --staged --stat
git diff --staged | grep -n "print(\|console\.log\|TODO\|FIXME"
```

### Review Output Format

```
## Code Review Summary

### Critical
- **src/auth.py:45** — SQL injection risk

### Warnings
- **src/models.py:23** — Password stored in plaintext

### Suggestions
- **src/utils.py:8** — Duplicates logic in core/utils.py

### Looks Good
- Clean separation of concerns
```

## Section 6: Codebase Inspection

Inspect codebases with pygount: LOC, languages, ratios.

```bash
pygount --format=summary .
pygount --format=summary --dirs=src,tests .
```

### Key Metrics

- Total lines of code
- Language breakdown
- Code-to-test ratio
- Comment density

---

## Section 7: Security Audit with Abuse Probes

Systematic security testing of API endpoints using local/staging servers. Produces a vulnerability matrix with evidence.

### When to Use

Trigger when: security audit, penetration test, abuse probe, vulnerability scan, pre-release security review.

### The Process

**Phase 1 — Read-only code audit** (never edit during audit):
1. Read AGENTS.md / COORDINATION.md / ARCHITECTURE.md for context
2. Identify auth middleware patterns (authMiddleware vs optionalAuth)
3. Map endpoints to their auth requirements
4. Check for mass assignment (spread of `req.body` without field whitelist)
5. Check CSP headers, JWT config, WebSocket auth method

**Phase 2 — Abuse probes** (local server only, never production destructive):
Write a self-contained Python probe script:
```python
import urllib.request, json

def api(method, path, data=None, token=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, method=method,
        headers={"Content-Type": "application/json"} if body else {})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except:
            return e.code, {"error": str(e)}
```

Key probes to run:
| Probe | What to test |
|-------|-------------|
| Mass assignment | PUT profile with `level=expert`, `role=["admin"]` |
| Email/PII exposure | GET search endpoints, check if email/phone returned |
| Draft access | GET content/courses/:id without auth, check if drafts readable |
| Auth bypass | Access protected endpoints without token |
| Invalid input | Send out-of-range values (-1, 0, 999, "abc") for numeric fields |
| Public endpoint auth | Check if truly-public endpoints work without auth |

**Why `urllib` not `curl`**: Hermes secret redaction redacts tokens in curl Authorization headers. Python `urllib` handles auth programmatically without exposing tokens in command output.

**Phase 3 — Output matrix**:
```
ID   Probe                                      HTTP  Confirmed?  Evidence
────────────────────────────────────────────────────────────────────────────
P1   PUT /profile level=expert                   200   ✅ YES      level saved to DB
P2   GET /search email exposure                  200   ✅ YES      email in response
```

### Pitfalls

- **Never run destructive probes against production** — use local DB / test server only
- **Use Python urllib, not curl** — avoids secret redaction blocking Authorization headers
- **Write probes as standalone script** — save to /tmp/, run with `terminal()`, inspect output
- **Check for rate limiting** — add `sleep` between probe batches if hitting 429
- **Verify findings** — one probe confirms the vulnerability exists; check the code to understand WHY
- **Report format**: Impact scope, reproduction steps, suggested fix file, acceptance test

## Common Pitfalls

1. **Three narrow reviewers beat one broad reviewer** — each deep-searches for one class
2. **Don't apply fixes that break tests** — revert and report
3. **Large diffs blow context** — scope down before delegating
4. **Respect project conventions** — fold AGENTS.md rules into reviewer prompts
5. **Apply ≠ rewrite** — cleanup of recent changes, not license to refactor everything

## References

- `references/safe-external-url-pattern.md` — Shared safeExternalUrl helper for XSS prevention in href attributes

## Verification Checklist

- [ ] Full diff captured before review
- [ ] All three reviewers completed
- [ ] False positives discarded
- [ ] Conflicts resolved (correctness > all)
- [ ] Tests pass after changes
- [ ] Linter passes
- [ ] Summary reported to user
