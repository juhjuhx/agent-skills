---
name: gitea-actions-and-ci
description: >
  Configures Gitea Actions — Gitea's GitHub Actions-compatible CI/CD
  runner — including self-hosted act_runner setup/registration and the
  specific differences from GitHub Actions (supported contexts, missing
  features, runner labels). Use when the user asks to "set up CI on
  Gitea," "configure Gitea Actions," "register an act_runner," "port a
  GitHub Actions workflow to Gitea," or "troubleshoot a Gitea Actions job
  that isn't picked up by any runner."
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: cicd-tooling
  maturity: stable
---

# Gitea Actions and CI

## Purpose

Gitea Actions gives a self-hosted Gitea (or Forgejo) instance a CI system
that intentionally mirrors GitHub Actions' workflow YAML syntax
(`.gitea/workflows/*.yml`, `on:`/`jobs:`/`steps:`), executed by a
self-hosted **act_runner** rather than GitHub's managed runners. This
matters operationally because most GitHub Actions YAML is *reusable with
caveats*, but the caveats — a smaller set of built-in contexts, no
GitHub-hosted runner equivalent, different marketplace-action
compatibility, and a distinct runner registration/labeling model — cause
real friction when a team assumes full parity. This skill covers Gitea
Actions setup and specifically where it diverges from
[github-actions-single-repo-workflows](../github-actions-single-repo-workflows/SKILL.md),
which this skill assumes as the baseline syntax reference.

## When to use

- A team self-hosts Gitea (or Forgejo, a Gitea fork) and wants to enable
  built-in CI instead of bolting on an external Jenkins/Drone instance.
- Porting an existing GitHub Actions workflow to run on Gitea and hitting
  unsupported syntax, contexts, or marketplace actions.
- Setting up and registering a self-hosted `act_runner` against a Gitea
  instance, or debugging why a workflow job never picks up a runner.
- Deciding which third-party GitHub Actions marketplace actions are safe/
  compatible to reuse on Gitea Actions versus needing a local
  reimplementation.
- Auditing self-hosted runner security posture, since every Gitea Actions
  runner is self-hosted by definition (no managed-runner option).

## Prerequisites & environment

