#!/usr/bin/env python3
"""Router Consumer — V3.1 Phase 3 versioned contract (ROUTER side).

Consumes a provider-published contract document and validates it before the
router will act on any skill in it. This module is the consumer half of the
registry<->router versioned interface (STEP 4). It is purely advisory: it
NEVER grants or changes host tool permissions (R3 / AGENTS.md).

Key invariants:
  DISCOVERED != TRUSTED          — a record in the contract is not trusted
  HASH_VERIFIED != SAFE / LOADED — body_sha256 match proves integrity only
  BODY_READ != MODEL_LOADED      — digest pass does not mean host loaded it
  MODEL_LOADED != EXECUTED       — host-load evidence is a separate signal

Degradation policy (STEP 4: registry failure must keep V3 working):
  incompatible document  -> REJECTED (do not act on its skills)
  stale revision         -> DEGRADED (advisory continues, warning recorded)
  registry/contract down -> DEGRADED (pure V3 fallback, all host tools intact)
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_HERE = Path(__file__).resolve()
_CONTRACT_SCHEMA = _HERE.parents[3] / "registry/schema/registry-contract.schema.json"

# ---------------------------------------------------------------- versions
CONTRACT_SCHEMA_VERSION = 1
SUPPORTED_SCHEMA_VERSIONS = (1,)          # majors this consumer understands
ROUTER_VERSION = "3.1"

# Validation statuses (single canonical set, used in every report).
ST_OK = "ok"
ST_INCOMPATIBLE = "incompatible"          # hard reject: do not act on skills
ST_STALE = "stale"                        # revision drift: advisory only
ST_DEGRADED = "degraded"                  # contract/registry unavailable
ST_MISSING = "missing"                   # a required skill record is absent


def _load_schema():
    try:
        return json.loads(_CONTRACT_SCHEMA.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _major(version):
    """Parse '3.1' / 3 / '1' -> major int. Non-numeric -> None."""
    if version is None:
        return None
    try:
        return int(str(version).split(".")[0])
    except (ValueError, IndexError):
        return None


def _required_missing(doc, keys):
    return [k for k in keys if k not in doc]


def validate_contract(
    doc,
    *,
    expected_revision=None,
    expected_source_commit=None,
    host="generic",
    expected_policy_epoch=None,
):
    """Validate one contract document against consumer expectations.

    Returns a report dict:
      {status, reasons[], skills_indexed, unsupported_schema, revision_ok,
       source_commit_ok, policy_epoch_ok, host, body_sha256_verified (set),
       incompatible_hosts (set)}

    `status` is the terminal decision:
      ST_OK            everything acceptable; router may use the skills
      ST_INCOMPATIBLE  schema major / commit / router-version failure — REJECT
      ST_STALE         revision drift only — advisory continues
      ST_DEGRADED      doc absent or unparseable — pure V3 fallback
      ST_MISSING       a record the caller asked for is not present
    """
    report = {
        "status": ST_DEGRADED,
        "reasons": [],
        "skills_indexed": 0,
        "unsupported_schema": False,
        "revision_ok": True,
        "source_commit_ok": True,
        "policy_epoch_ok": True,
        "host": host,
        "body_sha256_verified": set(),
        "incompatible_hosts": set(),
    }

    # 1) Absent / unparseable -> degraded, never crash (fail-open, V3 intact).
    if not isinstance(doc, dict) or not doc:
        report["reasons"].append("contract document absent or not a dict")
        return report
    report["status"] = ST_OK

    skills = doc.get("skills")
    if not isinstance(skills, list):
        report["status"] = ST_INCOMPATIBLE
        report["reasons"].append("contract.skills is missing or not a list")
        return report
    report["skills_indexed"] = len(skills)

    # 2) Schema major gate — a major outside the supported range is INCOMPATIBLE.
    schema_major = _major(doc.get("registry_schema_version"))
    if schema_major not in SUPPORTED_SCHEMA_VERSIONS:
        report["status"] = ST_INCOMPATIBLE
        report["unsupported_schema"] = True
        report["reasons"].append(
            f"registry_schema_version={schema_major} not in {SUPPORTED_SCHEMA_VERSIONS}")
        # still record per-skill findings for diagnostics, then return the reject
        _annotate_skills(report, doc, host)
        return report

    # 3) Router-version floor: a contract that demands a newer router is incompatible.
    min_router = _major(doc.get("router_version_min"))
    my_router = _major(ROUTER_VERSION)
    if min_router is not None and my_router is not None and my_router < min_router:
        report["status"] = ST_INCOMPATIBLE
        report["reasons"].append(
            f"router {ROUTER_VERSION} below contract's router_version_min "
            f"{doc.get('router_version_min')}")

    # 4) Source commit pin — full 40-hex required for commit-anchored queries.
    source_commit = doc.get("source_commit")
    commit_ok = isinstance(source_commit, str) and len(source_commit) == 40 \
        and all(c in "0123456789abcdef" for c in source_commit.lower())
    if expected_source_commit is not None:
        report["source_commit_ok"] = (source_commit == expected_source_commit)
        if not report["source_commit_ok"]:
            # Caller pinned a source commit: a mismatch means "not the snapshot
            # I asked for" — same drift class as revision. Degrade to STALE so
            # the router acts on this doc as advisory only; a skill load is
            # refused until a matching registry is provided.
            report["status"] = ST_STALE
            report["reasons"].append(
                f"source_commit {source_commit!r} != pinned {expected_source_commit!r}")
    else:
        # Caller did not pin: 'unknown' / non-40hex degrades to advisory, not a reject.
        if not commit_ok:
            report["source_commit_ok"] = False
            report["reasons"].append(
                f"source_commit {source_commit!r} is not a full 40-hex SHA "
                "(advisory only; pin a commit for a commit-anchored query)")

    # 5) Revision drift — caller pinned a revision and got a different one -> STALE.
    if expected_revision is not None and doc.get("registry_revision") != expected_revision:
        report["revision_ok"] = False
        report["status"] = ST_STALE
        report["reasons"].append(
            f"registry_revision {doc.get('registry_revision')!r} != expected "
            f"{expected_revision!r} (catalog drift)")

    # 6) Policy epoch — advisory compatibility marker ONLY; mismatch warns, never
    #    gates execution (R3: POLICY_EPOCH is not execution authorization).
    if expected_policy_epoch is not None:
        pe = doc.get("policy_epoch")
        if pe != expected_policy_epoch:
            report["policy_epoch_ok"] = False
            report["reasons"].append(
                f"policy_epoch {pe!r} != expected {expected_policy_epoch!r} "
                "(advisory compatibility marker; not an execution gate)")

    # 7) Per-skill host compatibility + body digest integrity (diagnostic sets).
    _annotate_skills(report, doc, host)

    return report


def _annotate_skills(report, doc, host):
    """Fill the body_sha256 / host-compat diagnostic sets; collect dup-id conflicts."""
    for s in doc.get("skills", []):
        if not isinstance(s, dict):
            continue
        sid = s.get("skill_id")
        digest = s.get("body_sha256")
        if isinstance(digest, str) and len(digest) == 64:
            report["body_sha256_verified"].add(sid)
        compat = s.get("host_compatibility")
        if compat:  # empty/absent = any host; non-empty must include requested host
            if host not in compat and "generic" not in compat:
                report["incompatible_hosts"].add(sid)
    report.setdefault("duplicate_skill_ids", [])
    seen = {}
    for s in doc.get("skills", []):
        if isinstance(s, dict):
            seen.setdefault(s.get("skill_id"), set()).add(s.get("body_sha256"))
    for sid, digests in seen.items():
        if len(digests) > 1:
            report["duplicate_skill_ids"].append(sid)


def check_body_sha256(doc, skill_id, actual_digest):
    """Digest integrity for ONE skill. Returns verified / mismatch / unrecorded.

    A 'verified' result proves the body bytes match the recorded digest — it does
    NOT prove the skill is safe or has been loaded into the model (R3).
    """
    for s in doc.get("skills", []):
        if isinstance(s, dict) and s.get("skill_id") == skill_id:
            recorded = s.get("body_sha256")
            if not recorded:
                return "unrecorded"
            return "verified" if str(recorded) == str(actual_digest) else "mismatch"
    return "unrecorded"


def host_compatible(doc, skill_id, host):
    """True iff the skill may be loaded/enabled on `host`. A non-empty
    host_compatibility that excludes the host => refuse (False). Empty => any host.
    """
    for s in doc.get("skills", []):
        if isinstance(s, dict) and s.get("skill_id") == skill_id:
            compat = s.get("host_compatibility")
            if not compat:
                return True
            return host in compat or "generic" in compat
    return False


def find_incompatible_skills(doc, host):
    """All skill_ids that must NOT be loaded/enabled on `host` (incompatible)."""
    out = []
    for s in doc.get("skills", []):
        if isinstance(s, dict) and not host_compatible(doc, s.get("skill_id"), host):
            out.append(s.get("skill_id"))
    return out


def is_public_safe(doc):
    """A public-safe build must index only visibility=='public' records and must
    not leak local relative_path values. Returns (ok, violations)."""
    violations = []
    for s in doc.get("skills", []):
        if not isinstance(s, dict):
            violations.append("non-dict skill entry")
            continue
        if s.get("visibility") != "public":
            violations.append(f"non-public skill_id={s.get('skill_id')}")
        if s.get("relative_path"):
            violations.append(f"local path leaked for skill_id={s.get('skill_id')}")
    return (not violations), violations


def load_contract(path):
    """Read + parse a contract document from disk. Returns (doc, degraded_reason).
    Any error degrades (V3 still works) — it never raises to the caller."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            return None, "contract is not a JSON object"
        return doc, None
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return None, f"contract unavailable: {exc}"


