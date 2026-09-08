import json
import unittest
from copy import deepcopy
from pathlib import Path

from tools.v3.contract_validation import (
    load_schema,
    validate_agent_model_separation,
    validate_file,
    validate_instance,
    validate_relationship_graph,
)
from tools.v3.compatibility import import_current_skill, import_skill_index_entry


ROOT = Path(__file__).resolve().parents[2]


class TaskSpecContractTests(unittest.TestCase):
    def test_minimal_taskspec_fixture_is_valid(self):
        result = validate_file(
            "TaskSpec",
            ROOT / "fixtures/v3/taskspec/minimal.json",
        )

        self.assertTrue(result.valid, result.errors)

    def test_unsupported_schema_version_is_rejected(self):
        with (ROOT / "fixtures/v3/taskspec/minimal.json").open(encoding="utf-8") as handle:
            task_spec = json.load(handle)
        task_spec["schema_version"] = "9.0"

        result = validate_instance("TaskSpec", task_spec)

        self.assertFalse(result.valid)
        self.assertTrue(any("schema_version" in error for error in result.errors))

    def test_unknown_required_capability_is_explicitly_unresolved(self):
        with (ROOT / "fixtures/v3/taskspec/minimal.json").open(encoding="utf-8") as handle:
            task_spec = json.load(handle)
        task_spec["required_capabilities"] = ["needs_future_capability"]

        result = validate_instance("TaskSpec", task_spec)

        self.assertTrue(result.valid, result.errors)
        self.assertEqual(result.unknown_capabilities, ["needs_future_capability"])
        self.assertTrue(any("unsatisfied" in warning for warning in result.warnings))

    def test_full_taskspec_fixture_is_valid(self):
        result = validate_file(
            "TaskSpec",
            ROOT / "fixtures/v3/taskspec/full.json",
        )

        self.assertTrue(result.valid, result.errors)


class SkillMetadataContractTests(unittest.TestCase):
    def test_valid_skill_metadata_fixture_is_valid(self):
        result = validate_file(
            "SkillMetadataV3",
            ROOT / "fixtures/v3/skills/valid.json",
        )

        self.assertTrue(result.valid, result.errors)

    def _fixture(self):
        with (ROOT / "fixtures/v3/skills/valid.json").open(encoding="utf-8") as handle:
            return json.load(handle)

    def test_invalid_trust_level_is_rejected(self):
        skill = self._fixture()
        skill["trust"] = "UNTRUSTED"

        result = validate_instance("SkillMetadataV3", skill)

        self.assertFalse(result.valid)

    def test_invalid_permission_is_rejected(self):
        skill = self._fixture()
        skill["permissions"]["filesystem"] = "root-access"

        result = validate_instance("SkillMetadataV3", skill)

        self.assertFalse(result.valid)

    def test_invalid_stage_role_is_rejected(self):
        skill = self._fixture()
        skill["roles"] = ["BUILD"]

        result = validate_instance("SkillMetadataV3", skill)

        self.assertFalse(result.valid)

    def test_invalid_relationship_is_rejected(self):
        skill = self._fixture()
        skill["relationships"][0]["type"] = "USES"

        result = validate_instance("SkillMetadataV3", skill)

        self.assertFalse(result.valid)

    def test_self_reference_is_rejected(self):
        skill = self._fixture()
        skill["relationships"] = [{"type": "REQUIRES", "target": skill["skill_id"]}]

        result = validate_relationship_graph([skill])

        self.assertFalse(result.valid)
        self.assertTrue(any("self-reference" in error for error in result.errors))

    def test_requires_cycles_are_rejected_but_complements_cycles_are_allowed(self):
        first = self._fixture()
        second = deepcopy(first)
        first["skill_id"] = "skill-a"
        second["skill_id"] = "skill-b"

        first["relationships"] = [{"type": "REQUIRES", "target": "skill-b"}]
        second["relationships"] = [{"type": "REQUIRES", "target": "skill-a"}]
        requires_result = validate_relationship_graph([first, second])

        first["relationships"] = [{"type": "COMPLEMENTS", "target": "skill-b"}]
        second["relationships"] = [{"type": "COMPLEMENTS", "target": "skill-a"}]
        complements_result = validate_relationship_graph([first, second])

        self.assertFalse(requires_result.valid)
        self.assertTrue(complements_result.valid, complements_result.errors)


class AgentAdapterContractTests(unittest.TestCase):
    def test_all_runtime_capability_fixtures_are_valid(self):
        fixture_dir = ROOT / "fixtures/v3/agents"

        for path in sorted(fixture_dir.glob("*.json")):
            with self.subTest(runtime=path.stem):
                result = validate_file("AgentAdapterManifest", path)
                self.assertTrue(result.valid, result.errors)

    def test_absolute_native_path_is_rejected(self):
        with (ROOT / "fixtures/v3/agents/codex.json").open(encoding="utf-8") as handle:
            manifest = json.load(handle)
        manifest["skill_discovery"]["native_paths"] = ["/tmp/untrusted-skills"]

        result = validate_instance("AgentAdapterManifest", manifest)

        self.assertFalse(result.valid)


