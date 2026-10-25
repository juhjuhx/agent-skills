---
name: fluent-bit-configuration-validation
description: >
  Validates Fluent Bit pipeline configuration syntax and tests the
  INPUT/FILTER/OUTPUT pipeline against sample log lines before a
  production rollout — dry-run checks, parser testing, and route/Match
  verification. Use when a user asks to "validate this Fluent Bit
  config before deploying," "test my Fluent Bit parser against sample
  logs," "will this Fluent Bit change break log routing," "check this
  Fluent Bit config in CI," or reports logs silently missing/misrouted
  after a Fluent Bit config change.
license: Apache-2.0
compatibility: "Claude Code, GitHub Copilot, OpenAI Codex, Cursor, Gemini CLI"
metadata:
  domain: observability-and-platform-extras
  maturity: stable
---

# Fluent Bit Configuration Validation

## Purpose

A Fluent Bit config that parses as valid YAML/INI can still be
functionally broken in ways that only surface once it's rolled out
cluster-wide as a DaemonSet: a `Match` pattern that doesn't actually
match the tag it's meant to filter, a parser that silently fails to
extract fields from real log lines, or an output pointed at the wrong
destination — none of which Fluent Bit's own parser rejects at load
time, because all of these are still structurally valid configuration.
This skill covers validating a Fluent Bit pipeline **before** it's
deployed broadly: a dry-run against sample input, testing parser
expressions against real sample log lines, and confirming `Match`
patterns actually route to the intended output — as a pre-deploy gate
on top of the pipeline design covered in
[fluent-bit-log-forwarding-configuration](../fluent-bit-log-forwarding-configuration/SKILL.md),
which this skill assumes is already designed and does not repeat.

## When to use

- Before merging or deploying any change to a Fluent Bit
  `fluent-bit.yaml`/`fluent-bit.conf` — new INPUT, new parser, new
  routing rule, or a changed OUTPUT destination.
- Writing or changing a parser expression (`json`, `logfmt`, `regexp`,
  `pattern`, `multiline`) and needing to confirm it actually extracts
  the expected fields from real log lines before it ships.
- Setting up a CI check that validates Fluent Bit config changes on
  every PR rather than discovering a routing mistake after rollout.
- Diagnosing why logs stopped appearing at an expected destination, or
  started appearing at the wrong one, immediately after a config
  change.
- Auditing an existing production Fluent Bit config for `Match`
  patterns that are broader (or narrower) than intended, as a
  proactive health check rather than only after an incident.

## Prerequisites & environment

- The `fluent-bit` binary (or the equivalent container image,
  `fluent/fluent-bit:<version>`) available locally or in CI to run
  dry-run/stdout checks without needing a live cluster.
- The candidate config file(s) — including any Helm-templated or
  ConfigMap-rendered output, since (as with Loki config validation)
  the raw `values.yaml`/chart input isn't the actual config Fluent Bit
  receives; render it first.
- A handful of real, representative sample log lines for each log
  format the pipeline needs to parse (plain text, JSON, logfmt,
  multiline stack traces) — parser validation without real samples
  only proves the parser is syntactically well-formed, not that it
  actually extracts anything useful.
- Familiarity with the pipeline's intended design (INPUT tags, filter
  order, OUTPUT routing) from
  [fluent-bit-log-forwarding-configuration](../fluent-bit-log-forwarding-configuration/SKILL.md) —
  this skill validates that an implementation matches that design, it
  does not re-derive the design itself.

## Step-by-step guidance

1. **Render the actual deployed config before validating anything**,
   the same discipline as validating Loki config — a raw Helm
   `values.yaml` or hand-maintained ConfigMap template is not what
   Fluent Bit actually loads:
   ```bash
   helm template fluent-bit fluent/fluent-bit -f values-production.yaml \
     --show-only templates/fluent-bit-configmap.yaml > rendered-fluent-bit.yaml
   ```

2. **Dry-run the rendered pipeline against stdout** to confirm it
   loads without error and to see, in real time, which records actually
   flow through which route — this is the single most useful
   validation step and catches most `Match` mistakes immediately:
   ```bash
   fluent-bit -c rendered-fluent-bit.yaml -o stdout -m '*'
   ```
   Feed it representative input (tail a file with sample log lines
   appended, or point a test `tail` input at a fixture file instead of
   `/var/log/containers/*.log`) rather than only checking that the
   process starts without a config-parse error — a config that loads
   cleanly can still route nothing anywhere.

3. **Test each parser expression against real sample log lines**
   in isolation before trusting it inside the full pipeline — a subtly
   wrong regex or pattern capture silently drops or mis-extracts
   fields rather than erroring:
   ```bash
   # single-parser test using the parsers.conf/parsers.yaml file directly
   echo '{"level":"error","msg":"payment declined","request_id":"abc123"}' | \
     fluent-bit -c /dev/null \
       -R parsers.yaml \
       -i stdin -p 'format=json' \
       -F parser -p 'key_name=log' -p 'parser=app_json' -m '*' \
       -o stdout
   ```
   For a `regexp`/`pattern` parser matching a custom log format, run it
   against several real sample lines that cover the format's actual
   variation (different log levels, a line with an unusually long
   field, a line missing an optional field) — not just the one
   cleanest example line.

