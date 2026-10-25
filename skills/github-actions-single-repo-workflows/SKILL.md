---
name: github-actions-single-repo-workflows
description: >
  Authors and troubleshoots GitHub Actions workflow YAML that lives in and
  serves a single repository — triggers, jobs/steps, matrix builds, caching
  with actions/cache, and composite actions defined within the same repo
  under .github/actions/. Use when the user asks to "write a GitHub Actions
  workflow," "add a matrix build," "fix a failing GitHub Actions job," "add
  a composite action to this repo," or "speed up this repo's GitHub Actions
  CI" for one repository's own pipeline.
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: cicd-tooling
  maturity: stable
---

# GitHub Actions Single-Repo Workflows

## Purpose

Most repos' CI needs are served by workflow YAML that lives entirely
within that repo under `.github/workflows/`, defining its own triggers,
jobs, and steps. This skill covers the concrete GitHub Actions mechanics
for that single-repo case — trigger syntax (`on:`), job/step structure,
matrix builds, `actions/cache`, and composite actions defined locally in
`.github/actions/` for within-repo reuse — as distinct from the
organization-wide reusable-workflow pattern covered in
[github-actions-centralized-reusable-workflows](../github-actions-centralized-reusable-workflows/SKILL.md).
Generic pipeline-design concepts (stage ordering, quality gates, caching
philosophy) are covered vendor-neutrally in
[ci-cd-pipeline-design](../../../devops/skills/ci-cd-pipeline-design/SKILL.md);
this skill focuses on GitHub Actions' actual YAML syntax and runner
behavior.

## When to use

- A repository needs its first CI workflow, or an existing
  `.github/workflows/*.yml` file is failing and needs debugging.
- Adding a matrix build (multiple OS/language versions) or parallel test
  sharding within one workflow.
- Speeding up a slow workflow via `actions/cache`, `concurrency`
  cancellation, or splitting a monolithic job into parallel jobs with
  `needs:`.
- Extracting duplicated step sequences within one repo's workflows into a
  local composite action under `.github/actions/`.
- Deciding whether logic duplicated across *multiple repos* (not just
  within one) should become an org-level reusable workflow instead — see
  [github-actions-centralized-reusable-workflows](../github-actions-centralized-reusable-workflows/SKILL.md).

## Prerequisites & environment

- GitHub Actions enabled on the repository (Settings → Actions → General).
- Runner availability: GitHub-hosted runners (`ubuntu-latest`,
  `windows-latest`, `macos-latest`) require no setup; self-hosted runners
  need registration and their own OS/tooling patching (Settings → Actions
  → Runners).
- Repo write/admin access to add workflow files and configure branch
  protection required-status-checks.
- Secrets already stored in **Settings → Secrets and variables → Actions**
  (repository or environment-scoped) — never hardcoded in the workflow
  YAML.
- Familiarity with YAML expression syntax (`${{ }}`) and GitHub's built-in
  contexts (`github.*`, `secrets.*`, `matrix.*`, `needs.*`).

## Step-by-step guidance

1. **Scope triggers precisely.** Use `paths:`/`paths-ignore:` in a
   monorepo so unrelated changes don't trigger a full pipeline, and add
   `concurrency` so superseded runs on the same ref are cancelled:
   ```yaml
   name: ci
   on:
     pull_request:
       branches: [main]
       paths: ["src/**", "package*.json"]
     push:
       branches: [main]
   concurrency:
     group: ci-${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```

2. **Use `strategy.matrix` for cross-version/cross-OS testing**, and
   `fail-fast: false` when you want every matrix leg's result even if one
   fails early:
   ```yaml
   jobs:
     test:
       runs-on: ${{ matrix.os }}
       strategy:
         fail-fast: false
         matrix:
           os: [ubuntu-latest, macos-latest]
           node: ["18", "20", "22"]
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v4
           with: { node-version: ${{ matrix.node }}, cache: "npm" }
         - run: npm ci
         - run: npm test
   ```