- A Gitea instance (1.19+ for Actions support; check **Site Administration
  → Actions** to confirm Actions is enabled instance-wide, since it's
  opt-in and off by default in older versions) or a Forgejo instance
  (Forgejo Actions is the same underlying design, forked from Gitea's).
- At least one **act_runner** binary or container registered against the
  instance — Gitea does not provide managed/hosted runners; every runner
  is infrastructure the team stands up and maintains itself.
- Docker (or another supported executor) on the runner host if workflows
  use container-based steps/actions, since act_runner's default executor
  model relies on Docker to run job containers, similar to
  `act`(the local GitHub Actions runner it's derived from).
- Repo or org admin access to enable Actions per-repository (**Repository
  Settings → Actions**) and to view/manage registered runners
  (**Site Administration → Actions → Runners**, or org/repo-level runner
  registration for scoped runners).
- Familiarity with GitHub Actions workflow YAML — see
  [github-actions-single-repo-workflows](../github-actions-single-repo-workflows/SKILL.md)
  for the baseline syntax this skill assumes.

## Step-by-step guidance

1. **Enable Actions at the instance level first**, then per-repo — Gitea
   Actions is disabled by default at both levels historically; confirm
   **Site Administration → Actions → Actions** is enabled before debugging
   a repo that "has no CI" for any other reason.

2. **Register at least one act_runner.** Download/run the `act_runner`
   binary or container, generate a registration token from the instance
   (**Site Administration → Actions → Runners → Create new Runner**, or
   `gitea actions generate-runner-token` on the server), and register:
   ```bash
   act_runner register \
     --instance https://gitea.example.com \
     --token ${GITEA_RUNNER_TOKEN} \
     --name ci-runner-1 \
     --labels ubuntu-latest:docker://node:20-bullseye,linux_amd64
   act_runner daemon
   ```
   The `--labels` mapping is important: unlike GitHub-hosted runners,
   act_runner's labels are locally defined and must explicitly map a
   label like `ubuntu-latest` to a container image — there is no implicit
   GitHub-managed `ubuntu-latest` image behind the scenes.

3. **Write the workflow under `.gitea/workflows/`, not
   `.github/workflows/`** — this is the single most common porting
   mistake:
   ```yaml
   # .gitea/workflows/ci.yml
   name: ci
   on:
     pull_request:
       branches: [main]
     push:
       branches: [main]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v4
           with: { node-version: "20" }
         - run: npm ci
         - run: npm test
   ```

4. **Verify marketplace action compatibility before relying on one.**
   Gitea Actions supports actions written for GitHub Actions in principle
   (it runs the same `action.yml` format), but actions calling GitHub-
   specific REST APIs (e.g. posting a check run via the GitHub API,
   using `actions/github-script` against `github.com` endpoints) won't
   work unmodified against a Gitea instance — prefer generic shell-based
   actions or Gitea-specific forks (many popular actions have a
   `https://gitea.com/...` mirror maintained for this reason) for
   anything that talks to the forge's API directly.

5. **Use `docker://` prefixed images for portability** where an action
   needs a specific toolchain, since act_runner's default execution model
   is container-based and this keeps behavior consistent across runner
   hosts:
   ```yaml
   jobs:
     build:
       runs-on: docker
       container:
         image: golang:1.22-bookworm
       steps:
         - uses: actions/checkout@v4
         - run: go build ./...
   ```

6. **Scope runners deliberately** (instance-wide, org-level, or
   repo-level registration) matching your trust boundary — a repo-scoped
   runner only picks up jobs from that one repo, which limits blast radius
   if a workflow in one repo were to run malicious code, versus an
   instance-wide runner available to every repo on the instance.

7. **Treat every runner host as sensitive infrastructure**, since (unlike
   GitHub-hosted runners, which are ephemeral and managed by GitHub) a
   self-hosted act_runner persists state and credentials on infrastructure
   your team fully controls and must patch/harden itself — apply the same
   self-hosted-runner security posture called out generically in
   [ci-cd-pipeline-design](../../../devops/skills/ci-cd-pipeline-design/SKILL.md).

8. **Check job/runner matching when a job never starts.** A job with
   `runs-on: ubuntu-latest` stays queued forever if no registered runner
   advertises that exact label — confirm via **Site Administration →
   Actions → Runners** (or org/repo scoped runner list) which labels are
   actually registered.

## Best practices

- Keep `.gitea/workflows/*.yml` syntax close to plain GitHub Actions YAML
  (avoid Gitea-only extensions unless necessary) if there's any chance of
  needing to run the same repo on GitHub too — this maximizes portability
  in both directions.
- Explicitly document each registered runner's labels-to-image mapping
  (e.g. in a README in the runner's provisioning repo/IaC) since, unlike
  GitHub's implicit `ubuntu-latest`/`macos-latest` meaning, Gitea's labels
  are whatever the team defined at registration time and can silently
  diverge between runner hosts if not centrally managed.
- Prefer Gitea-maintained or generic shell-based mirrors of common
  actions (checkout, setup-node, setup-go, docker build/push) over
  GitHub-API-dependent marketplace actions, and test any ported action
  against Gitea before assuming parity.
- Register runners per-scope (repo/org/instance) matching trust
  boundaries rather than defaulting every runner to instance-wide access.
- Since there's no managed-runner tier, budget for the operational load
  of patching runner hosts (OS updates, Docker version, act_runner binary
  updates) yourself — this is real infrastructure ownership, not a
  toggle.
- Pin action versions the same way as GitHub Actions
  (`actions/checkout@v4`, not `@main`) — see
  [github-actions-single-repo-workflows](../github-actions-single-repo-workflows/SKILL.md)
  for why this matters, and it applies identically here.

## Common pitfalls

- **Symptom:** A workflow file exists in the repo but no CI ever runs, no
  error shown anywhere obvious.
  **Fix:** Check the file is under `.gitea/workflows/`, not
  `.github/workflows/` (a straight copy from a GitHub-based repo commonly
  leaves it in the wrong path), and confirm Actions is enabled both
  instance-wide (**Site Administration → Actions**) and for the specific
  repository (**Repository Settings → Actions**).

- **Symptom:** A job stays queued/pending indefinitely and never starts.
  **Fix:** No registered act_runner advertises the label in `runs-on:`
  (e.g. `ubuntu-latest`) — check **Site Administration → Actions →
  Runners** for the actual registered labels, and either register a
  runner with that label or change `runs-on:` to match an existing one.

- **Symptom:** A marketplace action that works fine on GitHub Actions
  fails on Gitea with an API error or silently no-ops (e.g. an action
  that's supposed to post a PR comment via the GitHub API does nothing).
  **Fix:** The action is calling GitHub's REST API directly rather than
  using a forge-agnostic mechanism; look for a Gitea-compatible fork/
  mirror of the action, or replace it with a plain shell step using
  Gitea's own API (`https://gitea.example.com/api/v1/...`) with a
  suitably scoped token.

- **Symptom:** Two different repos' workflows produce different build
  results even though the workflow YAML is identical.
  **Fix:** Runner labels map to specific container images defined at
  registration time on each act_runner host — if two runner hosts were
  registered with the same label (e.g. `ubuntu-latest`) pointing at
  different underlying images/tags, jobs land on inconsistent
  environments; centralize and document the label-to-image mapping so all
  runners advertising a given label are actually equivalent.

- **Symptom:** A self-hosted act_runner host is compromised (unpatched OS,
  exposed Docker socket) and used to exfiltrate secrets from every repo
  it services.
  **Fix:** This is the real risk of self-hosted-only runners with no
  managed-runner alternative — treat runner hosts as sensitive
  infrastructure requiring the same patching cadence and network
  isolation as production systems, scope runners per-repo/org rather than
  instance-wide where workflows handle sensitive secrets, and never leave
  the Docker socket reachable from job containers unless the workflow
  genuinely and trustedly needs Docker-in-Docker.

## Worked example

**Scenario:** A team self-hosts Gitea for an internal Go service repo and
wants CI on every PR (lint, test, build) using a repo-scoped act_runner,
after previously running the same workflow logic on GitHub Actions.

Runner registration (run once on the dedicated CI host):
```bash
act_runner register \
  --instance https://gitea.internal.example.com \
  --token ${GITEA_RUNNER_TOKEN} \
  --name go-service-runner \
  --labels ubuntu-latest:docker://golang:1.22-bookworm,linux_amd64
act_runner daemon
```

`.gitea/workflows/ci.yml` (ported from an equivalent
`.github/workflows/ci.yml`, changing only the path and dropping one
GitHub-API-dependent step):
```yaml
name: ci
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: go vet ./...
      - run: go test ./... -coverprofile=coverage.out
      - run: go build -o bin/service ./cmd/service
      - name: Upload coverage artifact
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage.out
```
The team drops a previously-used `github-script` step that posted a PR
comment via the GitHub REST API (not compatible against a Gitea instance)
and replaces it, where still needed, with a plain `curl` call against
Gitea's own `/api/v1/repos/{owner}/{repo}/issues/{index}/comments`
endpoint using a scoped Gitea access token instead.

## Cross-references

- [github-actions-single-repo-workflows](../github-actions-single-repo-workflows/SKILL.md) — the baseline workflow YAML syntax this skill assumes and diverges from.
- [github-actions-centralized-reusable-workflows](../github-actions-centralized-reusable-workflows/SKILL.md) — note `workflow_call` reusable-workflow support varies by Gitea version; verify current support before relying on it for cross-repo centralization on Gitea.
- [ci-cd-pipeline-design](../../../devops/skills/ci-cd-pipeline-design/SKILL.md) — vendor-neutral stage/gate/self-hosted-runner security guidance underlying this setup.
