# FastMCP (Python MCP SDK) streamable-HTTP server pitfalls

Concrete, version-sensitive gotchas when serving a streamable-HTTP MCP server
(FastMCP) that a remote client connects to. Each is a rule + the mechanism,
not a transcript. Re-check the installed SDK's current API names, because
minor SDK versions rename symbols.

## 1. Do not run a sync event-loop runner inside an already-running loop

If your entrypoint is `async` (inside `asyncio.run(amain())`) and you call
the SDK's *synchronous* `mcp.run(transport="streamable-http")`, the server
crashes on boot with `RuntimeError: Already running asyncio in this thread`
-- the sync runner calls `anyio.run(...)`, which cannot start a second loop
in a thread that already has one running. Fix: `await` the *async* transport
runner instead (e.g. `await mcp.run_streamable_http_async()`). The symptom is
a clean startup traceback, not a silent hang.

## 2. The client-side factory symbol is renamed across SDK versions

The streamable-HTTP *client* context factory has moved/renamed between SDK
releases. In recent versions it is `streamablehttp_client` (import from
`mcp.client.streamable_http`), not `create_streamable_http_client`. Before
writing a client test, probe the installed SDK:
`python -c "import mcp.client.streamable_http as m; print([n for n in dir(m) if 'client' in n.lower()])"`
and use the symbol actually present. A wrong import is an `ImportError` at
test-collection time, which masquerades as "my server is broken" when it is
really the test's import.

## 3. A bearer token verifier requires companion auth settings

When you hand FastMCP a static-token `token_verifier`, the SDK still expects
an accompanying auth-settings object (issuer + resource-server URLs, required
scopes, redirect schemes). Passing only the verifier can raise at construction
(some versions want it, some reject `auth_settings=None` with a verifier).
Mint a minimal settings object; a bare loopback bearer path does not actually
use the OAuth endpoints, but they must exist so the SDK's metadata endpoints
are defined. Confirm what *your* installed SDK requires rather than assuming.

## 4. Capability flag names are not what the docs sometimes call them

The agent's `/capabilities` response is the source of truth, and its feature
flags are not always the literal names you expect. Read the response, not the
prose: e.g. the approval flag may be `run_approval_response` (not
`run_approval`), and an idempotency flag may be a nested object
(`runs_idempotency: {supported, durable, retention_seconds}`) rather than a
bool. Map defensively (accept the documented name *or* the observed one,
coerce the nested shape to bool). Getting this wrong makes a *supported*
feature look unsupported, so your bridge wrongly reports UNSUPPORTED.

## 5. Native idempotency is key+body; reused-with-different-body is an error

When the agent advertises run idempotency, a POST with an `Idempotency-Key`
returns the cached response *only if the request body is byte-identical*. Same
key with a changed body is rejected (a 409 conflict) -- the intended guard
against reusing a key for a different request. So a "does idempotency work"
test must replay the *identical* payload (including secondary fields like
instructions), or you get a 409 and mistake it for a failure. A first
submission *without* a key and a second *with* a key are two different runs,
by design.

## 6. A persistent SQLite ledger must commit

If the durable store is SQLite and you open/execute/close in a helper, every
INSERT/UPDATE is lost unless you explicitly `conn.commit()` (Python's legacy
transaction control rolls back on close otherwise). The failure mode is
silent: writes "succeed" in-process but nothing reaches the file, so a
restart reconcile finds zero open tasks. Add `commit()` on the success path
and `rollback()` on exception; verify with a *fresh* connection reopening
the same file that the rows are actually there.

## 7. macOS symlinked paths defeat naive containment checks

On macOS, `/var/folders/...` (TMPDIR, temp dirs) is a symlink to
`/private/var/folders/...`, and several user dirs are symlinked too. A
path-containment check that compares a *resolved* candidate path against an
*unresolved* project root will falsely report "outside the approved root".
Resolve **both** the root and the candidate before comparing; containment
must run in canonical (resolved) form.

## Testing the wire protocol

- Assert unauthenticated `initialize` is refused (401/403) *before* the
  authenticated session -- this proves the bearer gate is on.
- On the authenticated session: `initialize`, then `list_tools` and confirm
  every expected tool name is present (a missing name is a wiring bug, not a
  model problem).
- Call each tool over the wire, not just via in-process invocation, so you
  catch schema/serialization mismatches the unit tests miss.
- For a stop-confirmation flow, assert the tool reports the *pending* state
  (STOPPING) rather than a false STOPPED until the backend actually exits --
  a bridge that claims stopped early is a trust bug.

## Public-HTTPS exposure (tunnel) + 421 gotchas

- FastMCP binds loopback AND passes no `transport_security` argument, it
  auto-sets DNS-rebinding protection with `allowed_hosts =
  ["127.0.0.1:*", "localhost:*", "[::1]:*"]`. Any request whose Host header
  is a public tunnel hostname (trycloudflare.com, named-tunnel CF URL,
  Tailscale serve domain...) gets **HTTP 421 Misdirected Request** at the
  SDK middleware. Pass an explicit `TransportSecuritySettings` instead.
- The SDK matcher is exact-value or `host:*` (any-port) only. Globs like
  `*.trycloudflare.com` are NOT supported. A bare `127.0.0.1` entry does
  NOT match the Host header `127.0.0.1:8765`. Per entry emit:
  - host patterns: `<host>` and `<host>:*`
  - origin patterns: `http://<host>`, `https://<host>`, plus the `:*`
    forms when the entry is a bare hostname.
- After changing transport security, RE-RUN the local client test (8765
  direct) as well as the tunnel test: a too-narrow allowlist 421s local
  traffic; a too-broad one defeats the rebinding guard.
- Ephemeral tunnel URLs (quick tunnels) rotate on restart: merge them into
  the allowlist via an env var read at config-load time; never bake them
  into the JSON config.
- Negative test that proves the public edge is gated: POST /mcp with no
  Authorization must yield 401 (not 421, not 200) from the public URL.
