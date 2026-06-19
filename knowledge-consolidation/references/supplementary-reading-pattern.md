# Supplementary Directory Reading Pattern

When the user points to multiple directories of supplementary material, follow this pattern:

## Step 1: Discover All Files

```python
# Use search_files on EACH directory
for directory in user_mentioned_directories:
    results = search_files(pattern="*", target="files", path=directory)
    # Log all found files
```

## Step 2: Prioritize Reading Order

| Priority | File Type | Why |
|----------|-----------|-----|
| 1 | .md files | Structured content, easiest to integrate |
| 2 | .html files | May contain interactive elements, full content |
| 3 | Analysis/Report files | Pre-processed insights |
| 4 | Prompt files | Domain-specific structured prompts |
| 5 | SVG diagrams | Visual relationships between concepts |
| 6 | PNG/JPG images | Use vision_analyze for extraction |

## Step 3: Read Everything

Use `execute_code` with `read_file` in a loop to batch-read all files. Extract first 2000-3000 chars of each to understand content, then read completely those that are most relevant.

## Step 4: Integrate, Don't Just Append

Don't just copy supplementary content into the output. Instead:
- Identify unique content not in primary sources
- Identify better explanations of existing concepts
- Identify new concepts to add
- Merge the best of each source into unified sections

## Real Example: ETC Eos Knowledge Archive

Primary sources: 4 markdown files + 1 PDF about ETC Eos console
Supplementary directories:
- `diagram/` — 6 SVG diagrams (visual relationships)
- `ETC-Eos-Knowledge-Base/` — index.html, report.md, knowledge graph, infographic, 8 prompt files
- `infographic/` — infographic.png, structured-content.md, analysis.md, prompt
- `prompts/` — 9 detailed prompt files (submaster, patch, troubleshooting, macros, magic sheets, advanced techniques, network/timecode, color picker)

Result: Each prompt file added 100-200 lines of new content that wasn't in the primary sources.
