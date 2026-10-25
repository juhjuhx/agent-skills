---
name: sealed-secrets-and-external-secrets-operator
description: >
  Guides deep, Kubernetes-native implementation of two GitOps-friendly
  secrets patterns — Bitnami Sealed Secrets (controller install,
  kubeseal CLI encryption workflow, the SealedSecret CRD) and External
  Secrets Operator (SecretStore/ClusterSecretStore/ExternalSecret CRDs
  syncing from Vault, AWS Secrets Manager, or Azure Key Vault into native
  Kubernetes Secrets). Use when the user asks to "encrypt a Kubernetes
  secret for git with kubeseal", "install the Sealed Secrets controller",
  "write a SealedSecret manifest", "set up External Secrets Operator",
  "configure a ClusterSecretStore for Vault/AWS/Azure", "sync an
  ExternalSecret from AWS Secrets Manager into a K8s Secret", or "choose
  between Sealed Secrets and External Secrets Operator for GitOps".
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: security-scanning-tooling
  maturity: stable
---

# Sealed Secrets and External Secrets Operator

## Purpose

GitOps workflows (Argo CD, Flux) want every cluster resource, including
secret-bearing ones, declared in git — but a native Kubernetes `Secret`
is only base64-encoded, not encrypted, so committing one directly is
equivalent to committing plaintext. Two Kubernetes-native controller
patterns solve this from opposite directions. **Bitnami Sealed
Secrets** lets you encrypt a secret *client-side* into a `SealedSecret`
custom resource that is safe to commit to git in plaintext-ciphertext
form; only the in-cluster controller (holding the matching private key)
can decrypt it back into a real `Secret`, so the encrypted manifest is
useless to anyone without cluster access. **External Secrets Operator
(ESO)** inverts the flow entirely: nothing secret-bearing is ever
committed to git at all — a lightweight `ExternalSecret` resource
declares *which* secret to fetch from an external system (Vault, AWS
Secrets Manager, Azure Key Vault, GCP Secret Manager, and others), and
the operator continuously syncs the real value from there into a native
`Secret` object at runtime. Both are Kubernetes-native, CRD-driven, and
GitOps-compatible; choosing between them (or using both) depends on
whether the org already has a centralized secrets manager to sync from
and whether the encrypted-blob-in-git model or the no-secret-in-git
model fits the team's operating model better.

## When to use

- The user wants to commit a Kubernetes `Secret` to a GitOps repo
  without exposing its plaintext value, and asks specifically about
  `kubeseal` or the Sealed Secrets controller.
- The user wants Kubernetes workloads to consume secrets that live in
  Vault, AWS Secrets Manager, Azure Key Vault, or GCP Secret Manager,
  synced automatically into native `Secret` objects, and asks about
  External Secrets Operator, `SecretStore`, or `ExternalSecret`.
- The user is deciding between Sealed Secrets and External Secrets
  Operator (or using both together) for a specific GitOps setup.
- The user needs to rotate a cluster's Sealed Secrets encryption
  keypair, or migrate SealedSecrets after a cluster rebuild where the
  original controller key was lost.
- The user needs to set up authentication from ESO to a backing secrets
  manager (Vault Kubernetes auth, AWS IRSA, Azure Workload Identity) so
  the operator can fetch secrets without its own long-lived credential.
- The user is troubleshooting a `SealedSecret` that won't decrypt, or an
  `ExternalSecret` stuck in a non-`SecretSynced` state.

## Prerequisites & environment

- A Kubernetes cluster with permission to install a cluster-scoped
  controller/CRDs (`SealedSecret`/`ExternalSecret`, `SecretStore`,
  `ClusterSecretStore`) — both projects ship as Helm charts.
- **Sealed Secrets**: the `kubeseal` CLI (must match the installed
  controller's major version — `kubeseal` and the controller are
  versioned together and a mismatch can cause decryption/encryption
  incompatibilities) and cluster access sufficient to fetch the
  controller's public certificate for offline encryption.
- **External Secrets Operator**: `>= 0.9` for stable
  `ClusterSecretStore` multi-tenant behavior; a backing secrets manager
  already populated with the real secret values (ESO syncs *from*
  Vault/AWS/Azure/GCP, it does not replace them), and a workload
  identity mechanism for the operator to authenticate to that backend —
  see [secrets-management](../../../devsecops/skills/secrets-management/SKILL.md)
  for the underlying secrets-manager setup and the general
  "why not hardcode secrets" rationale this skill assumes rather than
  restates.
- For cloud-backed `SecretStore`s: workload identity federation already
  configured (AWS IRSA / Azure Workload Identity / GCP Workload
  Identity) so ESO authenticates without a long-lived static credential
  — see
  [cloud-iam-hardening](../../../cloud/skills/cloud-iam-hardening/SKILL.md)
  for the federation setup this depends on.
