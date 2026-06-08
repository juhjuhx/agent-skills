---
name: visual-atelier
description: "超級視覺引擎 — 將文字/數據轉為簡報、圖表、信息圖、動態投影片。Use when: 做簡報、PPT、slides、infographic、分鏡、數據視覺化、storyboard、視覺化。融合 20+ Skills，四種輸出模式，三旋鈕設計調控。"
---

# Visual Atelier v2 — 超級視覺工作坊

> 將文字、圖片、數據轉化為充滿設計感與藝術感的視覺作品。融合 20+ Skills，提供四種輸出模式，配備三旋鈕動態設計調控系統、五種動作種子動畫引擎、生成藝術引擎、3D 場景渲染、以及五層品質審查。

---

## 何時使用

- 需要將文章/口播稿變成簡報
- 需要將結構/流程變成圖表
- 需要將數據/文章變成信息圖
- 需要將場景描述變成分鏡
- 需要任何形式的視覺化輸出
- 需要 3D 場景、生成藝術、動態動畫
- 需要 Awwwards 級別的前端設計

---

## 四種輸出模式

| 模式 | 輸入 | 輸出 | 適用情境 |
|:---|:---|:---|:---|
| **Presentation** | 文字內容 | HTML 簡報（.html） | 會議、提案、教學、分享 |
| **Diagram** | 結構/流程描述 | SVG 圖表（.svg） | 架構圖、流程圖、心智圖、時間軸 |
| **Infographic** | 數據/文章 | 圖像（.png） | 社群媒體、報告、簡報配圖 |
| **Storyboard** | 場景描述 | 序列圖像 + 文字 | 電影、動畫、劇場、產品展示 |

---

## ★ 三旋鈕動態設計調控系統（源自 taste-skill）

> 每次生成前，先推斷 Brief，再設定三旋鈕。所有佈局、動畫、密度決策均由旋鈕驅動。

### 旋鈕定義

| 旋鈕 | 範圍 | 說明 |
|:---|:---|:---|
| **DESIGN_VARIANCE** | 1-10 | 1 = 完美對稱，10 = 藝術混沌 |
| **MOTION_INTENSITY** | 1-10 | 1 = 靜態，10 = 電影級/物理動畫 |
| **VISUAL_DENSITY** | 1-10 | 1 = 藝術畫廊/空氣感，10 = 駕駛艙/密集數據 |

**基準值：** `8 / 6 / 4`（除非 Brief 指示否則使用）

### 旋鈕推斷表

| 場景 | VARIANCE | MOTION | DENSITY |
|:---|:---|:---|:---|
| 劇場投影設計（預設） | 9 | 8 | 3 |
| 極簡/乾淨/編輯風 | 5-6 | 3-4 | 2-3 |
| 高級消費者/Apple 風 | 7-8 | 5-7 | 3-4 |
| 實驗性/Awwwards | 9-10 | 8-10 | 3-4 |
| 數據儀表板 | 4-5 | 3-4 | 7-8 |
| 簡報/教學 | 6-7 | 5-6 | 3-4 |
| 社群媒體圖卡 | 7-8 | 4-5 | 4-5 |

### Brief 推斷流程

1. **分析頁面類型** — 簡報、圖表、信息圖、分鏡
2. **識別語調詞** — "極簡"、"奢華"、"實驗性"、"劇場感"
3. **確認受眾** — 專業觀眾 vs 大眾 vs 藝術場域
4. **輸出一行 Design Read** — "以 [類型] 形式為 [受眾]，採用 [語調] 語言，偏向 [美學方向]"
5. **設定三旋鈕** — 根據推斷表

---

## ★ 五種動作種子動畫引擎（源自 styleseed）

> 所有動畫都基於五種性格驅動的種子，每種適用於不同場景。

### 種子定義

| 種子 | 氣質 | 適用場景 |
|:---|:---|:---|
| **Spring** | 彈性、活力、俏皮 | CTA 按鈕、成功狀態、活潑元素 |
| **Silk** | 絲滑、優雅、連續 | 編輯排版、金融儀表板、正式簡報 |
| **Snap** | 瞬間、果斷、精確 | 工具 UI、鍵盤操作、指令面板 |
| **Float** | 輕盈、柔和、夢幻 | 行銷頁面、英雄區域、氛圍 UI |
| **Pulse** | 節奏、律動、脈搏 | 通知、即時動態、狀態指示 |

### 五種上下文

