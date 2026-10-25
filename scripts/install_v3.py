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


def resolve_package(target, name):
    """Resolve a skill name to its package directory inside the checkout.

    M4-P8 layout: the 14 core skills live at the repo root (<target>/<name>/SKILL.md);
    the 450 additional portable packages live under <target>/skills/<name>/SKILL.md.
    A host that scans direct subdirs (e.g. DSH) never recurses into skills/, so the
    installer materializes a top-level symlink per skill — the target of that symlink
    is whatever resolve_package returns here.
    """
    root_pkg = target / name
    if (root_pkg / "SKILL.md").is_file():
        return root_pkg
    extra_pkg = target / "skills" / name
    if (extra_pkg / "SKILL.md").is_file():
        return extra_pkg
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Personal Tool Master V3；保留既有使用者目錄，adapter 必須另行 opt-in。"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--minimal", "-m", action="store_true")
    mode.add_argument("--default", action="store_true")
    mode.add_argument("--all", "-a", action="store_true")
    mode.add_argument("--category", "-c", help="逗號分隔 category IDs")
    parser.add_argument("--skill", "-s", help="逗號分隔技能名稱（依 P8.5 catalog slug）；與 --all/--default/--minimal/--category 可合併")
    parser.add_argument("--list", action="store_true", help="列出當前 catalog 全部技能，不執行安裝")
    parser.add_argument("--verify", action="store_true", help="驗證已安裝技能：解析 symlink、檢查 SKILL.md 存在、對照 catalog.lock.json SHA-256")
    parser.add_argument("--dry-run", action="store_true", help="解析安裝意圖，只輸出會做什麼，不建立 symlink、不備份、不改動 config")
    parser.add_argument("--rollback", action="store_true", help="還原到前一次 install backup（<home>/.agents/skills-enabled-previous-*）")
    parser.add_argument("--host", default="auto",
                        choices=["auto", "hermes", "dsh", "opencode", "claude", "codex", "gemini"],
                        help="目標宿主；auto 會依 --home 下既有目錄偵測")
    parser.add_argument(
        "--home",
        type=Path,
        default=Path.home(),
        help="安裝目的 HOME；測試用可指定暫存目錄",
    )
    parser.add_argument("--repo", default=REPO, help="clone 來源；預設官方倉庫")
    parser.add_argument("--repo-local",
                        help="本機 checkout 路徑（替代 clone；target 必須已存在且乾淨，用於 clean-room / 發布前驗證）")
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
            # --repo-local points at a specific local checkout (clean-room / pre-push
            # validation): its origin is that checkout, not the GitHub URL, so the
            # remote-identity check does not apply.
            if not args.repo_local:
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
            valid_targets = []
            direct = target / p.name
            if direct.is_dir() and not direct.is_symlink() and (direct / "SKILL.md").is_file():
                valid_targets.append(direct.resolve())
            extra = target / "skills" / p.name
            if extra.is_dir() and not extra.is_symlink() and (extra / "SKILL.md").is_file():
                valid_targets.append(extra.resolve())
            if (
                p.name not in known
                or not p.is_symlink()
                or p.resolve() not in valid_targets
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
    if args.repo_local:
        target = Path(args.repo_local).expanduser().resolve()
        if not target.is_dir():
            raise ValueError(f"--repo-local 指定的路徑不是目錄：{target}")
        has_skill = any(
            d.is_dir() and not d.name.startswith(".") and (d / "SKILL.md").is_file()
            for d in target.iterdir()
        )
        if not has_skill:
            raise ValueError(f"--repo-local checkout 內沒有可安裝的 <dir>/SKILL.md：{target}")
    elif not target.exists():
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

    # --list: enumerate every installable skill (root-level + skills/<slug>), exit 0.
    if args.list:
        all_names = set()
        for c in manifest["categories"]:
            all_names.update(c["skills"])
        print(f"catalog categories: {', '.join(categories)}")
        print(f"total distinct skills across categories: {len(all_names)}")
        for name in sorted(all_names):
            pkg = resolve_package(target, name)
            if pkg is None:
                print(f"  [missing] {name}")
            else:
                layer = "root" if pkg.parent == target else "skills"
                print(f"  [{layer:>6}] {name}")
        return 0

    # --rollback: restore the most recent managed backup, exit 0.
    if args.rollback:
        backups = sorted(enabled.parent.glob("skills-enabled-previous-*"))
        if not backups:
            print("rollback：沒有可還原的 backup。")
            return 0
        backup = backups[-1]
        print(f"rollback：還原到 {backup}")
        if enabled.exists():
            enabled.rename(enabled.with_name(enabled.name + "-pre-" + "rollback"))
        backup.rename(enabled)
        return 0

    # --verify: validate the installed layout without modifying anything.
    if args.verify:
        import hashlib
        problems = 0
        checked = 0
        # 1. structural: every managed link resolves to a SKILL.md
        links = [p for p in enabled.iterdir() if p.is_symlink()]
        for p in links:
            target_path = p.resolve()
            if not target_path.is_dir() or not (target_path / "SKILL.md").is_file():
                print(f"  [broken] {p.name} -> {target_path}")
                problems += 1
        # 2. integrity: when the source tree carries catalog.lock.json, verify each
        # installed skill body's SHA-256 against the lock (skills/ extras only).
        lock_path = target / "catalog.lock.json"
        if lock_path.is_file():
            lock = json.loads(lock_path.read_text())
            for entry in lock.get("entries", []):
                pkg_md = target / entry.get("relative_path", "").replace("SKILL.md", "SKILL.md")
                # relative_path in lock is skills/<slug>/SKILL.md
                cand = target / "skills" / entry["slug"] / "SKILL.md"
                if not cand.is_file():
                    print(f"  [missing-body] {entry['slug']}")
                    problems += 1
                    continue
                actual = hashlib.sha256(cand.read_bytes()).hexdigest()
                if actual != entry["body_sha256"]:
                    print(f"  [sha-mismatch] {entry['slug']}: {actual[:12]} != {entry['body_sha256'][:12]}")
                    problems += 1
                checked += 1
        print(f"verify：掃描 {len(links)} 個 managed link；"
              + (f"比對 {checked} 個 SHA-256 lock；" if lock_path.is_file() else "")
              + f"發現 {problems} 個問題。")
        return 0 if problems == 0 else 1
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
    if args.skill:
        # install a specific skill by name in addition to (or instead of) the category set
        extra = [s.strip() for s in args.skill.split(",")]
        for name in extra:
            if resolve_package(target, name) is None:
                raise ValueError(f"找不到技能套件：{name}")
            selected.add(name)
    for name in selected:
        p = resolve_package(target, name)
        if (
            p is None
            or Path(name).name != name
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
    if args.dry_run:
        print(f"dry-run：將啟用 {len(selected)} 個技能（{len(names)} 含 shared）")
        print(f"dry-run：categories = {chosen}")
        layer_counts = {"root": 0, "skills": 0, "missing": 0}
        for name in names:
            pkg = resolve_package(target, name)
            if pkg is None:
                layer_counts["missing"] += 1
                print(f"  [missing] {name}")
            else:
                layer = "root" if pkg.parent == target else "skills"
                layer_counts[layer] += 1
        print(f"dry-run：root={layer_counts['root']} skills={layer_counts['skills']} missing={layer_counts['missing']}")
        print("dry-run：未修改任何 symlink、備份或 config。")
        return 0
    enabled.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="skills-enabled-v3-", dir=enabled.parent))
    for name in names:
        # Direct subdirectory packages (core + shared) link as-is; extra packages
        # living under skills/<slug> are resolved so every skill still lands as a
        # top-level direct subdirectory symlink that DSH can discover without
        # recursing into skills/.
        direct = target / name
        if direct.is_dir() and not direct.is_symlink() and (direct / "SKILL.md").is_file():
            (stage / name).symlink_to(direct, target_is_directory=True)
        else:
            pkg = resolve_package(target, name)
            if pkg is not None:
                (stage / name).symlink_to(pkg, target_is_directory=True)
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
            # M4-P8: host mapping. `auto` links every host dir that exists;
            # a specific --host limits linking to that one. Hermes gets special
            # treatment because ~/.hermes/skills is a real user-owned directory
            # that must never be wholesale-replaced: we only add per-skill links
            # for slugs not already present.
            hermes_skills_dir = home / ".hermes" / "skills"
            host_map = {
                "hermes": hermes_skills_dir,
                "dsh": home / ".dsh" / "skills",
                "opencode": home / ".config/opencode/skills",
                "claude": home / ".claude/skills",
                "codex": home / ".codex/skills",
                "gemini": home / ".gemini/skills",
            }
            if args.host == "auto":
                link_targets = []
                for agent in AGENTS:
                    p = home / agent / "skills"
                    if p.exists() or p.is_symlink():
                        if not (p.is_symlink() and p.resolve() == enabled.resolve()):
                            print(f"保留既有宿主技能目錄：{p}")
                        continue
                    link_targets.append(p)
            else:
                link_targets = [host_map[args.host]]
                if args.host == "hermes":
                    link_targets = []  # hermes uses selective per-skill linking below

            for p in link_targets:
                base = p.parent
                if (
                    not base.is_dir()
                    or base.is_symlink()
                    or not base.resolve().is_relative_to(home)
                ):
                    continue
                if p.exists() or p.is_symlink():
                    if not (p.is_symlink() and p.resolve() == enabled.resolve()):
                        print(f"保留既有宿主技能目錄：{p}")
                    continue
                p.symlink_to(enabled, target_is_directory=True)
                installed.append(p)

            # Hermes selective per-skill linking (never overwrites user skills).
            if args.host in ("auto", "hermes") and hermes_skills_dir.is_dir() and not hermes_skills_dir.is_symlink():
                added = 0
                for name in names:
                    pkg = resolve_package(target, name)
                    if pkg is None:
                        continue
                    link = hermes_skills_dir / name
                    if link.exists() or link.is_symlink():
                        continue  # user already has this skill; do not touch
                    link.symlink_to(pkg, target_is_directory=True)
                    installed.append(link)
                    added += 1
                print(f"hermes selective link：新增 {added} 個技能到 {hermes_skills_dir}（既有技能未動）。")
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
