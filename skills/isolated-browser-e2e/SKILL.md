---
name: isolated-browser-e2e
description: "Isolated real-browser E2E that never touches the live env."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Browser-E2E, Isolation, Regression-Safety, Real-Browser, Web-App, Sandbox]
    related_skills: [self-audit, addyosmani-browser-testing-with-devtools, pre-push]
---

# Isolated, Regression-Safe Real-Browser E2E

Run a SEPARATE instance of a running web service (alternate home/config/port), drive its UI with a browser that can actually reach loopback, verify the real frames and interactions, then PROVE the live/production environment is unchanged. The whole point is two invariants at once: the UI is genuinely verified in a real browser, and the production/active environment was never mutated.

## When to Use
- Browser/UI acceptance testing of a RUNNING web app that must be verified WITHOUT touching the live/active instance (isolated sandbox home + separate port).
- User wording includes 'isolated'/'regression-safe'/'do not modify the live env'/'browser E2E'/'no curl substitute' with a real-browser mandate, or a gate requiring the active profile byte-unchanged.
- NOT for: unit tests, curl-only API checks, or debugging the LIVE (non-isolated) instance → `addyosmani-browser-testing-with-devtools`.

## Dominant Variable
**Live-environment integrity + real-browser proof.** A green check that touched the live profile, or a 'passed' that is really just `HTTP 200` / a registered route instead of rendered+interacted UI, both invalidate the test. The test's acceptance is the before/after hash diff of the live service PLUS evidence the UI frames actually completed — not either one alone.

## Always-On Rules

