---
name: kubernetes-network-policy-zero-trust
description: >
  Guides implementing zero-trust network segmentation in Kubernetes using
  native NetworkPolicy resources and, where a Calico CNI is in use,
  Calico-specific GlobalNetworkPolicy for cluster-wide default-deny and
  tiered policy. Use when a user asks to "write a NetworkPolicy", "set up
  default-deny networking in Kubernetes", "restrict pod-to-pod traffic",
  "implement zero-trust segmentation in a cluster", "allow a namespace to
  reach only specific services", or "debug why a NetworkPolicy is
  blocking traffic it shouldn't."
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: observability-and-platform-extras
  maturity: stable
---

# Kubernetes NetworkPolicy Zero Trust

## Purpose

By default, every pod in a Kubernetes cluster can reach every other pod
— there is no network segmentation unless it's explicitly configured.
That default is convenient for getting a cluster running and dangerous
in production: a single compromised or vulnerable pod can reach any
other workload's ports, including internal admin endpoints, databases,
and the Kubernetes API server itself, with no additional access
required. `NetworkPolicy` resources implement zero-trust micro-
segmentation inside the cluster: deny all traffic by default, then
explicitly allow only the specific pod-to-pod and pod-to-external
paths a workload actually needs. This requires a CNI plugin that
enforces `NetworkPolicy` (Calico, Cilium, and several others do;
Flannel alone does not, without an add-on), and — critically — it
requires allow-rules to exist *before or simultaneously with* any
default-deny policy, since applying default-deny alone, cluster-wide,
with no allow-rules yet written, silently breaks all traffic including
DNS resolution and health checks. This skill covers writing correct,
minimal `NetworkPolicy` and Calico `GlobalNetworkPolicy` resources
safely; it assumes the CNI itself (Calico vs. Flannel, and whether
`NetworkPolicy` enforcement is even active) is already chosen — see the
CNI-specific skill referenced below for that layer.

## When to use

- Establishing default-deny network segmentation for a namespace or
  cluster as a zero-trust baseline.
- Writing an allow-rule so a specific service can reach only the
  database, cache, or upstream API it actually depends on — nothing
  else.
- Restricting egress so workloads cannot reach the public internet (or
  the cloud metadata endpoint) except through an explicitly allowed
  path.
- Debugging unexpected connection refused/timeout errors that appear
  only after a `NetworkPolicy` was applied.
