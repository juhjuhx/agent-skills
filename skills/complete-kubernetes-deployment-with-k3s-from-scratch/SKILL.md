---
name: complete-kubernetes-deployment-with-k3s-from-scratch
description: >
  Sequences a complete K3s deployment from bare hosts (edge, on-prem VM,
  or dev/CI) to a production-ready lightweight cluster serving a first
  workload — topology/datastore choice, bundled Flannel CNI (with the
  Calico alternative noted), built-in Traefik vs. ingress-nginx, K3s's
  ServiceLB vs. MetalLB, cert-manager sized to actual reachability,
  footprint-scaled conformance validation, and a first Helm/HelmChart-CRD
  workload. An integration skill sequencing existing tool-specific skills
  in the correct order and flagging their handoff points — it does not
  restate their internals. Use when a user asks to "deploy K3s from
  scratch," "stand up a lightweight Kubernetes cluster end to end," "set
  up K3s for an edge site/dev environment/CI runner," "build a production
  K3s cluster on bare metal," or "give me the full sequence to go from
  nothing to a working K3s cluster."
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: kubernetes-platform
  maturity: stable
---

# Complete Kubernetes Deployment with K3s From Scratch

## Purpose

K3s's whole value proposition is that most of a full Kubernetes stack
(CNI, Ingress, a LoadBalancer implementation, a datastore) ships bundled
and pre-decided — which means the end-to-end deployment sequence for K3s
looks different in kind, not just in vendor-specific detail, from EKS/
AKS/GKE/OKE or a self-managed kubeadm cluster: several phases that are
mandatory elsewhere (install a CNI, install an Ingress controller, solve
the bare-metal LoadBalancer problem) are instead "confirm the bundled
default is acceptable, or deliberately disable and replace it." Getting
this sequence wrong most commonly means either fighting K3s's own
defaults without realizing they're what's causing the odd behavior, or
skipping the datastore-HA decision entirely and discovering the
single-server control plane is a hard single point of failure only after
an outage. This skill sequences topology/datastore choice, the bundled
Flannel CNI, Traefik-vs-ingress-nginx, ServiceLB-vs-MetalLB, cert-manager
sized for the deployment's actual reachability, a scaled-down conformance
gate, and a first workload into one ordered path for K3s specifically.

## When to use

- Standing up a new K3s cluster from scratch for an edge site, an on-prem
  small-footprint deployment, or local/CI development, and needing the
  full sequence rather than just the single-node install command.
- Auditing an existing K3s deployment for an unresolved default (bundled
  Traefik and ingress-nginx both installed and fighting over Ingress
  objects; ServiceLB left active alongside a manually-installed MetalLB)
  or a skipped HA/backup decision.
- Deciding, deliberately and once, which of K3s's bundled defaults
  (Traefik, ServiceLB, local-path-provisioner, Flannel) to keep vs.
  replace for a specific deployment, then executing that decision in the
  right order.
- Rebuilding a reference K3s environment (a second edge site, a fleet
  template) that should follow the same sequence as a known-good first
  cluster.

## Prerequisites & environment

- One or more Linux hosts (K3s does not run as a server node on Windows/
  macOS) with root/sudo access and `curl` reachability to `get.k3s.io`, or
  a pre-staged air-gapped bundle for sites with no internet access.
- A decision, made before Phase 1, on whether this deployment needs
  control-plane HA at all — a single-server embedded-SQLite K3s cluster
  is a legitimate, deliberate choice for dev/CI/edge, not a default to
  fall into by skipping the decision.
- If the hosts are physical edge/on-prem equipment rather than VMs or CI
  runners, the inventory and out-of-band management discipline from
  [on-prem-infrastructure-patterns](../../../cloud/skills/on-prem-infrastructure-patterns/SKILL.md)
  applies before K3s installation begins.
- **No built-in cloud workload-identity mechanism.** Unlike EKS/AKS/GKE/
  OKE, K3s has no IRSA/Workload-Identity-Federation equivalent baked in —
  if a workload on this cluster needs to call a cloud provider's API,
  plan that credential path (a secrets manager, HashiCorp Vault, or a
  cloud-specific federation mechanism configured independently of K3s
  itself) as part of Phase 1, not as an assumption carried over from a
  managed-Kubernetes deployment.
