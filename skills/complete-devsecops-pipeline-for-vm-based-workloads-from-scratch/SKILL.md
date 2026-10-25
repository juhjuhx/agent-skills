---
name: complete-devsecops-pipeline-for-vm-based-workloads-from-scratch
description: >
  Builds the complete security-gate sequence for a VM-based DevSecOps
  pipeline from scratch — SAST, SCA, golden-image scanning and CIS
  benchmark hardening baked into the machine image itself, config-
  management-applied secrets via Ansible Vault (never plaintext), and an
  ongoing patch/drift-detection gate that runs independently of any single
  deploy, distinct from the per-deploy scanning in the Kubernetes and
  serverless variants. Use when the user asks to "build a DevSecOps
  pipeline for EC2/VM workloads from scratch," "harden a golden AMI to CIS
  benchmarks in the pipeline," "apply secrets with Ansible Vault instead
  of plaintext," or "add ongoing patch/drift detection for a VM fleet."
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: devsecops
  maturity: stable
---

# Complete DevSecOps Pipeline Deployment for VM-Based Workloads, From Scratch

## Purpose

A VM-based DevSecOps pipeline has a gate sequence with a genuinely
different time dimension from the Kubernetes and serverless variants of
this skill. Those two are almost entirely **per-deploy** gates: a scan
runs, a decision is made, an artifact ships. A VM fleet built on
long-lived, immutable golden images additionally needs an **ongoing**
gate that has no equivalent in a pipeline that redeploys constantly — a
golden AMI baked and CIS-hardened once can still drift out of compliance
or accumulate newly-disclosed CVEs for months while sitting unchanged in
an Auto Scaling Group, so patch/drift detection has to run as its own
recurring check, independent of whether a new deploy happens at all.
Secrets follow yet another distinct model here too: applied by a
config-management tool (Ansible Vault) at provision/config-push time,
encrypted at rest in the same repo as the playbooks, rather than a
cluster-side operator (Kubernetes) or a runtime API call to a managed
secrets service (serverless).

## When to use

- A VM-based pipeline has individual security tools bolted on ad hoc, and
  the user wants the full gate sequence — including golden-image CIS
  hardening and an ongoing drift-detection gate — designed coherently from
  scratch.
- The user is building a new EC2/VM-based service's pipeline and wants
  security gates designed in from the start.
- The user wants to understand why a VM-based pipeline needs a
  *recurring*, deploy-independent security gate in addition to its
  per-deploy scans — the property that most distinguishes it from the
  Kubernetes and serverless variants.
- Diagnosing why a golden AMI that passed CIS benchmark scanning at bake
  time is now failing a compliance audit months later with no code change
  in between.

## Prerequisites & environment

- A working CI/CD pipeline that already builds, bakes a golden image (or
  prepares an Ansible-driven config push), and deploys via blue-green
  instance refresh or a playbook run — see
  [complete-cicd-pipeline-for-vm-based-workloads-from-scratch](../../../cicd-tooling/skills/complete-cicd-pipeline-for-vm-based-workloads-from-scratch/SKILL.md)
  for that base pipeline; this skill adds the security-gate layer onto it.
- SAST and SCA tooling chosen per
  [sast-integration](../sast-integration/SKILL.md) and
  [software-composition-analysis-sca](../software-composition-analysis-sca/SKILL.md).
- A CIS benchmark scanner — `kube-bench`'s non-Kubernetes sibling tooling,
  OpenSCAP, or a cloud-native CIS scanner — per
  [cis-benchmarks-hardening](../../../standards-and-compliance-frameworks/skills/cis-benchmarks-hardening/SKILL.md).
- Ansible ≥ 2.15 with `ansible-vault` for secrets encryption, per
  [ansible-playbook-and-role-design](../../../iac-and-automation-tooling/skills/ansible-playbook-and-role-design/SKILL.md).
- A scheduled job runner (a nightly/weekly CI cron trigger, or a fleet
  management tool) capable of running patch/drift checks against live,
  already-deployed instances independently of any deploy event.
- Drift-detection tooling for the underlying cloud resources (Auto Scaling
  Group configuration, security groups) per
  [cloud-resource-post-provisioning-validation-and-drift-detection](../../../cloud/skills/cloud-resource-post-provisioning-validation-and-drift-detection/SKILL.md).

## Step-by-step guidance

### Phase 1 — SAST on the diff (PR-time)

