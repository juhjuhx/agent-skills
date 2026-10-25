---
name: lightweight-kubernetes-k3s
description: >
  Guides deploying K3s for edge, on-prem, and development Kubernetes —
  single-binary install, choosing the embedded SQLite/etcd datastore vs.
  an external database for HA, and sizing tradeoffs for resource-
  constrained nodes. Use when a user asks to "set up a lightweight
  Kubernetes cluster," "install K3s on a Raspberry Pi/edge device,"
  "run Kubernetes on a small VM for dev," "make K3s highly available,"
  or "decide between K3s and a full Kubernetes distribution."
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: kubernetes-platform
  maturity: stable
---

# Lightweight Kubernetes (K3s)

## Purpose

K3s packages a CNCF-conformant Kubernetes distribution into a single
binary under 100MB, with sane defaults (embedded containerd, an
embedded CNI, an embedded Ingress controller, and a lightweight
datastore option) that make it practical to run on resource-constrained
edge devices, small on-prem VMs, CI ephemeral clusters, and local
development — contexts where a full kubeadm/managed-cluster install is
either infeasible or excessive. The most consequential decision is the
datastore: the default embedded SQLite is fine for single-server
clusters but has no HA story, while embedded etcd (or an external SQL
database) is required for multi-server HA — picking the wrong one for
the deployment's actual availability requirement is the most common
K3s planning mistake. This skill covers installation, datastore choice,
and sizing.

## When to use

- Standing up Kubernetes on edge devices (industrial gateways, retail
  POS, IoT hubs) with limited CPU/RAM and often no reliable connectivity
  to a central control plane.
- Running Kubernetes on a small on-prem VM or bare-metal box where a
  full multi-node kubeadm cluster's control-plane overhead isn't
  justified.
- Local development or CI ephemeral clusters needing a fast-starting,
  low-resource Kubernetes (an alternative to kind/minikube with a closer-
  to-production single-binary distribution).
- Deciding whether a deployment needs single-server K3s (embedded
  SQLite), HA K3s (embedded etcd, 3+ server nodes), or a full managed/
  self-managed Kubernetes distribution instead.
- Sizing node resources and datastore choice for a specific number of
  worker nodes and pods.

## Prerequisites & environment

- K3s ≥ v1.30 (K3s version strings embed the Kubernetes version, e.g.
  `v1.30.4+k3s1` — track upstream Kubernetes support windows the same
  way as any other distribution).
- A Linux host (K3s does not run natively on Windows/macOS as a server
  node; use a Linux VM for those) with `curl` access to
  `get.k3s.io` (or a pre-downloaded binary/air-gapped bundle for edge
  sites with no internet access — K3s explicitly supports air-gapped
  installs via a bundled image tarball).
- For multi-server HA: either an external SQL datastore (MySQL,
  PostgreSQL, or the officially supported etcd-compatible options) or
  K3s's embedded etcd, plus a fixed registration address (a load
  balancer or DNS name, not a single server's IP) for agents to join
  through.
- Root/sudo on each node to install the `k3s`/`k3s-agent` systemd
  service.
- Minimum practical sizing: K3s itself targets devices with as little
  as 512MB RAM / 1 vCPU for the smallest edge use cases, but real
  workload capacity must be added on top of that floor — size nodes for
  the actual pods scheduled, not just the K3s baseline.

## Step-by-step guidance

1. **Decide the datastore/HA model before installing anything**:
   - **Single server, embedded SQLite (default)**: simplest, zero extra
     infrastructure, no HA — a lost server node loses the control plane
     (workloads already running keep running via kubelet, but no new
     scheduling/API access until the server returns). Appropriate for
     edge devices, dev, and CI.
   - **Multi-server, embedded etcd**: run `k3s server --cluster-init` on
     the first node and join additional server nodes to it; gives
     control-plane HA with no external database to operate, at the cost
     of etcd's own quorum requirements (need an odd number ≥ 3 server
     nodes to tolerate a single node loss).
   - **Multi-server, external datastore (MySQL/PostgreSQL)**: control
     plane HA backed by a database the team already operates/backs up
     — a reasonable choice when etcd operational expertise isn't
     available in-house but a managed/existing RDBMS is.

2. **Install a single-server cluster** (dev/edge/CI):
   ```bash
   curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644
   sudo cat /etc/rancher/k3s/k3s.yaml   # kubeconfig for this node
   ```