- A registered DNS name and, if Let's Encrypt HTTP-01/DNS-01 is the TLS
  plan, either port 80 reachable from the internet or a DNS provider API
  credential — many K3s edge deployments have neither, which changes the
  Phase 5 decision materially (see that phase).
- `helm` ≥ 3.14 on a machine with `kubectl` access to the cluster.

## Step-by-step guidance

This is the phase sequence. Each phase links to the skill that covers its
full depth; the text here covers only K3s-specific sequencing and
integration decisions.

1. **Phase 1 — Decide topology and datastore before installing
   anything.** This is the single highest-leverage decision in the whole
   sequence and the hardest to change after the fact. See
   [lightweight-kubernetes-k3s](../lightweight-kubernetes-k3s/SKILL.md)
   for the full single-server-SQLite vs. multi-server-embedded-etcd vs.
   multi-server-external-datastore tradeoff. Decide explicitly which one
   this deployment needs based on its actual availability requirement,
   and — if HA — reserve a stable registration address (load balancer or
   DNS name) now, since it must be set as a TLS SAN from the very first
   server node.

2. **Phase 2 — Install K3s**, disabling bundled components deliberately
   rather than discovering the conflict later:
   ```bash
   # single-server (dev/edge/CI)
   curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644

   # multi-server HA with embedded etcd, Traefik/ServiceLB disabled up front
   # because Phase 4 will install ingress-nginx and MetalLB instead
   curl -sfL https://get.k3s.io | sh -s - server --cluster-init \
     --tls-san k3s-lb.internal.example.com \
     --disable traefik --disable servicelb
   ```
   Decide the Traefik/ServiceLB disable flags **in this phase**, at
   install time — re-disabling them on a running server requires a
   restart with changed flags and risks a brief window where both the
   bundled and replacement components are active simultaneously.

3. **Phase 3 — CNI: bundled Flannel by default.** K3s ships Flannel
   (VXLAN backend) pre-installed and running the moment a node joins —
   there is no separate "apply a CNI manifest" step the way a fresh
   kubeadm cluster requires. Confirm it's healthy:
   ```bash
   kubectl get pods -n kube-system -l app=flannel
   ```
   **Alternative:** if `NetworkPolicy` enforcement is required, Flannel's
   bundled default does not provide it — swap in Calico following
   [cni-networking-calico-flannel](../cni-networking-calico-flannel/SKILL.md),
   installed at `k3s server` startup via `--flannel-backend=none` plus a
   separate Calico install, decided in this phase rather than attempted
   as a live swap on a cluster with running workloads.

4. **Phase 4 — Ingress and the LoadBalancer story: Traefik/ServiceLB vs.
   ingress-nginx/MetalLB.** K3s bundles **both** an Ingress controller
   (Traefik) and a `LoadBalancer` Service implementation (**ServiceLB**,
   formerly "Klipper LB") by default — this is the biggest structural
   difference from every other skill in this sequence's family, since
   EKS/AKS/GKE/OKE need a cloud LB and on-prem kubeadm needs MetalLB, but
   K3s needs neither by default:
   - **Keep Traefik + ServiceLB** for the simplest possible edge/dev
     deployment — ServiceLB works by having each node that runs a
     matching pod bind the Service's port directly (closer to a
     `hostPort` trick than a real load balancer), which is adequate for
     small clusters but has no real load-spreading or health-aware
     failover the way MetalLB's BGP mode or a cloud LB does.
   - **Swap to ingress-nginx (see
     [ingress-nginx-configuration](../ingress-nginx-configuration/SKILL.md))
     and MetalLB (see
     [metallb-bare-metal-load-balancer-configuration](../metallb-bare-metal-load-balancer-configuration/SKILL.md))**
     when standardizing configuration across K3s and other on-prem/
     kubeadm clusters, or when ServiceLB's limitations (no real
     multi-node load spreading, coarse failover) are a real constraint —
     both must have been disabled in Phase 2 already, since re-disabling
     Traefik/ServiceLB after they're active can leave stale
     `IngressClass`/`Service` objects fighting the replacement.