Per [sast-integration](../sast-integration/SKILL.md): unchanged from any
other pipeline.

### Phase 2 — SCA on the application dependency tree (PR-time)

Per [software-composition-analysis-sca](../software-composition-analysis-sca/SKILL.md):
scan the lockfile before baking anything, exactly as in the base VM CI/CD
pipeline.

### Phase 3 — Golden-image scanning and CIS benchmark hardening, baked into the image itself

This is the VM-specific gate: after Packer bakes the AMI (per
[complete-cicd-pipeline-for-vm-based-workloads-from-scratch](../../../cicd-tooling/skills/complete-cicd-pipeline-for-vm-based-workloads-from-scratch/SKILL.md)),
scan the *resulting machine image* — its OS packages, its configuration
posture against CIS benchmarks — not just the application artifact that
was installed onto it:
```json
build {
  sources = ["source.amazon-ebs.payments_api"]
  provisioner "shell" { script = "scripts/install-app.sh" }
  provisioner "shell" {
    # CIS-aligned OS hardening applied at bake time, not left to the
    # instance's first boot or a later manual pass
    script = "scripts/cis-harden.sh"
  }
  provisioner "shell" {
    inline = ["sudo cis-cat-lite --benchmark rhel9 --profile level1-server --report /tmp/cis-report.html"]
  }
  post-processor "manifest" {}
}
```
Fail the pipeline (or require an explicit, expiring waiver) on any
Level-1 CIS finding, per
[cis-benchmarks-hardening](../../../standards-and-compliance-frameworks/skills/cis-benchmarks-hardening/SKILL.md)'s
guidance on interpreting PASS/FAIL/WARN against the actual benchmark text
rather than treating a scan pass as a compliance certification. This is
the machine-image analog of
[container-image-hardening](../container-image-hardening/SKILL.md)'s
non-root/read-only/minimal-base discipline, applied to a whole bootable OS
instead of a container layer.

### Phase 4 — Config-management-applied secrets via Ansible Vault, never plaintext

Where Kubernetes fetches secrets cluster-side and serverless fetches them
via a runtime API call, the VM-based model applies secrets at
config-push/provision time through Ansible, with the secret values
encrypted at rest in the same repo as the playbooks — never a plaintext
variable file:
```bash
ansible-vault encrypt group_vars/prod/vault.yml
```
```yaml
# group_vars/prod/vault.yml (encrypted at rest via ansible-vault)
vault_db_password: "S3cr3tValueNeverPlaintextInGit"
```
```yaml
# deploy.yml task referencing the vaulted variable
- name: Render application config with DB credentials
  ansible.builtin.template:
    src: templates/app-config.yml.j2
    dest: /etc/payments-api/config.yml
    mode: "0600"
  no_log: true
```
The playbook run itself decrypts `vault.yml` using a vault password
supplied out-of-band (a CI secret referencing the vault password, or
better, `--vault-id` backed by a secrets manager lookup) — the encrypted
file is safe to commit, but the vault password itself follows the same
never-hardcoded discipline as any other credential, per
[secrets-management](../secrets-management/SKILL.md) and
[ansible-playbook-and-role-design](../../../iac-and-automation-tooling/skills/ansible-playbook-and-role-design/SKILL.md).
`no_log: true` on any task handling the decrypted value prevents it from
being printed in Ansible's own execution output.

### Phase 5 — Deploy (unchanged from the base CI/CD pipeline)

Blue-green instance refresh or Ansible config push, per
[complete-cicd-pipeline-for-vm-based-workloads-from-scratch](../../../cicd-tooling/skills/complete-cicd-pipeline-for-vm-based-workloads-from-scratch/SKILL.md).

### Phase 6 — Ongoing patch/drift detection, independent of any single deploy

