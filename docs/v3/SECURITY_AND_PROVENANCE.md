# Security and Provenance

> Status: **policy contract proposal**. Trust and provenance are described here; no automatic import or security service is enabled by this PR.

## Trust states

Third-party skills are executable instructions, even when distributed as Markdown. Every imported capability must have an explicit trust state:

| State | Meaning | Default routing behavior |
|---|---|---|
| `CORE_TRUSTED` | Maintained canonical material with verified contract and provenance | Eligible subject to task policy |
| `CURATED` | Reviewed external material with declared scope | Eligible only for declared capabilities |
| `COMMUNITY` | External material not yet promoted to curated | Read-only metadata or sandbox evaluation |
| `LOCAL_GENERATED` | Locally generated or distilled candidate | Quarantine until reviewed |
| `QUARANTINE` | Unverified, incomplete, or awaiting evaluation | Manifest/source inspection only |
| `BLOCKED` | Fails schema, license, provenance, or security policy | Cannot load or route |

Trust is not a quality score. A trusted item can still be wrong for a stage, and an untrusted item cannot gain permission by describing itself as safe.

## Required provenance fields

For every external or generated skill/plugin/MCP capability, track:

```yaml
source_repo: <repository>
source_ref: <immutable-ref>
license: <SPDX-id-or-unknown>
import_date: <timestamp>
hash: <digest>
local_modifications: []
scripts: []
hooks: []
MCP: []
external_commands: []
network_permissions: []
```

The record must distinguish source content from local modifications. A new source ref or digest creates a new review target; it does not silently update a trusted record.

## Intake controls

1. Inspect source before loading instructions.
2. Validate manifest/schema and declared file set.
3. Verify license and provenance; unknown license stays quarantined.
4. Scan scripts, hooks, MCP declarations, external commands, and network permissions.
5. Check duplicate/overlap and trigger near-misses.
6. Evaluate in a least-privilege sandbox with no trusted secrets.
7. Record findings and require human/policy approval before promotion.

Unknown external skills/plugins/MCP must never be automatically promoted into the trusted core. A README, popularity signal, or model-generated summary is not a substitute for source inspection.

## Capability and permission boundaries

- A skill may declare required capabilities, but the adapter grants only the intersection with TaskSpec and policy.
- `external_write`, payment, publish, delete, credential access, and destructive commands require explicit policy handling.
- MCP tools declare read/write/publish/destructive scope, data destination, rate limit, and latency.
- Hooks are deterministic lifecycle enforcement and must be reviewed as executable behavior.
- Plugins cannot write canonical task state, change trust, bypass evidence gates, or add undeclared network endpoints.
- Model selection and reasoning effort cannot widen permissions or promote a capability.

## Threat model

The design treats prompt injection, hidden scripts, malicious hooks, undeclared network calls, secret exfiltration, path expansion, registry poisoning, license contamination, and capability spoofing as supply-chain risks. The response is provenance, quarantine, narrow grants, isolated evaluation, independent evidence, and reversible promotion—not trusting a skill because its prose is persuasive.
