---
name: complete-gitops-argocd-deployment-on-prem-from-scratch
description: >
  Walks through a complete, end-to-end Argo CD GitOps deployment on a
  self-managed on-prem or bare-metal Kubernetes cluster with no cloud IAM
  shortcut available — Helm install, ServiceAccount/RBAC-scoped cluster
  access (optionally backed by Vault-issued short-lived credentials
  instead of IRSA/Workload Identity), private registry authentication
  (Harbor/Nexus), MetalLB + Ingress + private-CA TLS instead of a cloud
  load balancer, the first Application, an ApplicationSet for
  multi-environment rollout, and sync/health policy. Use when the user
  asks to "set up Argo CD on-prem from scratch," "deploy GitOps end-to-end
  without a cloud provider," "give Argo CD cluster access without cloud
  IAM," "wire Vault-issued credentials into Argo CD," or "go from a bare
  self-managed cluster to a working multi-env GitOps pipeline."
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: gitops-argo-ecosystem
  maturity: stable
---

# Complete GitOps/Argo CD Deployment On-Prem, From Scratch

## Purpose

The EKS/AKS/GKE variants of this skill all solve the same problem the same
way: a cloud-native workload identity federation mechanism (IRSA, Azure AD
Workload Identity, GKE Workload Identity Federation) lets Argo CD's own
components authenticate without a long-lived static credential. On a
self-managed or bare-metal cluster **that mechanism does not exist** —
there is no cloud STS to federate against. This is the genuine mechanical
difference this skill exists to cover: cluster access has to fall back to
Kubernetes-native `ServiceAccount` tokens and RBAC, ideally made
short-lived via HashiCorp Vault's Kubernetes secrets engine rather than a
permanent bearer token; private registry authentication needs an
explicit `imagePullSecret`/credential-helper flow instead of an IRSA/
Workload-Identity-backed pull; and the Ingress/TLS layer needs a
bare-metal load balancer (MetalLB) and often an internal CA instead of a
cloud LB and public ACME issuance. Everything else — the `Application`
spec, `ApplicationSet` generators, sync policy — is identical to the cloud
variants and is not repeated here.

## When to use

- Starting from a bare, already-provisioned self-managed Kubernetes
  cluster (kubeadm, k3s, Cluster API, or a vendor distribution) with
  nothing GitOps-related installed, needing a working Argo CD + first
  deployed app + multi-environment rollout by the end of the session, with
  no cloud provider IAM available.
- The user explicitly wants cluster-access credentials issued by Vault
  (short-lived) instead of a permanent Kubernetes Secret bearer token.
- Standing up a second/third on-prem environment (a separate physical
  cluster or air-gapped site) for a service already GitOps-managed
  elsewhere.
- Migrating a team off manual `kubectl apply`/`helm upgrade` deploys on
  on-prem infrastructure onto a full GitOps flow, starting from zero.
- Diagnosing why a freshly installed Argo CD on-prem can't pull a private
  registry image, can't reach a second physical cluster, or has no
  externally reachable Ingress.

## Prerequisites & environment

- A self-managed Kubernetes cluster already provisioned and reachable via
  `kubectl` — bare-metal/VMware provisioning patterns are covered by
  [on-prem-infrastructure-patterns](../../../cloud/skills/on-prem-infrastructure-patterns/SKILL.md)
  and are not repeated here; this skill starts from "the cluster exists."
- `helm` ≥ 3.12, `kubectl`, and cluster-admin access to create
  `ServiceAccount`s, `ClusterRole`s, and `ClusterRoleBinding`s.
- A bare-metal load balancer already installed —
  [metallb-bare-metal-load-balancer-configuration](../../../kubernetes-platform/skills/metallb-bare-metal-load-balancer-configuration/SKILL.md)
  — since there is no cloud `LoadBalancer` Service type to fall back on for
  Ingress.
- A private container registry (Harbor, Nexus, or similar) already
  reachable from the cluster, with credentials available.
- Optional but recommended for anything beyond a small/dev deployment: a
  running Vault cluster — see
  [vault-operations-and-pki-engine-configuration](../../../security-scanning-tooling/skills/vault-operations-and-pki-engine-configuration/SKILL.md)
  for standing it up, and
  [secrets-management](../../../devsecops/skills/secrets-management/SKILL.md)
  for the general dynamic-secrets pattern this skill applies specifically
  to Argo CD's cluster-access credentials.
- A Git repository already reachable from the cluster's network path
  (self-hosted Gitea/GitLab is common on-prem — see
  [gitea-actions-and-ci](../../../cicd-tooling/skills/gitea-actions-and-ci/SKILL.md)
  if the config repo also lives there).

