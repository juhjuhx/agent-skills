---
name: diagrams
description: "Create technical diagrams: dark-themed SVG architecture diagrams and hand-drawn Excalidraw diagrams. Use when: architecture diagram, flowchart, system design, SVG diagram, Excalidraw."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Diagrams, Architecture, SVG, Excalidraw, Flowcharts, Visualization]
    related_skills: [ascii-content, popular-web-designs]
---

# Diagrams

Two diagramming tools — choose based on the output style needed.

## Quick Decision

| Need | Tool | Output |
|------|------|--------|
| Professional dark-themed tech diagrams | Architecture Diagram | Standalone HTML with inline SVG |
| Hand-drawn whiteboard sketches | Excalidraw | .excalidraw JSON file |

---

## Section 1: Architecture Diagrams (Dark SVG)

Generate professional, dark-themed technical architecture diagrams as standalone HTML files with inline SVG. No external tools, no API keys, no rendering libraries.

### Best suited for
- Software system architecture (frontend/backend/database)
- Cloud infrastructure (VPC, regions, subnets, managed services)
- Microservice topology
- Database + API maps, deployment diagrams

### Color Palette (Semantic)

| Component Type | Fill (rgba) | Stroke (Hex) |
|---------------|-------------|---------------|
| Frontend | `rgba(8, 51, 68, 0.4)` | `#22d3ee` (cyan) |
| Backend | `rgba(6, 78, 59, 0.4)` | `#34d399` (emerald) |
| Database | `rgba(76, 29, 149, 0.4)` | `#a78bfa` (violet) |
| AWS/Cloud | `rgba(120, 53, 15, 0.3)` | `#fbbf24` (amber) |
| Security | `rgba(136, 19, 55, 0.4)` | `#fb7185` (rose) |

### Document Structure

1. Header: Title with pulsing dot indicator
2. Main SVG: Diagram in rounded border card
3. Summary Cards: Three cards below for high-level details
4. Footer: Minimal metadata

### Template

Load the full HTML template:
```
skill_view(name="diagrams", file_path="templates/template.html")
```

---

## Section 2: Excalidraw Diagrams (Hand-drawn)

Create diagrams by writing Excalidraw element JSON and saving as `.excalidraw` files. Drag-and-drop onto excalidraw.com for viewing.

### Element Format

**Required fields:** `type`, `id`, `x`, `y`, `width`, `height`

**Labeled shape (container binding):**
```json
{ "type": "rectangle", "id": "r1", "x": 100, "y": 100, "width": 200, "height": 80,
  "roundness": { "type": 3 }, "backgroundColor": "#a5d8ff",
  "boundElements": [{ "id": "t_r1", "type": "text" }] },
{ "type": "text", "id": "t_r1", "x": 105, "y": 110, "width": 190, "height": 25,
  "text": "Hello", "fontSize": 20, "fontFamily": 1,
  "containerId": "r1", "originalText": "Hello", "autoResize": true }
```

**WARNING:** Do NOT use `"label": { "text": "..." }` on shapes — use container binding.

### Arrow Bindings

```json
{ "type": "arrow", "id": "a1", "x": 300, "y": 150, "width": 150, "height": 0,
  "points": [[0,0],[150,0]], "endArrowhead": "arrow",
  "startBinding": { "elementId": "r1", "fixedPoint": [1, 0.5] },
  "endBinding": { "elementId": "r2", "fixedPoint": [0, 0.5] } }
```

### Color Palette

| Use | Fill Color | Hex |
|-----|-----------|-----|
| Primary | Light Blue | `#a5d8ff` |
| Success | Light Green | `#b2f2bb` |
| Warning | Light Orange | `#ffd8a8` |
| Processing | Light Purple | `#d0bfff` |
| Error | Light Red | `#ffc9c9` |
| Notes | Light Yellow | `#fff3bf` |
| Storage | Light Teal | `#c3fae8` |

### Z-Order

Emit progressively: background zones → shape → its bound text → its arrows → next shape

### Font Sizes

- Minimum `fontSize`: 16 for body text
- Minimum `fontSize`: 20 for titles
- NEVER use `fontSize` below 14

---

## Common Pitfalls

1. **Architecture: Legend placement** — must be outside all boundary boxes
2. **Architecture: Z-order** — draw arrows early so they render behind boxes
3. **Excalidraw: Container binding** — MUST use boundElements + containerId, not label property
4. **Excalidraw: Text contrast** — never use light gray on white backgrounds
5. **Excalidraw: No emoji** — they don't render in Excalidraw's font