4. **Confirm each `Match` pattern actually matches its intended tag**
   using the stdout dry-run's visible tag output, rather than assuming
   a pattern is correctly scoped from reading it — this is exactly the
   mistake structural validation cannot catch, since an overly broad or
   overly narrow `Match` is still valid syntax:
   ```bash
   fluent-bit -c rendered-fluent-bit.yaml -o stdout -m '*' 2>&1 | grep -E '^\[.*\]'
   ```
   Confirm specifically: does `kube.payments.*` catch every payments
   pod's tag after the `kubernetes` filter's `kube_tag_prefix`
   rewrites it? Does `kube.security-audit.*` **not** also catch
   payments logs (an overly broad pattern silently duplicating output
   across destinations)? Verify both directions — under-matching
   (logs that should route somewhere don't) and over-matching (logs
   route to more places than intended).

5. **Verify filter ordering produces the field set each downstream
   stage actually expects** — a `parser`/`modify`/`grep` filter placed
   before the `kubernetes` enrichment filter won't have Kubernetes
   metadata available yet to filter or route on, and a filter placed
   after a redaction step can't act on a field that was already
   removed:
   ```bash
   fluent-bit -c rendered-fluent-bit.yaml -o stdout -m '*' | \
     jq 'select(.kubernetes == null)'   # should be empty after the kubernetes filter runs
   ```

6. **Confirm redaction filters actually remove the intended fields**
   from the final output, not just that the filter is present in the
   config — verify by inspecting the dry-run's actual emitted records:
   ```bash
   fluent-bit -c rendered-fluent-bit.yaml -o stdout -m '*' | \
     jq 'has("authorization") or has("password")'   # must be false for every record
   ```
   > **Warning:** never treat "the `modify`/`grep` redaction filter is
   > in the config" as sufficient evidence that redaction works — a
   > `Match` mismatch (step 4) or wrong `key_name` silently leaves the
   > filter never applied to the records that actually carry the
   > sensitive field. Confirm against real dry-run output before
   > trusting any redaction rule with production data.

7. **Validate output destination reachability and credentials
   separately from pipeline logic**, using each output's lightest-
   weight connectivity check rather than routing real production volume
   at an unverified destination:
   ```bash
   curl -sf -o /dev/null -w '%{http_code}' http://loki-gateway.monitoring.svc:3100/ready
   ```

8. **Wire steps 1-4 into CI** so a `Match`/parser mistake fails the PR
   instead of the deploy:
   ```yaml
   # GitHub Actions example
   - name: Render Fluent Bit config
     run: helm template fluent-bit fluent/fluent-bit -f values-production.yaml --show-only templates/fluent-bit-configmap.yaml > rendered.yaml
   - name: Dry-run against fixture logs
     run: |
       docker run --rm -i \
         -v "${{ github.workspace }}/rendered.yaml:/fluent-bit/etc/fluent-bit.yaml" \
         -v "${{ github.workspace }}/fixtures:/fixtures" \
         fluent/fluent-bit:3.1.9 \
         -c /fluent-bit/etc/fluent-bit.yaml -o stdout -m '*' < fixtures/sample-lines.log
   - name: Assert no leaked secret fields
     run: |
       ./scripts/dryrun_and_check.sh rendered.yaml fixtures/sample-lines.log \
         | jq -e 'has("authorization") or has("password") | not'
   ```
   Keep a small, checked-in fixture file of representative sample log
   lines per log format the pipeline handles, so this check is
   deterministic and doesn't depend on a live cluster's current traffic.

9. **After deploying, confirm real production behavior matches the
   validated dry-run** — static validation reduces but does not
   eliminate risk from something the fixture set didn't cover:
   ```bash
   kubectl logs -n monitoring -l app=fluent-bit --tail=200 | grep -i error
   ```
   A spike in Fluent Bit's own internal error/retry metrics
   immediately after a config rollout is the final real-world
   confirmation validation should have (but might not have) caught.

## Best practices

- Always render the actual deployed config (post-Helm-templating,
  post-ConfigMap-generation) before validating — never validate a
  hand-maintained source file that isn't what Fluent Bit actually
  loads.
- Run the stdout dry-run against real or realistic fixture log lines
  for every config change, not only a syntax check — a `Match`
  mismatch or broken parser is invisible to a syntax-only check and
  only visible in the dry-run's actual emitted output.
- Test parser expressions against multiple real sample lines covering
  the format's actual variation, not one clean example — edge cases
  (missing optional fields, unusually long values, an unexpected log
  level) are where regex/pattern parsers most often silently fail.
- Verify redaction filters by inspecting dry-run output for the
  redacted field's absence, never by confirming the filter rule merely
  exists in the config.