| 上下文 | 返回值 | 用途 |
|:---|:---|:---|
| `entrance` | `{ initial, animate, transition }` | 進場動畫 |
| `exit` | `{ exit, transition }` | 退場動畫 |
| `hover` | `{ whileHover, transition }` | 懸停效果 |
| `press` | `{ whileTap, transition }` | 點擊效果 |
| `layout` | `{ layout: true, transition }` | FLIP 版面重排 |

**5 種子 × 5 上下文 = 25 種即用動畫變體。**

### 動畫種子 → 語意映射

| 自然語言 | 種子 |
|:---|:---|
| 彈性、活潑、有生命力 | Spring |
| 絲滑、流暢、優雅、沉穩 | Silk |
| 清脆、快速、果斷、精確 | Snap |
| 輕盈、柔和、夢幻、漂浮 | Float |
| 節奏、脈搏、律動、心跳 | Pulse |

### 動畫效能規則（源自 fixing-motion-performance）

- **只動畫化合成層屬性**：`transform`、`opacity`
- **禁止動畫化版面屬性**：`width`、`height`、`top`、`left`、`margin`、`padding`
- **入場使用 `ease-out`**
- **互動回饋不超過 200ms**
- **尊重 `prefers-reduced-motion`**
- **循環動畫在離開視口時暫停**
- **使用 `IntersectionObserver` 或 Motion 的 `whileInView`，禁止 `scroll` 事件監聽**

---

## ★ 創意變異引擎（源自 soft-skill）

> 每次生成前「擲骰子」，選擇獨特的美學組合，確保輸出永不重複。

### A. 氣質與質感原型（選 1）

| 原型 | 適用場景 | 色彩 | 字體 | 質感 |
|:---|:---|:---|:---|:---|
| **空靈玻璃** | SaaS / AI / 科技 | 深黑 `#050505` + 紫/翠光暈 | 幾何 Grotesk | `backdrop-blur-2xl` + 極細描邊 |
| **編輯奢華** | 生活 / 房地產 / 代理商 | 暖奶油 `#FDFBF7` + 鼠尾草 | 變數 Serif | CSS 噪聲覆蓋 `opacity-[0.03]` |
| **柔軟結構主義** | 消費者 / 健康 / 作品集 | 銀灰/全白 | 粗體 Grotesk | 極柔擴散陰影 |
| **劇場暗黑** | 劇場投影（預設） | 暖金赭 + 深靛藍 | Noto Serif TC + Playfair Display | SVG 紋理 + 動態光影 |

### B. 佈局原型（選 1）

| 原型 | 描述 |
|:---|:---|
| **不對稱便當格** | CSS Grid 混合格子大小（如 `col-span-8 row-span-2` + `col-span-4` 堆疊） |
| **Z 軸層疊** | 元素如實體卡片般堆疊，略微重疊，配合微妙旋轉 |
| **編輯分割** | 左半巨大字型，右半互動式水平滾動內容 |
| **對角流動** | 元素沿對角線排列，打破數位網格 |

### C. 觸覺微美學

- **雙重邊框（Double-Bezel）**：外層包裝 + 內層核心，模擬物理加工質感
- **嵌套 CTA 按鈕**：全圓角膠囊 + 內嵌圖示圓圈
- **巨觀留白**：區塊間距 `py-24` 到 `py-40`
- **標籤徽章**：在主要標題前添加微小膠囊徽章 `rounded-full px-3 py-1 text-[10px] uppercase`

---

## ★ 設計令牌架構（源自 styleseed）

### 三層令牌系統

```
Primitive（原始值）→ Semantic（語意別名）→ Component（元件專用）
```

**範例：**
```css
/* Primitive */
--color-warm-gold: #a87b3a;
--color-deep-indigo: #1a2b4a;

/* Semantic */
--color-accent-primary: var(--color-warm-gold);
--color-bg-dramatic: var(--color-deep-indigo);

/* Component */
--slide-title-color: var(--color-accent-primary);
--slide-bg: var(--color-bg-dramatic);
```

### 五級灰階文字層級

| 層級 | 色值 | 用途 |
|:---|:---|:---|
| **Strong** | `#2A2A2A` | 最強調（數據中心值、標題） |
| **Primary** | `#3C3C3C` | 指標、區塊標題 |
| **Secondary** | `#6A6A6A` | 標籤、說明文字 |
| **Tertiary** | `#7A7A7A` | 副標題、日期 |
| **Disabled** | `#9B9B9B` | 非活躍狀態 |