1. **Isolate first, then test.** Copy the running service's config into a throwaway home (e.g. `/tmp/<iso>-home`), enable the exemption/feature under test ONLY there. Never write a test setting back to the live home. WHY: a leak into the active profile is worse than a failed test and is often irreversible.
2. **Different port, confirmed listening.** Pick a free port that is NOT the live instance's; start the isolated server in the background; assert it is actually LISTENing on that port (a socket probe) before opening a browser. WHY: testing the live port or a dead port silently tests the wrong thing.
3. **No live data reuse.** Do NOT copy the live service's sessions/storages/DB into the sandbox. WHY: re-using live state couples the test to production and can write back.
4. **Use a browser that reaches 127.0.0.1.** A local CDP browser (Hermes `browser_exec`) is the right 'real browser'. If only a cloud browser is available and it cannot reach loopback, record `BLOCKED_TOOL_UNAVAILABLE` — a cloud-browser connection failure is NOT an app fault and must not be scored against the feature. WHY: the user's mandate is 'no curl / no node-API standing in for a browser'; only a real DOM interaction counts.
5. **Real-browser proof beats status codes.** Do not declare PASS on `HTTP 200` or 'the asset route is registered'. Render the actual DOM, interact, and assert the expected result came back. Build any needed test data as a minimal fixture IN the sandbox, never by depending on the model to emit it.
6. **Regression PASS is a hash diff.** Before touching anything, capture a baseline (shasum of the live service's config/profile/credentials/key files). After the test, re-hash and diff; 'live unchanged' = identical. Record it. WHY: a green UI is meaningless if you quietly mutated the live profile.
7. **Never emit credentials.** Grab the server's boot token from its stdout into a `0600` file; redact it in every report. WHY: tokens are the exact secret a report must not leak.

## Procedure

1. **Baseline.** `shasum` the live service's config + profile + credentials (by name, not value) into a scratch manifest. Note the live port and its PID.
2. **Build the sandbox.** `mkdir -p /tmp/<iso>`; copy the live service's config dir (the profile, plugin tree, model config) and the minimal auth material; do NOT copy sessions/storages/DB. Re-point any now-broken relative symlinks to absolute paths (see Pitfalls). Keep the feature-under-test exemption in the sandbox copy only.
3. **Start isolated, background.** Launch the service with the alternate home + a free port + `--no-open`. Read the boot URL/`?token=` line from the process log; write it to a `0600` file.
4. **Confirm listen + auth fence.** Socket-probe the new port. Expect the service's auth fence to answer `401` at root with no token and `303` (redirect into the app shell) with the boot token — that is CORRECT behavior, not a failure.
5. **Drive a real local browser.** Open the token URL in `browser_exec` (or a local CDP browser). Wait for load; if the page resets to `about:blank` after a long write, `ensure_real_tab()` and re-open.
6. **Verify the frames, in order.** (A) shell renders / not blank; (B) no white-screen / stuck-loading / redirect loop; (C) session establishes; (D) target components actually mount in the DOM; (E) rich content renders (charts/diagrams/3D — assert the concrete DOM node / rendered SVG / canvas, not the loader); (F) framework features initialize; (G) buttons/inputs actually respond (click, assert the state change); (H) still correct after a page switch; (I) no fatal console errors (hook `console.error`/`window.error` up front); (J) no failed critical resource loads (hook a `PerformanceObserver` on `resource` entries ≥400).
7. **Force-render deterministically where the UI is streaming/LLM-backed.** Prefer a client-side trigger that renders locally without a model round-trip; otherwise create the minimal data fixture in the sandbox. Never wait on the model to produce the test's content.
8. **Prove live-unchanged.** Re-`shasum` the baseline files; diff to identical. Confirm the live port/PID still serves and the sandbox-only exemption was not copied back.
9. **Clean up.** Kill the isolated server, free the port, delete the sandbox. Keep the `0600` token only long enough to run.
10. **Report.** A compact block: `BROWSER_OPENED / DOM_RENDERED / <content>_RENDERED / INTERACTION / CONSOLE_ERRORS / NETWORK_FAILURES / SESSION / E2E_VERDICT / LIVE_UNCHANGED / REGRESSION`. Redact all credentials. Mark the feature PASS ONLY when the key frames AND interactions actually completed; otherwise `PARTIAL` with the named gap, or `BLOCKED_TOOL_UNAVAILABLE` if no loopback-capable browser existed.

## Pitfalls

- **React-controlled contenteditable swallows `el.textContent = …`.** Set composer input with `document.execCommand('insertText', false, text)` after focusing the node; React's reconciliation ignores direct `textContent` assignment and the character never reaches state. (This cost repeated turns.)
- **Copied relative symlinks break.** A profile/`node_modules` copied out of place loses `link:` deps and cross-tree refs; the boot skips/mangles the broken plugin. Re-point the broken links to their absolute source paths before starting the isolated server.
- **`HTTP 200` / 'route registered' is not UI verification.** The user's explicit rule: never claim a browser feature passed on a status code or a `webServer.register` call — prove the rendered DOM and a real interaction.
- **Cloud browser can't reach loopback ≠ app fault.** If the only available browser runs remotely and cannot hit `127.0.0.1`, the verdict is `BLOCKED_TOOL_UNAVAILABLE`, not 'feature broken'.
- **Boot token on stdout must not be printed.** It is a credential; capture to a `0600` file and redact in reports.
- **Auth-fence codes are expected.** Root no-token → `401`, token-URL → `303` into the app are the fence working; do not file them as errors.
- **Long `browser_exec` write can leave a stale tab (`about:blank`).** Recover with `ensure_real_tab()` then re-open the token URL; the lesson is the retry pattern, not that the browser is broken.
- **Copying live sessions/DB defeats isolation.** Re-using live state couples the test to production and risks write-back; keep the sandbox to config + auth material only.

## Output

```
ISOLATED BROWSER E2E — <feature>
Live baseline: <N files hashed, port/PID noted> | Live unchanged after: YES/NO (diff)
Sandbox: <path> port <P> (≠ live) | server: LISTENING (probed) | token: 0600-file (redacted)
Browser: local CDP reaching 127.0.0.1 (or BLOCKED_TOOL_UNAVAILABLE — cloud can't reach loopback)
Frames: A-shell <ok> B-no-blank <ok> C-session <ok> D-dom-mount <ok> E-<content>-render <ok/absent> G-interaction <ok> I-console-fatal <0> J-resource-failures <0>
VERDICT: E2E=PASS | PARTIAL(<gap>) | BLOCKED_TOOL_UNAVAILABLE
LIVE_UNCHANGED: YES/NO ; REGRESSION: PASS/FAIL
```
