---
name: skill-desc-optimizer
description: "Optimize skill descriptions for better routing. Use when: improve skill triggers, fix routing issues, update descriptions."
version: 1.0.0
author: Agnes + Hermes
license: MIT
tags: [optimization, skills, routing, descriptions]
related_skills: [skill-authoring, auto-learn, using-superpowers, skill-optimizer]
---

# Skill Description Optimizer

基於成功 skills 的模式優化描述和觸發詞，提升技能路由準確性。

## 核心原則

從 theater-projection-design 和 visual-atelier 提取的成功模式：

### 1. Description 格式
```yaml
description: "核心功能。Use when: [觸發條件1]、[觸發條件2]、[關鍵字]。"
```

### 2. 觸發詞策略
- **中英文混合**：同時包含英文和中文關鍵字
- **不同表述**：同一概念的多种说法（如"劇場投影"、"projection design"、"stage imagery"）
- **口語與正式**：涵蓋不同用戶表達方式
- **長尾詞**：包含具體功能詞（如"upscale to 8K"、"scene cue"）

### 3. 長度控制
- **系統提示**：≤ 60 字元（被截斷為 57 字 + "..."）
- **完整描述**：≤ 1024 字元（完整內容放在 skill body）
- **優先級**：路由信號在前，詳細說明在後

## 成功範例分析

### 範例 1: theater-projection-design
```yaml
description: "Theater projection design: AI image generation pipelines for stage projections. Use when: 劇場投影、projection design、stage imagery、生成投影圖、theater visuals、scene cue、upscale to 8K、投影設計、舞台投影。"
```

**成功要素**：
1. 核心功能前置（AI image generation pipelines）
2. 明確的 Use when 列表
3. 中英文混合
4. 涵蓋不同層級（theater → projection → design）
5. 包含具體功能詞（upscale to 8K、scene cue）

### 範例 2: visual-atelier
```yaml
description: "超級視覺引擎 — 將文字/數據轉為簡報、圖表、信息圖、動態投影片。Use when: 做簡報、PPT、slides、infographic、分鏡、數據視覺化、storyboard、視覺化。融合 20+ Skills，四種輸出模式，三旋鈕設計調控。"
```

**成功要素**：
1. 中文描述在前（符合用戶語言偏好）
2. 明確的功能範圍（簡報、圖表、信息圖）
3. 強調獨特價值（融合 20+ Skills）
4. 包含技術特權（三旋鈕調控）

## 優化流程

### Step 1: 分析現有描述
檢查條件：
- [ ] 長度是否 ≤ 1024 字元
- [ ] 是否包含 Use when
- [ ] 是否包含中英文觸發詞
- [ ] 是否列出 related_skills
- [ ] 是否有清晰的 tags

### Step 2: 識別問題模式

| 問題類型 | 特徵 | 優化建議 |
|---------|------|---------|
| 描述模糊 | 只有概述，沒有具體功能 | 添加 Use when 和關鍵字 |
| 觸發詞太少 | 只有一個語言版本 | 添加中英文混合觸發詞 |
| 結構不清 | 沒有 When to Use、Pitfalls 等 | 重構為標準格式 |
| 缺少關聯 | 沒有 related_skills | 添加相關 skills 引用 |
| Tags 不足 | 標籤太少或太泛 | 添加 5-8 個精確標籤 |

### Step 3: 應用優化模板

```yaml
---
name: skill-name
description: "核心功能。Use when: [觸發1]、[觸發2]、[中文關鍵字]。"
version: X.X.X
author: [Creator]
license: MIT
tags: [tag1, tag2, tag3, tag4, tag5]
related_skills: [related1, related2]
---

# Title

## When to Use
- [具體使用場景 1]
- [具體使用場景 2]
- [具體使用場景 3]

## Core
[核心功能描述，2-3 句]

## Pitfalls
- [常見問題 1]
- [常見問題 2]
- [常見問題 3]

## Examples
[使用示例或工作流程]
```

### Step 4: 驗證優化效果

使用以下檢查清單：
- [ ] Description ≤ 1024 字元
- [ ] 包含中英文觸發詞
- [ ] 有 Use when 或 When to Use
- [ ] 有 related_skills 關聯
- [ ] 有清晰的 tags（5-8 個）
- [ ] 結構清晰易讀
- [ ] 與現有 skills 不重複

## 自動化檢查腳本

創建檢查腳本：`~/.local/bin/skill-desc-check`

```bash
#!/bin/bash
# 檢查 skill description 質量
SKILL_FILE="$1"

if [ -z "$SKILL_FILE" ]; then
  echo "Usage: $0 <skill-file.md>"
  exit 1
fi

echo "=== Skill Description Quality Check ==="
echo "File: $SKILL_FILE"
echo ""

# 提取 description
desc=$(grep "^description:" "$SKILL_FILE" 2>/dev/null | head -1)
echo "Description: $desc"
echo "Length: ${#desc} chars"
echo ""

# 檢查必要元素
checks=(
  "Use when|use when"
  "related_skills"
  "tags:"
  "When to Use"
)

for check in "${checks[@]}"; do
  if grep -qi "$check" "$SKILL_FILE"; then
    echo "✓ Found: $check"
  else
    echo "✗ Missing: $check"
  fi
done
```

## 與 Auto-Learn 的協同

當 auto-learn 識別出新工作流程時：
1. 創建 skill 草稿
2. 使用本 skill 優化 description
3. 與用戶確認後正式創建
4. 更新相關 skills 的 related_skills 列表

## Pitfalls

1. **不要過度優化** — 保持 description 簡潔
2. **不要忽視中文** — 用戶主要使用繁體中文
3. **不要重複** — 檢查是否與現有 skills 功能重疊
4. **不要忘記驗證** — 優化後必須用 skill_view 驗證

## 相關 Skills

- `skill-authoring` — Skill 撰寫規範
- `auto-learn` — 自動學習工作流程
- `using-superpowers` — 自動掃描和匹配 skills
- `skill-optimizer` — 基於 SkillOpt 的進階優化（8+ learn-rule rows）

---

*此 skill 確保每個 skill 都能被正確識別和路由，提升整體工作效率。*