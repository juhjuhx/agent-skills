---
name: secure-cicd-gates
description: >
  Guides designing a coherent set of security gates across a CI/CD
  pipeline — combining SAST, SCA, secret-scanning, DAST, container
  scanning, and policy checks into ordered stages with clear
  block-vs-warn thresholds, instead of ad hoc, redundant, or
  contradictory individual checks. Use when the user asks to "design our
  pipeline security gates", "decide what should block a merge vs. just
  warn", "reduce pipeline security-check noise/duplication", "add a
  release gate before production deploy", or "build a DevSecOps pipeline
  from scratch".
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: devsecops
  maturity: stable
---

# Secure CI/CD Gates

## Purpose

Individually adding SAST, SCA, secret-scanning, DAST, container scanning,
and policy checks to a pipeline is necessary but not sufficient — without
a deliberate design, teams end up with checks that run at the wrong
stage (a 45-minute DAST scan blocking every PR), gates that duplicate
each other's coverage (three tools all flagging the same hardcoded
secret), inconsistent blocking thresholds (one tool blocks on medium
severity, another only on critical), and no clear escalation path when a
finding is legitimately hard to fix immediately. This skill is about the
*orchestration* layer: sequencing individual scan types into stages with
consistent severity thresholds, deciding what blocks a merge versus what
blocks a production deploy versus what's advisory, and building the
triage/exception workflow that keeps the whole pipeline trustworthy
rather than something developers route around.

## When to use

- The user is building a DevSecOps pipeline from scratch and wants a
  reference architecture for how the individual scan types fit together.
- An existing pipeline has multiple security tools bolted on ad hoc, and
  the user wants to rationalize them (remove duplication, fix
  inconsistent thresholds, reorder stages for speed).
- The user wants to decide what should be a **blocking** gate (fails the
  build/deploy) versus a **warning** (visible, tracked, non-blocking) for
  a specific finding type or severity.
- The user wants a distinct, stricter release/production-deploy gate
  layered on top of the PR-time gates.
- Developers are complaining about pipeline security checks being slow,
  noisy, or contradictory, and the user wants a redesign rather than
  another individual tool tweak.
- The user needs to explain, to an auditor or stakeholder, what security
  checks run at which stage and why.

## Prerequisites & environment

- At least one implemented control from each relevant category to
  orchestrate: static analysis
  ([sast-integration](../sast-integration/SKILL.md)), dependency
  scanning ([software-composition-analysis-sca](../software-composition-analysis-sca/SKILL.md)),
  secret detection ([secrets-management](../secrets-management/SKILL.md)),
  dynamic testing ([dast-integration](../dast-integration/SKILL.md)), and
  optionally policy/IaC checks
  ([policy-as-code-guardrails](../policy-as-code-guardrails/SKILL.md)).
  This skill assumes those individual tools are chosen/working and
  focuses on how to sequence and gate them together.
- A CI/CD system with distinguishable pipeline stages (e.g. GitHub
  Actions jobs with `needs:`, GitLab CI `stages:`, Jenkins pipeline
  stages) and the ability to mark checks as required vs. optional
  status checks on a PR.
- Agreement from engineering leadership on a severity-to-action mapping
  (e.g. "critical = block merge", "high = block release, not PR",
  "medium = ticket with SLA, non-blocking") — this is a policy decision,
  not a tooling one, and gates designed without this agreement tend to
  get silently disabled the first time they block a release.
- A single place findings land (SARIF into a code-scanning dashboard, a
  ticketing system integration, or a security dashboard) so gates from
  different tools don't each spawn their own disconnected reporting
  channel.

## Step-by-step guidance

1. **Map scan types to pipeline stages by cost and blast radius**, fastest
   and cheapest first:
   - **Pre-commit / local**: secret-scanning (Gitleaks), linters — sub-second
     feedback, catches the cheapest-to-fix issues before they're even
     committed.
   - **Pull request**: SAST (diff-aware), SCA (dependency scan), IaC
     policy checks (Conftest/OPA), secret-scanning (again, as a backstop) —
     these should complete in a few minutes and block the merge on
     high-confidence, high-severity findings in new/changed code.
   - **Merge to main / pre-release build**: container image scan (SCA
     against the built image), SBOM generation, artifact signing — runs
     once per merge, not per-commit-in-PR, since it needs a built
     artifact.
   - **Pre-production deploy / scheduled**: DAST baseline scan against a
     staging/preview environment, full-repo SAST/SCA sweep — these are
     slower and can run against a deployed environment rather than
     blocking the PR merge itself.
   - **Scheduled (nightly/weekly)**: DAST active/full scan, full
     dependency re-scan (to catch newly-disclosed CVEs against unchanged
     code), policy audit-mode review.