## Step-by-step guidance

### Phase 0 — Confirm no externally-reachable LoadBalancer exists yet

```bash
kubectl get svc -A -o wide | grep LoadBalancer
```
On a fresh self-managed cluster this is normally empty — a `Service` of
type `LoadBalancer` stays `<pending>` forever without MetalLB (or an
equivalent) installed. Install MetalLB (Phase 3 depends on it) before
assuming any `LoadBalancer`-typed Service will ever get an external IP.

### Phase 1 — Install Argo CD via Helm

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm install argocd argo/argo-cd \
  --namespace argocd --create-namespace \
  --version 7.6.12 \
  --set server.service.type=ClusterIP
kubectl get pods -n argocd
```
Identical to the cloud variants — the install itself has no cloud
dependency.

### Phase 2 — Cluster access without cloud IAM: ServiceAccount + RBAC, optionally Vault-issued

There is no OIDC-federated STS token to lean on here, so cluster access
for any *additional* destination cluster (a second physical site) falls
back to Kubernetes-native credentials, scoped as narrowly as possible per
[gitops-multi-cluster-management](../gitops-multi-cluster-management/SKILL.md):

```yaml
# Applied ON the spoke (second on-prem) cluster
apiVersion: v1
kind: ServiceAccount
metadata:
  name: argocd-manager
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: argocd-manager-role
rules:
  - apiGroups: ["apps", "", "batch", "networking.k8s.io"]
    resources: ["deployments", "services", "configmaps", "secrets", "jobs", "ingresses"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
    # Scoped to the resource kinds this spoke's workloads actually use —
    # not "*"/"*", since there is no cloud IAM boundary as a backstop.
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: argocd-manager-role-binding
subjects:
  - kind: ServiceAccount
    name: argocd-manager
    namespace: kube-system
roleRef:
  kind: ClusterRole
  name: argocd-manager-role
  apiGroup: rbac.authorization.k8s.io
```

The naive version of this uses the ServiceAccount's long-lived token
Secret directly in the hub's cluster registration `Secret` — functional,
but a permanent, non-rotating credential is exactly the failure mode
IRSA/Workload Identity exist to avoid on cloud. **Where the operational
maturity to run Vault already exists, prefer short-lived, Vault-brokered
credentials instead**: configure Vault's Kubernetes secrets engine (or a
scheduled rotation job) to periodically mint a fresh token for
`argocd-manager` and update the hub's cluster `Secret` via an External
Secrets Operator sync rather than a token that's valid forever:
```bash
vault write auth/kubernetes/config \
  kubernetes_host="https://<spoke-api-server>:6443"
vault policy write argocd-manager-policy - <<EOF
path "kubernetes/creds/argocd-manager" { capabilities = ["read"] }
EOF
```
See
[vault-operations-and-pki-engine-configuration](../../../security-scanning-tooling/skills/vault-operations-and-pki-engine-configuration/SKILL.md)
for standing up Vault's PKI/auth engines, and
[sealed-secrets-and-external-secrets-operator](../../../security-scanning-tooling/skills/sealed-secrets-and-external-secrets-operator/SKILL.md)
for the `ExternalSecret` that syncs the Vault-issued credential into the
hub's `argocd`-namespace cluster registration `Secret`.

### Phase 3 — Private registry auth and MetalLB-fronted Ingress/TLS

Unlike the cloud variants (IRSA/Workload-Identity-backed registry pulls),
on-prem private registry access is an explicit `imagePullSecret`, since
there is no cloud IAM-to-registry federation:
```bash
kubectl create secret docker-registry harbor-pull-secret \
  --docker-server=harbor.internal.example.com \
  --docker-username=argocd-reader \
  --docker-password="${HARBOR_ROBOT_TOKEN}" \
  -n argocd
```
Prefer a **Harbor robot account** (scoped to pull-only on specific
projects) over a personal account's credentials, and source
`HARBOR_ROBOT_TOKEN` from Vault/`secrets-management`, never hardcoded.

For Ingress, install
[metallb-bare-metal-load-balancer-configuration](../../../kubernetes-platform/skills/metallb-bare-metal-load-balancer-configuration/SKILL.md)
first so `ingress-nginx`'s own Service can actually get an external IP,
then front `argocd-server` with
[ingress-nginx-configuration](../../../kubernetes-platform/skills/ingress-nginx-configuration/SKILL.md).
TLS is the other on-prem-specific divergence: with no publicly resolvable
DNS name for an ACME HTTP-01/DNS-01 challenge, issue from an **internal CA**
via [cert-manager-tls-automation](../../../kubernetes-platform/skills/cert-manager-tls-automation/SKILL.md)'s
private-CA `Issuer` pattern (backed by Vault's PKI engine, if available)
instead of Let's Encrypt:
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata: { name: internal-vault-ca }
spec:
  vault:
    server: https://vault.internal.example.com:8200
    path: pki_int/sign/argocd
    auth:
      kubernetes:
        role: cert-manager
        mountPath: /v1/auth/kubernetes
```

### Phase 4 — First `Application`

Identical to the cloud variants — follow
[argocd-application-configuration](../argocd-application-configuration/SKILL.md)
in full:
```bash
kubectl apply -f payments-api-staging-application.yaml
argocd login argocd.internal.example.com --sso
argocd app sync payments-api-staging --dry-run
argocd app sync payments-api-staging
```

### Phase 5 — `ApplicationSet` for multi-environment/multi-site rollout

Per [argocd-applicationset-patterns](../argocd-applicationset-patterns/SKILL.md);
if staging and prod are separate physical clusters/sites, use the Cluster
generator filtered by label, with each site's registration reusing the
ServiceAccount/RBAC (or Vault-brokered) pattern from Phase 2.

### Phase 6 — Sync policy and health checks, deliberately

Manual sync until the pipeline feeding the config repo is trusted, then
`automated` per environment, plus custom Lua health checks for any
internal CRDs — both per
[argocd-application-configuration](../argocd-application-configuration/SKILL.md).

### Phase 7 — Verify end-to-end

```bash
argocd cluster list
argocd app list
kubectl get secret harbor-pull-secret -n argocd -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d
kubectl get certificate -n argocd argocd-server-tls -o jsonpath='{.status.conditions}'
```
Confirm the Harbor pull secret's embedded token is still valid (robot
tokens can expire independently of the Kubernetes Secret they're stored
in) and that the internal-CA certificate shows `Ready: True` before
trusting the Ingress is actually serving valid TLS.