- A GitOps controller (Argo CD/Flux) if the goal is committing
  `SealedSecret`/`ExternalSecret` manifests to a reconciled repo, though
  neither tool requires GitOps specifically — both work with plain
  `kubectl apply` too.

## Step-by-step guidance

### Sealed Secrets

1. **Install the controller** (Helm):
   ```bash
   helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
   helm install sealed-secrets-controller sealed-secrets/sealed-secrets \
     --namespace kube-system
   ```

2. **Fetch the controller's public certificate** for offline encryption
   (so `kubeseal` can encrypt without live cluster access, e.g. in a CI
   job that doesn't have cluster credentials):
   ```bash
   kubeseal --fetch-cert \
     --controller-name sealed-secrets-controller \
     --controller-namespace kube-system \
     > pub-cert.pem
   ```

3. **Create the plaintext Secret locally (never commit it)**, then
   seal it with `kubeseal`:
   ```bash
   kubectl create secret generic db-credentials \
     --namespace payments \
     --from-literal=username=svc-payments \
     --from-literal=password='<GENERATED_PASSWORD>' \
     --dry-run=client -o yaml > db-credentials.yaml

   kubeseal --format yaml --cert pub-cert.pem \
     < db-credentials.yaml > sealed-db-credentials.yaml

   rm db-credentials.yaml   # never commit the plaintext version
   ```
   Resulting `sealed-db-credentials.yaml` (safe to commit — ciphertext only):
   ```yaml
   apiVersion: bitnami.com/v1alpha1
   kind: SealedSecret
   metadata:
     name: db-credentials
     namespace: payments
   spec:
     encryptedData:
       username: AgBy3i4OJSWK+PiTySYZ...(ciphertext, truncated)...
       password: AgBy3i4OJSWK+PiTySYZ...(ciphertext, truncated)...
     template:
       metadata:
         name: db-credentials
         namespace: payments
       type: Opaque
   ```

4. **Commit and apply** — the controller watches for `SealedSecret`
   objects and decrypts them into a real `Secret` in the same namespace
   automatically:
   ```bash
   git add sealed-db-credentials.yaml
   kubectl apply -f sealed-db-credentials.yaml
   kubectl get secret db-credentials -n payments   # controller-created, decrypted
   ```

5. **Scope encryption to a namespace/name by default** — Sealed
   Secrets' default scope binds ciphertext to the target namespace and
   secret name, so the same ciphertext can't be copy-pasted into a
   different namespace and decrypted there. Use the broader
   `cluster-wide` or `namespace-wide` scope annotations only when a
   genuine cross-namespace reuse case exists, since it weakens this
   binding:
   ```bash
   kubeseal --scope namespace-wide --format yaml --cert pub-cert.pem \
     < db-credentials.yaml > sealed-db-credentials.yaml
   ```

6. **Back up the controller's private key** immediately after install
   and store it in a proper secrets manager/offline vault — losing it
   makes every previously-sealed secret permanently undecryptable:
   ```bash
   kubectl get secret -n kube-system \
     -l sealedsecrets.bitnami.com/sealed-secrets-key \
     -o yaml > sealed-secrets-key-backup.yaml
   ```
   Restore onto a rebuilt cluster by applying this backed-up key
   *before* the controller starts, so it reuses the same keypair rather
   than generating a new one.

### External Secrets Operator

7. **Install the operator** (Helm):
   ```bash
   helm repo add external-secrets https://charts.external-secrets.io
   helm install external-secrets external-secrets/external-secrets \
     --namespace external-secrets --create-namespace
   ```

8. **Define a `ClusterSecretStore`** pointing at the backing secrets
   manager, authenticating via workload identity rather than a static
   credential wherever the backend supports it. AWS Secrets Manager
   example (IRSA-based auth):
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: ClusterSecretStore
   metadata:
     name: aws-secrets-manager
   spec:
     provider:
       aws:
         service: SecretsManager
         region: us-east-1
         auth:
           jwt:
             serviceAccountRef:
               name: external-secrets-sa
               namespace: external-secrets
   ```
   Vault example (Kubernetes auth method):
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: ClusterSecretStore
   metadata:
     name: vault-backend
   spec:
     provider:
       vault:
         server: "https://vault.example.internal:8200"
         path: "myapp"
         version: "v2"
         auth:
           kubernetes:
             mountPath: "kubernetes"
             role: "payments-prod"
             serviceAccountRef:
               name: external-secrets-sa
               namespace: external-secrets
   ```
   Azure Key Vault example (Workload Identity):
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: ClusterSecretStore
   metadata:
     name: azure-keyvault
   spec:
     provider:
       azurekv:
         authType: WorkloadIdentity
         vaultUrl: "https://example-kv.vault.azure.net"
         serviceAccountRef:
           name: external-secrets-sa
           namespace: external-secrets
   ```

9. **Declare an `ExternalSecret`** per workload, referencing the store
   and the specific remote key(s) to sync:
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: ExternalSecret
   metadata:
     name: db-credentials
     namespace: payments
   spec:
     refreshInterval: 1h
     secretStoreRef:
       name: aws-secrets-manager
       kind: ClusterSecretStore
     target:
       name: db-credentials      # the native Secret ESO creates/updates
       creationPolicy: Owner
     data:
       - secretKey: username
         remoteRef:
           key: prod/payments/db
           property: username
       - secretKey: password
         remoteRef:
           key: prod/payments/db
           property: password
   ```

10. **Use a namespaced `SecretStore` instead of `ClusterSecretStore`**
    when different teams/namespaces should have independently-scoped
    credentials/paths to the backend, rather than one shared
    cluster-wide store everyone implicitly trusts.

11. **Verify sync status** rather than assuming success — ESO surfaces
    condition status on the `ExternalSecret` resource itself:
    ```bash
    kubectl get externalsecret db-credentials -n payments
    # NAME             STORE                  REFRESH INTERVAL   STATUS         READY
    # db-credentials   aws-secrets-manager    1h                 SecretSynced   True
    ```

12. **Set `refreshInterval` deliberately** — short intervals (e.g.
    `1m`) keep the cluster copy closer to real-time but add load on the
    backend API and its rate limits; longer intervals (e.g. `1h`) are
    usually sufficient since rotation events can also trigger an
    immediate re-sync via ESO's push-based reconciliation on backend
    change where the provider supports it.

## Best practices

- Never commit the plaintext `Secret` manifest used as `kubeseal`'s
  input, even momentarily, to a git-tracked working directory — generate
  it to a local, gitignored path, seal it, then delete the plaintext
  file immediately.
- Back up the Sealed Secrets controller's private key the moment it's
  created and store it in a real secrets manager (not another
  git-committed file) — this is the single most consequential Sealed
  Secrets operational step, since key loss makes every previously
  committed `SealedSecret` permanently unrecoverable.
- Prefer External Secrets Operator over Sealed Secrets when the
  organization already runs a centralized secrets manager (Vault, cloud
  secret manager) — ESO avoids putting even ciphertext of a secret in
  git and centralizes rotation/audit in the system of record; prefer
  Sealed Secrets when there's no centralized secrets manager and the
  goal is specifically "make Kubernetes Secrets git-committable" with
  minimal additional infrastructure.
- Authenticate ESO to its backend with workload identity (IRSA, Azure
  Workload Identity, GCP Workload Identity, or Vault's Kubernetes auth
  method) rather than a static access key/service-account key stored as
  a Kubernetes Secret feeding the very operator meant to eliminate that
  pattern — see
  [cloud-iam-hardening](../../../cloud/skills/cloud-iam-hardening/SKILL.md).
- Scope `SealedSecret` ciphertext to namespace (default) rather than
  cluster-wide unless there's a genuine cross-namespace need, and scope
  `SecretStore` (namespaced) over `ClusterSecretStore` when different
  teams should not implicitly share one trust boundary to the backend.
- Set `creationPolicy: Owner` on `ExternalSecret` targets so ESO
  manages the full lifecycle of the generated `Secret` (including
  cleanup when the `ExternalSecret` is deleted), and avoid manually
  editing the generated `Secret` directly since ESO will overwrite it on
  the next sync.
- Combine both patterns where useful: some teams use Sealed Secrets for
  a small number of cluster-bootstrap secrets needed before any
  external secrets manager integration is even running, and ESO for
  everything else once the cluster is up.

## Common pitfalls

- **Symptom:** A cluster is rebuilt (or the Sealed Secrets controller is
  reinstalled) and every previously-committed `SealedSecret` fails to
  decrypt, with the controller logging a decryption error.
  **Fix:** The controller generated a *new* keypair on install instead
  of reusing the original one. Restore the backed-up controller private
  key (step 6) *before* the new controller starts for the first time,
  or if the key truly is lost, every affected secret must be re-sealed
  from its original plaintext value against the new public certificate
  — this is unrecoverable otherwise, which is why the backup step is
  not optional.

- **Symptom:** A `SealedSecret` that worked fine in namespace `payments`
  fails to decrypt after being copy-pasted into namespace `payments-staging`
  for a "quick" environment clone.
  **Fix:** This is by design — default scope binds ciphertext to the
  exact namespace and secret name it was sealed for, so it cannot be
  reused elsewhere. Re-seal a fresh copy targeting the new namespace, or
  use `--scope namespace-wide`/`cluster-wide` deliberately (with the
  understanding that this weakens the binding) if genuine reuse across
  namespaces is required.

- **Symptom:** An `ExternalSecret` stays stuck showing `SecretSynced:
  False` and the target `Secret` never appears.
  **Fix:** Check the `ExternalSecret`'s status conditions and the ESO
  controller logs first (`kubectl describe externalsecret ... ` and
  `kubectl logs -n external-secrets deploy/external-secrets`) — the
  most common causes are the `SecretStore`/`ClusterSecretStore`
  authentication failing (workload identity misconfigured, wrong
  Vault role/policy) or the `remoteRef.key`/`property` not matching
  what actually exists in the backend; verify the backend path/key
  directly with the backend's own CLI before assuming ESO is broken.

- **Symptom:** `kubeseal` on a developer's laptop produces a
  `SealedSecret` that the in-cluster controller rejects or fails to
  decrypt, despite following the same steps that worked last month.
  **Fix:** A `kubeseal` CLI version mismatch against the controller's
  version, or an outdated cached public certificate, is the most common
  cause. Re-fetch the certificate (`kubeseal --fetch-cert`, step 2)
  rather than reusing a locally cached one, and confirm the `kubeseal`
  CLI major version matches the deployed controller's.

- **Symptom:** A workload's `Secret` (created by ESO) doesn't reflect a
  password that was just rotated in the backing secrets manager, and
  the pod keeps failing auth with the old value.
  **Fix:** Either `refreshInterval` hasn't elapsed yet (ESO polls, it
  doesn't necessarily push instantly unless the provider supports
  event-driven sync), or the *application* itself cached the old value
  in memory/a connection pool and hasn't reloaded it — force an ESO
  re-sync (annotate/touch the `ExternalSecret` to trigger reconciliation)
  and separately confirm the application has a mechanism to pick up an
  updated mounted/env secret (restart, file-watch reload, or short
  connection-pool lifetime), mirroring the same rotation-propagation
  problem general secrets-manager rotation has.

