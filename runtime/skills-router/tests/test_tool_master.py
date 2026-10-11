"""V3 精簡路由的公開契約；只使用暫存 catalog 與實際 CLI。"""

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "tool_master.py"


def load_module():
    spec = importlib.util.spec_from_file_location("tool_master", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ToolMasterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.records = []
        for name, description in [
            (
                "trace-errors",
                "Debug defects, reproduce errors and identify root cause.",
            ),
            ("verify-behavior", "Software tests and validation after a bug fix."),
            (
                "source-reader",
                "Read relevant source code to understand implementation.",
            ),
            ("review-pr", "Use only when reviewing a pull request or PR."),
            ("paper-finder", "Research reliable sources, citations and evidence."),
            ("make-change", "Implement code and maintain software features."),
        ] + [
            (f"scene-{n}", "Theatrical lighting composition and scenic color.")
            for n in range(20)
        ]:
            self.add_skill(name, description)
        self.write_catalog()

    def add_skill(self, name, description):
        path = self.root / name / "SKILL.md"
        path.parent.mkdir()
        body = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n正文\n"
        path.write_text(body, encoding="utf-8")
        self.records.append(
            {
                "skill_id": f"local:{name}",
                "canonical_name": name,
                "aliases": ["fault-hunter"] if name == "trace-errors" else [],
                "description": description,
                "relative_path": f"{name}/SKILL.md",
                "body_digest": hashlib.sha256(body.encode()).hexdigest(),
                "body_available": True,
                "route_eligible": True,
            }
        )

    def write_catalog(self):
        directory = self.root / ".superpowers"
        directory.mkdir(exist_ok=True)
        (directory / "SKILLS_INDEX.json").write_text(
            json.dumps({"catalog_revision": "fixture", "skills": self.records})
        )

    def packet(self, task="除錯，修復程式錯誤", **kwargs):
        return self.module.build_route_packet(task, root=self.root, **kwargs)

    def test_chinese_debug_ranks_metadata_and_excludes_pr_only(self):
        packet = self.packet()
        self.assertEqual(packet["intent"], "debug")
        self.assertEqual(packet["skills"][0]["id"], "local:trace-errors")
        self.assertNotIn("local:review-pr", [s["id"] for s in packet["candidates"]])
        self.assertLessEqual(len(packet["candidates"]), 20)
        self.assertGreaterEqual(len(packet["candidates"]), 10)
        self.assertGreaterEqual(len(packet["skills"]), 3)
        self.assertLessEqual(len(packet["skills"]), 8)

    def test_alias_and_explicit_pr_request_are_routable(self):
        self.assertEqual(
            self.packet("fault-hunter")["skills"][0]["id"], "local:trace-errors"
        )
        packet = self.packet("review the pull request PR")
        self.assertIn("local:review-pr", [s["id"] for s in packet["skills"]])

    def test_no_pr_phrase_excludes_pr_only_skill(self):
        for task in [
            "review this module without a pull request",
            "review code, no PR",
            "審查程式，沒有PR",
        ]:
            packet = self.packet(task)
            self.assertNotIn("local:review-pr", [x["id"] for x in packet["candidates"]])

    def test_review_workflow_does_not_request_implementation(self):
        packet = self.packet("Review Python code without a PR")
        self.assertEqual(packet["intent"], "review")
        self.assertTrue(any("不修改" in step for step in packet["workflow"]))

    def test_negated_pr_creation_does_not_supply_pr_context(self):
        for task in [
            "Review code but do not create a pull request",
            "Review module; don't open a PR",
            "審查 Python 模組，不要建立 PR",
        ]:
            self.assertNotIn(
                "local:review-pr", [x["id"] for x in self.packet(task)["candidates"]]
            )
        packet = self.packet(
            "Review existing pull request #12 but do not create another PR"
        )
        self.assertIn("local:review-pr", [x["id"] for x in packet["candidates"]])

    def test_discovered_hermes_skill_view_maps_load_skill(self):
        packet = self.packet(
            host="hermes",
            tools=[
                {
                    "name": "skill_view",
                    "description": "View full skill documentation by name",
                }
            ],
        )
        self.assertIn("skill_view", packet["tools"]["LOAD_SKILL"]["available"])
        self.assertEqual(
            self.packet(host="hermes")["tools"]["LOAD_SKILL"]["available"], []
        )

    def test_product_documentation_needs_matching_task_domain(self):
        self.add_skill("fictional-docs", "Search Fictional documentation")
        self.write_catalog()
        packet = self.packet(
            "Research and compare official source documentation", profile="guided"
        )
        self.assertNotIn("local:fictional-docs", [x["id"] for x in packet["skills"]])
        self.assertEqual(
            self.packet("Search Fictional documentation")["skills"][0]["id"],
            "local:fictional-docs",
        )

    def test_arithmetic_does_not_load_skills_from_numeric_noise(self):
        self.add_skill(
            "phase-2-theater", "Explain phase 2 lighting and scene composition"
        )
        self.write_catalog()
        self.assertEqual(self.packet("Explain 2+2")["skills"], [])

    def test_oversized_task_remains_a_small_packet(self):
        text = self.module.render_packet(self.packet("Fix bug " + "details " * 30000))
        self.assertLess(len(text.encode()), 20000)

    def test_general_review_skill_is_not_pr_only(self):
        self.add_skill(
            "quality-reader",
            "Provides review for Python software, architecture and security. Use when reviewing pull requests, reviewing code, architecture reviews, or audits.",
        )
        self.write_catalog()
        packet = self.packet("review Python architecture and software without a PR")
        self.assertIn("local:quality-reader", [x["id"] for x in packet["candidates"]])

    def test_index_reads_metadata_only_then_checks_selected_bodies(self):
        original = Path.read_bytes
        reads = []

        def observe(path):
            if path.name == "SKILL.md":
                reads.append(path.relative_to(self.root).as_posix())
            return original(path)

        with patch.object(Path, "read_bytes", observe):
            index = self.module.load_skill_index(self.root)
            self.assertEqual(reads, [])
            packet = self.packet(index=index)
        self.assertEqual(set(reads), {s["path"] for s in packet["skills"]})
        self.assertTrue(all(s["body_status"] == "verified" for s in packet["skills"]))

    def test_digest_mismatch_is_advisory_and_keeps_real_tools(self):
        (self.root / "trace-errors/SKILL.md").write_text("changed")
        packet = self.packet(
            tools=[
                {"name": "functions.exec_command", "description": "Runs shell command"}
            ],
            host="codex",
        )
        selected = next(s for s in packet["skills"] if s["id"] == "local:trace-errors")
        self.assertEqual(selected["body_status"], "digest_mismatch")
        self.assertIn("functions.exec_command", packet["tools"]["SHELL"]["available"])
        self.assertTrue(packet["advisory"])
        self.assertIn(
            "BODY_DIGEST_MISMATCH", [d["code"] for d in packet["diagnostics"]]
        )

    def test_actual_schema_names_and_descriptions_win_over_host_hints(self):
        packet = self.packet(
            host="opencode",
            tools={
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "fetch_local",
                            "description": "Read a local file",
                        },
                    },
                    {
                        "name": "search_live",
                        "description": "Search the web for sources",
                    },
                    {"name": "load_recipe", "description": "Load skill instructions"},
                ]
            },
        )
        self.assertIn("fetch_local", packet["tools"]["READ"]["available"])
        self.assertIn("search_live", packet["tools"]["WEB_SEARCH"]["available"])
        self.assertIn("load_recipe", packet["tools"]["LOAD_SKILL"]["available"])
        self.assertNotIn("bash", packet["tools"]["SHELL"]["available"])
        self.assertIn("bash", packet["tools"]["SHELL"]["host_hints"])

    def test_large_tool_inventory_is_bounded_and_discloses_omissions(self):
        packet = self.packet(
            tools=[
                {"name": f"web_search_{n}", "description": "Search the web"}
                for n in range(512)
            ]
        )
        mapping = packet["tools"]["WEB_SEARCH"]
        self.assertEqual(len(mapping["available"]), 8)
        self.assertEqual(mapping["additional_count"], 504)
        self.assertLess(len(self.module.render_packet(packet).encode()), 12000)

    def test_all_hosts_are_advisory_without_discovered_tools(self):
        for host in ["codex", "opencode", "dsh", "hermes", "claude", "generic"]:
            packet = self.packet(host=host)
            self.assertTrue(packet["advisory"])
            self.assertTrue(
                all(not item["available"] for item in packet["tools"].values())
            )

    def test_corrupt_catalog_falls_back_to_explicit_roots_without_yaml(self):
        (self.root / ".superpowers/SKILLS_INDEX.json").write_text("{invalid")
        contract = self.root / "runtime/skills-router/catalog/discovery-roots.json"
        contract.parent.mkdir(parents=True)
        contract.write_text(json.dumps({"roots": ["."], "max_entries": 100}))
        index = self.module.load_skill_index(self.root)
        self.assertEqual(index["source"], "discovery")
        self.assertEqual(len(index["skills"]), 26)
        self.assertIn("CATALOG_UNAVAILABLE", [d["code"] for d in index["diagnostics"]])
        self.assertEqual(
            self.packet(index=index)["skills"][0]["id"], "local:trace-errors"
        )

    def test_missing_index_outputs_general_workflow_without_gating(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = self.module.build_route_packet("回答 2+2", root=directory)
        self.assertEqual(packet["skills"], [])
        self.assertTrue(packet["workflow"])
        self.assertTrue(packet["advisory"])

    def test_simple_task_does_not_require_research_or_tdd(self):
        packet = self.packet("更正文檔錯字")
        text = "\n".join(packet["workflow"])
        self.assertNotIn("TDD", text)
        self.assertNotIn("研究", text)
        self.assertIn("AGENTS.md", packet["context_to_read"][0])
        self.assertTrue(any("README" in item for item in packet["context_to_read"]))

    def test_long_task_mentions_external_task_plan_state(self):
        packet = self.packet("跨多階段實作 migration 並重啟後接續 resume")
        self.assertTrue(any("TASK/PLAN/STATE" in step for step in packet["workflow"]))

    def test_packet_is_compact_and_has_contract_headings(self):
        rendered = self.module.render_packet(self.packet())
        for heading in [
            "TASK",
            "SKILLS",
            "TOOLS",
            "CONTEXT TO READ",
            "WORKFLOW",
            "DONE WHEN",
        ]:
            self.assertIn(heading, rendered)
        self.assertLess(len(rendered.encode("utf-8")), 9000)
        self.assertLess(
            len(json.dumps(self.packet(), ensure_ascii=False).encode("utf-8")), 18000
        )

    def test_unsafe_catalog_paths_do_not_read_outside_root(self):
        self.records[0]["relative_path"] = "../private/SKILL.md"
        self.write_catalog()
        index = self.module.load_skill_index(self.root)
        self.assertNotIn("local:trace-errors", [s["skill_id"] for s in index["skills"]])
        self.assertIn("INVALID_SKILL_RECORD", [d["code"] for d in index["diagnostics"]])

    def test_cli_stdin_json_accepts_task_and_real_tools(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "route",
                "--stdin",
                "--root",
                str(self.root),
                "--host",
                "dsh",
                "--json",
            ],
            input=json.dumps({"task": "除錯", "tools": [{"name": "bash"}]}),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads(result.stdout)
        self.assertIn("bash", packet["tools"]["SHELL"]["available"])

    def test_cli_tools_json_stdin_and_missing_catalog_succeed(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "route",
                "研究資料來源",
                "--root",
                str(self.root),
                "--tools-json",
                "-",
                "--json",
            ],
            input=json.dumps(["web_search"]),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "web_search", json.loads(result.stdout)["tools"]["WEB_SEARCH"]["available"]
        )

    def test_bad_metadata_fields_do_not_crash_advisory_packet(self):
        original = dict(self.records[0])
        for changes in (
            {"canonical_name": 7},
            {"canonical_name": None},
            {"triggers": None},
            {"triggers": 7},
        ):
            self.records[0] = {**original, **changes}
            self.write_catalog()
            packet = self.packet()
            self.assertTrue(packet["advisory"])
            self.assertTrue(
                any(d["code"] == "INVALID_SKILL_RECORD" for d in packet["diagnostics"])
            )

    def test_unknown_nonempty_catalog_schema_uses_local_metadata(self):
        (self.root / ".superpowers/SKILLS_INDEX.json").write_text(
            json.dumps(
                {
                    "skills": [
                        {
                            "name": "trace-errors",
                            "relative_path": "trace-errors/SKILL.md",
                            "description": "debug",
                        }
                    ]
                }
            )
        )
        packet = self.packet()
        self.assertEqual(packet["index_source"], "discovery")
        self.assertTrue(packet["skills"])

    def test_sql_execute_does_not_invent_filesystem_or_shell_capabilities(self):
        packet = self.packet(
            tools=[
                {
                    "name": "execute",
                    "description": "Execute a read-only SQL SELECT query in the database",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                    },
                }
            ]
        )
        for capability in (
            "READ",
            "SEARCH",
            "WRITE",
            "PATCH",
            "SHELL",
            "TEST",
            "GIT_READ",
            "GIT_WRITE",
        ):
            self.assertNotIn(
                "execute", packet["tools"][capability]["available"], capability
            )
        shell = self.packet(
            tools=[
                {
                    "name": "execute",
                    "description": "Execute shell commands in a terminal",
                }
            ]
        )
        self.assertIn("execute", shell["tools"]["SHELL"]["available"])


if __name__ == "__main__":
    unittest.main()