## Best practices

- Treat a static ServiceAccount token used for cross-cluster registration
  as an interim state, not the end state — plan the Vault-brokered
  rotation path (Phase 2) before the fleet grows past a handful of
  clusters, since manually rotating tokens across many clusters doesn't
  scale and a leaked long-lived token has an unbounded blast radius.
- Scope the spoke `argocd-manager` `ClusterRole` to the exact resource
  kinds each spoke's workloads use — there is no cloud IAM boundary
  backstopping an overly broad on-prem RBAC grant the way there might be
  with a scoped IAM policy in the cloud variants.
- Use registry robot/service accounts (Harbor robot accounts, Nexus
  service users) scoped to pull-only on specific projects for
  `imagePullSecret`s, never a personal admin account's credentials.
- Install MetalLB and validate it hands out an external IP to a test
  `LoadBalancer` Service *before* installing `ingress-nginx` — debugging
  "Ingress isn't reachable" is much harder once both layers are stacked
  and unverified.
- Prefer an internal CA (via cert-manager's `ca`/`vault` Issuer types) over
  self-signed per-service certs for anything beyond a single throwaway
  test — an internal CA's trust bundle can be distributed once to clients,
  where self-signed certs require per-service trust exceptions.

## Common pitfalls

- **Symptom:** `ingress-nginx`'s own Service stays `<pending>` forever with
  no external IP, and every Ingress behind it is unreachable.
  **Fix:** This is expected without MetalLB (or an equivalent bare-metal
  LB) installed and configured with an IP address pool — install
  [metallb-bare-metal-load-balancer-configuration](../../../kubernetes-platform/skills/metallb-bare-metal-load-balancer-configuration/SKILL.md)
  and confirm a plain test `LoadBalancer` Service gets an IP before
  troubleshooting Ingress routing itself.

- **Symptom:** The cross-cluster `argocd-manager` ServiceAccount token was
  copied once at spoke-registration time and, months later, cluster access
  from the hub silently fails after a spoke cluster's token-rotation
  policy (e.g. `--service-account-max-token-expiration`) invalidated it.
  **Fix:** A raw ServiceAccount token Secret does not auto-renew on
  clusters configured with bounded token lifetimes — either re-mint and
  update the hub's cluster `Secret` manually on a schedule, or migrate to
  the Vault-brokered rotation pattern in Phase 2 so renewal is automatic.

- **Symptom:** A Harbor `imagePullSecret` worked at initial setup and later
  every pod pull starts failing with `unauthorized` across the whole
  cluster simultaneously.
  **Fix:** Harbor robot account tokens have their own expiration
  independent of the Kubernetes Secret storing them — check the robot
  account's expiry in Harbor directly (`docker login` manually against the
  registry with the same credential to confirm), not just the Secret's
  presence in the cluster.

