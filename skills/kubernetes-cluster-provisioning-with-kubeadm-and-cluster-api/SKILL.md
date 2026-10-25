---
name: kubernetes-cluster-provisioning-with-kubeadm-and-cluster-api
description: >
  Guides bootstrapping self-managed/bare-metal Kubernetes clusters with
  kubeadm — `kubeadm init`/`kubeadm join`, stacked vs. external etcd,
  control-plane HA behind a load balancer/VIP — and managing cluster
  lifecycle declaratively and provider-agnostically with Cluster API
  (CAPI): `Cluster`, `KubeadmControlPlane`, and `MachineDeployment`
  objects reconciled by `clusterctl`-installed controllers. Use when a
  user asks to "bootstrap a Kubernetes cluster with kubeadm," "set up an
  HA control plane with kubeadm," "join a node to a kubeadm cluster,"
  "upgrade a kubeadm cluster," "manage clusters declaratively with
  Cluster API," "write a CAPI Cluster/KubeadmControlPlane manifest," or
  "provision bare-metal Kubernetes without a managed control plane."
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: kubernetes-platform
  maturity: stable
---

# Kubernetes Cluster Provisioning with kubeadm and Cluster API

## Purpose

Not every cluster runs on a managed control plane or a single-binary
lightweight distribution: bare-metal fleets, on-prem data centers, and
teams that need full control over control-plane composition still
bootstrap clusters directly with **kubeadm** — the upstream, vendor-
neutral tool for `init`/`join` that every managed and lightweight
distribution builds on internally. kubeadm bootstraps one cluster at a
time imperatively; **Cluster API (CAPI)** sits a layer above it,
turning cluster lifecycle itself into a Kubernetes-native, declarative,
provider-agnostic resource (a `Cluster` and its `KubeadmControlPlane`/
`MachineDeployment` objects reconciled continuously, the same
CRD-plus-controller pattern used elsewhere in the ecosystem) so that
provisioning, scaling, and upgrading many clusters follows one
consistent, GitOps-able workflow regardless of the underlying
infrastructure provider. This skill covers both: kubeadm for the
single-cluster imperative bootstrap, and CAPI for managing cluster
lifecycle declaratively at scale. It is the self-managed/bare-metal
counterpart to
[managed-kubernetes-eks-aks-gke](../managed-kubernetes-eks-aks-gke/SKILL.md)
(cloud-managed control planes) and
[lightweight-kubernetes-k3s](../lightweight-kubernetes-k3s/SKILL.md)
(single-binary, resource-constrained distributions) — choose this skill
when neither of those fits: full upstream Kubernetes, full control over
every control-plane component, on infrastructure you operate yourself.

## When to use

- Bootstrapping a brand-new self-managed or bare-metal cluster with
  `kubeadm init`/`kubeadm join` rather than a managed or lightweight
  distribution.
- Designing an HA control plane (stacked or external etcd, a load
  balancer/VIP in front of multiple API servers) for a kubeadm cluster.
- Joining additional control-plane or worker nodes to an existing
  kubeadm cluster, including regenerating expired join tokens/certificate
  keys.
- Upgrading a kubeadm cluster's control plane and nodes one minor
  version at a time.
- Managing many clusters' lifecycle (create, scale, upgrade, delete)
  declaratively and provider-agnostically with Cluster API instead of
  scripting `kubeadm` calls per cluster.
- Deciding whether a workload needs a self-managed kubeadm/CAPI cluster
  at all, versus a managed or lightweight alternative.

## Prerequisites & environment

- Matching minor versions of `kubeadm`, `kubelet`, and `kubectl` on
  every node (Kubernetes' version-skew policy allows the kubelet to
  trail the control plane by up to 3 minor versions in newer releases,
  but keep them aligned during initial bootstrap to avoid surprises).
- A container runtime already installed and configured with the CRI
  socket kubeadm expects (containerd is the common default) — see
  [container-runtime-docker-containerd](../container-runtime-docker-containerd/SKILL.md)
  for runtime selection/configuration; kubeadm does not install a
  runtime for you.
- Swap disabled, `br_netfilter` and `overlay` kernel modules loaded, and
  `net.bridge.bridge-nf-call-iptables=1` / `net.ipv4.ip_forward=1`
  sysctls set on every node — `kubeadm init`/`join` preflight checks
  fail loudly on most of these, but confirm them explicitly rather than
  fighting preflight errors one at a time.
- For control-plane HA: a load balancer or VIP mechanism (an external
  LB, or `kube-vip`/keepalived for bare metal with no LB appliance)
  reachable at a stable address *before* running `kubeadm init`, since
  `--control-plane-endpoint` must point at it from the very first node.
- No CNI plugin installed yet — a fresh `kubeadm init` leaves every node
  `NotReady` until one is applied; see
  [cni-networking-calico-flannel](../cni-networking-calico-flannel/SKILL.md)
  for choosing and installing one immediately after `init`.
