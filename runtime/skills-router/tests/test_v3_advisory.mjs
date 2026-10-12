import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { createSkillsRouter } from "../adapters/opencode/skills-router.js";

const ADAPTER = new URL("../adapters/opencode/skills-router.js", import.meta.url);
const tools = ["skill", "read", "glob", "grep", "bash", "write", "mcp_unknown"];

for (const scenario of ["missing", "throw", "deny", "stale", "wrong-session", "malformed"]) {
  test(`V3 ${scenario}: router cannot disable host tools`, async () => {
    const routePreflight = async () => {
      if (scenario === "throw") throw new Error("router unavailable");
      if (scenario === "missing") return null;
      if (scenario === "malformed") return "bad";
      return { decision: "deny", session_id: "another", created_at: "2000-01-01", failure: { code: "POLICY_DENIED" } };
    };
    const plugin = createSkillsRouter({ directory: "/tmp", routePreflight });
    await assert.doesNotReject(() => plugin["chat.message"]({ sessionID: "session" }, { parts: [{ type: "text", text: "Fix bug" }] }));
    // Asserted, not skipped: an adapter that drops the hook must fail here rather
    // than silently turn this whole invariant into a no-op assertion.
    assert.equal(typeof plugin["tool.execute.before"], "function", "adapter must expose an explicit non-authoritative tool gate");
    for (const tool of tools) {
      const input = {sessionID: "other", tool}, output = {args: {command: "python3 -m unittest", filePath: "/tmp/any-file"}};
      const before = structuredClone({input, output});
      await assert.doesNotReject(() => plugin["tool.execute.before"](input, output));
      assert.deepEqual({input, output}, before, "router cannot mutate host execution arguments");
    }
    await plugin.dispose();
  });
}

// Supplementary source heuristic; behavioural input/output invariants remain authoritative.
test("V3 adapter source contains no tool-blocking authority", () => {
  // Strip comments so the guard inspects executable structure, not prose that
  // merely documents the invariant. String literals are kept so the quoted
  // `tool.execute.before` hook key stays visible to the assertions below.
  const code = readFileSync(ADAPTER, "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1 ");
  for (const forbidden of [/\bthrow\b/, /permission\.(ask|reject)/, /\bexpires?\b/i, /\bttl\b/i, /RuntimeDecision/]) {
    assert.doesNotMatch(code, forbidden, `adapter code must not contain ${forbidden}`);
  }
  assert.match(code, /tool\.execute\.before/);
  assert.doesNotMatch(code, /tool\.execute\.after/, "V3 needs no post-execution authority either");
});
test("V3 session isolation retains advice, not permission state", async () => {
  const plugin = createSkillsRouter({ routePreflight: async (task) => ({ task, skills: [], workflow: ["Read", "Verify"] }) });
  await plugin["chat.message"]({ sessionID: "A" }, { parts: [{ type: "text", text: "Fix A" }] });
  await plugin["chat.message"]({ sessionID: "B" }, { parts: [{ type: "text", text: "Fix B" }] });
  const a = { system: [] }, b = { system: [] };
  await plugin["experimental.chat.system.transform"]({ sessionID: "A" }, a);
  await plugin["experimental.chat.system.transform"]({ sessionID: "B" }, b);
  assert.match(a.system.join(""), /Fix A/); assert.doesNotMatch(a.system.join(""), /Fix B/);
  assert.match(b.system.join(""), /Fix B/); assert.doesNotMatch(b.system.join(""), /Fix A/);
  assert.doesNotMatch(a.system.join(""), /RuntimeDecision/);
});


