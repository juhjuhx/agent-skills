#!/usr/bin/env python3
"""V3 公開安裝輔助：只處理檔案／symlink，沒有模型或權限設定。"""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO = "https://github.com/juhjuhx/agent-skills.git"
AGENTS = (
    ".config/opencode",
    ".claude",
    ".codex",
    ".gemini",
    ".cursor",
    ".windsurf",
    ".continue",
    ".aider",
)


def git(target, *args):
    return subprocess.check_output(["git", "-C", str(target), *args], text=True).strip()


def guarded(path, home):
    if path.is_symlink() or not path.resolve().is_relative_to(home):
        raise ValueError(f"拒絕覆寫 symlink／HOME 外路徑：{path}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Personal Tool Master V3；保留既有使用者目錄，adapter 必須另行 opt-in。"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--minimal", "-m", action="store_true")
    mode.add_argument("--default", action="store_true")
    mode.add_argument("--all", "-a", action="store_true")
    mode.add_argument("--category", "-c", help="逗號分隔 category IDs")
    parser.add_argument(
        "--home",
        type=Path,
        default=Path.home(),
        help="安裝目的 HOME；測試用可指定暫存目錄",
    )
    parser.add_argument("--repo", default=REPO, help="clone 來源；預設官方倉庫")
    parser.add_argument(
        "--update",
        action="store_true",
        help="只對沒有未提交／ignored 檔且 tracking origin 的 checkout 做 ff-only 更新",
    )
    parser.add_argument(
        "--no-links", action="store_true", help="不建立宿主入口／universal pointer"
    )
    parser.add_argument(
        "--opencode-advisory",
        action="store_true",
        help="另行 opt-in 複製 V3 adapter 與可選 primary；不改設定",
    )
    args = parser.parse_args(argv)
    home = args.home.expanduser().resolve()
    target, enabled, config = (
        home / ".agents" / x for x in ("skills", "skills-enabled", "skills-config.json")
    )
    for p in (target, enabled, config):
        guarded(p, home)
    if target.exists():
        if not (target / ".git").exists():
            raise ValueError("既有 skills 不是 Git checkout；保持原狀，不覆寫。")
        if git(target, "status", "--porcelain", "--untracked-files=all"):
            raise ValueError("既有 skills checkout 有未提交工作；拒絕更新或重建入口。")

        def normalize(value):
            return value.rstrip("/").removesuffix(".git")

        if normalize(git(target, "remote", "get-url", "origin")) != normalize(
            args.repo
        ):
            raise ValueError("既有 checkout origin 不符；拒絕更新。")
    previous = {}
    if config.exists():
        previous = json.loads(config.read_text())
    if enabled.exists():
        known = (
            set(previous.get("managed_links", []))
            if previous.get("installer") == "personal-tool-master-v3"
            else set()
        )
        for p in enabled.iterdir():
            if (
                p.name not in known
                or not p.is_symlink()
                or p.resolve() != (target / p.name).resolve()
            ):
                raise ValueError("skills-enabled 含非本安裝器管理的內容；保持原狀。")
    if args.opencode_advisory:
        for rel in (
            ".config/opencode/plugins/skills-router.js",
            ".config/opencode/agents/工具大師V3.md",
        ):
            p = home / rel
            guarded(p, home)
            if p.exists():
                raise ValueError(
                    "V3 opt-in 目的檔已存在（可能為舊 enforcing）；請先手動停用／備份，安裝器不覆寫。"
                )
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--", args.repo, str(target)], check=True)
    elif args.update:
        if git(target, "status", "--porcelain", "--ignored", "--untracked-files=all"):
            raise ValueError("更新拒絕 ignored／未提交檔案，避免上游覆寫使用者內容。")
        upstream = git(target, "rev-parse", "--abbrev-ref", "@{upstream}")
        if not upstream.startswith("origin/"):
            raise ValueError("更新僅接受 tracking origin 的分支；拒絕其他 upstream。")
        subprocess.run(
            ["git", "-C", str(target), "pull", "--ff-only", "origin", upstream[7:]],
            check=True,
        )
    else:
        print("使用現有乾淨 checkout；未執行 git pull。")
    manifest = json.loads((target / "categories.json").read_text())
    categories = {c["id"]: c["skills"] for c in manifest["categories"]}
    if args.category:
        chosen = [s.strip() for s in args.category.split(",")]
    elif args.all:
        chosen = manifest["profiles"]["full"]["categories"]
    elif args.minimal:
        chosen = manifest["profiles"]["minimal"]["categories"]
    elif args.default or not sys.stdin.isatty():
        chosen = manifest["profiles"]["default"]["categories"]
    else:
        print("分類：" + ", ".join(categories))
        raw = input("輸入 IDs（逗號分隔；Enter 採 default）：").strip()
        chosen = (
            [s.strip() for s in raw.split(",")]
            if raw
            else manifest["profiles"]["default"]["categories"]
        )
    if any(s not in categories for s in chosen):
        raise ValueError("未知 category；未修改技能入口。")
    selected = set(["using-superpowers"])
    selected.update(s for c in chosen for s in categories[c])
    for name in selected:
        p = target / name
        if (
            Path(name).name != name
            or p.is_symlink()
            or not p.resolve().is_relative_to(target.resolve())
            or not (p / "SKILL.md").is_file()
        ):
            raise ValueError(f"技能不存在或非可攜式 repo 內目錄：{name}")
    shared = [
        name
        for name in ("brooks-_shared", "logic-_shared")
        if (target / name).is_dir()
        and not (target / name).is_symlink()
        and any(s.startswith(name.split("-")[0] + "-") for s in selected)
    ]
    names = sorted(selected) + shared
    enabled.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="skills-enabled-v3-", dir=enabled.parent))
    for name in names:
        (stage / name).symlink_to(target / name, target_is_directory=True)
    # 先準備所有內容，再切換 managed links/config。失敗不留下半套 adapter。
    prepared = []
    installed = []
    backup = config_backup = None
    activated = config_activated = config_saved = False

    def temporary_file(parent):
        parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix="v3-install-", dir=parent)
        os.close(descriptor)
        path = Path(name)
        prepared.append(path)
        return path

    try:
        config_stage = temporary_file(config.parent)
        config_stage.write_text(
            json.dumps(
                {
                    "installer": "personal-tool-master-v3",
                    "mode": "categories",
                    "categories": chosen,
                    "managed_links": names,
                    "enabled_skills_count": len(selected),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        adapters = []
        if args.opencode_advisory:
            for rel, source in (
                (
                    ".config/opencode/plugins/skills-router.js",
                    "runtime/skills-router/adapters/opencode/skills-router.js",
                ),
                (
                    ".config/opencode/agents/工具大師V3.md",
                    "runtime/skills-router/adapters/opencode/工具大師V3.md",
                ),
            ):
                destination = home / rel
                guarded(destination, home)
                data = (target / source).read_bytes()
                temporary = temporary_file(destination.parent)
                temporary.write_bytes(data)
                adapters.append((temporary, destination))
        if enabled.exists():
            backup = Path(
                tempfile.mkdtemp(prefix="skills-enabled-previous-", dir=enabled.parent)
            )
            backup.rmdir()
            enabled.rename(backup)
        if config.exists():
            config_backup = temporary_file(config.parent)
            config_backup.unlink()
            config.rename(config_backup)
            config_saved = True
        stage.rename(enabled)
        activated = True
        os.link(config_stage, config)
        config_activated = True
        for temporary, destination in adapters:
            os.link(temporary, destination)  # exclusive；不覆寫途中出現的使用者檔案
            installed.append(destination)
        if not args.no_links:
            for agent in AGENTS:
                base = home / agent
                if (
                    not base.is_dir()
                    or base.is_symlink()
                    or not base.resolve().is_relative_to(home)
                ):
                    continue
                p = base / "skills"
                if p.exists() or p.is_symlink():
                    if not (p.is_symlink() and p.resolve() == enabled.resolve()):
                        print(f"保留既有宿主技能目錄：{p}")
                    continue
                p.symlink_to(enabled, target_is_directory=True)
                installed.append(p)
            pointer = home / ".local/share/agent-skills"
            if (
                not pointer.exists()
                and not pointer.is_symlink()
                and pointer.parent.resolve().is_relative_to(home)
            ):
                pointer.parent.mkdir(parents=True, exist_ok=True)
                pointer.symlink_to(enabled, target_is_directory=True)
                installed.append(pointer)
    except OSError:
        for destination in installed:
            destination.unlink()
        if config_activated:
            config.unlink()
        if config_saved:
            config_backup.rename(config)
        if activated:
            enabled.rename(stage)
        if backup is not None:
            backup.rename(enabled)
        raise
    finally:
        for temporary in prepared:
            if temporary.exists():
                temporary.unlink()
        if stage.exists():
            shutil.rmtree(stage)
    print(
        f"啟用 {len(selected)} 個技能；來源 {target}；model／agent／permissions 設定未改。"
    )
    if backup is not None:
        print(f"先前 managed links 備份：{backup}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"安裝停止：{error}", file=sys.stderr)
        raise SystemExit(1)