> **關鍵規則**：純黑 `#000` 永不使用。以 `#2A2A2A` 作為精緻黑。

### 陰影系統

- 陰影透明度 4-8%，幾乎不可見
- 卡片內部使用 `inset` 陰影模擬深度
- 避免 `shadow-md` 以上的粗糙陰影

---

## ★ 生成藝術引擎（源自 algorithmic-art）

> 為 Diagram 和 Storyboard 模式提供 p5.js 生成藝術能力。

### 適用場景

- **Diagram 模式**：用生成藝術替代傳統 SVG，創造有機流場圖表
- **Storyboard 模式**：為每個場景生成算法化的視覺元素
- **Presentation 模式**：背景動態生成藝術效果

### 技法庫

| 技法 | 描述 | 適用 |
|:---|:---|:---|
| **流場（Flow Fields）** | Perlin 噪聲驅動的向量場 + 粒子追蹤 | 有機背景、路徑圖 |
| **粒子系統** | 大量粒子遵循力場法則 | 數據視覺化、動態圖表 |
| **分形遞迴** | 自相似結構的數學之美 | 架構圖、層級結構 |
| **沃羅諾伊（Voronoi）** | 空間分割的自然韻律 | 地圖、區域劃分 |
| **反應擴散** | 化學反應模式（Turing Pattern） | 紋理背景、有機圖案 |
| **參數曲線** | Lissajous、Spirograph 數學曲線 | 裝飾元素、標誌設計 |

### 使用方式

1. 先寫「算法哲學」（.md）— 命名運動、闡述理念
2. 再寫 p5.js 草圖（.html + .js）— 90% 算法生成，10% 參數控制
3. 使用 `seed` 控制隨機性，確保可重現

---

## ★ 3D 場景能力（源自 threejs-*）

> 為 Presentation 和 Storyboard 模式提供 Three.js 3D 渲染。

### 十大技能模組

| 模組 | 能力 |
|:---|:---|
| `threejs-fundamentals` | 場景、相機、渲染器設定 |
| `threejs-geometry` | 幾何體創建與變形 |
| `threejs-materials` | 材質系統（PBR、自定義 Shader） |
| `threejs-lighting` | 光照模型（環境光、點光、聚光、HDRI） |
| `threejs-animation` | 動畫系統（關鍵幀、變形目標、骨骼） |
| `threejs-shaders` | GLSL 自定義著色器 |
| `threejs-postprocessing` | 後處理效果（Bloom、DOF、色調映射） |
| `threejs-textures` | 紋理載入與管理 |
| `threejs-loaders` | 3D 模型載入（GLTF、FBX、OBJ） |
| `threejs-interaction` | 互動（Raycaster、拖拽、軌道控制） |

### 適用場景

- **劇場投影設計**：3D 場景重建、即時投影映射
- **產品展示**：360° 旋轉展示
- **數據視覺化**：3D 圖表、地形圖
- **分鏡預覽**：3D 場景預覽與攝影機動畫

---

## 工作流

### Step 0：Brief 推斷（新增）

在任何設計工作之前：

1. **分析輸入類型** — 敘述性 / 結構性 / 數據性 / 場景性
2. **識別語調詞** — 使用者提到的風格關鍵詞
3. **確認受眾與場域**
4. **輸出 Design Read** — 一行話概括設計方向
5. **設定三旋鈕** — DESIGN_VARIANCE / MOTION_INTENSITY / VISUAL_DENSITY
6. **選擇創意組合** — 氣質原型 × 佈局原型

### Step 1：分析輸入

- **敘述性內容**（故事、文章、口播稿）→ Presentation 或 Storyboard
- **結構性內容**（系統、流程、關係）→ Diagram
- **數據性內容**（統計、比較、摘要）→ Infographic
- **場景性內容**（電影、動畫、劇場）→ Storyboard

### Step 2：推薦模式

向使用者推薦最適合的輸出模式，確認後執行。

### Step 3：生成輸出

根據選定的模式，調用對應的 Skills：