test("V3 valid route bounds host catalog metadata without changing tools", async () => {
  const plugin = createSkillsRouter({ routePreflight: async (task) => ({ task, skills: [{name: "debugging", body_status: "verified"}], workflow: ["Read", "Verify"] }) });
  const catalog = "Skills provide specialized instructions and workflows for specific tasks.\nUse the skill tool to load a skill when a task matches its description.\n<available_skills>" + ["using-superpowers", "debugging", "unrelated-animation"].map((name) => `<skill><name>${name}</name><description>metadata ${name}</description></skill>`).join("") + "</available_skills>";
  await plugin["chat.message"]({sessionID: "A"}, {parts: [{type: "text", text: "Fix A"}]});
  for (let step = 0; step < 2; step++) {
    const sharedSystem = ["HOST RULES KEEP", catalog];
    const output = {system: sharedSystem};
    await plugin["experimental.chat.system.transform"]({sessionID: "A"}, output);
    assert.equal(output.system, sharedSystem, "host retains the system array reference");
    assert.equal(output.system[0], "HOST RULES KEEP");
    assert.match(output.system.join(""), /<name>using-superpowers<\/name>/);
    assert.match(output.system.join(""), /<name>debugging<\/name>/);
    assert.doesNotMatch(output.system.join(""), /unrelated-animation/);
    assert.match(output.system.join(""), /Fix A/);
    const once = [...output.system];
    await plugin["experimental.chat.system.transform"]({sessionID: "A"}, output);
    assert.deepEqual(output.system, once, "real native catalog is idempotent too");
  }
  const unknown = {system: [catalog]};
  await plugin["experimental.chat.system.transform"]({sessionID: "B"}, unknown);
  assert.deepEqual(unknown.system, [catalog]);
  const input = {sessionID: "A", tool: "skill"}, output = {args: {name: "unrelated-animation"}};
  const before = structuredClone({input, output});
  await plugin["tool.execute.before"](input, output);
  assert.deepEqual({input, output}, before);
});


test("V3 timeout and fallback keep native catalog and execution untouched", async () => {
  const plugin = createSkillsRouter({timeoutMs: 5, routePreflight: () => new Promise(() => {})});
  await plugin["chat.message"]({sessionID: "A"}, {parts: [{type: "text", text: "Fix bug"}]});
  const catalog = "<available_skills><skill><name>unrelated-animation</name></skill></available_skills>";
  const system = [catalog], output = {system};
  await plugin["experimental.chat.system.transform"]({sessionID: "A"}, output);
  assert.equal(system[0], catalog);
  await assert.doesNotReject(() => plugin["tool.execute.before"]({tool: "bash"}, {args: {command: "echo test"}}));
  await plugin.dispose();
});


test("V3 preserves rule/user examples sharing catalog tags and is idempotent", async () => {
  const plugin = createSkillsRouter({routePreflight: async (task) => ({task, skills: [{name: "debugging"}], workflow: ["Read"]})});
  await plugin["chat.message"]({sessionID: "A"}, {parts: [{type: "text", text: "Review A"}]});
  const example = "Host rule example: NEVER reduce this list:\n<available_skills><skill><name>debugging</name></skill><skill><name>unknown</name></skill></available_skills>";
  const output = {system: [example]};
  await plugin["experimental.chat.system.transform"]({sessionID: "A"}, output);
  assert.equal(output.system[0], example);
  const first = [...output.system];
  await plugin["experimental.chat.system.transform"]({sessionID: "A"}, output);
  assert.deepEqual(output.system, first);
});


test("V3 bounds recognized oh-my skill tool metadata while preserving schema", async () => {
  const plugin = createSkillsRouter();
  assert.equal(typeof plugin["tool.definition"], "function");
  const prefix = "Load a skill or execute a slash command to get detailed instructions for a specific task.\n\nSkills and commands provide specialized knowledge and step-by-step guidance.\nUse this when a task matches an available skill's or command's description.\n\n**How to use:**\n- Call with a skill name: name='review-work'\n- Call with a command name (without leading slash): name='publish'\n- The tool will return detailed instructions with your context applied.\n";
  const catalog = "<available_items>\nPriority: project > user > opencode > builtin/plugin\nInvoke via: skill(name=\"item-name\") - omit leading slash for commands.\n" + ["using-superpowers", "unrelated-animation"].map((name) => `<command><name>/${name}</name><description>metadata</description><scope>user</scope></command>`).join("\n") + "\n</available_items>";
  const parameters = {name: {type: "string"}, user_message: {type: "string"}};
  const output = {description: prefix + catalog, parameters};
  await plugin["tool.definition"]({toolID: "skill"}, output);
  assert.equal(output.parameters, parameters);
  assert.ok(output.description.startsWith(prefix));
  assert.match(output.description, /using-superpowers/);
  assert.doesNotMatch(output.description, /unrelated-animation/);
  const unknown = {description: "Custom commands should stay: " + catalog, parameters};
  const before = structuredClone(unknown);
  await plugin["tool.definition"]({toolID: "skill"}, unknown);
  assert.deepEqual(unknown, before);
  const another = {description: prefix + catalog, parameters};
  await plugin["tool.definition"]({toolID: "read"}, another);
  assert.equal(another.description, prefix + catalog);
  await assert.doesNotReject(() => plugin["tool.execute.before"]({tool: "skill"}, {args: {name: "unrelated-animation"}}));
});