2. **Define one severity-to-action table** and apply it consistently
   across tools instead of letting each tool's default thresholds stand
   independently:
   ```
   | Severity        | PR merge gate     | Release gate        | SLA to fix       |
   |-----------------|--------------------|----------------------|------------------|
   | Critical        | Block              | Block                | 48 hours         |
   | High            | Block (new code)   | Block                | 2 weeks          |
   | Medium          | Warn (PR comment)  | Warn, tracked ticket | 90 days          |
   | Low/Info        | Report only        | Report only          | Best effort      |
   ```

3. **Wire required status checks** to match exactly this table — don't
   mark a tool as a "required" GitHub check if its default behavior would
   block on medium/low findings; configure the tool's own exit-code
   behavior to match the table first.
   ```yaml
   # Example: consistent exit-code gating across tools in one job
   jobs:
     security-gate:
       runs-on: ubuntu-latest
       needs: [sast, sca, secret-scan]
       steps:
         - name: Evaluate combined gate
           run: |
             python3 scripts/gate_check.py \
               --sast sast-results.sarif \
               --sca sca-results.json \
               --secrets gitleaks-report.json \
               --fail-on critical,high
   ```

4. **Separate PR gates from release gates explicitly** — a PR gate
   protects code entering `main`; a release gate protects what reaches
   production and can afford to be stricter and slower (e.g. include a
   DAST baseline scan against a preview environment that wouldn't be
   practical to run on every single commit).

5. **Give every blocking finding a suppression/exception path with an
   expiry**, consistent across tools (see the per-tool skills for
   tool-specific suppression syntax) — a gate with no legitimate escape
   hatch gets bypassed by disabling the whole check instead.

6. **Consolidate reporting** — export SARIF from SAST/DAST/IaC tools and
   JSON from SCA into one dashboard (GitHub code scanning, a SIEM, or a
   dedicated AppSec tool like DefectDojo) so a developer or reviewer
   checks one place, not four.

7. **Review the gate design itself periodically** (quarterly is
   reasonable) — check false-positive rate, time-to-fix against the SLA
   table, and whether any check has become a rubber stamp because it
   never actually blocks anything.

## Best practices

- Order gates by speed and confidence: fast, high-confidence checks
  (secret-scanning, diff-aware SAST) block PRs; slow or lower-confidence
  checks (full DAST, full-repo SAST sweep) run on a schedule or at
  release time and feed a dashboard instead of blocking every commit.
- Use one severity-to-action table across all tools rather than trusting
  each tool's own default thresholds — inconsistency here is the single
  biggest source of "why did this block but that similar thing didn't"
  developer confusion.
- Distinguish the PR gate from the release gate deliberately — release
  gates can and should be stricter (e.g. block on high, not just
  critical) since they're the last checkpoint before production impact.
- Never let a security gate become "advisory in practice" by having no
  teeth — if a required check has been failing and getting overridden by
  admins for months, either fix the underlying noise or formally
  downgrade it to non-blocking; a check nobody respects is worse than no
  check, because it creates false confidence.
- Instrument the gates themselves: track mean time-to-remediate by
  severity, false-positive rate per tool, and how often exceptions are
  granted — this data is what justifies (or corrects) the design over
  time.
- Keep the whole gate configuration in version control alongside the
  pipeline definition, reviewed like any other pipeline change — gates
  are production-security-relevant code.

## Common pitfalls

- **Symptom:** Every PR takes 40+ minutes because SAST, full SCA, and a
  DAST scan against a spun-up preview environment all run synchronously
  on every commit.
  **Fix:** Split into fast/blocking PR-time checks (diff-aware SAST,
  dependency scan, secret scan — should complete in a few minutes) and
  slow checks (DAST, full-repo sweeps) that run on a schedule or at
  release time instead of every commit.

