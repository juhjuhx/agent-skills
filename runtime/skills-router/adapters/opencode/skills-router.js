import { spawn } from "node:child_process";
import { homedir } from "node:os";
import { join } from "node:path";

// V3: advice only. Host permissions remain authoritative; no TTL/tool gate.
const SOURCE = process.env.SKILLS_ROUTER_SOURCE || join(homedir(), ".agents/skills");
const FALLBACK = "using-superpowers: routing unavailable. Discover relevant Skills and actual tools, inspect needed context, execute a small workflow, then verify. Host-native tools and permissions remain unchanged.";
const LIMIT = 16000;

function route(prompt, directory) {
  return new Promise((resolve) => {
    let result = "", bytes = 0, settled = false;
    const child = spawn(process.env.SKILLS_ROUTER_PYTHON || "python3", [
      join(SOURCE, "runtime/skills-router/tool_master.py"), "route", "--stdin",
      "--root", SOURCE, "--host", "opencode", "--json",
    ], { cwd: directory, shell: false, stdio: ["pipe", "pipe", "pipe"] });
    const finish = (value) => { if (!settled) { settled = true; clearTimeout(timer); resolve(value); } };
    const timer = setTimeout(() => { child.kill(); finish(null); }, 2000);
    child.on("error", () => finish(null));
    child.stdout.on("data", (chunk) => {
      bytes += chunk.length;
      if (bytes > 32768) { child.kill(); finish(null); return; }
      result += chunk.toString("utf8");
    });
    child.stderr.resume();
    child.on("close", (code) => {
      try { finish(code === 0 ? JSON.parse(result) : null); } catch { finish(null); }
    });
    child.stdin.on("error", () => finish(null));
    child.stdin.end(JSON.stringify({ task: prompt }));
  });
}

// Only a standalone native catalog is recognized. Mixed rules/examples stay intact.
function compactCatalog(text, names) {
  return text.replace(/^(Skills provide specialized instructions and workflows for specific tasks\.\r?\nUse the skill tool to load a skill when a task matches its description\.\r?\n)(<available_skills>[\s\S]*?<\/available_skills>)(\s*)$/, (original, prefix, block, suffix) => {
    const entries = [...block.matchAll(/<skill>[\s\S]*?<\/skill>/g)];
    if (!entries.length || block.slice("<available_skills>".length, -"</available_skills>".length)
      .replace(/<skill>[\s\S]*?<\/skill>/g, "").trim()) return original;
    const kept = entries.filter(([entry]) => names.has(entry.match(/<name>([^<]*)<\/name>/)?.[1]?.trim()));
    if (!kept.length) return original; // Unknown host format retains native discovery.
    return prefix + "<available_skills>\n" + kept.map(([entry]) => entry).join("\n") + "\n</available_skills>" + suffix;
  });
}

export function createSkillsRouter({ directory = process.cwd(), routePreflight = route, timeoutMs = 2200 } = {}) {
  const pending = new Map();
  const revisions = new Map();
  return {
    "chat.message": async (input, output) => {
      const id = input?.sessionID;
      if (typeof id !== "string" || !id || id.length > 256) return;
      // Request identity is never reused after cache eviction or disposal.
      const revision = Symbol();
      revisions.set(id, revision);
      pending.delete(id);
      const prompt = (Array.isArray(output?.parts) ? output.parts : [])
        .slice(0, 256).filter((p) => p?.type === "text" && typeof p.text === "string")
        .map((p) => p.text.slice(0, LIMIT)).join("\n").slice(0, LIMIT);
      let packet = null, timer;
      try {
        packet = await Promise.race([
          Promise.resolve().then(() => routePreflight(prompt, directory, id)),
          new Promise((resolve) => { timer = setTimeout(() => resolve(null), timeoutMs); }),
        ]);
      } catch { /* Router failure never disables host tools. */ }
      finally { clearTimeout(timer); }
      if (revisions.get(id) !== revision) return;
      const valid = packet && typeof packet === "object" && !Array.isArray(packet)
        && packet.task && Array.isArray(packet.workflow);
      pending.set(id, {
        advice: valid ? "[Personal Tool Master V3 — advisory; selected skills are recommendations, other native skills/tools remain available under host permissions] " + JSON.stringify(packet).slice(0, LIMIT) : FALLBACK,
        names: valid ? new Set(["using-superpowers", ...(Array.isArray(packet.skills) ? packet.skills.slice(0, 8).map((s) => s?.name).filter((name) => typeof name === "string") : [])]) : null,
      });
      while (pending.size > 100) pending.delete(pending.keys().next().value);
      while (revisions.size > 100) revisions.delete(revisions.keys().next().value);
    },
    "experimental.chat.system.transform": async (input, output) => {
      const route = pending.get(input?.sessionID);
      if (route && Array.isArray(output?.system)) {
        if (route.names) for (let i = 0; i < output.system.length; i++) {
          if (typeof output.system[i] === "string") output.system[i] = compactCatalog(output.system[i], route.names);
        }
        if (!output.system.includes(route.advice)) output.system.push(route.advice);
      }
    },
    "tool.definition": async (input, output) => {
      // This hook has no sessionID: never use another session's selected names.
      // Keep the real mother entry and leave execution/parameters untouched.
      const prefix = "Load a skill or execute a slash command to get detailed instructions for a specific task.\n\nSkills and commands provide specialized knowledge and step-by-step guidance.\nUse this when a task matches an available skill's or command's description.\n\n**How to use:**\n- Call with a skill name: name='review-work'\n- Call with a command name (without leading slash): name='publish'\n- The tool will return detailed instructions with your context applied.\n";
      if (input?.toolID !== "skill" || typeof output?.description !== "string"
        || !output.description.startsWith(prefix)) return;
      const catalog = output.description.slice(prefix.length).match(/^(\s*)<available_items>\r?\nPriority: project > user > opencode > builtin\/plugin(?: \| Skills listed before commands)?\r?\nInvoke via: skill\(name="item-name"\) - omit leading slash for commands\.\r?\n([\s\S]*?)\r?\n<\/available_items>(\s*)$/);
      if (!catalog || catalog[2].replace(/<(command|skill)>[\s\S]*?<\/\1>/g, "").trim()) return;
      const entries = [...catalog[2].matchAll(/<command>[\s\S]*?<\/command>/g)];
      const mother = entries.find(([entry]) => /<name>\/using-superpowers<\/name>/.test(entry));
      if (!mother) return;
      output.description = prefix + catalog[1] + "<available_items>\n" + mother[0]
        + "\n</available_items>\nPersonal Tool Master V3: use the task route packet for selected skill names/paths; discover additional skills or commands from their local metadata when needed. Unlisted items remain loadable under host permissions; no command or skill execution is disabled." + catalog[3];
    },
    "tool.execute.before": async () => { /* No router permission authority. */ },
    dispose: async () => { pending.clear(); revisions.clear(); },
  };
}

export const SkillsRouterPlugin = async ({ directory } = {}) => createSkillsRouter({ directory });
export default { id: "personal-tool-master-v3", server: SkillsRouterPlugin };
