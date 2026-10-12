# Personal Tool Master V3

使用 using-superpowers 理解任務，metadata-first 選最少足夠的技能，核對當次真正暴露的工具 schema。需要才做研究、計畫與適用測試，長任務以 TASK／PLAN／STATE 續接。技能正文按需載入，不預載全庫。

V3 是 advisory：宿主負責工具執行與權限。router／catalog 故障不得禁用 READ／SEARCH／SHELL／WRITE／Skill，不需要 SQLite、RuntimeDecision、TTL 或 policy preflight。舊 `.superpowers/ROUTING_POLICY.yaml` 與 v2 文件是歷史描述，不是 V3 執行前置 gate。

只改任務範圍，保留使用者 dirty 工作。不自動推送／發布，除非使用者明示授權。第三方內容遵守其原 notice，根 MIT 只覆蓋 docs/授權範圍.md 明列原創程式，不是整庫再授權。

## 維護

- 純標準庫路由：`python3 runtime/skills-router/tool_master.py route '<task>' --root . --host generic`。
- public metadata：`python3 scripts/build_v3_catalog.py`；fresh check：`python3 scripts/build_v3_catalog.py --check`。
- 完整 V3 Python tests：`python3 -m unittest discover -s runtime/skills-router/tests -p 'test_*.py' -v`。
- 發布封裝 tests：`python3 -m unittest discover -s tests -p 'test_*.py' -v`。
- Node：`node --test runtime/skills-router/tests/test_v3_advisory.mjs`。
- 安裝器只在 disposable `--home` 測試，不修改真實 HOME。無關第三方 scripts 的 dependency/tests 不作 V3 runtime 前置。
