# Diagram vs Codebase Validation

When reviewing an existing SVG architecture diagram against a real codebase, follow this checklist to catch drift, missing components, and stale references.

## Quick Audit Commands

Run these against the project root to get ground-truth counts:

```bash
# Backend structure
find backend/src -name "*.js" -not -path "*__tests__*" | sort
find backend/src/middleware -name "*.js" | wc -l
find backend/src/routes -name "*.js" | wc -l
find backend/src/services -name "*.js" -not -path "*__tests__*" | wc -l
find backend/src/utils -name "*.js" 2>/dev/null | wc -l
find backend/src/config -name "*.js" 2>/dev/null | wc -l

# Frontend structure
find frontend/src/pages -name "*.vue" | wc -l
find frontend/src/components -name "*.vue" | wc -l
find frontend/src/stores -name "*.js" | wc -l
find frontend/src/composables -name "*.js" | wc -l
```

## Common Drift Patterns

1. **Count mismatches** — Diagram says "8 stores" but code has 9. Usually caused by a store/composable being added after the diagram was made.
2. **Ghost services** — Diagram references external tools (e.g. "SearXNG") that were never actually integrated. Check with `grep -r -l "searx\|SearX" .` to verify.
3. **Missing utils/config** — Security hardening often adds utility files (`pagination.js`, `cronAuth.js`, `serverLimits.js`) that don't get categorized as "services" or "middleware" but deserve their own section.
4. **Notification/dispatcher systems** — Often split into multiple files (base class + channels). Count all files in the subdirectory, not just the top-level dispatcher.
5. **Test counts** — If the diagram claims "X suites / Y tests", verify with actual test runner output.

## What to Check (Ordered)

| Priority | Check | How |
|----------|-------|-----|
| P0 | Component counts match code | `wc -l` on directories vs diagram labels |
| P0 | No references to non-existent services | `grep -r` for each external service name |
| P1 | LOC counts are roughly current | `wc -l` on key files mentioned in diagram |
| P1 | All named files actually exist | `ls` or `find` for each filename in diagram |
| P2 | Legend stats match component counts | Cross-reference legend text with section headers |
| P2 | Connection arrows reflect actual data flow | Check for missing or extra arrows |

## Patching Workflow

After identifying discrepancies:
1. Fix count labels (section headers and legend stats)
2. Add missing components as new rows in their parent section
3. Replace stale references with actual services
4. Use `patch` mode for bulk SVG edits — one patch per logical change group
