# Read-Only Project Audit Pattern

> Proven workflow from ArtFactory audit (2026-06-25).
> Use when user says "先不要修改檔案，先回報" or "read-only review".

## Procedure

### Step 1: Read Required Files (5 files)

Read in this order — each provides different context:

1. `AGENTS.md` — agent instructions, commands, hard boundaries
2. `CLAUDE.md` — architecture, conventions, test accounts
3. `ARCHITECTURE.md` — design intent, data flow, DB schema
4. `COORDINATION.md` — current release status, blockers, locks
5. `.agents/AGENT_TASK_BOARD.md` — agent assignments, dirty files, progress

### Step 2: Run Verification Commands

```bash
# Git state
git status --short | head -50
git log --oneline -5
git rev-list --left-right --count origin/main...main

# Tests
npm test --workspace=backend -- --runInBand --silent 2>&1 | tail -8
npm test --workspace=frontend -- --run 2>&1 | tail -8

# Build
npm run build 2>&1 | tail -5

# Security
npm audit --omit=dev 2>&1 | tail -3
git ls-files | grep -E '\.env($|\.(local|production|development)$)'

# Production
curl -sS --max-time 10 {URL}/health
curl -sS --max-time 10 -o /dev/null -w "HTTP %{http_code}" {URL}/

# Coverage
npm run test:coverage --workspace=backend -- --runInBand --silent 2>&1 | grep "All files"
```

### Step 3: Code-Level Checks (Read-Only)

```bash
# Security patterns
grep -n "unsafe-inline\|unsafe-eval" {entry_file}
grep -n "req.body" {route_files}  # mass assignment
grep -n "sanitize\|escape" {middleware_files}

# Architecture
wc -l {service_files}  # god objects (>500 lines)
ls {pages_dir} | wc -l  # page count vs test count
```

### Step 4: Compile Report

Report structure:

```
═══ {Project} 只讀審計報告 ═══
審計時間：{timestamp}

## 一、Git 狀態
(branch, ahead/behind, dirty files, protected files)

## 二、測試結果
(table: layer, suites, tests, status)

## 三、建置
(code splitting, bundle sizes, build time)

## 四、生產環境
(table: endpoint, status, response)

## 五、問題清單
For EACH finding:
  ### {severity} {ID}: {title}
  **影響範圍**：{scope}
  **位置**：{file}:{line}
  **可重現**：{command}
  **現狀**：{what's wrong}
  **風險**：{impact}
  **建議修復**：{fix approach}
  **建議修改檔案**：{files}
  **驗收測試**：{test command + expected result}

## 六、優先級
🔴 最優先 → 🟠 次優先 → 🟡 中優先 → 🟢 低優先

## 七、驗收清單
- [ ] {check 1}
- [ ] {check 2}
```

## Severity Levels

| Level | Symbol | Meaning | Examples |
|-------|--------|---------|---------|
| Critical | 🔴 | Blocks release or has active exploit | Credential leak, SQL injection, mass assignment |
| High | 🟠 | Security risk or data integrity issue | CSP weakness, XSS vector, auth bypass |
| Medium | 🟡 | Quality/maintainability issue | God object, missing tests, code smell |
| Low | 🟢 | Improvement opportunity | Refactoring, documentation, optimization |

## Report Format Rules

1. **Every finding MUST have**: 影響範圍, 可重現方式, 建議修改檔案, 驗收測試
2. **Use tables** for structured data (git status, test results, endpoints)
3. **Use code blocks** for exact commands to reproduce
4. **Don't suggest fixes that require writing files** — this is read-only
5. **Mark protected/sensitive files** with ⚠️
6. **Include production URL** for health checks

## Pitfalls

- **Don't run destructive commands** — no `git reset`, `npm audit fix --force`, `git push`
- **Don't print secrets** — redact .env content, tokens, passwords
- **Don't modify any file** — read-only means read-only
- **Don't stage/commit** — even if you see obvious fixes
- **Do verify protected files are untracked** — `git ls-files SECURITY_REMEDIATION_PLAN.md` should return empty
- **Do check git history for leaked secrets** — `git log --all --onelist -- .env.production`
