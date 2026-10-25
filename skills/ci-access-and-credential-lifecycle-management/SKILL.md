---
name: ci-access-and-credential-lifecycle-management
description: >
  Manages the lifecycle of one-off/temporary repo and environment access
  grants and CI service-account credentials — granting time-boxed access
  for a specific task, revoking it reliably when the task ends, and
  rotating CI service-account tokens/keys before they expire or become
  stale. Use when the user asks to "give a contractor temporary repo
  access," "grant one-off access to the production environment," "rotate
  our CI service account token/API key," "find and revoke stale CI
  credentials," or "our CI token is about to expire, what do we do."
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: devops
  maturity: stable
---

# CI Access and Credential Lifecycle Management

## Purpose

CI/CD systems accumulate access grants and long-lived credentials faster
than they shed them: a contractor gets repo write access for a two-week
project and still has it a year later, a CI service account is issued a
token with no expiry "to avoid breaking the pipeline," and nobody owns
noticing when either becomes a stale, unused liability. This skill covers
the operational discipline of treating access and credentials as having a
lifecycle — granted for a reason, time-boxed, and reliably revoked or
rotated — rather than as a one-way ratchet that only ever adds permissions
and never removes them.

## When to use

- Granting a contractor, vendor, or short-term collaborator access to a
  specific repo, environment, or deployment target for a defined period.
- A CI service-account token, deploy key, or API credential is approaching
  its expiry (or has none set) and needs rotation before it breaks a
  pipeline or becomes a long-standing risk.
- Auditing who/what currently has access to production repos/environments
  and finding grants that should have been revoked already (an offboarded
  contractor, a decommissioned integration, a one-off access grant that
  was never time-boxed).
- Setting up a recurring process so credential rotation and access review
  happen on a schedule instead of only reactively after an incident or
  audit finding.
- Deciding between a long-lived static credential and a short-lived/
  federated one for a new CI integration.

## Prerequisites & environment

- An identity provider or access-management layer capable of time-boxed
  grants (temporary group membership, an expiring repo collaborator
  invite, a just-in-time access tool) rather than only permanent
  add/remove.
- A secrets manager or CI platform's native secret store (GitHub Actions
  environment secrets, GitLab CI/CD variables scoped per environment,
  HashiCorp Vault) capable of versioned secrets so a rotation doesn't
  require simultaneously updating every consumer at the exact same
  instant — see
  [secrets-management](../../../devsecops/skills/secrets-management/SKILL.md)
  for the broader secrets-handling discipline this builds on.
- Where the CI/CD platform and cloud provider support it, OIDC-based
  federation for CI-to-cloud authentication instead of a long-lived
  static access key — see
  [cloud-iam-hardening](../../../cloud/skills/cloud-iam-hardening/SKILL.md)
  for eliminating long-lived cloud credentials generally.
- A calendar/ticketing mechanism to track grant expiry and rotation due
  dates — an access grant or token with no tracked expiry date is
  functionally permanent regardless of what was intended when it was
  created.

## Step-by-step guidance

1. **Default every one-off access grant to a defined end date, not
   indefinite access "until someone remembers to remove it."** Prefer a
   platform mechanism that expires automatically over a manual reminder:
   ```bash
   # GitHub: repository collaborator invite (manually tracked expiry —
   # GitHub itself has no native invite TTL, so pair with a ticket/calendar
   # reminder or an org-level SAML/SCIM group with a time-boxed membership)
   gh api repos/<org>/<repo>/collaborators/<contractor-username> \
     -f permission=push
   # Track removal due date in the access-request ticket, not just memory.
   ```
   ```bash
   # AWS IAM Identity Center: time-boxed permission set assignment via a
   # just-in-time access tool, or a scheduled removal via automation
   # rather than a standing assignment with no review date.
   ```
   If the platform truly has no native expiry, the access-request ticket
   itself must carry the revoke-by date and an owner responsible for
   closing it out — an untracked "temporary" grant is not actually
   temporary.

