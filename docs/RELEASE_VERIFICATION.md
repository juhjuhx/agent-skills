# Release Verification (M4-P8)

## Verify the shipped skill bodies match their locks

```sh
python3 scripts/skills_cli.py verify   # checks each skills/<slug>/SKILL.md SHA-256 vs catalog.lock.json
```

## CI gates

GitHub Actions runs:
- `unittest` over `tests/` (installer, catalog, registry contract).
- `node --test` over the V3 router advisory tests.
- `python3 scripts/build_v3_catalog.py --check` (catalog determinism).

A release is not complete until CI is green and the remote HEAD + tag are confirmed.

## Numbers audit

Every count in the README and this doc is generated from `catalog.json`. To re-audit:

```sh
python3 -c "import json;c=json.load(open('catalog.json'));print('total',c['total_skills'],'extra',c['additional_skills_count'])"
```