- For Cluster API: the `clusterctl` CLI, a **management cluster** (a
  small kind/kubeadm/managed cluster that runs CAPI's controllers — it
  does not have to be, and usually isn't, one of the workload clusters
  it manages), and credentials for whichever infrastructure provider
  (CAPI has providers for most clouds and for bare metal/on-prem) will
  host the actual workload cluster's machines.

## Step-by-step guidance

1. **Author a `kubeadm-config.yaml`** and keep it in version control
   rather than passing ad hoc flags — this is what makes the bootstrap
   reproducible and reviewable:
   ```yaml
   apiVersion: kubeadm.k8s.io/v1beta4
   kind: ClusterConfiguration
   kubernetesVersion: v1.30.4
   controlPlaneEndpoint: "k8s-api.internal.example.com:6443"
   networking:
     podSubnet: "192.168.0.0/16"
   etcd:
     local: {}   # stacked etcd; use `external:` to point at an
                 # externally-operated etcd cluster instead
   ```

2. **Initialize the first control-plane node**:
   ```bash
   kubeadm init --config kubeadm-config.yaml --upload-certs
   mkdir -p $HOME/.kube
   sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
   sudo chown $(id -u):$(id -g) $HOME/.kube/config
   ```
   `--upload-certs` uploads the control-plane certs to a Secret so
   subsequent control-plane joins don't need certs copied by hand — but
   that Secret (and the certificate key printed in the output) **expires
   after 2 hours**; regenerate it if joining additional control-plane
   nodes later (step 5).

