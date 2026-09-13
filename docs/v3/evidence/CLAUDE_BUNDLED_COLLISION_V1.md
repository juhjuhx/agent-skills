# Agent Skills Matrix v3 — Claude Bundled Collision Evidence v1

## 結論

針對已安裝且已驗證 fingerprint 的 Claude Code `2.1.235`，本次只對第一個
canary candidate `module-map` 做 candidate-specific proof：

```yaml
BUNDLED_COLLISION: NONE_VERIFIED
calibration: PASSED
scope: CANDIDATE_SPECIFIC_ONLY
global_bundled_inventory: NOT_CLAIMED
```

這個結果不是「永久完整 bundled inventory」。Claude release 改變時必須重新做
artifact fingerprint 與 candidate proof。

## Artifact provenance

| 欄位 | 結果 |
|---|---|
| runtime | Claude Code |
| version | `2.1.235` |
| artifact class | versioned standalone executable |
| artifact SHA-256 | `sha256:83b8f806f6f2eea316cfe246628e6c23374711d868f1fd0409db551b877b7748` |
| artifact bytes | `313334608` |
| execution | `0`；未啟動 Claude |
| source/output persistence | 未保存 binary 或 raw excerpts |

artifact fingerprint 與 Phase 3L 完全一致；若變更，結果必須是
`RUNTIME_REQUALIFICATION_REQUIRED`，不得沿用本證據。

## Bounded inspection method

`tools/v3/claude_bundled.py` 以 standard-library chunked binary scan 完成：

1. 對 artifact 重新計算 SHA-256；
2. 只搜尋 exact ASCII token，不輸出 binary 內容；
3. 用同一 artifact 中可辨識的 bundled registry marker 校準 absence search；
4. 回報 known bundled identifier 與 candidate slug 的 presence/absence；
5. 沒有校準成功時，absence 一律維持 `BUNDLED_COLLISION_UNKNOWN`。

## Completeness calibration

同一 artifact 成功回收到：

- known bundled identifier：`claude-code-guide`；
- registry markers：`getBundledSkills`、
  `getRegisteredBundledSkillsIgnoringKillSwitch`、`registerBundledSkill`、
  `getBundledSkillsRoot`。

因此本次對 `module-map` 的 exact-token absence 才能升級為
`BUNDLED_COLLISION_NONE_VERIFIED`。若 marker 或 known identifier 無法回收，
即使 grep 沒找到 `module-map` 也只能回報 UNKNOWN。

## Candidate result

| candidate | installed artifact result | canary disposition |
|---|---|---|
| `module-map` | `BUNDLED_COLLISION_NONE_VERIFIED` | eligible for bounded canary, subject to all other collision gates |

本證據沒有提供 CLI override，也沒有 `--bundled-none`、`--allow-unknown` 或
synthetic namespace bypass。GitHub/community issue 只能說明 collision risk 為真，
不被用來推導本 release 的 bundled name inventory。