class ModelProfileContractTests(unittest.TestCase):
    def test_all_provider_profile_fixtures_are_valid(self):
        fixture_dir = ROOT / "fixtures/v3/models"

        for path in sorted(fixture_dir.glob("*.json")):
            with self.subTest(provider=path.stem):
                result = validate_file("ModelProfile", path)
                self.assertTrue(result.valid, result.errors)

    def test_agent_and_model_fixtures_are_separate_layers(self):
        with (ROOT / "fixtures/v3/agents/zcode.json").open(encoding="utf-8") as handle:
            agent = json.load(handle)
        with (ROOT / "fixtures/v3/models/glm.json").open(encoding="utf-8") as handle:
            model = json.load(handle)

        result = validate_agent_model_separation(agent, model)

        self.assertTrue(result.valid, result.errors)
        self.assertEqual(agent["runtime_id"], "zcode")
        self.assertEqual(model["provider_id"], "glm")

    def test_provider_identity_cannot_be_added_to_agent_manifest(self):
        with (ROOT / "fixtures/v3/agents/zcode.json").open(encoding="utf-8") as handle:
            agent = json.load(handle)
        with (ROOT / "fixtures/v3/models/glm.json").open(encoding="utf-8") as handle:
            model = json.load(handle)
        agent["provider_id"] = "glm"

        result = validate_agent_model_separation(agent, model)

        self.assertFalse(result.valid)
        self.assertTrue(any("provider_id" in error for error in result.errors))


class StageRouteContractTests(unittest.TestCase):
    def test_skills_selected_route_is_valid(self):
        result = validate_file(
            "StageRoute",
            ROOT / "fixtures/v3/routes/skills-selected.json",
        )

        self.assertTrue(result.valid, result.errors)

    def test_no_skill_needed_route_is_valid(self):
        result = validate_file(
            "StageRoute",
            ROOT / "fixtures/v3/routes/no-skill-needed.json",
        )

        self.assertTrue(result.valid, result.errors)

    def test_granted_unknown_capability_is_not_silent(self):
        with (ROOT / "fixtures/v3/routes/skills-selected.json").open(encoding="utf-8") as handle:
            route = json.load(handle)
        route["granted_capabilities"] = ["future_permission"]

        result = validate_instance("StageRoute", route)

        self.assertFalse(result.valid)
        self.assertIn("future_permission", result.unknown_capabilities)

    def test_missing_status_is_rejected_as_a_silent_route(self):
        with (ROOT / "fixtures/v3/routes/skills-selected.json").open(encoding="utf-8") as handle:
            route = json.load(handle)
        del route["status"]

        result = validate_instance("StageRoute", route)

        self.assertFalse(result.valid)
        self.assertTrue(any("status" in error for error in result.errors))

    def test_no_skill_route_cannot_contain_selected_skills(self):
        with (ROOT / "fixtures/v3/routes/no-skill-needed.json").open(encoding="utf-8") as handle:
            route = json.load(handle)
        route["selected_skills"] = [{"skill_id": "using-superpowers", "role": "GATE", "reason": "invalid"}]

        result = validate_instance("StageRoute", route)

        self.assertFalse(result.valid)


class CompatibilityTests(unittest.TestCase):
    def test_current_registry_entry_projects_without_inventing_provenance(self):
        with (ROOT / "fixtures/v3/compatibility/current-skill-index-entry.json").open(encoding="utf-8") as handle:
            entry = json.load(handle)
        registry = {
            "schema_version": "1.0",
            "source": "https://github.com/juhjuhx/agent-skills.git",
            "source_ref": "main"
        }

        projected = import_skill_index_entry(entry, registry)
        result = validate_instance("SkillMetadataV3", projected)

        self.assertTrue(result.valid, result.errors)
        self.assertEqual(projected["source"]["digest"], f"sha256:{entry['sha256']}")
        self.assertNotIn("license", projected["source"])
        self.assertIn("source.license", projected["extensions"]["compatibility"]["unavailable_fields"])

    def test_current_registry_import_reads_actual_source_truth(self):
        projected = import_current_skill(
            ROOT / ".superpowers/SKILLS_INDEX.json",
            "using-superpowers",
        )

        self.assertEqual(projected["skill_id"], "using-superpowers")
        self.assertEqual(projected["source"]["ref"], "main")
        self.assertEqual(projected["source"]["path"], "using-superpowers/SKILL.md")


class SchemaDocumentTests(unittest.TestCase):
    def test_all_public_schema_documents_are_loadable(self):
        schema_names = (
            "TaskSpec",
            "SkillMetadataV3",
            "AgentAdapterManifest",
            "ModelProfile",
            "StageRoute",
        )

        for name in schema_names:
            with self.subTest(schema=name):
                schema = load_schema(name)
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")


if __name__ == "__main__":
    unittest.main()