**Presentation 模式（5 核心 + 5 增強）：**
- `html-ppt`：PPT 框架（36 主題、31 版型、鍵盤導航、演講者模式）
- `frontend-design`：視覺美學（排版、色彩、動畫、空間構圖）
- `cinema-worldbuilder`：場景敘事（M5 Atmospheric 模式）
- `ui-ux-pro-max`：使用者體驗（設計模式、可訪問性）
- `web-video-presentation`：動畫效果（逐步揭示、進度條、過渡）
- ★ `taste-skill`：三旋鈕調控 + Design System Map
- ★ `soft-skill`：Awwwards 級觸覺微美學
- ★ `styleseed`：設計令牌架構 + 動作種子
- ★ `algorithmic-art`：生成藝術背景
- ★ `threejs-*`：3D 場景渲染

**Diagram 模式（2 核心 + 3 增強）：**
- `baoyu-diagram`：SVG 圖表（9 種類型、暗色主題）
- `frontend-design`：視覺品質
- ★ `algorithmic-art`：生成藝術圖表（流場、Voronoi、分形）
- ★ `styleseed`：設計令牌 + 色彩系統
- ★ `taste-skill`：佈局變異

**Infographic 模式（2 核心 + 3 增強）：**
- `baoyu-infographic`：信息圖（21 版型 × 22 風格）
- `baoyu-slide-deck`：幻燈片圖像生成
- ★ `styleseed`：69 條視覺設計規則
- ★ `soft-skill`：雙重邊框 + 觸覺美學
- ★ `brandkit`：品牌套件生成

**Storyboard 模式（3 核心 + 4 增強）：**
- `cinema-worldbuilder`：場景構圖（5 cinema mode）
- `baoyu-slide-deck`：序列圖像生成
- `web-video-presentation`：節奏控制
- ★ `threejs-animation`：3D 場景動畫
- ★ `algorithmic-art`：生成藝術分鏡
- ★ `styleseed`：動作種子（5 種動畫氣質）
- ★ `image-to-code-skill`：參考圖 → 程式碼實現

### Step 4：五層品質審查（增強版）

| 層級 | 審查內容 | 來源 Skill |
|:---|:---|:---|
| **L1 語義正確性** | HTML 語義、ARIA 標籤、SEO | `code-review-excellence` |
| **L2 可訪問性** | WCAG 2.2 AA、鍵盤導航、色彩對比 | `fixing-accessibility` |
| **L3 動畫效能** | 合成層屬性、`prefers-reduced-motion`、視口暫停 | `fixing-motion-performance` |
| **L4 視覺品質** | 設計令牌一致性、排版層級、留白比例 | `baseline-ui` |
| **L5 代碼品質** | 複雜度分析、邏輯正確性、效能瓶頸 | `complexity-cuts` + `logic-lens` |

### Step 5：交付

將最終產出交付給使用者。

---

## 設計原則

### 排版（強化版）

- **禁用字體**：Inter、Roboto、Arial、Open Sans、Helvetica、系統字體
- **推薦展示字體**：Geist、Clash Display、PP Editorial New、Plus Jakarta Sans
- **中文**：Noto Sans TC / Noto Serif TC
- **英文**：Playfair Display / DM Serif Display / DM Sans
- **字體配對**：展示字體（標題）+ 正文字體（內文），風格對比而非相似
- **數字顯示**：大數字 + 小單位，比率 2:1（如 `48px` 數字 + `24px` 單位）

### 色彩（強化版）

- **承諾連貫的美學**（使用 CSS 變量 / 設計令牌）
- **單一強調色原則**：用一個品牌色統一全場，其餘為灰階
- **純黑禁令**：`#000` → 改用 `#2A2A2A`（精緻黑）
- **色彩稀有性原則**：強調色只用於小面積（active 狀態、進度條、徽章）
- **避免陳詞濫調的配色方案**（特別是白色背景上的紫色漸變）

### 動畫（強化版）

- **動作種子系統**：Spring / Silk / Snap / Float / Pulse
- **觸覺物理動畫**：自定義 cubic-bezier（如 `cubic-bezier(0.32, 0.72, 0, 1)`）
- **磁性按鈕懸停**：`group-hover:translate-x-1 group-hover:-translate-y-[1px]`
- **滾動進入動畫**：`translate-y-16 blur-md opacity-0` → 解析
- **漢堡選單變形**：線條流暢旋轉成 X，不是消失
- **交錯序列**：`animation-delay` 創造編排效果
- **效能鐵律**：只動畫化 `transform` + `opacity`，禁止版面屬性

### 空間構圖（強化版）

