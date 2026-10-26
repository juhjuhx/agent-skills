# Router Decision Flow

Static reference for the V3 advisory router's decision path and failure branches.
Supplements the narrative in [V3_SYSTEM_ARCHITECTURE](V3_SYSTEM_ARCHITECTURE.md).

All diagrams use box-drawing characters only (no Mermaid, no SVG). Box
interiors are ASCII; CJK annotations are in surrounding prose. Display width
is verified at generation time (80-column hard limit).

## Flow

```
+------------+
| INPUT TASK |
+============+
| intent parse (CJK-aware)
v
+---------------------------------------------+
|         CATALOG CANDIDATE RETRIEVAL         |
| metadata keyword scoring, top-20 candidates |
+=============================================+
|
v
+-----------------------------------+
|    RANKING / CAPABILITY CHECK     |
| profile picks 0-8 positive skills |
+===================================+
|
v
+-----------------------------------+
| DIGEST / COMPATIBILITY VALIDATION |
| selected body digests only        |
+===================================+
|
v
+---------------------------------+
|           ROUTEPACKET           |
| suggestion packet for the agent |
+=================================+
|
v
+--------------------+
| HOST SKILL LOADING |
+====================+
|
v
+-----------------------------------+
|          TASK EXECUTION           |
| host tools under host permissions |
+===================================+
|
v
+---------------------------------+
|       RESULT VERIFICATION       |
| evidence required before claims |
+=================================+
failures:
  invalid candidate   -> excluded from candidates
  router failure      -> fail-open fallback
  host load missing   -> report NOT_LOADED
model_loaded requires host load evidence; absence stays NOT_LOADED
```

## Stage notes

| Stage | Input | Output | Failure branch |
|---|---|---|---|
| Intent parse | raw task string | normalised intent (CJK-aware) | — |
| Candidate retrieval | intent | top-20 metadata-scoring candidates | invalid candidate → excluded |
| Ranking / capability | candidates + profile | 0–8 positive skills (guided/normal/high = 3/5/8) | — |
| Digest / compatibility | selected skill bodies | SHA-256 digest check | mismatch → candidate dropped |
| RoutePacket | selected skills + host tools | advisory suggestion packet | router failure → fail-open fallback |
| Host skill loading | RoutePacket | host-loaded skill context | host load missing → report NOT_LOADED |
| Task execution | loaded context + host permissions | results | host decides; router does not gate |
| Result verification | results | evidenced completion | absence of host load evidence → NOT_LOADED, not MODEL_LOADED |

## Invariants

- Router output is **advisory**; it never authorises a tool call.
- No stage writes TASK/PLAN/STATE automatically; the agent does.
- `MODEL_LOADED` requires **host** load evidence; the router cannot claim it.
- A `router failure` degrades to metadata fallback or a manual workflow; the host
  retains its native tools regardless.

## Related

- [System Architecture](V3_SYSTEM_ARCHITECTURE.md) — narrative + original flow
- [Component Reference](V3_COMPONENT_REFERENCE.md) — files, helper interface
- [Workflow & Tool Mapping](V3_WORKFLOW_AND_TOOL_MAPPING.md) — per-host adapters
- [Testing & Limits](V3_TESTING_AND_LIMITATIONS.md) — what CI does and does not prove