- **Symptom:** Three different tools (a SAST rule, a dedicated
  secret-scanner, and the SCA tool's license scanner) all separately flag
  the same hardcoded value, and developers see triplicate noise for one
  real issue.
  **Fix:** Assign each finding category to exactly one primary tool
  (e.g. secret-scanning owns secret detection; disable overlapping
  secret-detection rulesets in the SAST tool) and consolidate into one
  report instead of running fully overlapping checks blind to each
  other.

- **Symptom:** A critical finding blocks a release, engineering leadership
  overrides the gate to ship on a deadline, and there's no record of the
  override or follow-up commitment.
  **Fix:** Build an explicit, auditable override mechanism (a
  documented emergency-bypass process requiring named sign-off and an
  auto-created follow-up ticket with a deadline) rather than an informal
  "an admin disabled the check" workaround that leaves no trail.

- **Symptom:** A required status check has been red for months because
  the underlying tool is too noisy, and PRs merge via admin override so
  routinely that the check is effectively decorative.
  **Fix:** This is a signal to fix the noise (better rules, diff-aware
  scanning, tuned suppressions) or formally reclassify the check as
  non-blocking — a permanently-overridden "required" check trains the
  team to ignore red X's generally, including on checks that matter.

- **Symptom:** Security wants to add a new blocking gate; engineering
  pushes back that it will break every in-flight PR on rollout day.
  **Fix:** Roll out new gates in warn-only/report mode first (mirroring
  the audit-mode pattern from
  [policy-as-code-guardrails](../policy-as-code-guardrails/SKILL.md)),
  review the hit rate for a representative period, then flip to blocking
  once the false-positive rate is acceptable.

## Worked example

A team designs a four-stage gate structure for a containerized service.

Stage table (documented in the repo, e.g. `docs/security-gates.md`):
```
| Stage                | Checks                                  | Blocking on          |
|----------------------|------------------------------------------|-----------------------|
| Pre-commit           | Gitleaks (secrets)                       | Any match             |
| Pull request         | Semgrep SAST (diff), Trivy SCA (fs),     | Critical/High (new)  |
|                       | Conftest IaC policy                      |                       |
| Merge to main         | Trivy image scan, Syft SBOM, cosign sign | Critical/High         |
| Release (pre-prod)    | ZAP baseline DAST vs. preview env        | High-risk/High-conf   |
| Nightly               | ZAP full scan, full-repo SAST/SCA sweep  | Report only (ticketed)|
```

`.github/workflows/pr-gates.yml`:
```yaml
name: pr-security-gates
on: [pull_request]

jobs:
  sast:
    runs-on: ubuntu-latest
    container: { image: semgrep/semgrep:1.78.0 }
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - run: semgrep ci --config p/owasp-top-ten --baseline-commit "${{ github.event.pull_request.base.sha }}"

  sca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@0.24.0
        with: { scan-type: 'fs', severity: 'CRITICAL,HIGH', exit-code: '1', ignore-unfixed: true }

  iac-policy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: terraform plan -out=plan.tfplan && terraform show -json plan.tfplan > plan.json
      - run: conftest test plan.json --policy policies/

  gate-summary:
    needs: [sast, sca, iac-policy]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Fail if any required gate failed
        run: |
          if [[ "${{ contains(needs.*.result, 'failure') }}" == "true" ]]; then
            echo "One or more blocking security gates failed."
            exit 1
          fi
   ```
`gate-summary` becomes the single required PR status check, so branch
protection references one job instead of three independently-configured
checks that could drift out of sync.

## Cross-references

- [sast-integration](../sast-integration/SKILL.md) — the PR-time static
  analysis stage this pipeline design incorporates.
- [software-composition-analysis-sca](../software-composition-analysis-sca/SKILL.md) —
  the dependency-scanning stage, run both at PR time (filesystem) and
  merge time (built image).
- [dast-integration](../dast-integration/SKILL.md) — the
  release/nightly-stage dynamic testing this design defers out of the
  PR-blocking path.
- [secrets-management](../secrets-management/SKILL.md) — the
  pre-commit/PR-time secret-scanning stage.
- [policy-as-code-guardrails](../policy-as-code-guardrails/SKILL.md) —
  the IaC/admission policy checks incorporated as a pipeline stage here.