5. **Phase 5 — cert-manager, sized to the deployment's actual
   reachability.** Install cert-manager per
   [cert-manager-tls-automation](../cert-manager-tls-automation/SKILL.md),
   but choose the issuance mechanism based on what this specific K3s
   deployment can actually reach — an edge site with no public IP and no
   port-80 ingress cannot use HTTP-01 at all, and may not have a
   DNS-provider API credential available either:
   - **Internet-reachable K3s (dev, CI, small public-facing on-prem
     site)**: Let's Encrypt HTTP-01 or DNS-01 exactly as documented in
     [cert-manager-tls-automation](../cert-manager-tls-automation/SKILL.md).
   - **Air-gapped or NAT'd edge sites with no public DNS-01 path**: a
     private/internal CA `Issuer` (cert-manager's self-signed root plus
     an intermediate `CA` Issuer, or an existing internal CA's key
     pair) is usually the only viable option — plan trust-bundle
     distribution to any client that must validate the resulting
     certificates, since there is no public CA trust to rely on.

6. **Phase 6 — Conformance and smoke validation, scaled to K3s's
   footprint.** Full CNCF `certified-conformance` is designed for
   clusters with real spare scheduling capacity — running it against a
   512MB-RAM edge device is likely to produce capacity-driven false
   failures rather than a meaningful conformance signal. See
   [kubernetes-cluster-post-provision-conformance-validation](../kubernetes-cluster-post-provision-conformance-validation/SKILL.md)
   for the base procedure, and adapt it for K3s:
   - Run **quick mode** on every K3s deployment, edge included — it's
     fast and low-resource enough to be a legitimate gate everywhere.
   - Run **full `certified-conformance`** only on a cluster with genuine
     spare capacity (a dev/CI K3s cluster, or a staging cluster built with
     the same config as the target edge fleet) rather than directly
     against a resource-constrained production edge device.
   - Always run the **targeted DNS/storage/ingress smoke tests**
     regardless of tier — these are cheap and catch the CNI/Ingress/CSI
     misconfigurations specific to whatever was decided in Phases 3–5.
   - If multi-server HA was chosen in Phase 1, add an etcd/datastore
     health check (member count, quorum) to this gate — see
     [etcd-backup-restore-and-cluster-health](../etcd-backup-restore-and-cluster-health/SKILL.md),
     which applies to K3s's embedded etcd exactly as it does to kubeadm's.

7. **Phase 7 — Deploy the first workload, via Helm or K3s's built-in
   HelmChart CRD.** Standard `helm upgrade --install` works exactly as
   [helm-chart-authoring](../helm-chart-authoring/SKILL.md) describes.
   K3s-specific alternative: its built-in Helm controller reconciles
   `HelmChart`/`HelmChartConfig` custom resources declaratively, useful
   for GitOps-style bootstrap of a chart at cluster creation time without
   a separate `helm` invocation:
   ```yaml
   apiVersion: helm.cattle.io/v1
   kind: HelmChart
   metadata:
     name: payments-api
     namespace: kube-system
   spec:
     chart: oci://ghcr.io/example/charts/payments-api
     version: 2.3.0
     targetNamespace: payments
     valuesContent: |-
       replicaCount: 2
   ```
   Prefer this path specifically when the chart install should be part of
   the same GitOps-applied manifest set as the rest of the cluster's
   bootstrap config; otherwise plain `helm` is simpler to reason about.

8. **Phase 8 — Node/cluster health baseline, including the datastore
   backup Phases 3–6 didn't finalize.** Establish node drain/cordon
   discipline via
   [kubernetes-node-maintenance-and-troubleshooting](../kubernetes-node-maintenance-and-troubleshooting/SKILL.md),
   and — unlike the managed-Kubernetes skills in this family — **actually
   schedule the datastore backup now**, since K3s's control plane is
   entirely self-managed regardless of topology:
   ```bash
   k3s etcd-snapshot save --name baseline-$(date +%F)   # embedded etcd (HA) only
   ```
   For single-server embedded-SQLite deployments, back up
   `/var/lib/rancher/k3s/server/db/state.db` directly (K3s's own
   `etcd-snapshot` command only covers the embedded-etcd path); for an
   external SQL datastore, back it up through that database's own
   tooling. See
   [etcd-backup-restore-and-cluster-health](../etcd-backup-restore-and-cluster-health/SKILL.md)
   for the restore procedure and quorum-monitoring detail this baseline
   depends on.