3. **Install a CNI plugin immediately** — nodes stay `NotReady` until
   this is applied:
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/tigera-operator.yaml
   ```
   See
   [cni-networking-calico-flannel](../cni-networking-calico-flannel/SKILL.md)
   for choosing between Calico and Flannel and sizing `podSubnet`
   correctly before this point — changing it after nodes join is
   disruptive.

4. **Set up a load balancer/VIP for the API server** before joining
   more control-plane nodes, if not already provisioned. On bare metal
   with no external LB appliance, `kube-vip` is a common choice — run it
   as a static pod on each control-plane node so the VIP fails over
   automatically:
   ```yaml
   # /etc/kubernetes/manifests/kube-vip.yaml on each control-plane node
   apiVersion: v1
   kind: Pod
   metadata: { name: kube-vip, namespace: kube-system }
   spec:
     containers:
       - name: kube-vip
         image: ghcr.io/kube-vip/kube-vip:v0.8.0
         args: ["manager"]
         env:
           - { name: vip_interface, value: eth0 }
           - { name: address, value: "10.0.0.100" }
           - { name: vip_arp, value: "true" }
         securityContext: { capabilities: { add: ["NET_ADMIN", "NET_RAW"] } }
   ```

5. **Join additional control-plane nodes** using a fresh join command
   and certificate key (both expire; regenerate rather than reusing an
   old value from your notes):
   ```bash
   kubeadm token create --print-join-command
   kubeadm init phase upload-certs --upload-certs   # new cert key
   ```
   ```bash
   kubeadm join k8s-api.internal.example.com:6443 \
     --token <TOKEN> \
     --discovery-token-ca-cert-hash sha256:<HASH> \
     --control-plane --certificate-key <NEW_CERT_KEY>
   ```

6. **Join worker nodes** (no `--control-plane`/`--certificate-key`
   needed):
   ```bash
   kubeadm join k8s-api.internal.example.com:6443 \
     --token <TOKEN> \
     --discovery-token-ca-cert-hash sha256:<HASH>
   ```

7. **Upgrade the cluster one minor version at a time**, control plane
   first, then nodes:
   ```bash
   kubeadm upgrade plan
   kubeadm upgrade apply v1.31.0        # on the first control-plane node
   kubeadm upgrade node                 # on every other control-plane/worker node
   ```
   Drain each node before upgrading its kubelet — see
   [kubernetes-node-maintenance-and-troubleshooting](../kubernetes-node-maintenance-and-troubleshooting/SKILL.md)
   for the cordon/drain/PDB-aware sequence to follow per node.

8. **For managing cluster lifecycle declaratively instead, install
   Cluster API on a management cluster**:
   ```bash
   clusterctl init --infrastructure <provider>   # e.g. docker, metal3, aws
   ```

9. **Define the cluster declaratively** with a `Cluster`,
   `KubeadmControlPlane`, and `MachineDeployment` (abbreviated; the
   infrastructure-specific `*Cluster`/`*Machine` templates referenced
   here vary per provider):
   ```yaml
   apiVersion: cluster.x-k8s.io/v1beta1
   kind: Cluster
   metadata: { name: workload-a, namespace: default }
   spec:
     controlPlaneRef:
       apiVersion: controlplane.cluster.x-k8s.io/v1beta1
       kind: KubeadmControlPlane
       name: workload-a-control-plane
     infrastructureRef:
       apiVersion: infrastructure.cluster.x-k8s.io/v1beta1
       kind: <ProviderCluster>
       name: workload-a
   ---
   apiVersion: controlplane.cluster.x-k8s.io/v1beta1
   kind: KubeadmControlPlane
   metadata: { name: workload-a-control-plane, namespace: default }
   spec:
     replicas: 3
     version: v1.30.4
     machineTemplate:
       infrastructureRef:
         apiVersion: infrastructure.cluster.x-k8s.io/v1beta1
         kind: <ProviderMachineTemplate>
         name: workload-a-control-plane
   ```
   `clusterctl generate cluster` scaffolds this (plus the provider-
   specific pieces) for a supported infrastructure provider rather than
   hand-writing every object from scratch.

10. **Apply and watch reconciliation**:
    ```bash
    clusterctl generate cluster workload-a --infrastructure <provider> \
      --kubernetes-version v1.30.4 --control-plane-machine-count 3 \
      --worker-machine-count 3 > workload-a.yaml
    kubectl apply -f workload-a.yaml
    clusterctl describe cluster workload-a
    ```
    `clusterctl describe cluster` shows the full object tree
    (`Cluster` → `KubeadmControlPlane`/`MachineDeployment` → `Machine`s)
    and each object's `Ready` condition — this is the CAPI equivalent of
    `kubectl get nodes` during a manual kubeadm bootstrap, and is where
    a stuck provisioning step actually surfaces.

11. **Validate the cluster before declaring it usable**, whichever
    method provisioned it — see
    [kubernetes-cluster-post-provision-conformance-validation](../kubernetes-cluster-post-provision-conformance-validation/SKILL.md)
    for running Sonobuoy conformance and smoke tests immediately after
    step 6 (kubeadm) or once CAPI reports the cluster `Ready` (step 10),
    before treating either as production-ready.

## Best practices

- Keep `kubeadm-config.yaml` (and, for CAPI, the generated
  `Cluster`/`KubeadmControlPlane`/`MachineDeployment` manifests) in
  version control as the source of truth — never reconstruct a
  bootstrap from remembered CLI flags after the fact.
- Provision the control-plane load balancer/VIP and decide
  `controlPlaneEndpoint` *before* running `kubeadm init` on the first
  node — changing the control-plane endpoint after the cluster exists
  requires re-issuing certificates and is far more disruptive than
  planning it up front.
- Use an odd number (3 or 5) of control-plane/etcd nodes for HA, and
  place them on genuinely separate failure domains (distinct hosts,
  racks, or availability zones) — etcd quorum tolerance means nothing if
  all "separate" nodes share one physical failure point.
- Treat bootstrap tokens and `--upload-certs` certificate keys as
  short-lived secrets, not values to keep around for later reuse — both
  expire (24h and 2h respectively by default) and regenerating them is
  the correct response, not a workaround.
- Upgrade one minor version at a time, control plane before nodes,
  following Kubernetes' documented version-skew policy — skipping
  versions or upgrading nodes ahead of the control plane is unsupported
  and can break in subtle, hard-to-diagnose ways.
- For Cluster API, keep the management cluster itself small, boring, and
  well-backed-up (it is a single point of control for every workload
  cluster it manages) — don't run production workloads on it, and don't
  let its own health go unmonitored just because it "only" runs
  controllers.

## Common pitfalls

- **Symptom:** `kubeadm join` fails on a worker node with a certificate
  validation or "token expired" error.
  **Fix:** Bootstrap tokens expire after 24 hours by default. Generate a
  fresh one from an existing control-plane node
  (`kubeadm token create --print-join-command`) rather than reusing an
  old token from documentation or a runbook.

- **Symptom:** Joining a second/third control-plane node fails with
  "certificate key has expired" or a certificate-decryption error.
  **Fix:** The `--upload-certs` Secret and its certificate key expire 2
  hours after `kubeadm init`. Regenerate with
  `kubeadm init phase upload-certs --upload-certs` on an existing
  control-plane node and use the new key — don't keep retrying the
  original one.

- **Symptom:** Every node shows `NotReady` immediately after
  `kubeadm init`/`kubeadm join`, with no obvious error.
  **Fix:** This is expected until a CNI plugin is applied — kubeadm
  deliberately does not install one. Apply Calico or Flannel (see
  [cni-networking-calico-flannel](../cni-networking-calico-flannel/SKILL.md))
  and confirm its pod CIDR matches `podSubnet` from `kubeadm-config.yaml`
  exactly.

- **Symptom:** `kubeadm upgrade apply` or a node's `kubeadm upgrade node`
  fails, or the kubelet won't start after an upgrade.
  **Fix:** Usually a version-skew violation (upgrading a node ahead of
  the control plane, or skipping a minor version). Run
  `kubeadm upgrade plan` first, upgrade exactly one minor version at a
  time, control plane before any node, and drain each node before
  touching its kubelet — see
  [kubernetes-node-maintenance-and-troubleshooting](../kubernetes-node-maintenance-and-troubleshooting/SKILL.md).

- **Symptom:** A Cluster API `Machine` stays stuck in `Provisioning` and
  never reaches `Running`.
  **Fix:** `clusterctl describe cluster <name> --show-conditions all`
  surfaces which object in the reconciliation chain is failing (often
  the infrastructure provider's own controller, not CAPI's core
  controllers) — check that controller's logs
  (`kubectl logs -n <provider-system-namespace> deploy/<provider-controller>`)
  rather than only the top-level `Cluster` status, which just reports
  "not ready" without the specific cause.

- **Symptom:** Someone runs `kubeadm reset` on a live control-plane node
  to "start over" without draining it first.
  **Fix:** `kubeadm reset` tears down that node's control-plane
  components and local etcd member membership immediately —
  > **Warning:** running this against a node still serving production
  API traffic or holding an etcd quorum vote is destructive and can take
  down the whole control plane if it drops below quorum. Drain the node
  first (see
  [kubernetes-node-maintenance-and-troubleshooting](../kubernetes-node-maintenance-and-troubleshooting/SKILL.md)),
  remove it from the etcd member list cleanly, and confirm remaining
  control-plane nodes still hold quorum before resetting it.

## Worked example

**Scenario:** Bootstrap a 3-node HA kubeadm cluster on bare metal with
`kube-vip` fronting the API server, then define an equivalent cluster
declaratively via Cluster API for a second environment.

```yaml
# kubeadm-config.yaml
apiVersion: kubeadm.k8s.io/v1beta4
kind: ClusterConfiguration
kubernetesVersion: v1.30.4
controlPlaneEndpoint: "10.0.0.100:6443"
networking: { podSubnet: "192.168.0.0/16" }
```

```bash
# node-1
kubeadm init --config kubeadm-config.yaml --upload-certs
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/tigera-operator.yaml
kubeadm init phase upload-certs --upload-certs
kubeadm token create --print-join-command
```

```bash
# node-2 and node-3 (control-plane join)
kubeadm join 10.0.0.100:6443 --token <TOKEN> \
  --discovery-token-ca-cert-hash sha256:<HASH> \
  --control-plane --certificate-key <CERT_KEY>
