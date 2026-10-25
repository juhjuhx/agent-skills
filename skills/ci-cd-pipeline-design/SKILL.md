---
name: ci-cd-pipeline-design
description: >
  Designs and troubleshoots CI/CD pipelines (GitHub Actions, GitLab CI, or
  equivalent) including stage layout, caching, parallelization, quality
  gates, and secrets handling. Use when the user asks to "set up a CI/CD
  pipeline," "add a build/test/deploy workflow," "fix a failing pipeline
  stage," "speed up CI," "add branch protection / required checks," or
  "design a deployment pipeline" for an application or infrastructure repo.
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: devops
  maturity: stable
---

# CI/CD Pipeline Design

## Purpose

A CI/CD pipeline is the mechanism that turns a code change into a verified,
deployable artifact and, eventually, a running system — reliably, repeatably,
and fast enough that engineers trust it over manual steps. Badly designed
pipelines either fail to catch real regressions (weak gates, flaky tests
suppressed rather than fixed) or become so slow and brittle that engineers
route around them (manual deploys, skipped checks). This skill covers
designing pipeline stages, gates, caching, and parallelization so that CI/CD
is both trustworthy and fast enough to stay in the critical path of every
change.

## When to use

- Standing up CI/CD for a new service or monorepo from scratch.
- A pipeline is slow (multi-tens-of-minutes) and engineers are asking to
  skip it or it's blocking delivery cadence.
- Adding quality gates: required checks, branch protection, test coverage
  thresholds, or manual approval gates before production deploy.
- Migrating a pipeline between platforms (e.g., Jenkins to GitHub Actions,
  or GitHub Actions to GitLab CI).
- Diagnosing flaky or intermittently failing pipeline stages.
- Adding matrix builds, caching, or parallel test sharding to reduce
  pipeline wall-clock time.

## Prerequisites & environment

- A version-controlled repository (Git) with a CI platform already
  available or to be provisioned: GitHub Actions, GitLab CI, Jenkins,
  CircleCI, etc. Examples below use GitHub Actions and GitLab CI syntax.
- Repository or project admin permission to configure branch protection,
  required status checks, and CI/CD variables/secrets.
- For GitHub Actions: Actions enabled on the repo; runner availability
  (GitHub-hosted or self-hosted) understood, since self-hosted runners
  need their own patching/security posture.
- For GitLab CI: a configured runner (shared or project-specific) and
  `.gitlab-ci.yml` support; GitLab 15+ recommended for modern
  `rules:`/`workflow:` syntax (older `only:`/`except:` still works but is
  deprecated in favor of `rules:`).
- Secrets already stored in the platform's secret store (GitHub Actions
  secrets/environments, GitLab CI/CD variables marked "masked" and
  "protected") — never in the pipeline file itself.

## Step-by-step guidance

1. **Define the stage model before writing YAML.** A typical pipeline has:
   `lint/static-analysis` → `build` → `unit test` → `package/containerize`
   → `integration test` → `publish artifact` → `deploy (per environment)`.
   Keep fast, cheap checks (lint, unit tests) first so failures surface in
   seconds/minutes, not after a 20-minute build.

2. **Trigger scoping.** Run the full pipeline on pushes to the default
   branch and on pull requests; run only relevant subsets on other
   branches. For monorepos, use path filters so a docs-only change doesn't
   trigger a full backend build.

   GitHub Actions:
   ```yaml
   name: ci
   on:
     pull_request:
       branches: [main]
     push:
       branches: [main]
   concurrency:
     group: ci-${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   jobs:
     lint:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v4
           with:
             node-version: "20"
             cache: "npm"
         - run: npm ci
         - run: npm run lint

     test:
       needs: lint
       runs-on: ubuntu-latest
       strategy:
         matrix:
           shard: [1, 2, 3, 4]
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v4
           with:
             node-version: "20"
             cache: "npm"
         - run: npm ci
         - run: npm test -- --shard=${{ matrix.shard }}/4

     build:
       needs: test
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - run: docker build -t myapp:${{ github.sha }} .
   ```

   GitLab CI equivalent (`.gitlab-ci.yml`):
   ```yaml
   stages: [lint, test, build]

   workflow:
     rules:
       - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
       - if: '$CI_COMMIT_BRANCH == "main"'

   lint:
     stage: lint
     script:
       - npm ci
       - npm run lint

   test:
     stage: test
     parallel: 4
     script:
       - npm ci
       - npm test -- --shard=$CI_NODE_INDEX/$CI_NODE_TOTAL

   build:
     stage: build
     needs: ["test"]
     script:
       - docker build -t myapp:$CI_COMMIT_SHORT_SHA .
   ```

3. **Cache dependencies, not build output you can't trust.** Cache package
   manager directories (`~/.npm`, `~/.m2`, `~/.cache/pip`) keyed by a lock
   file hash. Avoid caching compiled artifacts across unrelated commits —
   stale caches cause "works in CI, fails locally" (or the reverse) bugs.

4. **Add required quality gates as required status checks**, not just as
   jobs that "happen to run." In GitHub: Settings → Branches → branch
   protection rule → "Require status checks to pass" and select the exact
   job names. A job that runs but isn't marked required can fail silently
   and still allow merge.

