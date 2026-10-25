---
name: cloud-iam-hardening
description: >
  Guides hardening identity and access management across AWS, Azure, and
  GCP — least-privilege policy design, eliminating long-lived credentials
  in favor of federation (OIDC/Workload Identity), break-glass access, and
  periodic access review. Use when a user asks to "reduce IAM
  permissions", "remove unused IAM roles", "set up federated/keyless
  access for CI/CD", "harden our cloud identity posture", "review who has
  admin access", "implement least privilege", or "get rid of long-lived
  access keys".
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: cloud
  maturity: stable
---

# Cloud IAM Hardening

## Purpose

Identity is the perimeter in cloud environments — network controls help,
but the vast majority of real-world cloud breaches trace back to
over-permissioned roles, leaked long-lived credentials, or a human/service
account with far more access than its job requires. IAM hardening is not
a one-time setup step; it is a continuous discipline of shrinking
permissions to what's actually used, replacing static credentials with
short-lived federated tokens, and reviewing access on a cadence. This
skill applies across AWS IAM, Azure RBAC/Entra ID, and GCP IAM, since the
underlying failure modes (privilege creep, standing admin access,
long-lived keys) are identical even though the primitives differ.

## When to use

- Reducing an over-broad policy (e.g. `AdministratorAccess`, `Owner`,
  `roles/editor`) down to least privilege for a specific workload or team.
- Setting up CI/CD pipelines (GitHub Actions, GitLab CI, Azure DevOps) to
  authenticate to cloud APIs without storing static access keys/service
  account keys as secrets.
- Investigating "who can do X" or "why does this role have this
  permission" during an incident or audit.
- Implementing break-glass emergency access that bypasses normal SSO/MFA
  flows only when genuinely needed, with full audit logging.
- Running a quarterly or post-incident access review to find unused
  permissions, stale credentials, or orphaned service principals.
- Responding to a cloud security posture finding like "N IAM users have
  console access keys older than 90 days" or "M service accounts have
  organization-level Owner."

## Prerequisites & environment

- Read access to the relevant IAM surface: AWS IAM Access Analyzer /
  CloudTrail, Azure AD sign-in + audit logs / Entra Permissions
  Management, or GCP IAM Recommender / Policy Analyzer — these tools
  generate the "what's actually used" data that least-privilege
  redesigns depend on; don't guess permissions from documentation alone.
- For CI/CD federation: the CI platform must support OIDC token issuance
  (GitHub Actions, GitLab CI ≥ 15.7, CircleCI, Azure DevOps all do
  natively as of 2024).
- Terraform ≥ 1.5 (or the cloud-native IaC of choice) if policies are
  managed as code — strongly recommended over console-managed IAM once
  past a handful of roles.
- Organizational agreement on a break-glass process owner and an alerting
  destination (e.g. a PagerDuty escalation) before implementing
  break-glass access, so its use is always followed up on.

## Step-by-step guidance

1. **Inventory current access before changing anything.** Pull a
   permissions-usage report:
   - AWS: IAM Access Analyzer's "unused access" findings, or
     `aws iam generate-service-last-accessed-details`.
   - Azure: Entra Permissions Management (if licensed) or
     `az role assignment list --all` cross-referenced with Azure AD
     sign-in logs.
   - GCP: `gcloud recommender recommendations list
     --recommender=google.iam.policy.Recommender --project=<PROJECT_ID>`
     or the IAM Policy Analyzer in the console.