```

```bash
kubectl get nodes         # all 3 control-plane nodes Ready
kubectl get pods -n kube-system -l k8s-app=kube-vip   # VIP active on one node
```

Second environment, provisioned declaratively via CAPI on a management
cluster instead of manual `kubeadm` calls:

```bash
clusterctl init --infrastructure metal3
clusterctl generate cluster workload-b --infrastructure metal3 \
  --kubernetes-version v1.30.4 \
  --control-plane-machine-count 3 --worker-machine-count 3 > workload-b.yaml
kubectl apply -f workload-b.yaml
clusterctl describe cluster workload-b
```

`clusterctl describe cluster workload-b` shows `Cluster/workload-b`,
`KubeadmControlPlane/workload-b-control-plane`, and each `Machine`
reaching `Ready: True` in turn — once all three control-plane
`Machine`s and the `MachineDeployment`'s workers report ready, both
clusters proceed to conformance/smoke validation (see
[kubernetes-cluster-post-provision-conformance-validation](../kubernetes-cluster-post-provision-conformance-validation/SKILL.md))
before either is considered production-ready.

## Cross-references

- [kubernetes-cluster-post-provision-conformance-validation](../kubernetes-cluster-post-provision-conformance-validation/SKILL.md) — the required validation gate immediately after either provisioning path above completes.
- [managed-kubernetes-eks-aks-gke](../managed-kubernetes-eks-aks-gke/SKILL.md) — the managed-control-plane alternative when self-operating kubeadm/etcd isn't the right tradeoff.
- [lightweight-kubernetes-k3s](../lightweight-kubernetes-k3s/SKILL.md) — the single-binary alternative for edge/dev/resource-constrained deployments that don't need full kubeadm/CAPI control.
- [cni-networking-calico-flannel](../cni-networking-calico-flannel/SKILL.md) — choosing and installing the CNI plugin a fresh kubeadm cluster needs before nodes go `Ready`.
- [container-runtime-docker-containerd](../container-runtime-docker-containerd/SKILL.md) — installing/configuring the container runtime kubeadm requires on every node before `init`/`join`.
- [kubernetes-node-maintenance-and-troubleshooting](../kubernetes-node-maintenance-and-troubleshooting/SKILL.md) — safely draining nodes during a `kubeadm upgrade` or before a `kubeadm reset`.