3. **Cache dependencies keyed on the lockfile hash**, with a restore-key
   fallback for partial cache hits:
   ```yaml
   - uses: actions/cache@v4
     with:
       path: ~/.cache/pip
       key: pip-${{ runner.os }}-${{ hashFiles('requirements.txt') }}
       restore-keys: |
         pip-${{ runner.os }}-
   ```
   Prefer the language-specific setup action's built-in `cache:` input
   (`actions/setup-node@v4` with `cache: "npm"`,
   `actions/setup-python@v5` with `cache: "pip"`) over hand-rolled
   `actions/cache` where available — it's pre-wired to the right paths and
   keys.

4. **Shard slow test suites across matrix legs** rather than running the
   full suite serially in one job:
   ```yaml
   strategy:
     matrix:
       shard: [1, 2, 3, 4]
   steps:
     - run: npm test -- --shard=${{ matrix.shard }}/4
   ```

5. **Extract repeated step sequences into a local composite action**
   under `.github/actions/<name>/action.yml` when the same steps recur
   across jobs *within this repo* — this is the single-repo analog of a
   shared library, scoped to one repo:
   ```yaml
   # .github/actions/setup-toolchain/action.yml
   name: "Setup toolchain"
   description: "Checks out code and installs Node + cached deps"
   runs:
     using: "composite"
     steps:
       - uses: actions/checkout@v4
       - uses: actions/setup-node@v4
         with: { node-version: "20", cache: "npm" }
       - run: npm ci
         shell: bash
   ```
   Consumed within the same repo's workflow as:
   ```yaml
   steps:
     - uses: ./.github/actions/setup-toolchain
     - run: npm test
   ```

6. **Gate deploy jobs with `environment:` protection rules** rather than
   a manual convention, and separate the deploy job from the test/build
   job via `needs:` so a deploy can be re-run without re-running tests:
   ```yaml
   deploy-staging:
     needs: build
     runs-on: ubuntu-latest
     environment: { name: staging }
     steps:
       - run: ./deploy.sh staging ${{ github.sha }}
   ```

7. **Pin every third-party action to a full commit SHA or, at minimum, a
   major version tag** (`actions/checkout@v4`, not `@main` or an unpinned
   floating tag) — see the pitfalls below for why this matters more than
   it looks.

8. **Surface structured results**, not just exit codes: upload JUnit/
   coverage artifacts and use `actions/upload-artifact@v4` so a failure is
   diagnosable from the PR without re-running locally.

## Best practices

- Pin actions by SHA (`actions/checkout@8459de2...`) or major-version tag,
  and update deliberately via Dependabot/Renovate rather than tracking
  `@main` — an upstream action change can silently alter your pipeline's
  behavior otherwise.
- Use `permissions:` at the workflow or job level to scope the
  `GITHUB_TOKEN` down from its (sometimes broad) default — e.g.
  `permissions: { contents: read }` for a job that only builds/tests and
  never needs to push or open issues.
- Keep one workflow file's job graph readable: prefer several small
  workflow files over one enormous file with dozens of jobs sharing
  unclear `needs:` chains.
- Use `if: always()` deliberately and sparingly on cleanup/notification
  steps — it's easy to accidentally suppress a should-have-failed job by
  overusing `continue-on-error` alongside it.
- When step logic is copy-pasted three or more times *within this repo*,
  extract a local composite action (`.github/actions/`); when it's
  copy-pasted *across repos*, that's the trigger to build an org-level
  reusable workflow instead — see
  [github-actions-centralized-reusable-workflows](../github-actions-centralized-reusable-workflows/SKILL.md).
- Treat `pull_request_target` with extreme caution — it runs with access
  to secrets and the base repo's permissions even for a fork's PR; never
  check out and execute a fork's untrusted code under `pull_request_target`
  without explicit, reviewed guardrails.

## Common pitfalls