## Best practices

- Decide topology/datastore (Phase 1) and which bundled components to
  keep vs. disable (Phase 2) before the first `k3s server` command ever
  runs — both are far more disruptive to change once nodes have joined
  and workloads are scheduled.
- Never assume a managed-Kubernetes workload-identity pattern (IRSA,
  Azure AD Workload Identity, Workload Identity Federation) is available
  on K3s — if a workload needs cloud API access, design that credential
  path explicitly and independently in Phase 1.
- Scale conformance validation to the deployment's actual footprint
  (Phase 6) rather than either skipping it entirely on edge devices or
  forcing the full suite onto hardware it will simply fail against for
  capacity reasons unrelated to correctness.
- Schedule the datastore backup (Phase 8) as part of initial deployment,
  not as a follow-up task — K3s gives no managed-control-plane safety net
  the way EKS/AKS/GKE/OKE do.
- For edge fleets deploying the same K3s configuration repeatedly,
  encode Phases 2–5's decisions in a config file
  (`/etc/rancher/k3s/config.yaml`) rather than long, easy-to-typo CLI
  flag strings passed by hand at each site.

## Common pitfalls

- **Symptom:** Both Traefik and a separately installed ingress-nginx are
  active, and Ingress routing behaves unpredictably — some hosts route
  through one controller, some through the other.
  **Fix:** Traefik was never disabled in Phase 2 before ingress-nginx was
  installed in Phase 4. Disable Traefik at the K3s server level
  (`--disable traefik`, which typically requires reinstalling/restarting
  the server with the flag rather than a live toggle) and confirm no
  stray `IngressClass: traefik` resources remain claiming Ingress objects
  intended for `nginx`.

- **Symptom:** `LoadBalancer` Services get an `EXTERNAL-IP` from
  ServiceLB, but behavior differs confusingly from a MetalLB-based
  on-prem cluster running the "same" configuration elsewhere.
  **Fix:** ServiceLB and MetalLB are different mechanisms with different
  failover/load-spreading characteristics (see Phase 4) — this is
  expected once compared side by side, not a bug in either. If
  configuration parity across K3s and kubeadm/MetalLB clusters is the
  actual goal, disable ServiceLB and install MetalLB on K3s too rather
  than trying to make ServiceLB behave identically.

- **Symptom:** cert-manager's `Certificate` in Phase 5 never issues, and
  the `Challenge` resource shows the HTTP-01 solver's temporary pod is
  unreachable from Let's Encrypt's validation servers.
  **Fix:** Confirm the deployment's actual internet reachability was
  assessed honestly in Phase 5 before choosing HTTP-01 — a NAT'd or
  firewalled edge site with no inbound port 80 cannot complete an HTTP-01
  challenge no matter how correctly cert-manager itself is configured;
  switch to an internal CA `Issuer` instead of continuing to debug a
  network path that structurally cannot work.

- **Symptom:** A single-server K3s cluster's node goes offline for
  unrelated maintenance, and every `kubectl` command (and any GitOps
  reconciliation depending on API access) fails simultaneously.
  **Fix:** This is the expected consequence of the Phase 1 topology
  decision, not a new problem — a single-server cluster has no control-
  plane HA by design. If this outage class is unacceptable, the fix is
  revisiting Phase 1's topology choice (multi-server embedded etcd or
  external datastore) for this deployment, not patching around a single
  incident after the fact.