3. **Install an HA cluster with embedded etcd** (3 server nodes):
   ```bash
   # first server node
   curl -sfL https://get.k3s.io | sh -s - server --cluster-init \
     --tls-san k3s-lb.internal.example.com

   # subsequent server nodes join via a shared token
   curl -sfL https://get.k3s.io | sh -s - server \
     --server https://k3s-lb.internal.example.com:6443 \
     --token <TOKEN_FROM_FIRST_SERVER>
   ```
   `--tls-san` must include the load-balanced registration address so
   the server's TLS certificate validates for whatever hostname/IP
   agents and `kubectl` actually connect through — a missing SAN entry
   here is the most common HA setup failure.

4. **Join agent (worker) nodes**:
   ```bash
   curl -sfL https://get.k3s.io | K3S_URL=https://k3s-lb.internal.example.com:6443 \
     K3S_TOKEN=<TOKEN_FROM_FIRST_SERVER> sh -
   ```

5. **Disable bundled components you don't want**, since K3s ships
   opinionated defaults (Traefik as Ingress controller, a local-path
   storage provisioner, ServiceLB) that may conflict with a
   deliberately chosen alternative:
   ```bash
   curl -sfL https://get.k3s.io | sh -s - server \
     --disable traefik --disable servicelb
   ```
   Disable `traefik` if standardizing on
   [ingress-nginx-configuration](../ingress-nginx-configuration/SKILL.md)
   instead, and disable the bundled local-path provisioner if a
   different CSI/storage backend is required for the workload.

6. **Air-gapped/edge install** where the site has no direct internet
   access:
   ```bash
   # on a connected machine: download the binary + air-gap image tarball
   # for the target k3s version, then transfer both to the edge device
   sudo cp k3s /usr/local/bin/k3s
   sudo mkdir -p /var/lib/rancher/k3s/agent/images/
   sudo cp k3s-airgap-images-amd64.tar.gz /var/lib/rancher/k3s/agent/images/
   INSTALL_K3S_SKIP_DOWNLOAD=true sh install.sh
   ```

7. **Back up the datastore** regardless of which model is chosen — K3s
   has a built-in snapshot mechanism for the embedded etcd/SQLite
   datastore:
   ```bash
   k3s etcd-snapshot save --name pre-upgrade-snapshot
   k3s etcd-snapshot ls
   ```
   For an external SQL datastore, back it up through the database's own
   backup tooling instead — K3s's snapshot command only covers the
   embedded datastore path.

8. **Size nodes deliberately for the actual workload**, not just the
   K3s floor: start from expected pod count × typical
   request/limit, add the K3s/OS baseline (roughly 200–500MB RAM, well
   under 0.5 vCPU idle on a modest edge device, varying by enabled
   add-ons), and validate under real load rather than assuming the
   documented minimums include headroom for your workloads.

## Best practices

- Never run a production workload requiring control-plane HA on a
  single-server embedded-SQLite install "temporarily" without a
  concrete plan and timeline to move to multi-server etcd — the
  single-point-of-failure control plane is the single biggest
  availability gap teams underestimate with K3s.
- Set `--tls-san` for every registration hostname/IP the cluster will
  ever be reached through (including a future load balancer address)
  at initial server creation — regenerating server certificates to add
  a SAN later is more disruptive than including it up front.
- Explicitly decide and document which bundled components (Traefik,
  ServiceLB, local-path-provisioner) are kept vs. disabled per
  deployment, rather than leaving defaults in place and later
  discovering a conflict with a separately installed Ingress controller
  or storage class.
- Take an `etcd-snapshot` (or external-datastore backup) before every
  K3s version upgrade, not just on a periodic schedule — upgrades are
  the highest-risk moment for datastore-level issues.
- For edge fleets, standardize the install/join process
  (config file at `/etc/rancher/k3s/config.yaml` rather than long CLI
  flag strings) so provisioning is reproducible across many
  similar-but-not-identical devices.
- Treat K3s's smaller footprint as an operational simplification, not a
  security simplification — the same RBAC, NetworkPolicy, and
  image-provenance discipline used on a full cluster still applies.

## Common pitfalls