- Implementing cluster-wide, tiered policy (e.g. "no namespace may ever
  bypass this baseline policy, even with its own permissive
  NetworkPolicy") using Calico's `GlobalNetworkPolicy` and tiers, which
  plain Kubernetes `NetworkPolicy` cannot express.
- Auditing an existing cluster for namespaces with no `NetworkPolicy`
  at all (fully open) as part of a security review.

## Prerequisites & environment

- A CNI plugin that **enforces** `NetworkPolicy` — Calico, Cilium, and
  most managed-Kubernetes default CNIs on EKS (with the AWS VPC CNI's
  NetworkPolicy support, or Calico add-on), AKS (Azure CNI with Calico
  or Cilium enforcement), and GKE (Dataplane V2/Cilium-based). Plain
  Flannel does **not** enforce `NetworkPolicy` on its own — confirm
  enforcement is actually active before assuming a written
  `NetworkPolicy` does anything (`kubectl` will happily accept and
  store a `NetworkPolicy` object even if nothing enforces it).
- Understanding of which pods are DNS servers (usually CoreDNS in
  `kube-system`) and API server addresses, since default-deny egress
  policies must explicitly allow DNS (UDP/TCP 53) and, where needed,
  Kubernetes API access, or workloads will fail in ways that look
  unrelated to networking (e.g. a pod hangs on startup because it can't
  resolve a Service DNS name).
- A namespace-level or cluster-level rollout plan — apply default-deny
  and allow-rules together, in the same change, never as two separate
  steps with a gap in between.
- For Calico-specific `GlobalNetworkPolicy`/tiers: Calico installed as
  the CNI (or as a policy-only layer on top of another CNI's dataplane,
  e.g. Calico for policy + a different CNI for networking) — these CRDs
  don't exist without Calico specifically. See
  [cni-networking-calico-flannel](../../../kubernetes-platform/skills/cni-networking-calico-flannel/SKILL.md)
  for choosing and installing the CNI layer itself.

## Step-by-step guidance

1. **⚠️ Warning — never apply a bare default-deny policy to a
   namespace or cluster without allow-rules ready in the same
   change.** A `NetworkPolicy` that selects all pods and specifies no
   `ingress`/`egress` rules denies **all** matching traffic, including
   DNS and existing healthy connections — apply it together with the
   allow-rules below, or roll it out gradually per-namespace with
   allow-rules already validated in a lower environment first.

2. **Start with a default-deny-all baseline** for a namespace,
   covering both ingress and egress:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: default-deny-all
     namespace: payments
   spec:
     podSelector: {}        # selects all pods in the namespace
     policyTypes:
       - Ingress
       - Egress
   ```

3. **Immediately pair it with an allow-DNS egress rule** — without
   this, every pod in the namespace loses DNS resolution the moment
   default-deny takes effect:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: allow-dns-egress
     namespace: payments
   spec:
     podSelector: {}
     policyTypes:
       - Egress
     egress:
       - to:
           - namespaceSelector:
               matchLabels:
                 kubernetes.io/metadata.name: kube-system
             podSelector:
               matchLabels:
                 k8s-app: kube-dns
         ports:
           - protocol: UDP
             port: 53
           - protocol: TCP
             port: 53
   ```

4. **Add explicit, narrow allow-rules per workload dependency** rather
   than one broad rule for the namespace:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: payments-api-allow
     namespace: payments
   spec:
     podSelector:
       matchLabels:
         app: payments-api
     policyTypes:
       - Ingress
       - Egress
     ingress:
       - from:
           - namespaceSelector:
               matchLabels:
                 kubernetes.io/metadata.name: ingress-nginx
             podSelector:
               matchLabels:
                 app.kubernetes.io/name: ingress-nginx
         ports:
           - protocol: TCP
             port: 8443
     egress:
       - to:
           - podSelector:
               matchLabels:
                 app: payments-db
         ports:
           - protocol: TCP
             port: 5432
   ```
   This allows `payments-api` to receive traffic only from the ingress
   controller on port 8443, and to reach only `payments-db` on 5432 —
   nothing else, including other pods in the same namespace.

5. **Restrict egress to the public internet/cloud metadata endpoint**
   explicitly where a workload has no legitimate need to reach it — in
   particular, always block the cloud metadata IP
   (`169.254.169.254`) for workloads that don't need instance-role
   credentials, since it's a common SSRF/pivot target:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: block-metadata-egress
     namespace: payments
   spec:
     podSelector: {}
     policyTypes:
       - Egress
     egress:
       - to:
           - ipBlock:
               cidr: 0.0.0.0/0
               except:
                 - 169.254.169.254/32
   ```
   Combine with the narrower allow-rules above (`NetworkPolicy`
   ingress/egress rules are additive/union across all policies
   selecting a pod — there is no explicit "deny" rule, only the
   absence of an "allow").

6. **For cluster-wide, non-bypassable baseline policy, use Calico's
   `GlobalNetworkPolicy` with tiers** (requires Calico as CNI or policy
   layer) — this covers what plain `NetworkPolicy` cannot express: a
   policy that applies across all namespaces and cannot be overridden
   by a namespace's own more-permissive `NetworkPolicy`:
   ```yaml
   apiVersion: projectcalico.org/v3
   kind: GlobalNetworkPolicy
   metadata:
     name: default-deny-cluster-baseline
   spec:
     tier: security-baseline
     order: 100
     selector: all()
     types:
       - Ingress
       - Egress
     ingress:
       - action: Allow
         protocol: TCP
         source:
           selector: k8s-app == 'kube-dns'
     egress:
       - action: Allow
         protocol: UDP
         destination:
           ports: [53]
       - action: Allow
         protocol: TCP
         destination:
           ports: [53]
   ```
   Calico tiers are evaluated in `order` before namespace-scoped
   `NetworkPolicy`/Calico `NetworkPolicy` objects, so a
   `security-baseline` tier policy (e.g. "never allow egress to
   0.0.0.0/0 without an explicit exception") holds even if an
   individual team writes an overly permissive namespace-level policy
   later.

7. **Test in a lower environment before rolling default-deny into
   production**, and roll out namespace-by-namespace rather than
   cluster-wide in one shot — start with the namespace least likely to
   break something customer-facing, validate, then proceed.

8. **Verify enforcement, not just that the object was accepted.**
   `kubectl apply` on a `NetworkPolicy` succeeds even on a CNI that
   doesn't enforce it. Confirm with a connectivity test
   (e.g. `kubectl exec` into a pod and attempt a curl/nc to a
   supposedly-blocked target) rather than assuming the manifest is
   doing anything.

9. **Debug unexpected blocks** by listing every `NetworkPolicy`
   selecting the affected pod (`kubectl get networkpolicy -n
   <namespace>` plus checking `podSelector` matches) — remember rules
   across multiple policies selecting the same pod are additive
   (union), so a missing allow-rule, not a wrong deny-rule, is almost
   always the actual cause.

## Best practices

- **Roll out default-deny with allow-rules in the same change, never
  as separate steps**, and always namespace-by-namespace rather than
  cluster-wide in one shot for an existing production cluster.
- **Always explicitly allow DNS egress (UDP/TCP 53 to
  kube-system/kube-dns) in every default-deny namespace** — this is the
  single most common self-inflicted outage from adopting
  `NetworkPolicy`.
- **Write the narrowest allow-rule that satisfies the real dependency**
  (specific `podSelector` + specific port), not a broad
  `namespaceSelector: {}` with no pod selector or port restriction —
  the latter defeats the purpose of zero-trust segmentation.
- **Block the cloud metadata endpoint (`169.254.169.254`) by default**
  for workloads that don't need instance-role credentials — it's one
  of the highest-value single rules for limiting SSRF/pivot blast
  radius.
- **Use Calico `GlobalNetworkPolicy` with tiers for anything that must
  never be bypassable by a namespace owner's own policy** — plain
  `NetworkPolicy` has no precedence/override concept; every matching
  policy is purely additive, so there's no way to express "this rule
  always wins" without a tiered-policy CNI feature.
- **Label namespaces and pods consistently** (e.g.
  `kubernetes.io/metadata.name` for namespace selection, a standard
  `app`/`app.kubernetes.io/name` label for pod selection) — inconsistent
  labeling is the most common reason an intended allow-rule silently
  doesn't match.
- **Test policy changes against a real connectivity check**, not just
  `kubectl apply` succeeding — the object being accepted proves nothing
  about enforcement or correctness.
- **Treat `NetworkPolicy` as one layer of defense-in-depth**, not a
  replacement for authentication/authorization at the application
  layer (mTLS via a service mesh, API-level auth) — network
  segmentation limits blast radius, it doesn't substitute for identity-
  based access control.

## Common pitfalls

- **Symptom:** Immediately after applying a default-deny
  `NetworkPolicy` to a namespace, every pod in it starts failing with
  DNS resolution errors or connection timeouts, including to services
  that were working fine moments before.
  **Fix:** Default-deny was applied without a corresponding allow-DNS-
  egress rule (and possibly without any other allow-rules) in the same
  change. **This is the most damaging and most common mistake with
  NetworkPolicy** — always apply default-deny and its required
  allow-rules (starting with DNS) together, never default-deny alone
  "to be added to later."

- **Symptom:** A `NetworkPolicy` is applied, `kubectl get networkpolicy`
  shows it, but traffic that should be blocked still gets through.
  **Fix:** The CNI in use doesn't enforce `NetworkPolicy` at all (e.g.
  plain Flannel without a policy add-on), so the object is stored but
  has no effect. Confirm the CNI actively enforces `NetworkPolicy`
  before treating written policies as real controls — see
  [cni-networking-calico-flannel](../../../kubernetes-platform/skills/cni-networking-calico-flannel/SKILL.md).

- **Symptom:** An allow-rule was written for a specific service, but
  the connection is still blocked.
  **Fix:** The `podSelector`/`namespaceSelector` labels in the policy
  don't actually match the target pod/namespace's real labels (e.g.
  the policy uses `namespace: ingress-nginx` as a bare string instead
  of the correct `namespaceSelector.matchLabels` with
  `kubernetes.io/metadata.name`, which Kubernetes doesn't support as a
  literal namespace-name field). Verify actual labels with
  `kubectl get pods --show-labels`/`kubectl get ns --show-labels`
  rather than assuming selector syntax matches intent.

- **Symptom:** A namespace has a strict default-deny policy, but a
  team applies their own `NetworkPolicy` allowing broad egress to
  0.0.0.0/0, defeating the intended baseline, and nobody notices for
  weeks.
  **Fix:** Plain Kubernetes `NetworkPolicy` has no precedence model —
  every applicable policy is purely additive, so a permissive rule
  from any policy immediately widens access regardless of other
  stricter policies. If a non-bypassable baseline is required, enforce
  it via Calico `GlobalNetworkPolicy` in a higher-order tier (step 6),
  and audit namespace-level policies on a schedule for accidental
  over-broad rules in the meantime.

- **Symptom:** Egress is blocked to the internet, but a compromised pod
  can still reach the cloud provider's instance-metadata endpoint and
  exfiltrate node/instance credentials.
  **Fix:** The egress default-deny/allow-list didn't explicitly exclude
  `169.254.169.254` from any broad "allow egress to 0.0.0.0/0" rule.
  Add the `except: [169.254.169.254/32]` exclusion (step 5) to every
  broad egress-allow rule, and prefer scoping IAM/instance-role
  permissions tightly regardless (defense in depth), rather than
  relying on network policy alone to protect metadata access.

## Worked example

**Scenario:** The `payments` namespace currently has no `NetworkPolicy`
at all — every pod in the cluster can reach `payments-db` and
`payments-api` directly. A security review flags this as a zero-trust
gap ahead of a compliance audit, and the team needs default-deny
segmentation without breaking the ingress path or DNS.

1. In a staging cluster first, apply the default-deny-all policy (step
   2) and the allow-DNS-egress policy (step 3) **in the same commit/
   change**, and confirm pods can still resolve internal Service DNS
   names via `kubectl exec ... -- nslookup payments-db.payments.svc`.
2. Add the `payments-api-allow` policy (step 4): ingress only from the
   `ingress-nginx` namespace's ingress-controller pods on port 8443,
   egress only to `payments-db` on port 5432.
3. Add a matching `payments-db-allow` policy: ingress only from pods
   labeled `app: payments-api` on port 5432, no egress rule at all
   (the database doesn't need to initiate outbound connections).
4. Add the `block-metadata-egress` broad-egress rule (step 5) for any
   pod that might otherwise reach `0.0.0.0/0`, explicitly excluding
   `169.254.169.254`.
5. Validate in staging: confirm the ingress path still works
   end-to-end (external request → ingress-nginx → payments-api →
   payments-db), and confirm a test pod in a different namespace can
   no longer reach `payments-db:5432` directly.
6. Roll the same four policies out to production namespace-by-namespace
   (not cluster-wide in one shot), starting with a lower-traffic
   internal namespace before `payments` itself, monitoring error rates
   during each rollout step.
7. For the compliance requirement that this baseline can never be
   silently widened by a future namespace-level policy change, add a
   Calico `GlobalNetworkPolicy` (step 6) in a `security-baseline` tier
   enforcing the metadata-endpoint block and default DNS-only egress
   cluster-wide, so even a future overly permissive namespace
   `NetworkPolicy` cannot reopen access to the metadata endpoint.

## Cross-references

- [prometheus-and-grafana-monitoring-stack](../prometheus-and-grafana-monitoring-stack/SKILL.md)
- [velero-backup-and-restore](../velero-backup-and-restore/SKILL.md)
- [cni-networking-calico-flannel](../../../kubernetes-platform/skills/cni-networking-calico-flannel/SKILL.md)