- **Symptom:** A required check named `test` passes even though one
  matrix leg actually failed.
  **Fix:** With `fail-fast: false`, GitHub still reports the overall job
  as failed if any matrix leg fails — but if branch protection points at
  an *individual matrix leg's* generated check name instead of the job as
  a whole, adding/removing a matrix entry silently changes which check
  names exist; point required checks at a summary/gate job instead
  (mirroring the `gate-summary` pattern in
  [secure-cicd-gates](../../../devsecops/skills/secure-cicd-gates/SKILL.md)).

- **Symptom:** A workflow that ran safely for months suddenly executes
  unexpected code or exfiltrates a secret after a third-party action
  update.
  **Fix:** This is the risk of tracking `@main`/`@latest` on a third-party
  action; pin to a full commit SHA (most defensible) or at least a
  specific version tag, and review action source before pinning to a new
  major version.

- **Symptom:** `actions/cache` restores a stale `node_modules` and tests
  pass in CI but the same code fails when run fresh locally (or vice
  versa).
  **Fix:** Key the cache on the lockfile hash
  (`hashFiles('package-lock.json')`), not a static string or branch name,
  so a dependency change invalidates the cache instead of silently reusing
  stale content.

- **Symptom:** `pull_request_target` workflow checks out and runs a
  fork's PR branch code, and a malicious PR exfiltrates repo secrets.
  **Fix:** Never combine `pull_request_target` with checking out and
  executing the PR head's untrusted code; if you need secrets available
  to a fork PR's workflow, keep the trusted workflow on `pull_request_target`
  narrow (e.g. only to post a comment) and run the untrusted build under
  plain `pull_request` (no secrets) instead.

- **Symptom:** Two pushes to the same branch in quick succession both run
  the full pipeline, wasting runner minutes and creating confusing
  out-of-order status updates.
  **Fix:** Add `concurrency: { group: ci-${{ github.ref }}, cancel-in-progress:
  true }` so a newer push cancels the superseded in-flight run.

## Worked example

**Scenario:** A single Python service repo needs CI across three Python
versions with sharded tests, dependency caching, and a composite action
that both the CI and a separate nightly workflow reuse for environment
setup.

`.github/actions/setup-python-env/action.yml`:
```yaml
name: "Setup Python env"
description: "Checkout + Python + cached pip deps"
inputs:
  python-version:
    required: true
runs:
  using: "composite"
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: ${{ inputs.python-version }}
        cache: "pip"
    - run: pip install -r requirements.txt -r requirements-dev.txt
      shell: bash
```

`.github/workflows/ci.yml`:
```yaml
name: ci
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
        shard: [1, 2]
    steps:
      - uses: ./.github/actions/setup-python-env
        with: { python-version: ${{ matrix.python-version }} }
      - run: pytest --shard-id=${{ matrix.shard }} --num-shards=2 --junitxml=reports/junit.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: junit-${{ matrix.python-version }}-${{ matrix.shard }}
          path: reports/junit.xml

  gate:
    needs: test
    if: always()
    runs-on: ubuntu-latest
    steps:
      - run: |
          if [[ "${{ contains(needs.*.result, 'failure') }}" == "true" ]]; then
            echo "test matrix had a failure"; exit 1
          fi
```
Branch protection requires only the `gate` job, so adding/removing matrix
entries in `test` never requires updating the required-checks list.

## Cross-references

- [github-actions-centralized-reusable-workflows](../github-actions-centralized-reusable-workflows/SKILL.md) — promote this pattern to `workflow_call` once it's duplicated across multiple repos.
- [ci-cd-pipeline-design](../../../devops/skills/ci-cd-pipeline-design/SKILL.md) — vendor-neutral stage layout and gating concepts this workflow implements.
- [secure-cicd-gates](../../../devsecops/skills/secure-cicd-gates/SKILL.md) — designing the `gate` job's blocking rules and adding security scan steps.