2. **Scope every grant to the narrowest resource and permission that
   completes the task**, not "give them admin so we don't have to ask
   again." A contractor fixing one repo's CI config needs write access to
   that repo, not org-owner; a one-off production debugging session needs
   read-only access to specific logs/metrics, not a standing production
   credential.

3. **Revoke reliably at the end date — verify, don't assume.** Build
   revocation into the same ticket/workflow that granted access, and
   periodically audit for grants past their stated end date:
   ```bash
   # Example audit: list repo collaborators and cross-reference against
   # active-contractor list / ticket due dates, flagging anything stale.
   gh api repos/<org>/<repo>/collaborators --jq '.[].login'
   ```
   Treat "the contract ended three months ago and access was never
   revoked" as a finding to fix immediately, not a minor housekeeping
   item.

4. **Rotate CI service-account tokens on a schedule, before expiry —
   not reactively after a pipeline starts failing with 401s.** Track each
   credential's expiry date and set a rotation reminder well before it
   (e.g., 30 days out for a 90-day token), and prefer credentials that
   support **overlap during rotation** (both old and new valid briefly)
   over a hard cutover that risks an outage if any consumer wasn't
   updated:
   ```bash
   # Example: rotate a GitHub App private key used by CI, keeping the
   # old key valid until the new one is confirmed working everywhere
   # that consumes it, then explicitly revoking the old key.
   gh api /app/installations/<id>/access_tokens   # verify new key works
   # ...only after confirming all consumers use the new key:
   # revoke the old private key in the GitHub App settings.
   ```

5. **Prefer short-lived, federated credentials over long-lived static
   ones for new CI-to-cloud integrations**, so there is no long-lived
   secret to rotate at all:
   ```yaml
   # GitHub Actions -> AWS via OIDC, no long-lived AWS access key stored
   # as a secret
   permissions:
     id-token: write
     contents: read
   steps:
     - uses: aws-actions/configure-aws-credentials@v4
       with:
         role-to-assume: arn:aws:iam::<AWS_ACCOUNT_ID>:role/ci-deploy-role
         aws-region: us-east-1
   ```
   Where OIDC federation isn't available (some on-prem or older SaaS
   integrations), fall back to a short-TTL static credential with
   mandatory rotation rather than a "no expiry" token issued for
   convenience.

6. **Audit for orphaned credentials tied to decommissioned
   integrations/service accounts** — a token whose owning
   pipeline/service was removed months ago but whose credential is still
   valid is a pure liability with no offsetting benefit. Cross-reference
   active tokens against active pipelines/integrations on a recurring
   schedule (quarterly is a reasonable default cadence), not only when
   an audit or incident forces the question.

7. **Log every grant and revocation** (who approved it, for what task,
   for how long, and when it was actually revoked) so an access review
   or incident investigation doesn't depend on anyone's memory.

## Best practices

- Treat "no expiry set" as a defect on any credential or access grant,
  not a convenience — every credential should have a tracked expiry or
  review date, even if long.
- Prefer federated/short-lived credentials (OIDC, workload identity) for
  CI-to-cloud auth over long-lived static keys wherever the platform
  supports it; this eliminates the rotation problem for that credential
  entirely rather than just scheduling around it.
- Build revocation into the same workflow/ticket that created the grant,
  so "grant" and "revoke by" are always paired, not tracked separately
  (or not tracked at all).
- Rotate on a schedule ahead of expiry, with overlap between old and new
  credentials, rather than reactively after a pipeline breaks with an
  auth failure.
- Run a recurring (quarterly is reasonable) access review specifically
  looking for stale one-off grants and orphaned service-account
  credentials, not only ad hoc when prompted by an audit finding.
- Scope every grant to the narrowest resource/permission that completes
  the specific task, never a broader role "to save a future request."

## Common pitfalls

