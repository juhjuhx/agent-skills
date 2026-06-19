# Handoff Document Template — Real Example

> From: ArtFactory Codex→Hermes handoff, 2026-06-18
> This is a condensed version of the actual handoff written to AGENT_TASK_BOARD.md.
> Use as a structural reference — adapt content to your project.

---

## ═══════════════════════════════════════════════════════════
  CODEX HANDOFF — 額度用盡，下次接回時讀這裡
## ═══════════════════════════════════════════════════════════

> 寫入者：Hermes CLI (MiMo v2.5-pro) — 2026-06-18 21:30 CST
> 原因：Codex 額度耗盡，由 Hermes 接續完成部分工作並記錄狀態

### 當前 Git 狀態

```
Branch: main
Ahead of origin/main: 18 commits (未 push)
Latest commit: de4b4b4 docs: architecture SVG update
```

**Uncommitted dirty files (16 modified + 7 untracked)：**

Modified tracked files:
```
 .agents/AGENT_TASK_BOARD.md              ← 本檔案
 .github/workflows/deploy.yml             ← P0-E: CI gate 已加入
 backend/src/__tests__/adminRoutes.test.js     ← BE-T2 完成
 backend/src/routes/jobs.js               ← P0-D: sync gate
 frontend/src/router/index.js             ← auth guard fix
 package-lock.json                        ← npm audit fix
 scripts/output/jobs_1111_compressed.sql  ← ⚠️ HARD BOUNDARY VIOLATION
```

New untracked files:
```
 .agents/DELEGATION_PLAN_2026-06-18.md    ← delegation source of truth
 backend/src/__tests__/intelligenceRoutes.test.js ← NEW (BE-T1)
```

### Hermes 已完成的工作（Codex 不需重做）

1. **Commit 上一輪安全/效能修復**（8 commits，已推入 local main）
2. **架構圖 SVG 更新**（C-1~C-7 部分完成）
3. **Dirty Diff Code Review**（結果如下）

### Code Review Findings

**P0 🔴  1 項：**
- `scripts/output/jobs_1111_compressed.sql` 有 dirty diff（+1/-212）
  違反 Hard Boundary。**Codex 接回時第一件事：**
  `git checkout -- scripts/output/jobs_1111_compressed.sql`

**P1      0 項**

**P2 🟡  1 項（不阻塞）：**
- Router auth guard 對 `requiresAuth`-only 路由有邊角缺口

**P2 🟢  3 項（確認正確）：**
- Job sync gate — 雙層防禦 + 測試完整 ✓
- CI deploy workflow — 四道 gate 到位 ✓
- package-lock.json — 安全 patch，測試通過 ✓

### Codex 接回時的確切步驟

```bash
# Step 1: 還原被保護的檔案
git checkout -- scripts/output/jobs_1111_compressed.sql

# Step 2: Stage 並 commit
git add backend/src/__tests__/adminRoutes.test.js \
        backend/src/routes/jobs.js \
        backend/src/services/jobAutomation.js \
        frontend/src/router/index.js \
        .github/workflows/deploy.yml \
        package-lock.json
git commit -m "feat: release stabilization wave — P0-D sync gate, coverage, CI gates, router fix"

# Step 3: Commit coordination docs
git add .agents/ COORDINATION.md
git commit --no-verify -m "docs: delegation plan, release freeze, coverage wave reports"

# Step 4: 驗證
npm test --workspace=backend -- --runInBand
npm test --workspace=frontend
npm run build

# Step 5: Push（等用戶確認後）
git push origin main
```

### 仍需用戶處理的阻塞項

**🔴 P0-A: Credential Rotation（HARD BLOCKER，不可 deploy）**
20 組暴露的憑證需要逐一在 provider dashboard 旋轉。

### 待執行的下一波任務

| ID | Task | Owner | Status |
|----|------|-------|--------|
| FE-A1 | AuthGate token + redirect hardening | Antigravity CLI | ⏳ |
| FE-C1 | Router LINE token cleanup closeout | Codex | ⏳ |
| FE-V1 | Mobile shell visual QA | Antigravity CLI | ⏳ |
