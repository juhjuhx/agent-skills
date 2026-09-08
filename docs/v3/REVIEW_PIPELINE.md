# Independent Review and Evidence Pipeline

> Status: **evidence contract proposal**. Review commands and lanes are documented; no review service is installed or run by this PR.

## OpenCodeReview evidence lane

Alibaba OpenCodeReview (OCR) is an independent evidence lane, not a synonym for the host agent's review. Preserve both native modes:

```text
ocr scan
  = current-source / full-file audit

ocr review
  = diff / change review
```

`ocr scan` answers whether the current source or selected full files violate the resolved rules. `ocr review` answers whether a change set introduces findings relative to its comparison scope. Their inputs, rule scope, and evidence must remain distinguishable.

OCR Delegate mode separates deterministic engineering from review intelligence:

- OCR determines file selection and rule resolution deterministically.
- The host agent supplies review intelligence over that selected scope.
- Delegate output is `OCR_DELEGATE`, not a native OCR LLM scan.

Do not relabel host-agent delegate review as a native OCR LLM scan.

## Evidence classes

The canonical evidence taxonomy is:

| Class | What it proves | Required provenance |
|---|---|---|
| `OCR_NATIVE_FULL_SOURCE` | Native OCR source/full-file findings | OCR version, command, scope, rules |
| `OCR_NATIVE_DIFF` | Native OCR change/diff findings | refs, diff scope, command, rules |
| `OCR_DELEGATE` | Host-agent intelligence over OCR-selected scope | selector/rules plus host adapter/model |
| `AGENT_CODE_REVIEW` | Runtime agent review | runtime, model profile, selected skills |
| `SECURITY_REVIEW` | Security-specific analysis | reviewer/tool, threat scope, result |
| `PERFORMANCE_REVIEW` | Performance-specific analysis | workload, measurements, environment |
| `TEST_EVIDENCE` | Tests/checks executed | command, version, result, fixtures |
| `RUNTIME_EVIDENCE` | Behavior at a real runtime boundary | environment, inputs, outputs, logs |

One class cannot be changed to another because the result looks similar. Multiple lanes may agree, but each keeps its original provenance.

## Pipeline

```text
Review stage
  -> deterministic scope and policy check
  -> OCR native full-source and/or diff lane
  -> OCR delegate lane when selected
  -> agent code review
  -> security/performance review as risk requires
  -> Verify stage tests and runtime evidence
  -> evidence gate
```

The evidence gate compares findings to acceptance criteria and risk. It may request a new route or hardening stage. It must not suppress an unresolved finding merely because another lane passed.

## Review record

```yaml
evidence:
  id: E-<stable-id>
  class: OCR_NATIVE_DIFF
  task_id: <task-id>
  stage: review
  source: <tool-or-runtime>
  command: <command-or-api>
  scope: <files-or-refs>
  rules_ref: <rule-resolution-ref>
  result: pass | findings | unavailable
  findings: []
  environment: <version-and-platform>
  generated_at: <timestamp>
```

A missing lane is reported as unavailable, not as a pass. Native OCR, agent review, and verification are complementary controls with different failure modes.