- **Symptom:** An edge device runs fine for months, then a K3s version
  upgrade corrupts or loses cluster state.
  **Fix:** Phase 8's datastore backup was scheduled as a "someday" task
  rather than actually configured at deployment time. Confirm
  `k3s etcd-snapshot save` (or the SQLite file backup / external-database
  backup, depending on Phase 1's topology) has been running on a real
  schedule with verified restorability before treating any upgrade as
  routine.

## Worked example

**Scenario:** Stand up a 3-node HA K3s cluster (embedded etcd) for a
regional edge site with intermittent-but-present internet connectivity,
swapping Traefik/ServiceLB for ingress-nginx/MetalLB to match the
company's on-prem kubeadm clusters, with Let's Encrypt DNS-01 (the site
has no reliably reachable inbound port 80) and a footprint-appropriate
validation gate.

```bash
# Phase 1/2 — server-1, HA topology decided, bundled components disabled up front
curl -sfL https://get.k3s.io | sh -s - server --cluster-init \
  --tls-san k3s-edge-lb.internal.example.com \
  --disable traefik --disable servicelb
sudo cat /var/lib/rancher/k3s/server/node-token   # shared join token

# server-2, server-3
curl -sfL https://get.k3s.io | sh -s - server \
  --server https://k3s-edge-lb.internal.example.com:6443 \
  --token <TOKEN_FROM_SERVER_1> --disable traefik --disable servicelb

# Phase 3 — bundled Flannel confirmed healthy (no NetworkPolicy requirement here)
kubectl get pods -n kube-system -l app=flannel

# Phase 4 — MetalLB + ingress-nginx instead of ServiceLB/Traefik
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.8/config/manifests/metallb-native.yaml
kubectl apply -f metallb-pool-and-l2advertisement.yaml
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.service.type=LoadBalancer

# Phase 5 — cert-manager with DNS-01 (no reliable inbound HTTP-01 path)
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace --version v1.15.1 --set crds.enabled=true
kubectl apply -f dns01-staging-issuer.yaml   # validate, then swap to prod

# Phase 6 — quick mode always; full conformance run against an identically-configured staging cluster, not this edge site directly
sonobuoy run --mode quick --wait && sonobuoy results "$(sonobuoy retrieve)"
kubectl run dns-check --image=busybox:1.36 --rm -it --restart=Never -- \
  nslookup kubernetes.default.svc.cluster.local

# Phase 7 — first workload via K3s's built-in HelmChart CRD
kubectl apply -f payments-api-helmchart.yaml

# Phase 8 — datastore backup and node health baseline
k3s etcd-snapshot save --name baseline-$(date +%F)
kubectl get nodes -o wide
```

`kubectl get nodes` shows all three server nodes `Ready` on separate
underlying hardware, `curl -I https://payments-edge.example.com` returns
`HTTP/2 200` with a production Let's Encrypt certificate issued via
DNS-01, and the etcd snapshot confirms the datastore backup discipline
from Phase 8 is active before the site is considered handed off.

## Cross-references

- [lightweight-kubernetes-k3s](../lightweight-kubernetes-k3s/SKILL.md) — full detail for Phase 1's topology/datastore decision and Phase 2's install flags.
- [on-prem-infrastructure-patterns](../../../cloud/skills/on-prem-infrastructure-patterns/SKILL.md) — inventory/out-of-band management discipline for physical edge hardware hosting K3s.
- [cni-networking-calico-flannel](../cni-networking-calico-flannel/SKILL.md) — the Calico alternative to K3s's bundled Flannel referenced in Phase 3.
- [ingress-nginx-configuration](../ingress-nginx-configuration/SKILL.md) — full detail for swapping Traefik for ingress-nginx in Phase 4.
- [metallb-bare-metal-load-balancer-configuration](../metallb-bare-metal-load-balancer-configuration/SKILL.md) — full detail for swapping ServiceLB for MetalLB in Phase 4.
- [cert-manager-tls-automation](../cert-manager-tls-automation/SKILL.md) — full detail for Phase 5's Issuer/Certificate setup, both the ACME and private-CA paths.
- [kubernetes-cluster-post-provision-conformance-validation](../kubernetes-cluster-post-provision-conformance-validation/SKILL.md) — the base validation procedure Phase 6 scales down for K3s's footprint.
- [etcd-backup-restore-and-cluster-health](../etcd-backup-restore-and-cluster-health/SKILL.md) — full detail for the embedded-etcd backup/restore/quorum-monitoring referenced in Phases 6 and 8.
- [helm-chart-authoring](../helm-chart-authoring/SKILL.md) — full detail for the standard `helm install` path in Phase 7.
- [kubernetes-node-maintenance-and-troubleshooting](../kubernetes-node-maintenance-and-troubleshooting/SKILL.md) — the ongoing operational baseline established in Phase 8.