- Check `Match` patterns in both directions: confirm intended logs are
  caught (no under-matching) and confirm unintended logs are excluded
  (no over-matching/duplication across destinations).
- Keep a small, version-controlled fixture set of representative sample
  log lines per format, and run it through CI on every config change —
  this is what makes validation repeatable and independent of a live
  cluster's current traffic mix.
- Treat this validation as a gate before rollout, not a substitute for
  watching the pipeline's own error/retry metrics immediately after
  deploying.

## Common pitfalls

- **Symptom:** A Fluent Bit config change deploys cleanly (no
  parse/load error) but a specific log stream stops appearing at its
  destination.
  **Fix:** The relevant output's `Match` pattern doesn't actually match
  the stream's tag after upstream filters rewrote it — run the stdout
  dry-run (step 2/4) against a sample of that stream's tag and confirm
  the pattern catches it; this is exactly the class of mistake
  structural config loading cannot detect.

- **Symptom:** A new parser expression is added for a custom log
  format, and it "works" in a quick manual test but silently fails to
  extract fields for a meaningful fraction of real production lines.
  **Fix:** The parser was only tested against one clean example line.
  Re-test against several real sample lines covering the format's
  actual variation (different log levels, missing optional fields,
  unusually long values) before trusting it broadly.

- **Symptom:** A redaction filter meant to strip a sensitive field from
  logs is present in the config and reviewed as correct, but the field
  still reaches the destination.
  **Fix:** Confirm via dry-run output (step 6), not by reading the
  filter's config, that the field is actually absent from emitted
  records — a `Match`/`key_name` mismatch commonly leaves a redaction
  filter never applied to the records that actually carry the field.

- **Symptom:** Two teams' logs that were meant to go to two different
  destinations both end up at both destinations after a routing change.
  **Fix:** One or both outputs' `Match` patterns are broader than
  intended (over-matching). Verify each `Match` pattern excludes the
  other stream's tag explicitly using the dry-run's visible tag output,
  not just that each pattern matches its own intended stream.

- **Symptom:** A config change is validated with a single "does it
  start" check in CI, passes, and still breaks routing in production.
  **Fix:** "Starts without error" only proves structural validity, not
  correct behavior. Add the fixture-based stdout dry-run (step 8) to
  CI so `Match`/parser correctness is checked automatically on every
  PR, not just config load success.

## Worked example

**Scenario:** A PR adds a new `regexp` parser for a legacy application's
custom log format and changes an existing `Match` pattern from
`kube.payments.*` to `kube.*payments*` intended to also catch a newly
renamed `payments-batch` service's logs.

1. Render the actual deployed config:
   ```bash
   helm template fluent-bit fluent/fluent-bit -f values-production.yaml \
     --show-only templates/fluent-bit-configmap.yaml > rendered.yaml
   ```
2. Dry-run against a fixture file containing sample lines from both
   `payments-api` and the newly renamed `payments-batch`, plus a
   `security-audit` line that must **not** be caught by the changed
   pattern:
   ```bash
   fluent-bit -c rendered.yaml -o stdout -m '*' < fixtures/sample-lines.log
   ```
3. Output confirms `payments-api` and `payments-batch` lines both now
   route to the `loki` output as intended — the pattern change works
   as designed. But it also shows a `security-audit-payments-reconciliation`
   service's logs (an unrelated service with "payments" in its name)
   now unexpectedly routing to the same Loki output — over-matching
   caught before merge.
4. The new `regexp` parser is tested in isolation against five sample
   lines from the legacy app, including one with a missing optional
   `duration` field — the parser initially fails to handle the missing
   field gracefully, dropping the whole line instead of extracting the
   fields that are present; the pattern is fixed to make that capture
   group optional and re-tested until all five samples parse correctly.
5. The `Match` pattern is corrected to `kube.*payments-api*` OR an
   explicit second entry for `kube.*payments-batch*`, re-validated with
   the dry-run to confirm `security-audit-payments-reconciliation` is
   now correctly excluded.
6. CI is updated to include the `security-audit-payments-reconciliation`
   sample line in the fixture set permanently, so this specific
   over-matching regression is caught automatically on any future
   `Match` pattern change.

## Cross-references

- [fluent-bit-log-forwarding-configuration](../fluent-bit-log-forwarding-configuration/SKILL.md) — the pipeline design (INPUT/FILTER/OUTPUT structure, buffering, redaction) this skill validates before rollout without repeating.
- [loki-configuration-validation](../loki-configuration-validation/SKILL.md) — the equivalent pre-deploy validation discipline applied to the Loki side of the same pipeline this Fluent Bit config feeds.
- [logql-query-authoring](../logql-query-authoring/SKILL.md) — querying logs once they land, useful for confirming a validated pipeline's fields actually arrive queryable at the destination.
- [incident-investigation-using-metrics-logs-traces](../incident-investigation-using-metrics-logs-traces/SKILL.md) — using logs shipped by a validated pipeline as one leg of a live cross-signal investigation.
