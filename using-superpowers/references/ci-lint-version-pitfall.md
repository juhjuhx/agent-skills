# CI Lint/Format Version Pitfall

When fixing lint or format issues in a project, ALWAYS check the CI's pinned tool versions before running tools locally.

## The Trap

Running `ruff format` locally with a newer version (e.g. 0.15.x) produces different output than the CI's pinned version (e.g. 0.6.x). This causes:
- "Would reformat" errors in CI even after local formatting
- Repeated commit-fix-commit cycles that never resolve
- Wasted time debugging "why does my format not stick"

## The Fix

Before running any linter/formatter:

```bash
# 1. Check CI pinned versions
cat tests/requirements.txt | grep ruff    # or package.json, pyproject.toml, etc.
cat .github/workflows/ci.yml | grep -A 5 "ruff"

# 2. Install the EXACT pinned version
pip install ruff==0.6.9   # use whatever CI specifies

# 3. THEN run the check/format
ruff check src/ tests/
ruff format --check src/ tests/
```

## Why This Happens

- Ruff (and many tools) change formatting rules between major versions
- `pip install ruff` gives you the latest (0.15.x), but CI pins to 0.6.9
- Formatting differences are invisible locally — the tool says "formatted" but CI disagrees

## General Rule

Any time you run a tool that CI also runs, match the CI version first. This applies to:
- Linters (ruff, eslint, prettier)
- Formatters (black, isort, rustfmt)
- Test runners (pytest version differences)
- Type checkers (mypy version differences)
