---
name: language-debugging
description: "Debug Python and Node.js: pdb, debugpy, node inspect, CDP. Use when: debug Python, debug Node.js, pdb, debugpy, node inspect, breakpoints, post-mortem."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Debugging, Python, Node.js, pdb, debugpy, node-inspect, CDP, Breakpoints]
    related_skills: [systematic-debugging, test-driven-development]
---

# Language Debugging

Debug Python and Node.js code from the terminal. Two language-specific toolkits — pick based on the codebase.

## Section 1: Python Debugging (pdb + debugpy)

Three tools, picked by situation:

| Tool | When |
|------|------|
| `breakpoint()` + pdb | Local, interactive, simplest |
| `python -m pdb` | Launch script under pdb with no source edits |
| `debugpy` | Remote / headless / attach to already-running process |

**Start with `breakpoint()`.** It's the cheapest thing that works.

### pdb Quick Reference

| Command | Action |
|---------|--------|
| `n` | next line (step over) |
| `s` | step into |
| `r` | return from current function |
| `c` | continue |
| `l` / `ll` | list source / full function |
| `w` | where (stack trace) |
| `u` / `d` | move up / down in stack |
| `p expr` / `pp expr` | print / pretty-print |
| `b file:line` | set breakpoint |
| `b file:line, cond` | conditional breakpoint |
| `interact` | drop into full Python REPL in current scope |
| `!stmt` | execute arbitrary Python |
| `q` | quit |

### Recipe 1: Local breakpoint

```python
def compute(x, y):
    result = some_helper(x)
    breakpoint()           # <-- drops into pdb here
    return result + y
```

**Don't forget to remove before committing:** `rg -n 'breakpoint()' --type py`

### Recipe 2: Debug pytest

```bash
pytest tests/test.py::test_name --pdb -p no:xdist  # Drop to pdb on failure
pytest tests/test.py::test_name --trace              # Drop at START of test
```

**pdb does NOT work under xdist** — always use `-p no:xdist` or `-n 0`

### Recipe 3: Post-mortem

```python
import pdb, sys
try:
    run_the_thing()
except Exception:
    pdb.post_mortem(sys.exc_info()[2])
```

### Recipe 4: Remote debug with debugpy

```python
import debugpy
debugpy.listen(("127.0.0.1", 5678))
debugpy.wait_for_client()
debugpy.breakpoint()
```

Or attach to running process:
```bash
python -m debugpy --listen 127.0.0.1:5678 --pid <pid>
```

**For terminal-friendly remote debugging:** Use `remote-pdb` instead:
```python
from remote_pdb import set_trace
set_trace(host="127.0.0.1", port=4444)
# Then: nc 127.0.0.1 4444
```

## Section 2: Node.js Debugging (node inspect + CDP)

Two tools:

| Tool | When |
|------|------|
| `node inspect` | Built-in, zero install, CLI REPL |
| CDP via `chrome-remote-interface` | Scriptable, automated breakpoints |

**Prefer `node inspect` first.** Always available.

### node inspect Quick Reference

```bash
node inspect path/to/script.js
node --inspect-brk $(which tsx) path/to/script.ts  # TypeScript
```

| Command | Action |
|---------|--------|
| `c` / `cont` | continue |
| `n` / `next` | step over |
| `s` / `step` | step into |
| `o` / `out` | step out |
| `sb('file.js', 42)` | set breakpoint |
| `sb('functionName')` | break on function call |
| `cb('file.js', 42)` | clear breakpoint |
| `bt` | backtrace |
| `list(5)` | show 5 lines around current |
| `repl` | drop into REPL in current scope |
| `exec expr` | evaluate expression |
| `pause` | pause running code |

### Attaching to Running Process

```bash
kill -SIGUSR1 <pid>  # Enable inspector
node inspect -p <pid>
```

### Programmatic CDP

```javascript
const CDP = require('chrome-remote-interface');
const client = await CDP({ port: 9229 });
const { Debugger, Runtime } = client;

Debugger.paused(async ({ callFrames }) => {
    const top = callFrames[0];
    console.log(`PAUSED @ ${top.url}:${top.location.lineNumber + 1}`);
    // Walk scopes for locals
    for (const scope of top.scopeChain) {
        if (scope.type === 'local') {
            const { result } = await Runtime.getProperties({
                objectId: scope.object.objectId, ownProperties: true
            });
            for (const p of result) {
                console.log(`  ${p.name} =`, p.value?.value);
            }
        }
    }
    await Debugger.resume();
});

await Debugger.enable();
await Debugger.setBreakpointByUrl({ urlRegex: '.*app\\.tsx$', lineNumber: 119 });
await Runtime.runIfWaitingForDebugger();
```

### TypeScript Note

Breakpoints hit emitted JS, not `.ts`. Either:
- Break in `dist/*.js`
- Enable sourcemaps: `node --enable-source-maps`

---

## Common Pitfalls

1. **pdb under xdist silently does nothing** — always use `-p no:xdist`
2. **`breakpoint()` in CI hangs** — safe locally; never commit it
3. **`PYTHONBREAKPOINT=0`** disables all breakpoints — check env
4. **debugpy attach fails on hardened kernels** — `ptrace_scope=1` blocks injection
5. **Node `--inspect` vs `--inspect-brk`** — `--inspect` doesn't pause; use `-brk` to set breakpoints first
6. **Port collisions** — use `--inspect=0` for random port, check `/json/list`
7. **Child processes** — `--inspect` on parent doesn't inspect children; use `NODE_OPTIONS`

## Verification Checklist

- [ ] Correct tool chosen for the situation
- [ ] `breakpoint()` removed before committing
- [ ] `-p no:xdist` used with pytest + pdb
- [ ] Port confirmed listening for remote debug
- [ ] Breakpoint actually hits (check PYTHONBREAKPOINT, xdist, timing)
- [ ] Post-debug cleanup: no stray `breakpoint()` / `set_trace()`