test("V3 preserves full native catalog quoted in project instructions", async () => {
  const plugin = createSkillsRouter({routePreflight: async (task) => ({task, skills: [{name: "debugging"}], workflow: ["Read"]})});
  await plugin["chat.message"]({sessionID: "A"}, {parts: [{type: "text", text: "Review A"}]});
  const catalog = "Skills provide specialized instructions and workflows for specific tasks.\nUse the skill tool to load a skill when a task matches its description.\n<available_skills><skill><name>debugging</name></skill><skill><name>unknown</name><description>PROJECT RULE KEEP</description></skill></available_skills>";
  for (const example of ["Keep this example verbatim:\n```text\n" + catalog + "\n```", catalog + "\nPROJECT RULE KEEP AFTER CATALOG"]) {
    const output = {system: [example]};
    await plugin["experimental.chat.system.transform"]({sessionID: "A"}, output);
    assert.equal(output.system[0], example, "mixed project instructions must not be reduced as a standalone native catalog");
  }
  await plugin.dispose();
});

test("V3 discarded session request cannot overwrite newest advice after counter eviction", async () => {
  let finishOld, startedOld;
  const started = new Promise((resolve) => { startedOld = resolve; });
  const plugin = createSkillsRouter({routePreflight: async (task) => {
    if (task === "OLD A") {
      startedOld();
      return new Promise((resolve) => { finishOld = resolve; });
    }
    return {task, skills: [], workflow: ["Read"]};
  }});
  const send = (id, task) => plugin["chat.message"]({sessionID: id}, {parts: [{type: "text", text: task}]});
  await send("A", "WARM A");
  for (let i = 0; i < 99; i++) await send("B" + i, "WARM B");
  const old = send("A", "OLD A");
  await started;
  await send("B99", "NEW B");
  await send("A", "NEW A");
  await send("A", "NEWEST A");
  finishOld({task: "OLD A", skills: [], workflow: ["Wrong workflow"]});
  await old;
  const output = {system: []};
  await plugin["experimental.chat.system.transform"]({sessionID: "A"}, output);
  assert.match(output.system.join(""), /NEWEST A/);
  assert.doesNotMatch(output.system.join(""), /OLD A/);
  await plugin.dispose();
});


test("V3 preserves complete oh-my catalog examples inside a custom skill description", async () => {
  const plugin = createSkillsRouter();
  const prefix = "Load a skill or execute a slash command to get detailed instructions for a specific task.\n\nSkills and commands provide specialized knowledge and step-by-step guidance.\nUse this when a task matches an available skill's or command's description.\n\n**How to use:**\n- Call with a skill name: name='review-work'\n- Call with a command name (without leading slash): name='publish'\n- The tool will return detailed instructions with your context applied.\n";
  const catalog = "<available_items>\nPriority: project > user > opencode > builtin/plugin\nInvoke via: skill(name=\"item-name\") - omit leading slash for commands.\n<command><name>/using-superpowers</name></command><command><name>/permission-example</name><description>PROJECT RULE KEEP</description></command>\n</available_items>";
  const parameters = {name: {type: "string"}};
  for (const description of [prefix + "Keep this example verbatim:\n```text\n" + catalog + "\n```", prefix + catalog + "\nPROJECT RULE KEEP AFTER CATALOG"]) {
    const output = {description, parameters};
    await plugin["tool.definition"]({toolID: "skill"}, output);
    assert.equal(output.description, description);
    assert.equal(output.parameters, parameters);
  }
});