5. **Add a manual approval gate before production deploy** using GitHub
   Actions `environment:` protection rules or GitLab's `when: manual` with
   `environment:`, rather than trusting a human to remember to "deploy
   only after checking."

   ```yaml
   deploy-prod:
     needs: build
     runs-on: ubuntu-latest
     environment:
       name: production
       url: https://app.example.com
     steps:
       - run: ./deploy.sh prod ${{ github.sha }}
   ```
   Configure `production` as a protected GitHub environment requiring
   reviewer approval under Settings → Environments.

6. **Fail fast and make failures actionable.** Surface test reports, not
   just exit codes (JUnit XML upload, annotations on the PR diff). A red
   pipeline with no indication of *what* failed drives engineers to rerun
   blindly instead of fixing the root cause.

7. **Measure and budget pipeline duration.** Track p50/p95 pipeline
   duration over time; if it creeps past your team's tolerance (commonly
   cited target: keep PR feedback under ~10-15 minutes), invest in test
   sharding, dependency caching, or splitting slow integration suites into
   a separate, less-blocking pipeline.

## Best practices

- Pin action/image versions (e.g., `actions/checkout@v4`, not `@main`) to
  avoid supply-chain surprises from upstream changes; update deliberately
  via Dependabot/Renovate rather than floating on `latest`.
- Keep pipeline definitions in the same repo as the code they build
  ("pipeline as code"), reviewed via the same PR process as application
  code.
- Separate CI (build/test/verify) concerns from CD (deploy) concerns into
  distinct workflows/stages so a deploy can be re-triggered without
  rerunning the entire test suite.
- Use `concurrency`/pipeline cancellation so superseded runs on the same
  branch don't waste runner minutes.
- Treat flaky tests as a defect to fix, not something to retry away
  indefinitely — a `retry: 2` band-aid that runs forever hides real
  instability.
- Emit structured build metadata (commit SHA, build number, timestamp)
  into the artifact/image so any deployed instance is traceable back to
  its pipeline run — this underpins
  [release-versioning-and-changelog-automation](../release-versioning-and-changelog-automation/SKILL.md).
- Keep secrets out of logs: mask output, avoid `set -x` around commands
  that interpolate secret env vars, and use the platform's masked/secret
  variable feature rather than plain CI variables.

## Common pitfalls

- **Symptom:** Pipeline is green but a bug reaches production anyway.
  **Fix:** Audit whether the job that "should have" caught it is actually
  a *required* status check, not just a job that runs — non-required jobs
  can fail without blocking merge.

- **Symptom:** CI takes 40+ minutes and engineers start merging with
  `--no-verify` or bypassing checks.
  **Fix:** Profile the pipeline (per-step timing), parallelize the test
  suite via sharding, cache dependencies keyed on lockfile hash, and move
  slow end-to-end suites to a separate, non-blocking nightly pipeline.

- **Symptom:** Same test fails ~5% of the time with no code change
  ("flaky test"), and the team adds automatic retries to make it pass.
  **Fix:** Quarantine the flaky test (mark it non-blocking, file a ticket),
  fix the root cause (shared state, timing assumption, unseeded
  randomness), then re-enable it as blocking — indefinite silent retries
  erode trust in the whole pipeline signal.

- **Symptom:** A secret leaks in build logs (e.g., printed via `env` or an
  `-x` shell trace).
  **Fix:** Store secrets only in the platform's secret store, reference
  them as `${{ secrets.NAME }}` / `${SECRET_NAME}` masked CI/CD variables,
  and audit logs for accidental `echo`/`env`/`printenv` dumps of the
  environment.

- **Symptom:** Self-hosted runner has stale tooling and pipeline behavior
  differs from GitHub-hosted runners used elsewhere.
  **Fix:** Pin the runner image/tooling versions explicitly in the
  workflow (language runtime, Docker version) rather than relying on
  whatever happens to be installed on the runner host.

## Worked example

**Scenario:** A Node.js service repo needs CI on every PR (lint, unit test,
build, container image) and CD to a `staging` environment automatically on
merge to `main`, with a manual gate to `production`.

`.github/workflows/ci-cd.yml`:
```yaml
name: ci-cd
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "npm" }
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --coverage
      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with: { name: coverage, path: coverage/ }

  build-image:
    needs: verify
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions: { contents: read, packages: write }
    steps:
      - uses: actions/checkout@v4
      - run: |
          docker build -t ghcr.io/${{ github.repository }}:${{ github.sha }} .
          echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker push ghcr.io/${{ github.repository }}:${{ github.sha }}

  deploy-staging:
    needs: build-image
    runs-on: ubuntu-latest
    environment: { name: staging }
    steps:
      - run: ./deploy.sh staging ${{ github.sha }}

  deploy-prod:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: { name: production }   # protected: requires reviewer approval
    steps:
      - run: ./deploy.sh prod ${{ github.sha }}
```
With branch protection on `main` requiring the `verify` job's checks
(`lint`, `test`) and the `production` environment configured with a
required reviewer, a bad change cannot reach production without a passing
pipeline and a human sign-off — while staging still deploys automatically
for fast feedback.

## Cross-references

- [environment-promotion-strategy](../environment-promotion-strategy/SKILL.md)
- [release-versioning-and-changelog-automation](../release-versioning-and-changelog-automation/SKILL.md)
- [gitops-workflow](../gitops-workflow/SKILL.md)