- **慷慨的負空間**：區塊間距 `py-24` 到 `py-40`
- **不對稱、重疊、對角流動**
- **打破網格的元素**
- **雙重邊框（Double-Bezel）**：外層包裝 + 內層核心
- **嵌套 CTA 架構**：全圓角膠囊 + 內嵌圖示圓圈
- **標籤微徽章**：`rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.2em]`

### 避免（強化版）

- ❌ 通用的 AI 生成美學
- ❌ 過度使用的字體系列
- ❌ 陳詞濫調的配色方案
- ❌ 可預測的佈局和組件模式
- ❌ 標準 `linear` 或 `ease-in-out` 過渡
- ❌ 無插值的瞬間狀態切換
- ❌ 通用 1px 灰色實線邊框
- ❌ 粗糙的深色投影（`shadow-md`、`rgba(0,0,0,0.3)`）
- ❌ 貼頂的全寬導航欄
- ❌ 對稱無聊的三欄 Bootstrap 網格
- ❌ `h-screen`（改用 `min-h-[100dvh]`）

---

## Cinema Worldbuilder 的五種模式

| 模式 | 適用場景 | 鏡頭語言 |
|:---|:---|:---|
| **M1 Narrative** | 真實戲劇場景 | ARRI Alexa 35 + Panavision anamorphic, handheld realism |
| **M2 Studio** | 棚拍/編輯/時尚 | ARRI Alexa Mini LF + Cooke S4/i, saturated editorial grade |
| **M3 Action** | 動作/追逐/戰鬥 | ARRI Alexa 35 + Panavision anamorphic, gritty documentary |
| **M4 Performance** | 演唱會/舞台/表演 | ARRI Alexa 35 + Panavision anamorphic, stage-lighting color cast |
| **M5 Atmospheric** | 氛圍/空景/無人 | ARRI Alexa Mini LF + Panavision anamorphic, palette-driven |

**劇場投影設計預設使用 M5 Atmospheric。**

---

## SVG Storyboard 模式

### 概念

為每個場景生成程式碼繪製的精緻 SVG 插畫，用幾何形狀、色塊、光影、動畫傳達氛圍與情緒。

### 技術實現

- **SVG 尺寸**：480×270（16:9 比例）
- **動畫**：使用 `<animate>` 標籤（呼吸、閃爍、上升、移動）
- **色彩**：使用場景的主色調（暖金赭、深靛藍、粉紅等）
- **光影**：使用 SVG `<radialGradient>` 模擬聚光燈效果
- **紋理**：使用 SVG `<pattern>` 模擬雨滴、裂痕、抖動線條
- ★ **生成藝術**：可用 p5.js 流場/粒子/分形替代傳統 SVG

### 九種場景視覺風格

| 場景組 | SVG 視覺元素 | 動畫效果 |
|:---|:---|:---|
| 家景三部曲 | 廚房（窗戶+吊燈+流理臺+電鍋+水壺） | 雨滴/蒸氣/黎明曙光 |
| 街景循環 | 透視道路+街樹+電箱+路燈 | 道路移動、紅色閃爍 |
| 電話壓力 | 深藍背景+中央黃色亮光 | 聲波漣漪 |
| 暴力衝突 | 剪影+電視掃描線+紅綠燈 | 紅光閃爍、紅黃綠交替 |
| 傳教士染綠 | 街景+綠色漸層+文字碎片 | 綠色波動、文字淡入淡出 |
| 補習班回憶 | 全暗+抖動白色線條 | 線條抖動 |
| 車禍現場 | 蜘蛛網裂痕+群手 | 裂痕擴散、手部伸縮 |
| 雨景 | 窗戶+雨滴流動 | 雨滴下落 |
| 少女幻想 | 粉紅背景+上升泡泡 | 泡泡上升、光點閃爍 |

---

## 色票速查（劇場投影專用）

| 名稱 | 色票 | 用途 |
|:---|:---|:---|
| 暖金赭 | `#a87b3a` | 室內主色 |
| 米灰 | `#a89880` | 室內輔色 |
| 奶油黃 | `#f0d090` | 吊燈光暈 |
| 深靛藍 | `#1a2b4a` | 窗外主色 |
| 近黑藍 | `#0d1521` | 高樓剪影 |
| 暖黃 | `#d4a857` | 窗內點光 |
| 大同電鍋綠 | `#4a7a3a` | 電鍋 |

---

## 鍵盤導航（Presentation 模式）

```
←  →  Space  PgUp  PgDn  Home  End    翻頁
F                                       全螢幕
S                                       演講者模式
N                                       筆記
T                                       切換主題
O                                       概覽
```