## Worked example

A team GitOps-manages a `payments` namespace with Argo CD. They use
Sealed Secrets for one bootstrap TLS secret needed before anything else
starts, and External Secrets Operator synced from AWS Secrets Manager
for all application runtime secrets.

Bootstrap secret, sealed once and committed:
```bash
kubectl create secret tls bootstrap-tls \
  --namespace payments \
  --cert=bootstrap.crt --key=bootstrap.key \
  --dry-run=client -o yaml \
  | kubeseal --format yaml --cert pub-cert.pem \
  > sealed-bootstrap-tls.yaml
```

Application secrets, via ESO (`ClusterSecretStore` from step 8's AWS
example, plus this `ExternalSecret`):
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: payments-db-credentials
  namespace: payments
spec:
  refreshInterval: 30m
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: payments-db-credentials
    creationPolicy: Owner
  data:
    - secretKey: connection-string
      remoteRef:
        key: prod/payments/db
        property: connection_string
```

Argo CD `Application` manifest points at the repo path containing both
`sealed-bootstrap-tls.yaml` (safe ciphertext) and the `ExternalSecret`/
`ClusterSecretStore` YAML (contains no secret material at all, just
references) — neither file, if leaked, exposes a usable credential:
the sealed one requires the cluster's private key to decrypt, and the
ExternalSecret one is just a pointer requiring the operator's live
workload-identity-authenticated access to AWS Secrets Manager.

Result: `git log` on this repo shows every secret-related change (a
`SealedSecret` update, or an `ExternalSecret`'s `remoteRef` pointing at
a new key) without ever having exposed a plaintext credential in git
history, satisfying both the GitOps "everything in git" requirement and
the "no plaintext secrets in git" requirement simultaneously.

## Cross-references

- [secrets-management](../../../devsecops/skills/secrets-management/SKILL.md) —
  the underlying "why not hardcode secrets" rationale, secrets-manager
  selection (Vault/cloud/SOPS), and rotation/response workflow this
  skill assumes and builds the Kubernetes-native sync/encryption layer
  on top of.
- [cloud-iam-hardening](../../../cloud/skills/cloud-iam-hardening/SKILL.md) —
  the workload identity federation (IRSA, Workload Identity) that
  External Secrets Operator should authenticate to its backend with,
  instead of a static credential.
- [trivy-vulnerability-scanning](../trivy-vulnerability-scanning/SKILL.md) —
  Trivy's secret-scanner mode can catch an accidentally-plaintext
  Kubernetes `Secret` committed alongside `SealedSecret`/`ExternalSecret`
  manifests as a safety net.
- [sysdig-secure-runtime-security](../sysdig-secure-runtime-security/SKILL.md) —
  runtime detection can flag unexpected in-cluster access to secret
  material (e.g. an unusual process reading a mounted secret volume)
  as a complementary, after-the-fact control.
