#!/usr/bin/env python3
"""Personal Tool Master V3：標準庫、metadata 優先、永不限制 host 工具的建議封包。

公開介面：load_skill_index(root)、build_route_packet(task, *, root, host,
tools, profile, index)、render_packet(packet)。root 是技能 repo，並非任務專案。
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys

CAPABILITIES = (
    "READ",
    "SEARCH",
    "LOAD_SKILL",
    "WRITE",
    "PATCH",
    "SHELL",
    "WEB_SEARCH",
    "WEB_FETCH",
    "DELEGATE",
    "TEST",
    "GIT_READ",
    "GIT_WRITE",
)
HOSTS = ("codex", "opencode", "dsh", "hermes", "claude", "generic")
PROFILES = ("guided", "normal", "high")
# 僅提示名稱；絕不放進 available，亦不代表授權。
HOST_HINTS = {
    "codex": {
        "SHELL": ["exec_command"],
        "PATCH": ["apply_patch"],
        "WEB_SEARCH": ["web.run"],
        "WEB_FETCH": ["web.run"],
        "DELEGATE": ["spawn_agent"],
    },
    "opencode": {
        "READ": ["read"],
        "SEARCH": ["grep", "glob"],
        "LOAD_SKILL": ["skill"],
        "WRITE": ["write"],
        "PATCH": ["edit", "apply_patch"],
        "SHELL": ["bash"],
        "WEB_SEARCH": ["websearch"],
        "WEB_FETCH": ["webfetch"],
        "DELEGATE": ["task"],
    },
    "claude": {
        "READ": ["Read"],
        "SEARCH": ["Grep", "Glob"],
        "LOAD_SKILL": ["Skill"],
        "WRITE": ["Write"],
        "PATCH": ["Edit"],
        "SHELL": ["Bash"],
        "WEB_SEARCH": ["WebSearch"],
        "WEB_FETCH": ["WebFetch"],
        "DELEGATE": ["Agent"],
    },
    "dsh": {},
    "hermes": {},
    "generic": {},
}
# 任務同義詞擴充，不列舉 catalog 技能名稱。
INTENTS = {
    "review": (
        r"\b(review|audit)\b|審查|審核|稽核",
        "review code quality architecture findings evidence audit",
    ),
    "debug": (
        r"\b(debug|bug|defect|traceback|error|broken|fix)\b|除錯|偵錯|錯誤|故障|修復|異常",
        "debug bug defect error reproduce root cause fix test validation software source code implementation",
    ),
    "research": (
        r"\b(research|investigate|sources?|citations?|latest|compare)\b|研究|查證|查詢|資料來源|最新|比較",
        "research search reliable source evidence citation documentation investigate compare",
    ),
    "code": (
        r"\b(code|implement|refactor|software|feature|migration|api)\b|實作|程式|重構|功能|遷移|開發",
        "implement code software feature source interface maintain validation",
    ),
    "simple": (
        r"\b(typo|rename|translate|summarize)\b|錯字|更正|翻譯|摘要|改名|回答",
        "documentation edit text translate summarize",
    ),
}


def _diagnostic(code, message, **details):
    return {"code": code, "message": message, **details}


def _safe_path(root, relative):
    path = Path(str(relative))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("路徑超出技能 repo")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("路徑或連結超出技能 repo")
    return resolved


def _valid_records(records, root, diagnostics):
    result, seen = [], set()
    for record in records:
        try:
            if not isinstance(record, dict):
                raise ValueError("metadata 必須為物件")
            identifier = record.get("skill_id")
            if not isinstance(identifier, str) or not identifier or identifier in seen:
                raise ValueError("缺少或重複 ID")
            _safe_path(root, record["relative_path"])
            if not isinstance(record.get("description", ""), str):
                raise ValueError("description 必須為字串")
            if not isinstance(record.get("canonical_name", ""), str):
                raise ValueError("canonical_name 必須為字串")
            triggers = record.get("triggers", [])
            if not isinstance(triggers, list) or any(
                not isinstance(t, str) for t in triggers
            ):
                raise ValueError("triggers 必須為字串陣列")
            aliases = record.get("aliases", [])
            if not isinstance(aliases, list) or any(
                not isinstance(a, str) for a in aliases
            ):
                raise ValueError("aliases 必須為字串陣列")
            seen.add(identifier)
            if record.get("route_eligible", True) and not record.get(
                "deprecated", False
            ):
                result.append(dict(record))
        except (KeyError, ValueError, OSError, RuntimeError) as error:
            diagnostics.append(_diagnostic("INVALID_SKILL_RECORD", str(error)))
    return result


def _frontmatter(path, limit):
    # 只讀 bounded header；不需要 PyYAML，不載入正文。
    with path.open("rb") as stream:
        text = stream.read(limit).decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result, active = {}, None
    for line in lines[1:]:
        if line.strip() == "---":
            return result
        match = re.match(r"^(name|description):\s*(.*)$", line)
        if match:
            active, value = match.groups()
            result[active] = (
                "" if value in (">", "|", ">-", "|-") else value.strip().strip("\"'")
            )
        elif active and line[:1].isspace():
            result[active] += " " + line.strip()
        elif line and not line[:1].isspace():
            active = None
    return {}  # 無完整 frontmatter 不猜測正文。


def _discover(root, diagnostics):
    config_path = root / "runtime/skills-router/catalog/discovery-roots.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(config, dict) or not isinstance(config.get("roots"), list):
            raise ValueError("缺少明列 roots")
    except (OSError, ValueError) as error:
        diagnostics.append(
            _diagnostic(
                "DISCOVERY_ROOTS_UNAVAILABLE", f"僅掃描明列預設根目錄「.」：{error}"
            )
        )
        config = {"roots": ["."]}
    limit = min(max(int(config.get("max_entries", 4096)), 1), 4096)
    header_limit = min(max(int(config.get("max_frontmatter_bytes", 65536)), 1), 65536)
    excluded = set(config.get("exclude_names", [])) | {
        "runtime",
        "docs",
        "tests",
        "node_modules",
    }
    result, seen, visited = [], set(), 0
    for relative in config["roots"][:64]:
        try:
            directory = _safe_path(root, relative)
            children = sorted(directory.iterdir(), key=lambda p: p.name)
        except (OSError, ValueError, RuntimeError) as error:
            diagnostics.append(
                _diagnostic(
                    "DISCOVERY_ROOT_UNAVAILABLE", str(error), root=str(relative)
                )
            )
            continue
        for child in children:
            visited += 1
            if visited > limit:
                diagnostics.append(
                    _diagnostic("DISCOVERY_LIMIT", "已達 metadata 探索上限")
                )
                return result
            if (
                child.name.startswith(".")
                or child.name in excluded
                or child.is_symlink()
            ):
                continue
            path = child / "SKILL.md"
            if not child.is_dir() or path.is_symlink() or not path.is_file():
                continue
            relative_path = path.relative_to(root).as_posix()
            if relative_path in seen:
                continue
            seen.add(relative_path)
            try:
                metadata = _frontmatter(path, header_limit)
            except OSError as error:
                diagnostics.append(
                    _diagnostic("METADATA_UNAVAILABLE", str(error), path=relative_path)
                )
                continue
            if not metadata.get("description"):
                continue
            result.append(
                {
                    "skill_id": "local:"
                    + child.relative_to(root).as_posix().replace("/", ":"),
                    "canonical_name": metadata.get("name") or child.name,
                    "aliases": [],
                    "description": metadata["description"],
                    "relative_path": relative_path,
                    "body_digest": None,
                    "body_available": True,
                    "route_eligible": True,
                }
            )
    return result


def load_skill_index(root):
    """回傳 skills/source/revision/diagnostics；catalog 壞掉採 bounded metadata 探索。"""
    root = Path(root).expanduser().resolve()
    diagnostics = []
    try:
        path = root / ".superpowers/SKILLS_INDEX.json"
        if path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("catalog 超過輕量讀取上限")
        catalog = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(catalog, dict) or not isinstance(catalog.get("skills"), list):
            raise ValueError("catalog 缺少 skills 陣列")
        skills = _valid_records(catalog["skills"], root, diagnostics)
        if (
            catalog["skills"]
            and not skills
            and any(d["code"] == "INVALID_SKILL_RECORD" for d in diagnostics)
        ):
            raise ValueError("catalog 非空但沒有有效 metadata；改用本機探索")
        return {
            "skills": skills,
            "source": "catalog",
            "revision": catalog.get("catalog_revision"),
            "root": str(root),
            "diagnostics": diagnostics,
        }
    except (OSError, ValueError, RuntimeError) as error:
        diagnostics.append(
            _diagnostic("CATALOG_UNAVAILABLE", f"使用 metadata fallback：{error}")
        )
    try:
        skills = _discover(root, diagnostics)
    except (TypeError, ValueError, OSError, RuntimeError) as error:
        diagnostics.append(
            _diagnostic("DISCOVERY_UNAVAILABLE", f"使用一般 workflow：{error}")
        )
        skills = []
    return {
        "skills": skills,
        "source": "discovery" if skills else "general",
        "revision": None,
        "root": str(root),
        "diagnostics": diagnostics,
    }


def _tokens(text):
    text = text.lower()
    words = re.findall(r"[a-z0-9]+|[\u3400-\u9fff]+", text)
    result = []
    for word in words:
        if re.fullmatch(r"[\u3400-\u9fff]+", word):
            result.extend(word[i : i + 2] for i in range(max(1, len(word) - 1)))
        else:
            # 輕量英語詞形：errors/tests/defects 與單數描述共用 metadata 詞。
            if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
                word = word[:-1]
            if not word.isdigit() and word not in {
                "explain",
                "please",
                "the",
                "this",
                "that",
                "and",
                "with",
                "without",
                "for",
                "what",
                "how",
                "is",
                "are",
                "a",
                "an",
            }:
                result.append(word)
    return result


def _intent(task):
    for name, (pattern, _) in INTENTS.items():
        if re.search(pattern, task, re.I):
            return name
    return "general"


def _pr_only(record):
    description = record.get("description", "").lower()
    mentions_pr = re.search(r"pull[ -]requests?|\bpr\b|合併請求|拉取請求", description)
    explicit_only = re.search(r"only when|only for|專用|僅.*(?:pr|請求)", description)
    single_purpose = len(description.split()) <= 12 and re.search(
        r"(?:review|create|open|merge|address).*pull[ -]request", description
    )
    requires_pr_input = bool(
        re.match(
            r"(?:turn|convert).*pull[ -]request|(?:pr|pull[ -]request)[ -]+review",
            description,
        )
    )
    return bool(mentions_pr and (explicit_only or single_purpose or requires_pr_input))


def _rank(task, records, intent):
    pr_context = re.sub(
        r"(?:\b(?:no|without|not)\s+(?:a\s+)?|沒有|無|不是)(?:pull[ -]requests?|pr|合併請求|拉取請求)",
        "",
        task,
        flags=re.I,
    )
    pr_context = re.sub(
        r"\b(?:do\s+not|don't|never|avoid|not)\s+(?:create|open|make|publish|submit)(?:\s+\w+){0,4}\s+(?:pull[ -]requests?|pr\b)|(?:不要|別|不應|禁止)(?:建立|創建|開立|提交|發起)\s*(?:新的|另一個)?\s*(?:PR|合併請求|拉取請求)",
        "",
        pr_context,
        flags=re.I,
    )
    has_pr = bool(
        re.search(r"pull[ -]requests?|\bpr\b|合併請求|拉取請求", pr_context, re.I)
    )
    eligible = [r for r in records if has_pr or not _pr_only(r)]
    documents = [
        Counter(
            _tokens(
                " ".join(
                    [
                        r.get("canonical_name", ""),
                        r.get("description", ""),
                        " ".join(r.get("aliases", [])),
                        " ".join(str(t) for t in r.get("triggers", [])),
                    ]
                )
            )
        )
        for r in eligible
    ]
    frequency = Counter(token for doc in documents for token in doc)
    average = sum(sum(doc.values()) for doc in documents) / max(len(documents), 1)
    query = Counter(_tokens(task + " " + INTENTS.get(intent, ("", ""))[1]))
    ranked = []
    for record, doc in zip(eligible, documents):
        score = 0.0
        length = sum(doc.values())
        for token, weight in query.items():
            count = doc.get(token, 0)
            if count:
                idf = math.log(
                    1
                    + (len(documents) - frequency[token] + 0.5)
                    / (frequency[token] + 0.5)
                )
                score += (
                    idf
                    * count
                    * 2.2
                    / (count + 1.2 * (0.25 + 0.75 * length / max(average, 1)))
                    * min(weight, 2)
                )
        for alias in [
            record.get("canonical_name", ""),
            record.get("skill_id", ""),
        ] + record.get("aliases", []):
            if alias and alias.lower() in task.lower():
                score += 20
        specific_docs = re.match(
            r"(?:search|browse|fetch|read) ([\w.-]+) (?:documentation|docs|references?)$",
            record.get("description", "").strip(),
            re.I,
        )
        if specific_docs and specific_docs[1].lower() not in task.lower():
            score = (
                0.0  # Product-only documentation is irrelevant without that product.
            )
        relative = str(record.get("relative_path", ""))
        if "/skills/" in relative:
            domain = relative.split("/")[0]
            domain_words = [
                w for w in _tokens(domain) if len(w) > 2 and w not in {"tooling"}
            ]
            if not any(w in _tokens(task) for w in domain_words):
                score *= (
                    0.45  # specialized nested libraries need a matching task domain
                )
        ranked.append((score, record))
    return sorted(ranked, key=lambda pair: (-pair[0], pair[1]["skill_id"]))


def _tool_records(tools):
    if isinstance(tools, dict):
        if "tools" in tools:
            tools = tools["tools"]
        elif "functions" in tools:
            tools = tools["functions"]
        elif "name" in tools or "function" in tools:
            tools = [tools]
        else:
            tools = [
                {"name": name, **(value if isinstance(value, dict) else {})}
                for name, value in tools.items()
            ]
    if not isinstance(tools, list):
        return []
    result = []
    for tool in tools[:512]:
        if isinstance(tool, str):
            result.append((tool, ""))
        elif isinstance(tool, dict):
            function = tool.get("function", tool)
            if isinstance(function, dict) and isinstance(function.get("name"), str):
                result.append((function["name"], str(function.get("description", ""))))
    return result


def _tool_map(tools, host):
    result = {
        cap: {"available": [], "host_hints": HOST_HINTS.get(host, {}).get(cap, [])}
        for cap in CAPABILITIES
    }
    for name, description in _tool_records(tools):
        short = re.split(r"[.:/]|__", name.lower())[-1]
        text = name.lower() + " " + description.lower()
        caps = set()
        if short in ("read", "read_file", "view_file", "get_file", "cat") or re.search(
            r"\b(?:read|view|get)\b.*\b(?:local )?files?\b|讀取.*檔案",
            description.lower(),
        ):
            caps.add("READ")
        if re.search(r"grep|glob|search.*(?:files?|code|local)|檔案搜尋", text):
            caps.add("SEARCH")
        if short in ("skill", "load_skill", "skill_view") or re.search(
            r"(?:load|view).*skill|載入.*技能", text
        ):
            caps.add("LOAD_SKILL")
        if short in ("write", "write_file") or re.search(
            r"write.*file|寫入.*檔案", text
        ):
            caps.add("WRITE")
        if short in ("edit", "apply_patch", "patch", "edit_file") or "patch" in text:
            caps.add("PATCH")
        if short in (
            "bash",
            "shell",
            "exec_command",
            "terminal",
        ) or re.search(r"(?:run|execute)s?.*shell|shell command", text):
            caps.update(
                (
                    "SHELL",
                    "READ",
                    "SEARCH",
                    "WRITE",
                    "PATCH",
                    "TEST",
                    "GIT_READ",
                    "GIT_WRITE",
                )
            )
        if re.search(
            r"web[_ .]?search|websearch|search.*(?:web|internet)|搜尋.*(?:網路|網頁)",
            text,
        ):
            caps.add("WEB_SEARCH")
        if re.search(
            r"web[_ .]?fetch|webfetch|fetch.*(?:url|web)|browse|open.*url", text
        ):
            caps.add("WEB_FETCH")
        if name.lower().endswith(("web__run", "web.run")):
            caps.update(("WEB_SEARCH", "WEB_FETCH"))
        if short in ("task", "agent", "spawn_agent", "delegate") or re.search(
            r"spawn.*agent|delegate.*task", text
        ):
            caps.add("DELEGATE")
        if short in ("test", "run_tests") or re.search(r"run.*tests?|執行.*測試", text):
            caps.add("TEST")
        if re.search(r"git[_ .](status|diff|log|show|read)", text):
            caps.add("GIT_READ")
        if re.search(r"git[_ .](commit|push|merge|write|checkout)", text):
            caps.add("GIT_WRITE")
        for cap in caps:
            if name not in result[cap]["available"]:
                result[cap]["available"].append(name)
    for mapping in result.values():
        mapping["additional_count"] = max(0, len(mapping["available"]) - 8)
        mapping["available"] = mapping["available"][:8]
    return result


def _body_status(record, root, diagnostics):
    try:
        path = _safe_path(root, record["relative_path"])
        if (
            not record.get("body_available", True)
            or path.stat().st_size > 4 * 1024 * 1024
        ):
            raise OSError("正文不可用或超過大小上限")
        body = path.read_bytes()  # 僅 selected，絕不預讀全庫。
        expected = record.get("body_digest")
        if expected and hashlib.sha256(body).hexdigest() != str(expected).removeprefix(
            "sha256:"
        ):
            diagnostics.append(
                _diagnostic(
                    "BODY_DIGEST_MISMATCH",
                    "略過該正文；host 工具仍可用",
                    id=record["skill_id"],
                )
            )
            return "digest_mismatch"
        if not expected:
            diagnostics.append(
                _diagnostic(
                    "BODY_DIGEST_UNAVAILABLE",
                    "fallback 正文未有 catalog 摘要",
                    id=record["skill_id"],
                )
            )
            return "unverified"
        return "verified"
    except (OSError, ValueError, RuntimeError) as error:
        diagnostics.append(
            _diagnostic("BODY_UNAVAILABLE", str(error), id=record["skill_id"])
        )
        return "unavailable"


def build_route_packet(
    task, *, root, host="generic", tools=None, profile="normal", index=None
):
    """以 metadata 篩選至多 20 候選與 8 正文，回傳可 JSON 化的 advisory packet。"""
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task 必須是非空文字")
    if host not in HOSTS or profile not in PROFILES:
        raise ValueError("未知 host 或 profile")
    task = task.strip()
    source_length = len(task)
    if source_length > 2400:
        task = (
            task[:1800]
            + "\n[長任務封包摘要：原始需求仍以使用者訊息／TASK.md為準]\n"
            + task[-500:]
        )
    root = Path(root).expanduser().resolve()
    index = load_skill_index(root) if index is None else index
    diagnostics = list(index.get("diagnostics", []))
    if source_length > 2400:
        diagnostics.append(
            _diagnostic(
                "TASK_SUMMARIZED",
                "封包只保留首尾；執行前核對原始需求／TASK.md",
                original_characters=source_length,
            )
        )
    intent = _intent(task)
    ranked = _rank(task, index.get("skills", []), intent)
    candidates = ranked[:20]
    positive = [pair for pair in candidates if pair[0] > 0]
    count = {"guided": 3, "normal": 5, "high": 8}[profile]
    if intent == "simple":
        count = min(count, 3)
    selected = positive[:count]
    skills = [
        {
            "id": record["skill_id"],
            "name": record.get("canonical_name", ""),
            "path": record["relative_path"],
            "digest": record.get("body_digest"),
            "score": round(score, 3),
            "body_status": _body_status(record, root, diagnostics),
        }
        for score, record in selected
    ]
    context = [
        "任務專案及上層適用的 AGENTS.md",
        "任務專案 README.md 或同等入口文件",
        "與請求直接相關的 source、設定或現有產物；先搜尋再限量讀取",
    ]
    referenced = re.findall(r"(?:[\w.\-]+/)+[\w.\-]+\.[a-zA-Z0-9]+", task)
    context.extend(dict.fromkeys(referenced[:6]))
    workflow = [
        "先讀適用規則與相關現物，確認可觀察的完成條件。",
        "依現有工具載入相關技能；只載入 verified 正文，fallback unverified 先自行確認。",
    ]
    if intent == "debug":
        workflow.extend(
            [
                "重現錯誤，查明根因，再做範圍內的最小修復。",
                "執行能證明修復的回歸或現有測試，回報實際結果。",
            ]
        )
    elif intent == "review":
        workflow.extend(
            [
                "以唯讀方式核對需求與原始程式、測試或產物，不修改受審內容。",
                "列出可重現問題、位置、影響與證據；把已驗證與未驗證分開。",
            ]
        )
    elif intent == "research":
        workflow.extend(
            [
                "依問題使用可用搜尋或 web 工具，閱讀原始來源並核對日期。",
                "整合證據，提供來源與未解問題。",
            ]
        )
    elif intent == "code":
        workflow.extend(
            [
                "依既有介面實作最小完整變更；需要時先寫可失敗的驗證。",
                "執行與變更相稱的測試或檢查並檢視 diff。",
            ]
        )
    else:
        workflow.extend(
            [
                "直接完成範圍內工作；只有資料不足時做必要搜尋。",
                "用與任務相稱的檢查確認產物並回報結果。",
            ]
        )
    long_task = len(task) > 500 or bool(
        re.search(
            r"multi.stage|migration|resume|多階段|跨.*階段|長任務|重啟|接續", task, re.I
        )
    )
    if long_task:
        workflow.insert(
            1,
            "長任務將 TASK/PLAN/STATE 保存在任務專案；接續先讀現物、進度與下一步，不依賴 SQLite。",
        )
    if profile == "guided":
        workflow.append("guided：逐步說明關鍵選擇；僅有實質歧義時詢問。")
    elif profile == "high":
        workflow.append("high：必要時拆分工作與驗證；工具和技能選擇仍以實際任務為準。")
    done = [
        "請求的結果或產物已完成，且有相稱的驗證證據。",
        "回報變更、實際檢查結果與仍未驗證的限制。",
    ]
    return {
        "version": "3-slim",
        "advisory": True,
        "task": task,
        "intent": intent,
        "host": host,
        "profile": profile,
        "index_source": index.get("source", "provided"),
        "catalog_revision": index.get("revision"),
        "skills_root": str(root),
        "candidates": [
            {"id": r["skill_id"], "score": round(s, 3)} for s, r in candidates
        ],
        "skills": skills,
        "tools": _tool_map(tools, host),
        "context_to_read": context,
        "workflow": workflow,
        "done_when": done,
        "diagnostics": diagnostics,
    }


def render_packet(packet):
    """渲染精簡 TASK/SKILLS/TOOLS/CONTEXT TO READ/WORKFLOW/DONE WHEN。"""
    lines = [
        "TASK",
        packet["task"],
        f"模式：{packet['intent']} / {packet['profile']}；host：{packet['host']}；建議不限制工具。",
        "\nSKILLS",
        f"root：{packet['skills_root']}",
    ]
    lines.extend(
        f"- {s['id']} → {s['path']} [{s['body_status']}]" for s in packet["skills"]
    )
    if not packet["skills"]:
        lines.append("- 無相關技能，使用一般 workflow。")
    lines.append("\nTOOLS")
    for capability, mapping in packet["tools"].items():
        if mapping["available"]:
            more = mapping.get("additional_count", 0)
            suffix = f"；另 {more} 個已提供工具，需時再查當次 schema" if more else ""
            lines.append(f"- {capability}: {', '.join(mapping['available'])}{suffix}")
        elif mapping["host_hints"]:
            lines.append(
                f"- {capability}: 未探索；host 名稱提示 {', '.join(mapping['host_hints'])}"
            )
    if not any(m["available"] for m in packet["tools"].values()):
        lines.append(
            "- 尚無真實工具 schema；先探索 host 工具。名稱提示不是已探索工具或授權。"
        )
    for heading, key in [
        ("CONTEXT TO READ", "context_to_read"),
        ("WORKFLOW", "workflow"),
        ("DONE WHEN", "done_when"),
    ]:
        lines.append("\n" + heading)
        lines.extend("- " + item for item in packet[key])
    if packet["diagnostics"]:
        lines.append("\nDIAGNOSTICS")
        lines.extend(
            f"- {d['code']}: {d['message']}" for d in packet["diagnostics"][:10]
        )
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="V3 精簡任務→技能→真實工具建議路由")
    sub = parser.add_subparsers(dest="command", required=True)
    route = sub.add_parser("route", help="輸出建議工作封包")
    route.add_argument("text", nargs="?", help="任務文字")
    route.add_argument(
        "--stdin", action="store_true", help="讀取文字或含 task/text/tools 的 JSON"
    )
    route.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[2]),
        help="技能 repo 根目錄",
    )
    route.add_argument("--host", choices=HOSTS, default="generic")
    route.add_argument(
        "--tools-json", help="真實工具 schema/names JSON 路徑；- 代表 stdin"
    )
    route.add_argument("--profile", choices=PROFILES, default="normal")
    route.add_argument("--json", action="store_true", help="輸出 JSON")
    args = parser.parse_args(argv)
    task, tools, diagnostics = args.text, None, []
    stdin_data = sys.stdin.read() if args.stdin or args.tools_json == "-" else None
    if args.stdin:
        try:
            envelope = json.loads(stdin_data)
        except ValueError:
            envelope = None
        if isinstance(envelope, dict):
            task = envelope.get("task", envelope.get("text"))
            tools = envelope.get("tools")
        else:
            task = stdin_data
    if args.tools_json:
        try:
            if args.tools_json == "-" and args.stdin:
                if tools is None:
                    raise ValueError("共用 stdin 時 JSON 必須包含 task/text 與 tools")
            else:
                raw = (
                    stdin_data
                    if args.tools_json == "-"
                    else Path(args.tools_json).read_text(encoding="utf-8")
                )
                tools = json.loads(raw)
        except (OSError, ValueError) as error:
            diagnostics.append(
                _diagnostic("TOOLS_UNAVAILABLE", f"繼續使用 host 工作流程：{error}")
            )
    try:
        packet = build_route_packet(
            task, root=args.root, host=args.host, tools=tools, profile=args.profile
        )
    except ValueError as error:
        parser.error(str(error))
    packet["diagnostics"].extend(diagnostics)
    print(
        json.dumps(packet, ensure_ascii=False, indent=2)
        if args.json
        else render_packet(packet),
        end="\n" if args.json else "",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
