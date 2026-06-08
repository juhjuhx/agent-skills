---
id: py-set-add-in-loop-large-n
title: set.add() over a stream — unbounded memory; use HyperLogLog if you only need the count
severity: info
impact: MEDIUM
impactDescription: Suboptimal; flag when n is large or on a hot path
language: python
tags: python, info, mathguard
---

# set.add() over a stream — unbounded memory; use HyperLogLog if you only need the count

Accumulating every item into a `set` to count distinct values over an unbounded stream grows memory with the cardinality — at billions of distinct items the set alone is hundreds of gigabytes and OOMs. When the caller only needs the *count* (and tolerates small error), HyperLogLog estimates cardinality in kilobytes.

## Fix

If you only need the count of distinct items, use a probabilistic cardinality estimator (HyperLogLog, e.g. datasketch). If you need membership of a bounded set, this is fine — ignore.

## Incorrect

```python
# Memory grows with cardinality — OOMs at billions of distinct IPs
seen = set()
for line in log_stream:
    seen.add(line.split()[0])
return len(seen)
```

## Correct

```python
# ~12 KB regardless of cardinality; ~0.8% standard error at p=14
from datasketch import HyperLogLog

hll = HyperLogLog(p=14)
for line in log_stream:
    hll.update(line.split()[0].encode('utf-8'))
return int(hll.count())
```

## Escalate to

If this pattern is widespread in the codebase, load **mathguard** for the corrective workflow.