- **Symptom:** The first `Application` was created with `automated:
  {prune: true, selfHeal: true}` immediately, and a bad initial manifest
  deleted an unrelated pre-existing resource in the target namespace.
  **Fix:** Same end-to-end sequencing pitfall as the cloud variants —
  always run the first sync manually with `--dry-run` (Phase 4) before
  enabling `automated` in a later, deliberate step (Phase 6).

- **Symptom:** cert-manager's internal-CA `ClusterIssuer` (Vault-backed)
  issues certificates that browsers/clients reject as untrusted, even
  though `kubectl describe certificate` shows `Ready: True`.
  **Fix:** `Ready: True` only confirms cert-manager successfully obtained
  a certificate from the configured issuer — it says nothing about
  whether *clients* trust that issuer's root. Distribute the internal CA's
  root certificate to client trust stores (or your org's device management
  baseline) separately; this is expected behavior for an internal CA, not
  a cert-manager misconfiguration.

## Worked example

**Scenario:** Stand up Argo CD from scratch on a self-managed `payments-prod`
kubeadm cluster with no cloud provider, using Harbor for private images,
Vault for both PKI and Argo CD's own cross-cluster credential rotation,
and MetalLB + Ingress for external access.

```bash
# Phase 0/3 — MetalLB first
helm install metallb metallb/metallb -n metallb-system --create-namespace
kubectl apply -f metallb-ip-pool.yaml

# Phase 1
helm install argocd argo/argo-cd -n argocd --create-namespace --version 7.6.12

# Phase 2 — spoke ServiceAccount + RBAC (applied on payments-staging)
kubectl apply -f argocd-manager-rbac.yaml --context payments-staging

# Phase 3 — Harbor pull secret + internal-CA Ingress
kubectl create secret docker-registry harbor-pull-secret \
  --docker-server=harbor.internal.example.com \
  --docker-username=argocd-reader --docker-password="${HARBOR_ROBOT_TOKEN}" -n argocd
kubectl apply -f argocd-server-ingress-internal-ca.yaml

# Phase 4 — first Application, manual sync
kubectl apply -f payments-api-staging-application.yaml
argocd app sync payments-api-staging --dry-run
argocd app sync payments-api-staging
```
Phase 5 then replaces the single `Application` with a Cluster-generator
`ApplicationSet` selecting `tier: staging`/`tier: prod` labeled on-prem
clusters (full YAML in
[argocd-applicationset-patterns](../argocd-applicationset-patterns/SKILL.md)),
and Phase 6 promotes staging's sync policy to `automated` once verified —
identical decision structure to the cloud variants, just built on
ServiceAccount/RBAC and Vault-issued credentials instead of IRSA/Workload
Identity.

## Cross-references

- [on-prem-infrastructure-patterns](../../../cloud/skills/on-prem-infrastructure-patterns/SKILL.md) — bare-metal/VMware cluster provisioning this skill assumes and builds on.
- [argocd-application-configuration](../argocd-application-configuration/SKILL.md) — full depth on the `Application` spec used in Phase 4/6.
- [argocd-applicationset-patterns](../argocd-applicationset-patterns/SKILL.md) — generator mechanics used in Phase 5.
- [gitops-multi-cluster-management](../gitops-multi-cluster-management/SKILL.md) — hub-and-spoke registration pattern this skill's Phase 2 adapts with ServiceAccount/RBAC and Vault-issued credentials.
- [metallb-bare-metal-load-balancer-configuration](../../../kubernetes-platform/skills/metallb-bare-metal-load-balancer-configuration/SKILL.md) and [ingress-nginx-configuration](../../../kubernetes-platform/skills/ingress-nginx-configuration/SKILL.md) — the bare-metal LB/Ingress layer Phase 3 depends on.
- [cert-manager-tls-automation](../../../kubernetes-platform/skills/cert-manager-tls-automation/SKILL.md) — the internal-CA `Issuer` pattern used instead of public ACME issuance.
- [vault-operations-and-pki-engine-configuration](../../../security-scanning-tooling/skills/vault-operations-and-pki-engine-configuration/SKILL.md) and [sealed-secrets-and-external-secrets-operator](../../../security-scanning-tooling/skills/sealed-secrets-and-external-secrets-operator/SKILL.md) — standing up Vault and syncing its issued credentials into Argo CD's cluster registration.
- [gitops-workflow](../../../devops/skills/gitops-workflow/SKILL.md) — the vendor-neutral GitOps concepts this on-prem runbook implements.