- **Symptom:** A single-server K3s cluster's node goes offline and
  every `kubectl` command starts failing, even though the workload pods
  were still technically running fine right before the outage.
  **Fix:** This is expected for a single-server (single control-plane)
  topology — there is no HA without multiple server nodes. If the
  workload has an actual availability requirement beyond "already-
  scheduled pods survive a control-plane blip," move to a 3-node
  embedded-etcd or external-datastore HA topology; a single-server
  cluster should be treated as dev/edge/non-critical by design, not
  patched around after the fact.

- **Symptom:** Joining a second/third server node for HA fails with a
  certificate validation or connection error against the registration
  address.
  **Fix:** The first server's `--tls-san` didn't include the
  load-balanced/DNS registration address used by the joining nodes.
  Regenerate the server's certificates with the correct `--tls-san`
  values (this does require a controlled restart) rather than pointing
  joining nodes at a raw IP that happens to work around the mismatch.

- **Symptom:** A workload's Ingress or LoadBalancer Service behaves
  unexpectedly differently than an equivalent setup on a full
  Kubernetes cluster.
  **Fix:** K3s ships Traefik and ServiceLB by default, which most teams
  don't run on their primary clusters — confirm whether the observed
  behavior comes from K3s's bundled defaults rather than a general
  Kubernetes behavior difference, and disable the bundled component
  (`--disable traefik`/`--disable servicelb`) if standardizing on a
  different Ingress/LB stack.

- **Symptom:** Upgrading K3s corrupts or loses cluster state on an
  embedded-datastore node.
  **Fix:** No pre-upgrade `etcd-snapshot`/datastore backup was taken.
  Always snapshot before an upgrade (`k3s etcd-snapshot save`) and
  confirm the snapshot's restorability in a non-production environment
  periodically — a snapshot mechanism that's never been test-restored
  is not a verified backup.

- **Symptom:** An edge device with severely constrained RAM starts
  evicting pods or the K3s agent itself becomes unstable under normal
  load.
  **Fix:** The device's total capacity was sized against K3s's
  documented minimums without headroom for the actual scheduled
  workload's requests/limits plus OS/K3s baseline overhead. Re-size
  using real observed usage (`kubectl top nodes`, `k3s check-config`)
  rather than the bare minimum figures quoted for K3s alone.

## Worked example

**Scenario:** Stand up a 3-node HA K3s cluster (embedded etcd) for a
regional edge site running a handful of lightweight services, with
Traefik disabled in favor of ingress-nginx, and a pre-upgrade backup
step included in the runbook.

```bash
# server-1
curl -sfL https://get.k3s.io | sh -s - server --cluster-init \
  --tls-san k3s-edge-lb.internal.example.com \
  --disable traefik --disable servicelb

sudo cat /var/lib/rancher/k3s/server/node-token   # shared join token
```

```bash
# server-2 and server-3
curl -sfL https://get.k3s.io | sh -s - server \
  --server https://k3s-edge-lb.internal.example.com:6443 \
  --token <TOKEN_FROM_SERVER_1> \
  --disable traefik --disable servicelb
```

```bash
# agent nodes
curl -sfL https://get.k3s.io | \
  K3S_URL=https://k3s-edge-lb.internal.example.com:6443 \
  K3S_TOKEN=<TOKEN_FROM_SERVER_1> sh -
```

```bash
kubectl get nodes -o wide     # 3 control-plane + N agent nodes, all Ready
k3s etcd-snapshot save --name baseline-$(date +%F)
```

Before the next K3s upgrade:

```bash
k3s etcd-snapshot save --name pre-upgrade-$(date +%F)
k3s etcd-snapshot ls
```

`kubectl get nodes` confirms all three server nodes report `Ready` and
are separate failure domains (verify they run on distinct underlying
hosts/hypervisors — etcd quorum tolerance is meaningless if all three
"nodes" share one physical failure point), giving the edge site a
control plane that survives the loss of any single server node.

## Cross-references

- [managed-kubernetes-eks-aks-gke](../managed-kubernetes-eks-aks-gke/SKILL.md) — the alternative when the deployment's scale/availability needs exceed what a self-operated K3s HA cluster comfortably provides.
- [helm-chart-authoring](../helm-chart-authoring/SKILL.md) — K3s ships a Helm controller (`HelmChart`/`HelmChartConfig` CRDs) for declaratively installing charts at cluster bootstrap time.
- [cni-networking-calico-flannel](../cni-networking-calico-flannel/SKILL.md) — K3s bundles Flannel by default; swapping in Calico for NetworkPolicy enforcement follows the same tradeoffs described there.