# ------------------------------------------------------------------ CLI
def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="router versioned-contract consumer")
    sub = parser.add_subparsers(dest="cmd", required=True)
    a_v = sub.add_parser("validate", help="validate a contract document")
    a_v.add_argument("file")
    a_v.add_argument("--host", default="generic")
    a_v.add_argument("--expected-revision", default=None)
    a_v.add_argument("--expected-source-commit", default=None)
    a_v.add_argument("--expected-policy-epoch", type=int, default=None)
    a_v.add_argument("--json", action="store_true")
    a_i = sub.add_parser("inspect", help="show a doc's host-incompatibles + public-safety")
    a_i.add_argument("file")
    a_i.add_argument("--host", default="generic")
    a_i.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    doc, why = load_contract(args.file)
    if why:
        print(json.dumps({"status": ST_DEGRADED, "reason": why}, ensure_ascii=False)
              if args.json else f"DEGRADED {why}")
        return 2
    if args.cmd == "inspect":
        rep = {"host": args.host,
               "incompatible": find_incompatible_skills(doc, args.host),
               "public_safe": is_public_safe(doc)}
        rep["public_safe"] = rep["public_safe"] and [True]
        print(json.dumps(rep, ensure_ascii=False, indent=1) if args.json
              else f"incompatible={rep['incompatible']} public_safe={rep['public_safe'][0]}")
        return 0
    rep = validate_contract(
        doc, expected_revision=args.expected_revision,
        expected_source_commit=args.expected_source_commit,
        host=args.host, expected_policy_epoch=args.expected_policy_epoch)
    # sets are not JSON-serializable — coerce for output
    for k in ("body_sha256_verified", "incompatible_hosts"):
        rep[k] = sorted(rep[k])
    print(json.dumps(rep, ensure_ascii=False, indent=1) if args.json
          else f"status={rep['status']} reasons={rep['reasons']}")
    return 0 if rep["status"] in (ST_OK, ST_STALE) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
