---
name: spiffe-spire-workload-identity-configuration
description: >
  Guides configuring SPIRE Server and Agent to issue cryptographic
  workload identities (SPIFFE IDs, X.509-SVIDs, JWT-SVIDs) for zero-trust
  service-to-service authentication — trust domain design, node and
  workload attestation (registration entries with selectors), SVID
  rotation, and federation between trust domains. Use when the user asks
  to "set up SPIFFE/SPIRE," "issue a workload identity to a service,"
  "configure SPIRE node/workload attestation," "design a SPIFFE ID
  namespace," "federate two SPIRE trust domains," or "implement true
  zero-trust mTLS between services without shared secrets." Distinct from
  enterprise-sso-and-idp-federation-configuration (human/workforce
  identity) and from vault-operations-and-pki-engine-configuration
  (general-purpose secrets/PKI issuance) — this skill is specifically
  about automated, attested cryptographic identity for *workloads*.
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: security-scanning-tooling
  maturity: stable
---

# SPIFFE/SPIRE Workload Identity Configuration

## Purpose

Zero-trust service-to-service authentication requires each workload to
prove *what it is* cryptographically, without relying on a shared
secret, a static API key, or network location (which IP/subnet it's on)
as a stand-in for identity — all three of those are exactly what an
attacker who's compromised one node can trivially forge or steal.
**SPIFFE** (Secure Production Identity Framework For Everyone) defines
the identity model: a URI-formatted **SPIFFE ID**
(`spiffe://trust-domain/path`) naming a workload, and two token formats
carrying it — an **X.509-SVID** (a short-lived X.509 certificate with
the SPIFFE ID in its URI SAN, used for mTLS) and a **JWT-SVID** (a
short-lived signed JWT, used where mTLS isn't practical, e.g. calling
through an intermediary that terminates TLS). **SPIRE** is the reference
implementation: a **SPIRE Server** acting as the trust domain's
certificate authority and identity registry, and a **SPIRE Agent**
running on every node that **attests** each local workload's identity
(verifying, via a selector like a Kubernetes service account or a Unix
process attribute, that a workload really is what it claims to be)
before handing it a short-lived SVID — with no long-lived credential
ever touching disk. This is a different layer than
[enterprise-sso-and-idp-federation-configuration](../enterprise-sso-and-idp-federation-configuration/SKILL.md),
which federates *human* workforce identity into applications, and than
[vault-operations-and-pki-engine-configuration](../vault-operations-and-pki-engine-configuration/SKILL.md),
which issues general-purpose secrets and certificates on request but has
no built-in concept of automatically *attesting* which specific workload
process is asking. This skill covers designing the trust domain and
SPIFFE ID structure, configuring node and workload attestation, SVID
rotation, and trust domain federation.

## When to use

- Designing a zero-trust service-to-service authentication scheme where
  workload identity must be cryptographically provable, not
  network-location- or shared-secret-based.
- Standing up SPIRE Server and Agent(s) for a Kubernetes cluster, a
  fleet of VMs, or a hybrid environment spanning both.
- Designing a SPIFFE ID naming scheme (trust domain and path structure)
  before registration entries proliferate without one.
- Writing registration entries that attest a workload via a selector —
  a Kubernetes service account/namespace/pod label, a Unix UID, a Docker
  label, or a cloud instance metadata attribute.
- Rotating SVIDs automatically (they're deliberately short-lived) and
  confirming workloads actually pick up rotated identities without a
  restart.
- Federating two SPIRE trust domains — connecting workload identity
  across two clusters, two clouds, or an organizational boundary after
  an acquisition — without either trust domain trusting the other's
  full workload population by default.
- Reviewing an existing SPIRE deployment for overly broad selectors that
  would let an unintended workload obtain another workload's identity.

## Prerequisites & environment

- SPIRE 1.8+ recommended for stable Federation API and OIDC Discovery
  Provider support; confirm the exact registration entry CLI/API shape
  against the installed version, since selector syntax and some CLI
  flags have changed across major releases.
- A decision on the **trust domain** name (e.g. `example.org` or
  `prod.example.internal`) — this is embedded in every SPIFFE ID issued
  under it and is expensive to change later since it's baked into every
  workload's identity and every relying party's trust configuration.
- A **SPIRE Server** deployment with a datastore (SQL — PostgreSQL or
  MySQL — for anything beyond a single-node trial; the default embedded
  SQLite is not intended for production HA) and an upstream CA
  configuration — either SPIRE's self-signed root, or an upstream
  authority (a Vault PKI mount via SPIRE's `upstream_authority` plugin,
  or a cloud provider's ACM Private CA) if the org wants SPIRE's issued
  certificates chained to an already-trusted root.
- A **SPIRE Agent** running on every node that hosts workloads needing an
  identity — deployed as a Kubernetes DaemonSet for a Kubernetes cluster,
  or as a system service on each VM/bare-metal host.
- A **node attestation** mechanism appropriate to the environment — the
  Kubernetes PSAT (Projected Service Account Token) node attestor for
  Kubernetes, the AWS/GCP/Azure node attestor plugins for cloud VM
  fleets, or the `join_token` attestor only for small/manual setups
  (not recommended at scale — it doesn't cryptographically verify
  anything about the node itself).
- A **workload attestation** mechanism appropriate to how workloads run
  — the Kubernetes workload attestor (matching on namespace, service
  account, pod label/selector) for containerized workloads, or the Unix
  workload attestor (matching on UID/GID/path) for processes on a
  traditional VM.
- Network reachability from every SPIRE Agent to the SPIRE Server's
  registration API, and from every workload to its local Agent's Unix
  domain socket (the standard, expected transport for the Workload API)
  — never expose the Workload API over a network socket.

## Step-by-step guidance

1. **Design the SPIFFE ID path structure deliberately before the first
   registration entry is created** — a consistent, hierarchical scheme
   makes selector-to-identity intent legible and makes future policy
   (e.g. "anything under `/ns/payments/` may call the payments database")
   expressible:
   ```
   spiffe://prod.example.internal/ns/payments/sa/payments-service
   spiffe://prod.example.internal/ns/payments/sa/payments-worker
   spiffe://prod.example.internal/ns/checkout/sa/checkout-service
   ```
   Mirror the identity path structure to something already meaningful in
   the environment (Kubernetes namespace/service account, or an
   environment/team/service hierarchy for VMs) rather than an arbitrary
   flat list of workload names.

2. **Configure the SPIRE Server** with its trust domain, datastore, and
   (optionally) an upstream authority instead of relying on SPIRE's
   self-signed root for a production trust domain that needs to chain to
   an already-trusted CA:
   ```hcl
   # server.conf
   server {
     trust_domain = "prod.example.internal"
     data_dir     = "/opt/spire/data/server"
     log_level    = "INFO"
     ca_ttl       = "24h"
     default_svid_ttl = "1h"
   }

   plugins {
     DataStore "sql" {
       plugin_data {
         database_type = "postgres"
         connection_string = "postgres://spire:${SPIRE_DB_PASSWORD}@postgres.internal/spire_server sslmode=require"
       }
     }
     NodeAttestor "k8s_psat" {
       plugin_data {
         clusters = {
           "prod-cluster" = {
             service_account_allow_list = ["spire:spire-agent"]
           }
         }
       }
     }
     UpstreamAuthority "vault" {
       plugin_data {
         vault_addr = "https://vault.internal:8200"
         pki_mount_point = "pki_int"
         ca_cert_path = "/etc/spire/certs/vault-ca.pem"
       }
     }
   }
   ```
   `default_svid_ttl` (short — an hour is a common production value) is
   the single most consequential setting here: it's what makes every
   issued identity naturally expire and rotate rather than becoming a
   long-lived credential by another name.

3. **Configure the SPIRE Agent** on each node with the matching trust
   domain and the node attestor appropriate to the environment:
   ```hcl
   # agent.conf (Kubernetes DaemonSet)
   agent {
     trust_domain  = "prod.example.internal"
     server_address = "spire-server.spire.svc"
     server_port   = 8081
     socket_path   = "/run/spire/sockets/agent.sock"
   }

   plugins {
     NodeAttestor "k8s_psat" {
       plugin_data {
         cluster = "prod-cluster"
       }
     }
     WorkloadAttestor "k8s" {
       plugin_data {
         skip_kubelet_verification = false
       }
     }
     KeyManager "memory" {
       plugin_data {}
     }
   }
   ```

4. **Write registration entries scoped as narrowly as the workload
   attestor allows** — a selector matching an entire namespace grants
   that identity to *every* pod in the namespace, which is rarely the
   intent:
   ```bash
   spire-server entry create \
     -spiffeID spiffe://prod.example.internal/ns/payments/sa/payments-service \
     -parentID spiffe://prod.example.internal/spire/agent/k8s_psat/prod-cluster \
     -selector k8s:ns:payments \
     -selector k8s:sa:payments-service \
     -ttl 3600
   ```
   > **Warning:** a registration entry using only a broad selector (e.g.
   > `-selector k8s:ns:payments` alone, with no service-account
   > selector) grants the `payments-service` SPIFFE ID to *any* pod in
   > the `payments` namespace, including a future, unrelated workload
   > someone deploys into that namespace later. Combine selectors (
   > namespace **and** service account, or namespace **and** a specific
   > pod label) to scope an identity to the exact workload it's meant
   > for.

5. **Fetch SVIDs through the Workload API — never read the Agent's key
   material or SVID files directly from disk** if avoidable; the
   Workload API (a local Unix domain socket, gRPC) is what handles
   automatic rotation transparently to the workload:
   ```go
   // Go SDK: fetch and watch for SVID rotation via the Workload API
   source, err := workloadapi.NewX509Source(ctx,
       workloadapi.WithClientOptions(workloadapi.WithAddr("unix:///run/spire/sockets/agent.sock")),
   )
   if err != nil {
       log.Fatal(err)
   }
   defer source.Close()

   tlsConfig := tlsconfig.MTLSServerConfig(source, source, tlsconfig.AuthorizeAny())
   server := &http.Server{TLSConfig: tlsConfig}
   ```
   `NewX509Source` maintains a background connection to the Agent and
   transparently swaps in the newest SVID as it rotates — the
   application code never manually reloads a certificate file.

6. **Authorize peers by SPIFFE ID, not by which CA signed their
   certificate** — mTLS alone only proves "signed by a CA I trust," not
   "this is specifically the workload I intend to talk to":
   ```go
   // authorize only a specific expected peer identity, not "any" SVID
   // from the trust domain
   tlsConfig := tlsconfig.MTLSClientConfig(source, source,
       tlsconfig.AuthorizeID(spiffeid.RequireFromString(
           "spiffe://prod.example.internal/ns/payments/sa/payments-service",
       )),
   )
   ```
   `tlsconfig.AuthorizeAny()` (used in step 5's server example) accepts
   any valid SVID from the trust domain and is appropriate only when the
   caller-side authorization is enforced elsewhere (e.g. an application-
   layer allow-list); a client connecting to a specific expected service
   should authorize that exact SPIFFE ID.

7. **Expose a JWT-SVID for workloads that can't do mTLS directly** (e.g.
   calling through a load balancer or proxy that terminates TLS before
   the request reaches the workload):
   ```bash
   # fetch a JWT-SVID for a specific audience via the Workload API CLI
   spire-agent api fetch jwt -audience payments-api \
     -socketPath /run/spire/sockets/agent.sock
   ```
   The receiving service validates the JWT-SVID's signature against the
   trust domain's published JWKS and checks the `aud` claim matches
   itself — treat an unchecked `aud` claim the same as an unchecked JWT
   audience in any other OIDC flow (see
   [enterprise-sso-and-idp-federation-configuration](../enterprise-sso-and-idp-federation-configuration/SKILL.md)
   for the equivalent human-identity pitfall).

8. **Federate two trust domains explicitly**, exchanging each domain's
   trust bundle and scoping which SPIFFE IDs from the far side are
   actually trusted — federation is opt-in per relying party, not a
   blanket cross-trust the moment two SPIRE Servers know about each
   other:
   ```bash
   # on trust domain A's SPIRE Server: register domain B as a federated bundle
   spire-server federation create \
     -trustDomain acquired-co.internal \
     -bundleEndpointURL https://spire-server.acquired-co.internal:8443 \
     -bundleEndpointProfile https_web
   ```
   ```bash
   # a registration entry that federates: this workload accepts SVIDs
   # from the federated trust domain too, not just its own
   spire-server entry create \
     -spiffeID spiffe://prod.example.internal/ns/payments/sa/payments-service \
     -parentID spiffe://prod.example.internal/spire/agent/k8s_psat/prod-cluster \
     -selector k8s:ns:payments -selector k8s:sa:payments-service \
     -federatesWith acquired-co.internal
   ```
   Scope `-federatesWith` per registration entry to the specific
   workloads that genuinely need to talk across the trust domain
   boundary, rather than a blanket federation trusted by every workload
   in the domain.

9. **Monitor SPIRE Server/Agent health and SVID issuance rate** as a
   first-class operational signal — a SPIRE Server outage or an Agent
   losing its connection to the Server means workloads eventually can't
   rotate expiring SVIDs and start failing mTLS handshakes as their
   current SVID expires:
   ```
   # key metrics to alert on (SPIRE exposes Prometheus-format telemetry)
   spire_server_registration_entry_count
   spire_agent_svid_rotate_failure
   spire_server_ca_manager_rotate_failure
   ```

## Best practices

- Choose the trust domain name deliberately and treat it as effectively
  permanent — every issued SPIFFE ID and every relying party's trust
  configuration bakes it in, making a later rename a coordinated,
  disruptive migration rather than a config edit.
- Keep `default_svid_ttl` short (an hour is a common production
  baseline) and rely on the Workload API's automatic rotation rather
  than ever extending TTL "to reduce load" — short-lived, automatically
  rotated identity is the core security property SPIFFE/SPIRE provides.
- Scope every registration entry's selectors as narrowly as the
  workload attestor supports (namespace **and** service account/pod
  label, not namespace alone) — a broad selector is a standing
  privilege-escalation path for any future workload landing in that
  scope.
- Authorize peers by exact SPIFFE ID (`AuthorizeID`) wherever the caller
  knows exactly which service it intends to reach; reserve
  `AuthorizeAny` for cases where authorization genuinely happens at
  another layer.
- Never expose the Workload API over a network socket — it is designed
  to be reached only via a local Unix domain socket, scoped to workloads
  actually running on that node.
- Scope trust domain federation per registration entry to the specific
  workloads that need cross-domain access, not a blanket mutual trust
  between two entire trust domains.
- Monitor SPIRE Server/Agent health and SVID rotation failures as
  actively as any other identity-critical infrastructure — an
  undetected rotation failure becomes a wave of mTLS handshake failures
  exactly when the current SVID batch expires.

## Common pitfalls

- **Symptom:** A workload unexpectedly receives a SPIFFE identity meant
  for a different service running in the same namespace.
  **Fix:** The registration entry's selector matched on namespace alone
  (or an otherwise too-broad selector) rather than combining namespace
  with a service-account or pod-label selector specific to the intended
  workload (step 4). Tighten every registration entry to the narrowest
  selector combination the workload attestor supports, and audit
  existing entries for this exact broad-selector pattern.

- **Symptom:** mTLS between two SPIRE-issued workloads succeeds even
  though the calling service should never have been allowed to reach
  this particular callee.
  **Fix:** The server side is using `AuthorizeAny()` and relying on no
  other authorization check, so *any* valid identity from the trust
  domain is accepted as a peer (step 6). mTLS with SPIRE proves *which*
  workload is calling, not that it's *authorized* to call — add an
  explicit `AuthorizeID`/allow-list check, or an application-layer
  authorization step, rather than treating "presented a valid SVID" as
  equivalent to "is allowed to call this service."

- **Symptom:** All workloads across a node start failing mTLS
  handshakes with expired-certificate errors at roughly the same time.
  **Fix:** The SPIRE Agent on that node lost connectivity to the SPIRE
  Server (network issue, Server outage, or a node attestation failure
  after a node's underlying instance was replaced) and stopped rotating
  SVIDs before they expired. Alert on `spire_agent_svid_rotate_failure`
  and Agent-to-Server connectivity specifically, rather than only
  noticing after workloads start failing at the application layer.

- **Symptom:** After federating two trust domains, a workload in trust
  domain A can successfully authenticate to a service in trust domain B
  that was never intended to be reachable across the boundary.
  **Fix:** The federation was configured as a blanket trust bundle
  exchange with `-federatesWith` applied too broadly, rather than
  scoped per registration entry to the specific workloads meant to
  cross the boundary (step 8). Review every registration entry using
  `-federatesWith` and restrict it to the minimum set of workloads that
  genuinely need cross-domain access.

- **Symptom:** A newly onboarded team stands up their own node
  attestation using `join_token`, and months later an audit can't
  explain what actually proves a node running under that token is the
  node it claims to be.
  **Fix:** `join_token` node attestation provides no cryptographic
  verification of the node's actual identity/environment — it's meant
  for small manual/testing setups, not production fleets. Migrate to an
  environment-appropriate attestor (`k8s_psat` for Kubernetes, the
  cloud-provider node attestor for VM fleets) that ties node identity to
  something independently verifiable (a cloud instance's own attested
  metadata, a Kubernetes-issued service account token).

## Worked example

**Scenario:** `payments-service` and `checkout-service` run as
Kubernetes workloads in the `prod.example.internal` trust domain and
need mutual TLS between them with cryptographically attested identity —
no shared API keys, no long-lived certificates.

1. Trust domain and server config (as in step 2), with `default_svid_ttl
   = "1h"` and Postgres-backed SQL datastore.
2. Registration entries, scoped to namespace + service account:
   ```bash
   spire-server entry create \
     -spiffeID spiffe://prod.example.internal/ns/payments/sa/payments-service \
     -parentID spiffe://prod.example.internal/spire/agent/k8s_psat/prod-cluster \
     -selector k8s:ns:payments -selector k8s:sa:payments-service -ttl 3600

   spire-server entry create \
     -spiffeID spiffe://prod.example.internal/ns/checkout/sa/checkout-service \
     -parentID spiffe://prod.example.internal/spire/agent/k8s_psat/prod-cluster \
     -selector k8s:ns:checkout -selector k8s:sa:checkout-service -ttl 3600
   ```
3. `checkout-service` fetches an X.509-SVID via the Workload API and
   opens an mTLS connection to `payments-service`, authorizing the
   specific expected peer identity:
   ```go
   tlsConfig := tlsconfig.MTLSClientConfig(source, source,
       tlsconfig.AuthorizeID(spiffeid.RequireFromString(
           "spiffe://prod.example.internal/ns/payments/sa/payments-service",
       )),
   )
   ```
4. `payments-service` accepts the connection using `AuthorizeAny()` plus
   an explicit application-layer check that the caller's SPIFFE ID path
   starts with `spiffe://prod.example.internal/ns/checkout/`, rejecting
   any other otherwise-valid identity from the trust domain.
5. One hour later, both SVIDs rotate transparently via the Workload
   API's background watch — no restart, no manual certificate reload,
   and no connection disruption, since the `X509Source` swaps in the new
   SVID for any new TLS handshake automatically.
6. Six months later, `acquired-co.internal`'s SPIRE trust domain is
   federated, scoped narrowly: only `checkout-service`'s registration
   entry gets `-federatesWith acquired-co.internal` added, so it alone
   (not every workload in `prod.example.internal`) can now authenticate
   against a specific service in the acquired company's trust domain.

## Cross-references

- [vault-operations-and-pki-engine-configuration](../vault-operations-and-pki-engine-configuration/SKILL.md) — general-purpose secrets/PKI issuance (including a possible `UpstreamAuthority` chain target for SPIRE's own CA), distinct from SPIRE's automated, attested workload-identity issuance covered here.
- [enterprise-sso-and-idp-federation-configuration](../enterprise-sso-and-idp-federation-configuration/SKILL.md) — the equivalent federation and audience-validation discipline applied to human/workforce SSO rather than workload identity, including the same "validate the audience claim" pitfall that applies to JWT-SVIDs here.
- [certificate-lifecycle-management-at-scale](../certificate-lifecycle-management-at-scale/SKILL.md) — rotating and automating longer-lived certificates across many services, a complementary concern to SPIRE's short-lived SVID rotation for workloads that also need conventional TLS certificates.
- [sealed-secrets-and-external-secrets-operator](../sealed-secrets-and-external-secrets-operator/SKILL.md) — a Kubernetes-native secret-sync pattern worth contrasting with SPIFFE/SPIRE's no-secrets-at-rest identity model for service-to-service auth specifically.