---

## 五層品質審查清單

### L1：語義與結構（code-review-excellence）
- [ ] 語義 HTML（正確使用標籤）
- [ ] ARIA 標籤（icon-only 按鈕需 `aria-label`）
- [ ] 響應式設計（mobile-first，`min-h-[100dvh]` 替代 `h-screen`）
- [ ] 國際化（繁體中文、Unicode）

### L2：可訪問性（fixing-accessibility）
- [ ] 所有互動控制有可訪問名稱
- [ ] Tab 鍵可到達所有互動元素
- [ ] 破壞性操作使用 AlertDialog
- [ ] 載入中使用骨架屏
- [ ] 尊重 `safe-area-inset`

### L3：動畫效能（fixing-motion-performance）
- [ ] 只動畫化 `transform` + `opacity`
- [ ] 入場使用 `ease-out`
- [ ] 互動回饋 ≤ 200ms
- [ ] 循環動畫離屏暫停
- [ ] `backdrop-blur` 只用於固定/置頂元素
- [ ] 噪聲/顆粒覆蓋使用 `position: fixed; pointer-events: none`

### L4：視覺品質（baseline-ui）
- [ ] 設計令牌一致性（CSS 變量）
- [ ] 排版層級清晰（5 級灰階）
- [ ] 陰影透明度 4-8%
- [ ] 純黑 `#000` 未使用
- [ ] 強調色稀有分布

### L5：代碼品質（complexity-cuts + logic-lens）
- [ ] 無過度工程化
- [ ] 邏輯正確性（無競態條件、無空值錯誤）
- [ ] 效能瓶頸檢查

---

## 融合 Skills 完整清單

| # | Skill | 類別 | 融合貢獻 |
|:---|:---|:---|:---|
| 1 | `html-ppt` | 框架 | PPT 框架、36 主題、31 版型 |
| 2 | `frontend-design` | 設計 | 排版、色彩、動畫、空間構圖 |
| 3 | `cinema-worldbuilder` | 敘事 | 5 cinema mode、攝影機語言 |
| 4 | `ui-ux-pro-max` | 體驗 | 設計模式、可訪問性 |
| 5 | `web-video-presentation` | 動畫 | 逐步揭示、進度條、過渡 |
| 6 | `baoyu-slide-deck` | 生成 | 幻燈片圖像生成 |
| 7 | `baoyu-diagram` | 圖表 | 9 種 SVG 圖表類型 |
| 8 | `baoyu-infographic` | 信息圖 | 21 版型 × 22 風格 |
| 9 | `code-review-excellence` | 審查 | 全面代碼審查 |
| 10 | ★ `taste-skill` | **調控** | **三旋鈕系統、Design System Map、Brief 推斷** |
| 11 | ★ `styleseed` | **系統** | **69 設計規則、5 動作種子、令牌架構** |
| 12 | ★ `soft-skill` | **美學** | **Awwwards 觸覺微美學、創意變異引擎** |
| 13 | ★ `algorithmic-art` | **生成** | **p5.js 流場/粒子/分形生成藝術** |
| 14 | ★ `threejs-fundamentals` | **3D** | **場景、相機、渲染器** |
| 15 | ★ `threejs-animation` | **3D** | **3D 動畫系統** |
| 16 | ★ `threejs-shaders` | **3D** | **GLSL 著色器** |
| 17 | ★ `threejs-postprocessing` | **3D** | **後處理效果** |
| 18 | ★ `baseline-ui` | **基線** | **動畫效能、排版規範、元件約束** |
| 19 | ★ `fixing-motion-performance` | **效能** | **動畫效能審查與修復** |
| 20 | ★ `fixing-accessibility` | **合規** | **WCAG 2.2 AA 無障礙審查** |
| 21 | ★ `complexity-cuts` | **品質** | **代碼複雜度分析** |
| 22 | ★ `logic-lens` | **品質** | **邏輯正確性審查** |
| 23 | ★ `brandkit` | **品牌** | **品牌套件生成（Logo、配色、字型）** |
| 24 | ★ `image-to-code-skill` | **轉換** | **參考圖 → 程式碼實現** |

---

## 安裝路徑

```
~/.agents/skills/visual-atelier/
├── SKILL.md                    # 本檔（深度融合版）
```

---

**END OF VISUAL ATELIER v2 SKILL**
