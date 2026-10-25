---
name: hermes-mcp-bridge
description: Build a local MCP control plane for an agent's runs API.
version: 1.0.0
license: Apache-2.0
metadata:
  domain: ai-agent
  hermes:
    tags:
      - mcp
      - control-plane
      - agent-integration
    related_skills:
      - mcp-server-development
      - agent-evaluation-and-guardrails
---

# Agent MCP Control Bridge

A **bridge** is a thin, secured control plane that exposes a *native* agent's
control surface (its task / submit / status / stop / steer API) to a remote
MCP client. It is NOT a second agent and NOT a reimplementation of one.
The value chain is: remote client -> auth+policy bridge -> native agent API ->
real execution -> evidence back. Everything that is an *agent capability*
stays in the native agent; the bridge only adds auth, authorization policy,
idempotency, and durable state.

## When to use

- "Connect ChatGPT/Claude/Cursor to my local agent over MCP."
- "Wrap this agent's runs API as remote MCP tools."
- "Add a secure bridge in front of my local agent on macOS" (without
  building a new agent or a new scheduler).
- Reviewing whether an MCP bridge has exposed too much of the local host.

## Always-on rules

- **The bridge never replaces the agent.** Every real execution goes through
  the agent's native run API. Do not re-implement agent turns, tool loops,
  or orchestration inside the bridge -- that creates two competing executors
  that diverge. Bridge = control plane only.
- **Probe capabilities before assuming endpoints.** On boot, call the
  agent's `/capabilities`-equivalent and gate each tool on the flags it
  actually advertises. A feature that is not advertised must report
  UNSUPPORTED, not be called via a guessed endpoint. This is what makes
  stop/steer/approval safe across agent versions.
- **Fail-closed authorization.** Unknown project -> deny. Unknown mode ->
  deny. A high-risk request with no verified human-approval channel ->
  refuse, do not auto-approve. Never enable bypass/YOLO/dangerous-skip flags.
- **Durable state is the bridge's own store, not memory.** An in-memory job
  table is not a task source of truth. Persist task_id, agent_run_id,
  idempotency_key, status, and evidence location to a local durable store
  (SQLite is enough). On restart, *reconcile* each open task against the
  agent API and refresh status -- never blindly resubmit.
- **One writer per worktree; never fight a scheduler.** If another local
  process (a cron / auto-pilot) owns a worktree, the bridge must not write
  to the same tree. Constrain the bridge to its own allowlisted project roots.
- **Secrets live only on the local host, 0600, never in git, never in
  logs.** Generate tokens with a CSPRNG (`secrets.token_urlsafe`). Redact
  full tokens/keys/ssh material from log lines. Do not write the agent's
  API key into a repo.
- **Do not expose the agent's API port to the public internet.** The remote
  entry point is a secured tunnel that terminates TLS and enforces its own
  auth; the local agent port stays loopback-only.

## Enable the agent's API server without touching protected config

The agent's API server (its OpenAI-compatible + Runs HTTP surface) reads its
enable/port/host/key from **process environment variables** (`API_SERVER_*`)
*as well as* the config file / dot-env. This means you can bring it up under
a **bridge-owned** process that exports those vars from a bridge-local secrets
file -- without editing the user's protected global config or dot-env (which
the user marks off-limits and which edits to get rejected). Start the agent's
server as a wrapper that sets the env vars, keep it loopback bind, and confirm
reachability by hitting the capabilities/health endpoint with the bearer key
*inside the script* (do not echo the key to the shell). Why this rule
exists: it is the non-invasive path that respects a user's protected-files
boundary while still giving the bridge a live backend.

## Test before deploy

- Unit-test the bridge's own decision logic (policy, idempotency,
  persistence, status mapping, stop-confirmation) against a fake agent client
  so it runs with the backend down. This is the bulk of spec compliance and
  needs no network.
- Then run a **live** end-to-end against the real agent API: submit a
  trivial read-only run, get a real run id, poll to a terminal status, read
  back evidence, exercise stop. Use a dedicated isolated scratch project for
  the live path, never a real user project.
- Then exercise the actual MCP wire protocol with a real client (initialize,
  tools/list, call each tool, and assert unauthenticated requests are refused).
- Mark remote-tunnel and client-account-login steps as **USER_ACTION_REQUIRED**
  and do not claim the remote end is connected if you could not test it
  yourself. Do not open public ports; do not log in to cloud/OpenAI/ChatGPT
  on the user's behalf.

## FastMCP / streamable-HTTP gotchas

See `references/fastmcp-streamable-http.md` for the concrete Python MCP-SDK
server pitfalls (event-loop, transport entrypoints, bearer + auth-settings,
capability-flag naming, idempotency body-match, SQLite commit, macOS
symlinked paths) that cost real time to rediscover.

## Exposing the bridge over public HTTPS (tested 2026-10-12)

- **Cloudflare quick tunnel works and is the fastest real-HTTPS path to a
  loopback-only MCP bridge**: `brew install cloudflared` (arm64), then
  `cloudflared tunnel --url http://127.0.0.1:8765` prints an ephemeral
  `*.trycloudflare.com` URL. The full 7-tool MCP lifecycle (initialize,
  tools/list, submit, status, evidence, stop) has been verified through it,
  including the negative test: unauthenticated POST /mcp -> HTTP 401. No
  Cloudflare account needed; the URL CHANGES on every tunnel restart, so
  treat it as test-only. A persistent URL needs a named tunnel + CF account
  (user decision, out of the default scope).
- **HTTP 421 Misdirected Request is the Host-allowlist, not a tunnel bug.**
  FastMCP auto-configures a localhost-only `TransportSecuritySettings`
  (`127.0.0.1:*`, `localhost:*`, `[::1]:*`) when you bind loopback and pass
  no `transport_security`. A public tunnel hostname is rejected with 421 at
  the SDK middleware. Pass an explicit `TransportSecuritySettings` built
  from your config's `allowed_hosts`.
- **The SDK's host matching is exact-or-`host:*` only — no globs.**
  `*.trycloudflare.com` does NOT work. A bare hostname entry fails to match
  `127.0.0.1:8765`-style Host headers (they carry a port), so emit BOTH
  forms per entry: the exact host AND `host:*` (and for origins, both
  `scheme://host` and `scheme://host:*`). Getting this wrong in the first
  fix can break local access with 421 too — re-run the local 8765 client
  test after every transport-security change.
- **Keep ephemeral hostnames out of the config file.** Append them via an
  env var (here `HCB_ALLOWED_HOSTS_EXTRA=<host>`, merged into the allowlist
  at load time) so restarting the quick tunnel never requires editing JSON.
- Auth model that stays valid behind public HTTPS: Cloudflare edge +
  static bearer (constant-time compare) + host allowlist + the bridge's
  policy layer. The agent's own API port (8642) remains loopback-only at
  all times; only the bridge port sits behind the edge.

## Cross-references

- `mcp-server-development` -- general MCP tool-schema + security design.
- `agent-evaluation-and-guardrails` -- the fail-closed guardrails this
  bridge enforces.
