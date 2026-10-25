# Python `unittest` fixture gotchas

Concrete pitfalls that turn a correctly-*designed* hermetic fixture into a red
or miscounted test. Each is a generalizable rule with the mechanism in one
clause.

## `TemporaryDirectory` lifetime

`with tempfile.TemporaryDirectory():` **inside `setUpClass` deletes the dir
before any test runs.** The `with` block exits at the end of `setUpClass`, so
every test then hits `KeyError`/`FileNotFound` on a fixture that is already
gone. Keep the `TemporaryDirectory()` object on the class and `cleanup()` it
in `tearDownClass`:

```python
def setUpClass(cls):
    cls._tmp = tempfile.TemporaryDirectory()   # object survives the method
    root = pathlib.Path(cls._tmp.name)
    # write fixture records under root ...        # still present during tests

def tearDownClass(cls):
    cls._tmp.cleanup()
```

Mechanism: `with` owns the context manager; the dir lives only for the `with`
body, and `setUpClass`'s body ends the moment the method returns.

## Class-level function reference binds as a method

Assigning a **module function** to a class attribute and calling it through an
instance auto-binds it, because Python's descriptor protocol wraps the plain
function in a bound method:

```python
def setUpClass(cls):
    cls._safe = composer._safe      # module-level function
def test_something(self):
    self._safe(root, rel)          # TypeError: _safe() takes 2 positional
                                   # arguments but 3 were given
```

`self._safe` is now a bound method with `self` already consumed, so the call
passes 3 args where 2 are expected.

- **Call through the owning object**: `self._composer._safe(root, rel)`.
- Or expose it via a **non-function wrapper** (a `lambda` or a method) so the
  descriptor binding does not apply.

Mechanism: functions defined at module/class scope are descriptors; accessed
through an instance they return a bound method, not the raw function.

## Exact-count assertion hygiene

When a test computes a total, derive the expected value **from the same
helper the implementation uses** rather than a hand count:

```python
# bad — literal went stale the day the catalog grew
self.assertEqual(reconcile['ACTIVE_COUNT'], 350)

# good — recompute from the same source the SUT reads
expected = sum(1 for r in records if r['status'] == 'active')
self.assertEqual(reconcile['ACTIVE_COUNT'], expected)
```

Mechanism: a hardcoded literal is a snapshot; the data it describes keeps
moving, and the mismatch surfaces as a confusing "why did this suddenly
fail" on the first run after a data change.

## CJK / mixed-locale tokenization

If the SUT tokenizes user text for search and your tests exercise CJK or
CamelCase input, two traps:

- **Single-character noise.** Splitting CamelCase (`MyCase` → `My`+`Case`)
  can emit one-letter tokens that pollute the index. Filter tokens by
  `len(token) >= 2` before ranking.
- **CJK has no whitespace word boundaries.** Naive `.split()` yields whole
  runs as one token. Use bigrams (or the library's CJK segmenter) so a query
  shares tokens with the index; add a small alias table for common synonyms so
  recall doesn't depend on the exact surface form.

Mechanism: a tokenizer that the production ranking and the test fixture use
differently will rank divergently, so "correct" expected hits become false
negatives in the test while the real engine behaves differently.

## Real-execution isolation (when the SUT has env-var state roots)

For a REAL end-to-end run of a pipeline whose state binds to env vars, the
"never read the real location" rule is satisfied by REDIRECTING, not faking:

```python
iso = tempfile.mkdtemp(prefix="e2e-")
os.environ["SCHED_STATE"]  = iso + "/schedstate"
os.environ["SCOUT_STATE"]  = iso
# spawn the real CLI/subprocess — it re-binds module constants from env at
# its OWN import, so no in-process reload dance is needed
```

- The subprocess is the honest target: it re-binds module-level constants from
  env at its own import. Testing an in-process module that cached its state
  paths at first import requires `sys.modules.pop(...)` + re-exec of the
  module spec after changing the env vars — otherwise your "isolated" run
  silently writes the live state.
- Evidence to record: `exit code`, the last structured event line of stdout,
  and the cursor/record count. Then `shutil.rmtree(iso)` and confirm no new
  files appeared under the live private layers (the isolation proof).
- A run that exercises the network path (e.g. `--github`) is the only thing
  that proves upstream scanning works; a fixture-backed run must be reported
  as offline, never as proof of the upstream path.