This is the gate with no equivalent in the Kubernetes or serverless
variants: a golden image or a fleet of long-lived VMs can silently
accumulate risk (new CVEs disclosed against already-installed package
versions, manual `ssh`-and-fix drift from the golden config, a security
group edited out-of-band) with zero code changes and zero new deploys.
Schedule this as its own recurring job, not tied to the deploy pipeline
trigger:
```yaml
name: fleet-patch-and-drift-scan
on:
  schedule:
    - cron: '0 4 * * *'
jobs:
  patch-scan:
    runs-on: ubuntu-latest
    steps:
      - run: |
          aws ssm start-automation-execution \
            --document-name AWS-RunPatchBaseline \
            --parameters "Operation=Scan"
      - run: trivy image --severity CRITICAL,HIGH "${LATEST_GOLDEN_AMI_REPO_REF}"
  drift-scan:
    runs-on: ubuntu-latest
    steps:
      - run: ansible-playbook -i inventories/prod check-drift.yml --check --diff
```
`check-drift.yml --check --diff` runs every task in dry-run mode against
the live fleet and reports any host whose actual state no longer matches
the playbook's declared state — catching a manually-`ssh`'d config change
on a running instance the same way
[gitops-workflow](../../../devops/skills/gitops-workflow/SKILL.md)'s
`selfHeal` catches drift in Kubernetes, but as an explicit scheduled
report rather than a continuously-reconciling controller, since Ansible
push has no equivalent of an in-cluster operator watching state
continuously.

### Phase 7 — Verify

```bash
aws ssm describe-instance-patch-states-for-patch-group --patch-group payments-api-prod
ansible-playbook -i inventories/prod check-drift.yml --check --diff | grep -c changed
```
A nonzero `changed` count from the drift check means at least one host has
diverged from the declared playbook state and needs investigation before
it's treated as routine.

## Best practices

- Bake CIS hardening into the golden image at build time (Phase 3), not
  as a post-boot script run once and never re-verified — an image that's
  hardened once at bake time and then re-baked on every pipeline run stays
  provably compliant; a post-boot script only run at first launch can be
  skipped, fail silently, or be undone by later manual changes.
- Treat a CIS scan pass as a hardening signal, not a compliance
  certification, per
  [cis-benchmarks-hardening](../../../standards-and-compliance-frameworks/skills/cis-benchmarks-hardening/SKILL.md)
  — document any Level-1 waiver with an expiry and a reviewer, the same
  suppression discipline as SAST/SCA findings elsewhere in this repo.
- Run the patch/drift gate (Phase 6) on a schedule independent of the
  deploy pipeline — a fleet that hasn't had a code deploy in three months
  still needs patch scanning during that entire window, since new CVEs are
  disclosed against already-running versions constantly.
- Never commit an unencrypted Ansible variables file "temporarily" —
  `ansible-vault encrypt` before the first commit, not after a secret
  is discovered in git history; treat a plaintext secret found in a vars
  file with the same rotate-first response as any other leaked credential,
  per [secrets-management](../secrets-management/SKILL.md).
- Rebuild and rescan the golden image on a cadence even when application
  code hasn't changed, so newly-disclosed base-OS CVEs are caught by the
  next bake rather than only by the separate Phase 6 patch scan — the two
  gates are complementary, not redundant.

## Common pitfalls

- **Symptom:** A golden AMI passed its CIS scan at bake time six months
  ago, and a compliance audit today finds several Level-1 findings on
  instances still running that same AMI.
  **Fix:** This is expected without a recurring gate — a CIS scan result
  is only valid as of the moment it ran; without Phase 6's scheduled
  patch/drift scan (or a periodic rebake-and-rescan cadence), an
  unchanged golden image accumulates newly-disclosed findings silently.
  Add the scheduled scan, and treat "last CIS scan date" as a tracked
  fleet metric, not a one-time checkbox.

- **Symptom:** An Ansible `group_vars/prod/vault.yml` was committed
  unencrypted "just for local testing," and by the time someone notices
  and runs `ansible-vault encrypt`, the plaintext secret is already in git
  history.
  **Fix:** Treat it as a leaked credential exactly like any other secret
  — rotate the underlying value at its source system first, then encrypt
  and re-commit, and only then consider the finding closed; encrypting the
  current version does not retroactively protect the plaintext already in
  history, per
  [secrets-management](../secrets-management/SKILL.md).

- **Symptom:** The drift-detection playbook (`--check --diff`) reports a
  handful of hosts as "changed" every single run, even right after a clean
  deploy, and the team starts ignoring the report entirely.
  **Fix:** This is usually a genuinely non-idempotent task (a `command:`/
  `shell:` task with no `changed_when` guard that Ansible can't evaluate
  as idempotent) rather than real drift — audit the flagged tasks for
  idempotency per
  [ansible-playbook-and-role-design](../../../iac-and-automation-tooling/skills/ansible-playbook-and-role-design/SKILL.md)
  before concluding the hosts have actually drifted, since a
  false-positive "changed" every run trains the team to stop reading the
  report, the same trust-erosion failure mode as a chronically-noisy SAST
  gate.

