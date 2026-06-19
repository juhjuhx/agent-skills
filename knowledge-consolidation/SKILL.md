---
name: knowledge-consolidation
description: "Build comprehensive knowledge archives from multiple source files — consolidates notes, PDFs, supplementary directories, and web research into structured .md + interactive .html knowledge bases. Use when: knowledge base, knowledge archive, knowledge graph, 知識圖譜, consolidate notes, build reference, 結構化知識庫, merge documents, multi-source research."
---

# Knowledge Consolidation — Multi-Source Knowledge Archive Builder

Consolidate scattered knowledge from multiple source files, supplementary directories, and web research into comprehensive, structured knowledge archives with both markdown and interactive HTML outputs.

## When to Use

- User has notes/PDFs/markdown files on a topic and wants a structured knowledge base
- User points to multiple directories of supplementary material to integrate
- Need to create both .md (reference) and .html (interactive) knowledge documents
- Domain knowledge needs web research supplementation
- User wants a searchable, browsable knowledge archive

## Workflow (6 Phases)

### Phase 1: Source Discovery & Ingestion

1. **Read ALL primary source files** — never skip any, even if they seem redundant
2. **Scan ALL supplementary directories** the user points to — use `search_files(target='files')` on each directory
3. **Read every file found** — markdown, HTML, SVG, analysis docs, prompts, reports
4. **Note the user's PDFs** — use `vision_analyze` for image-based PDFs; for text PDFs use `web_extract` with file:// or read_file
5. **Catalog source quality** — classify each source as A (official), B (personal notes), C (secondary), D (community)

### Phase 2: Domain Research

1. **Web search for official documentation** — manufacturer docs, official help, knowledge bases
2. **Web search for professional insights** — interviews, blog posts, practitioner experiences
3. **Web search for community wisdom** — forums, Reddit, social media posts by practitioners
4. **Web extract key pages** — get full content from the most relevant URLs
5. **Search in the user's working language** — if the user works in Traditional Chinese, search in both English AND Traditional Chinese

### Phase 3: Structure Design

Before writing, design the knowledge architecture:

```
1. Title + metadata (author, version, date, scope)
2. Knowledge Architecture Overview (ASCII/SVG diagram)
3. Core Modules (the main content — 5-15 modules depending on domain)
4. Cross-cutting Concerns (troubleshooting, workflows, quick reference)
5. Supplementary Knowledge (from web research)
6. Expert Insights (quotes, best practices from practitioners)
7. Learning Path (beginner → intermediate → advanced → master)
8. Quick Reference / Cheat Sheet
9. Appendices (complete reference tables)
```

### Phase 4: Content Creation (Parallel)

**CRITICAL: Use delegate_task with parallel subagents for .md and .html**

Both files share the same source material but serve different purposes:
- `.md` — comprehensive reference, searchable, printable, Mermaid diagrams
- `.html` — interactive, visual, searchable, filterable, beautiful

Dispatch two parallel subagents with:
- Complete context about ALL source material
- Explicit structure requirements
- Design requirements for HTML (theme, colors, typography)
- Content requirements for .md (sections, tables, diagrams)

### Phase 5: Quality Verification

After both files are created:
1. Check file sizes (should be substantial — 50KB+ each)
2. Verify line counts (1000+ lines expected)
3. Spot-check key content (author credit, main sections, interactive features)
4. Verify HTML works offline (no external dependencies)

### Phase 6: Iterative Refinement

When user provides feedback:
1. **Read the feedback carefully** — user corrections are FIRST-CLASS signals
2. **Re-read supplementary sources** if user points to new directories
3. **Web research for specific topics** the user wants deepened
4. **Re-dispatch subagents** with updated requirements and all new context
5. **Verify changes** after update

## Pitfalls

| Pitfall | Prevention |
|---------|------------|
| Skipping supplementary directories | Always scan ALL directories user mentions, even if they seem redundant |
| Abstract philosophy instead of practical teaching | Always use "Design Intent → Tool/Command → Specific Action → Result" format |
| Forgetting author credit | Add author in header AND footer of both files |
| Not reading enough source material | Read every file completely — truncated reads lose critical context |
| Single-agent bottleneck | Use parallel subagents for .md and .html — they're independent |
| Ignoring web research | Always search for official docs + practitioner insights + community wisdom |
| Missing Traditional Chinese content | If user works in zh-TW, ALL output must be in Traditional Chinese |
| HTML with external dependencies | All CSS/JS must be inline, no CDN links, works offline |

## Design Philosophy Teaching Pattern

When creating technical documentation that teaches "how to use tool X to create Y":

```
### [Concept Name] — [One-line artistic principle]

[2-3 sentence philosophical connection between concept and art]

#### How to Realize

| Design Intent | Shortcut | Command | Design Result |
|:---|:---|:---|:---|
| [What artist wants] | [Key combo] | [Exact command] | [What happens] |

#### Master Class Tip
> [Professional insight from real practitioner]

#### Practical Example
Step-by-step key sequence for a real scenario.
```

**NEVER** use abstract-only explanations. Every concept must have:
1. A practical "How to Realize" table
2. A "Master Class Tip" with real practitioner insight
3. A step-by-step practical example

## HTML Output Requirements

- Dark theme (deep colors, warm accents) — theatrical/professional feel
- All CSS and JS inline — no external dependencies
- Responsive design
- Interactive features: search, filters, expandable sections, theme toggle
- localStorage for user state (checklists, preferences)
- Print-friendly CSS
- Author credit in header and footer
- Data visualizations (charts, diagrams) using inline SVG or CSS

## Reference Files

See `references/supplementary-reading-pattern.md` for the multi-directory reading pattern.