2. **Replace long-lived credentials with federation.** For CI/CD:
   - **AWS**: configure an OIDC identity provider trusting the CI
     platform's token issuer, and a role with a trust policy scoped to
     the specific repo/branch:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [{
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::<AWS_ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": {
             "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
           },
           "StringLike": {
             "token.actions.githubusercontent.com:sub": "repo:example-org/checkout-service:ref:refs/heads/main"
           }
         }
       }]
     }
     ```
   - **GCP**: use Workload Identity Federation — a workload identity pool
     mapped to the CI OIDC issuer, with an attribute condition restricting
     which repo/branch can impersonate the target service account.
   - **Azure**: use a federated credential on an Entra app registration
     (`az ad app federated-credential create`) scoped to the specific
     repo and environment, eliminating the client-secret entirely.
   Delete the static access key / service account key / client secret
   only after confirming the federated path works end-to-end in a
   non-production pipeline run.

3. **Shrink standing permissions to least privilege**, iteratively:
   - Start from the access-usage report from step 1, not from a blank
     policy — build the allow-list from what's actually called.
   - Replace broad AWS managed policies (`AmazonS3FullAccess`) with
     resource-scoped custom policies naming specific buckets/prefixes.
   - In GCP, replace basic roles (`roles/editor`, `roles/owner`) with
     predefined or custom roles scoped to the specific service and
     project.
   - In Azure, replace `Owner`/`Contributor` at the subscription level
     with built-in roles scoped to a resource group, or custom RBAC
     roles listing only the needed `actions`.

4. **Convert standing admin access to just-in-time (JIT) elevation**
   where the platform supports it: AWS IAM Identity Center permission
   sets combined with a JIT approval workflow, Azure PIM (Privileged
   Identity Management) for time-bound role activation, or GCP's
   temporary elevated access via IAM Conditions with an expiry timestamp:
   ```json
   {
     "role": "roles/owner",
     "members": ["user:oncall-engineer@example.com"],
     "condition": {
       "title": "temporary-incident-access",
       "expression": "request.time < timestamp('2026-08-01T00:00:00Z')"
     }
   }
   ```

5. **Design break-glass access deliberately, not implicitly.** Create a
   small number of emergency-access identities (e.g. an AWS IAM user held
   in a sealed/rotated-after-use credential vault, or an Azure emergency
   access account excluded from Conditional Access) with wide permissions
   but wired to trigger a high-priority alert on every use, and require a
   post-use incident review.

6. **Set up continuous drift detection**: run the IAM Access
   Analyzer / IAM Recommender / Azure Permissions Management scan on a
   schedule (weekly, in CI) and fail a pipeline or open a ticket when a
   new unused-permission finding appears, rather than relying on an
   annual manual audit.

7. **Review and prune on a cadence.** Quarterly at minimum: revoke access
   for anyone who changed teams/left, delete unused roles/service
   accounts flagged by the recommender tools, and rotate any credential
   that IAM hardening hasn't yet fully replaced with federation.

## Best practices

- **Prefer federation over any long-lived credential** — access keys,
  service account JSON keys, and client secrets are the highest-leverage
  thing to eliminate; almost every modern CI/CD and workload runtime
  supports OIDC/Workload Identity Federation today.
- **Scope trust policies to the narrowest subject possible** (specific
  repo + branch/environment, not `repo:example-org/*`) — a wildcard OIDC
  trust policy is only marginally better than a static key.
- **Grant permissions to groups/roles, not individual identities** — an
  individual leaving should never require touching resource policies.
- **Treat SCPs/Organization Policies/Azure Policy as a backstop, not the
  primary control** — see the respective landing-zone skills; IAM policy
  is where least privilege actually lives.
- **Time-box elevated access** using PIM, IAM Conditions with expiry, or
  short-lived `sts:AssumeRole` sessions instead of standing admin grants.
- **Log every policy change** and require peer review on IAM/RBAC
  Terraform changes the same way you would for application code — IAM
  is production infrastructure.
- Avoid **policy sprawl from copy-pasted "just in case" permissions** —
  every `*` in an `Action` or `Resource` field is a future audit finding.

## Common pitfalls

- **Symptom:** A least-privilege policy rollout breaks a production
  workload at 2am because a rarely-used code path (e.g. a monthly batch
  job) needed a permission the usage report didn't capture.
  **Fix:** Access-usage reports only reflect the lookback window queried
  (often 90 days). Before tightening a policy used by infrequent
  workloads, either extend the lookback, deploy the tightened policy in
  monitor/audit mode first (AWS IAM Access Analyzer policy generation,
  GCP `dry-run` mode is not natively available so stage in a non-prod
  project), or keep the change behind a feature flag with a fast
  rollback path.

- **Symptom:** OIDC federation trust policy works from the `main` branch
  but any other branch or a fork's PR fails to assume the role — good —
  but then someone widens the `sub` condition to `repo:org/*:*` to "fix"
  a legitimate need, quietly re-opening the exposure.
  **Fix:** Add environment- or branch-specific conditions instead of
  wildcarding the whole repo (e.g.
  `repo:example-org/checkout-service:environment:production`), and gate
  production environments in the CI platform (GitHub Environments,
  GitLab protected environments) so only protected branches can even
  request that OIDC token.

- **Symptom:** A quarterly access review finds several service
  accounts/roles with no owner, last used over a year ago, holding
  broad permissions.
  **Fix:** No lifecycle policy existed for service identities created
  during a migration or POC. Add a tagging requirement (`owner`,
  `created-for-ticket`) enforced at creation (see the landing-zone
  skills' tag-policy guardrails), and schedule automatic flagging (not
  automatic deletion without human sign-off) of identities unused for
  90+ days.

- **Symptom:** Break-glass credentials are used routinely for normal
  operations because the "proper" federated path is slower or less
  convenient.
  **Fix:** This defeats the purpose of break-glass and erodes its
  audit-trail value. Treat repeated break-glass use as a signal that the
  standard access path is missing a legitimate permission — fix the
  standard path (add a scoped permission or a JIT elevation option)
  rather than normalizing the emergency path.

## Worked example

**Scenario:** A security review finds that the `checkout-service`
deployment pipeline authenticates to AWS using a long-lived IAM user
access key stored as a GitHub Actions secret, with `AdministratorAccess`
attached "to avoid permission errors."

1. Pull the IAM user's `generate-service-last-accessed-details` report —
   it shows the pipeline only ever calls `s3:PutObject` on one bucket
   prefix, `ecs:UpdateService`, and `ecr:PutImage`/`ecr:GetAuthorizationToken`.
2. Create an OIDC identity provider for `token.actions.githubusercontent.com`
   and an IAM role `checkout-service-ci-deploy` with a trust policy scoped
   to `repo:example-org/checkout-service:environment:production`.
3. Attach a custom policy to that role granting exactly the three
   services/actions found in step 1, scoped to the specific bucket ARN,
   ECS cluster/service ARN, and ECR repository ARN.
4. Update the GitHub Actions workflow to use
   `aws-actions/configure-aws-credentials` with `role-to-assume` instead
   of static `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` secrets, and
   configure the workflow's `production` environment as a GitHub
   protected environment requiring a reviewer.
5. Run the pipeline end-to-end against a staging environment to confirm
   the scoped role works, then delete the IAM user and its access key.
6. Add a weekly IAM Access Analyzer scan that alerts if any new IAM user
   with console/API access keys appears, to prevent regression.

## Cross-references

- [aws-landing-zone-setup](../aws-landing-zone-setup/SKILL.md)
- [azure-landing-zone-setup](../azure-landing-zone-setup/SKILL.md)
- [gcp-landing-zone-setup](../gcp-landing-zone-setup/SKILL.md)