- **Symptom:** A security group attached to the fleet was edited directly
  in the console "to open a port for debugging" and never reverted, and
  it's now a standing exposure nobody remembers creating.
  **Fix:** Manual cloud-console changes to fleet-supporting infrastructure
  (security groups, launch templates) are a different drift surface from
  the instance-level Ansible drift check — pair Phase 6's host-level drift
  scan with infrastructure-level drift detection per
  [cloud-resource-post-provisioning-validation-and-drift-detection](../../../cloud/skills/cloud-resource-post-provisioning-validation-and-drift-detection/SKILL.md),
  since neither one alone covers both layers.

## Worked example

**Scenario:** `payments-api`'s VM fleet gets its full DevSecOps gate
sequence: SAST/SCA at PR time, CIS-hardening baked into the golden AMI,
database credentials applied via Ansible Vault, and a nightly
patch/drift-detection job independent of the deploy pipeline.

```yaml
# .github/workflows/ci-cd.yml (build/bake/deploy jobs per the base VM CI/CD skill)
jobs:
  sast: { /* per sast-integration */ }
  sca: { /* per software-composition-analysis-sca */ }
  bake-and-scan-image:
    needs: [sast, sca]
    runs-on: ubuntu-latest
    steps:
      - run: packer build payments-api.pkr.hcl
      - run: |
          AMI_ID=$(jq -r '.builds[-1].artifact_id' manifest.json | cut -d: -f2)
          # cis-cat-lite runs as a Packer provisioner during the bake (Phase 3);
          # its report is a build artifact reviewed here
          aws s3 cp cis-report.html "s3://payments-api-compliance-reports/${AMI_ID}.html"
  apply-config-and-secrets:
    needs: bake-and-scan-image
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          ansible-playbook -i inventories/prod deploy.yml \
            --vault-password-file <(aws secretsmanager get-secret-value --secret-id ansible-vault-prod --query SecretString --output text)
```
```yaml
# .github/workflows/fleet-patch-and-drift-scan.yml — independent schedule
name: fleet-patch-and-drift-scan
on:
  schedule: [{ cron: '0 4 * * *' }]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - run: aws ssm start-automation-execution --document-name AWS-RunPatchBaseline --parameters "Operation=Scan"
      - uses: actions/checkout@v4
      - run: ansible-playbook -i inventories/prod check-drift.yml --check --diff
```
The nightly job runs whether or not `payments-api` had a deploy that day —
catching newly-disclosed OS CVEs against the already-running golden image
and any manual configuration drift on the live fleet, entirely independent
of the per-deploy gate sequence above it.

## Cross-references

- [complete-cicd-pipeline-for-vm-based-workloads-from-scratch](../../../cicd-tooling/skills/complete-cicd-pipeline-for-vm-based-workloads-from-scratch/SKILL.md) — the base image-baking/deploy pipeline this skill adds security gates onto.
- [sast-integration](../sast-integration/SKILL.md) and [software-composition-analysis-sca](../software-composition-analysis-sca/SKILL.md) — Phase 1-2 gate mechanics.
- [cis-benchmarks-hardening](../../../standards-and-compliance-frameworks/skills/cis-benchmarks-hardening/SKILL.md) — Phase 3's golden-image CIS scanning and waiver-process mechanics.
- [container-image-hardening](../container-image-hardening/SKILL.md) — the container-image analog of Phase 3's hardening discipline, for contrast.
- [ansible-playbook-and-role-design](../../../iac-and-automation-tooling/skills/ansible-playbook-and-role-design/SKILL.md) — Ansible Vault and idempotency mechanics used in Phase 4/6.
- [secrets-management](../secrets-management/SKILL.md) — general secrets-handling discipline Phase 4 applies via Ansible Vault specifically.
- [cloud-resource-post-provisioning-validation-and-drift-detection](../../../cloud/skills/cloud-resource-post-provisioning-validation-and-drift-detection/SKILL.md) — infrastructure-level (not just host-level) drift detection that complements Phase 6.
- [complete-devsecops-pipeline-for-kubernetes-from-scratch](../complete-devsecops-pipeline-for-kubernetes-from-scratch/SKILL.md) and [complete-devsecops-pipeline-for-serverless-from-scratch](../complete-devsecops-pipeline-for-serverless-from-scratch/SKILL.md) — the same gate-sequencing goal with fundamentally different primary gates and secrets models.