- **Symptom:** A contractor's repo access is still active months after
  their engagement ended, discovered only during a security audit.
  **Fix:** Pair every access grant with an explicit revoke-by date
  tracked in a ticket (step 1), and run a recurring audit
  cross-referencing active grants against active engagements (step 3) —
  don't rely on someone remembering to remove access manually.

- **Symptom:** A CI pipeline suddenly starts failing with authentication
  errors because a service-account token quietly expired with no advance
  warning.
  **Fix:** Track every credential's expiry date and rotate on a schedule
  well before expiry, with overlap between old and new credentials
  (step 4) — rotation should never be a reactive scramble after a
  pipeline outage.

- **Symptom:** A CI-to-cloud integration uses a long-lived static access
  key "because setting up federation seemed like extra work," and that
  key later shows up in a leaked-secret scan.
  **Fix:** Default new CI-to-cloud integrations to OIDC/workload-identity
  federation (step 5), which removes the long-lived secret from the
  picture entirely rather than requiring it to be rotated and protected
  indefinitely.

- **Symptom:** A one-off production access grant given "just to
  debug this one issue" is scoped to full admin because it was faster
  than figuring out the minimal permission set, and it's never revisited.
  **Fix:** Scope every grant to the narrowest permission for the stated
  task (step 2) — a broader grant "to save time" becomes a standing risk
  that outlives the task it was meant for.

- **Symptom:** A service account's credential is still valid long after
  the pipeline or integration that used it was decommissioned.
  **Fix:** Include orphaned-credential detection in the recurring access
  review (step 6) — cross-reference active credentials against actually
  active pipelines/integrations, not just against a list of employees.

## Worked example

**Scenario:** An external QA vendor needs temporary read/write access to
a `checkout-api` repo's CI configuration for a two-week load-testing
engagement, and separately the team notices their GitHub App's CI
deployment key expires in 45 days.

1. **Grant, time-boxed:** access request ticket created with an explicit
   `revoke-by: 2026-08-11` date (two weeks out), granting the vendor
   `push` access to only `checkout-api` (not the org, not other repos),
   scoped further by branch protection so they still can't push directly
   to `main`.
2. **Track:** the ticket is tagged `access-expiry` and surfaced on a
   weekly automated report of grants nearing their revoke-by date.
3. **Revoke, verified:** on 2026-08-11, the vendor's collaborator access
   is removed via `gh api repos/<org>/checkout-api/collaborators/<user> -X DELETE`,
   and the ticket is closed with a timestamped confirmation — not just
   assumed done because the engagement "should be" over.
4. **Credential rotation, scheduled ahead of expiry:** with the GitHub
   App deployment key expiring in 45 days, a new key is generated 30 days
   out, added to the CI secret store alongside the old one, and every
   consuming workflow is updated to reference the new key. Only after
   confirming (via a successful run of every consuming pipeline) that
   the new key works is the old key explicitly revoked in the GitHub App
   settings — 15 days before its natural expiry, with no last-minute
   scramble.
5. **Quarterly audit:** the next scheduled access review cross-references
   all current repo collaborators and CI credentials against active
   engagements and active pipelines, confirming no stale grants or
   orphaned credentials remain from either the vendor engagement or the
   rotation.

## Cross-references

- [secrets-management](../../../devsecops/skills/secrets-management/SKILL.md) —
  the broader secrets-manager and secret-scanning discipline that CI
  credential storage and rotation build on.
- [cloud-iam-hardening](../../../cloud/skills/cloud-iam-hardening/SKILL.md) —
  eliminating long-lived cloud credentials via federation, applied here
  specifically to CI-to-cloud authentication.
- [ci-cd-pipeline-design](../ci-cd-pipeline-design/SKILL.md) — where
  pipeline-level secrets/credentials fit into the overall pipeline
  design this skill's rotation and access practices operate within.
- [emergency-hotfix-deployment-procedure](../emergency-hotfix-deployment-procedure/SKILL.md) —
  a related case of temporary, exceptional access (an emergency approval
  bypass) that should be similarly logged and time-boxed, not left
  standing.
