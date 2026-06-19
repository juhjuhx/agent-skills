# Theatrical / Technical Design Documentation Pattern

When creating documentation that teaches how to use a technical tool to achieve artistic/design goals, follow this pattern.

## The Problem

Most technical documentation is either:
- Pure reference (dry, no context for WHY to use something)
- Pure philosophy (abstract, no concrete HOW-TO)

The user wants BOTH: artistic intent mapped to specific technical actions.

## The Pattern: Intent → Tool → Action → Result

### Structure for Each Concept

```markdown
### [Concept Name] — [One-line artistic principle]

[2-3 sentence paragraph connecting the concept to artistic practice.
This is the "why" — not abstract philosophy, but the artistic REASON
this tool exists.]

#### How to Realize

| Design Intent | Shortcut | Command | Design Result |
|:---|:---|:---|:---|
| Create emotional pacing | I | Time 6 / 2 | 6s fade in, 2s fade out |
| Gentle disappearance | N | Chan 1 @ Full Sneak | Light slowly returns to cue state |
| Wave across stage | Ctrl+O | Offset → Odd/Even | Odd/even fixtures phase apart |

#### Master Class Tip
> [Real quote or insight from a professional practitioner.
> Source: Name, Role, Context]

#### Practical Example: [Scenario Name]
Step-by-step key sequence for a concrete scenario.
Include the artistic reasoning for each step.
```

### Real-World Examples Section

Always include a section with insights from actual practitioners:
- Interviews from manufacturer blogs
- Quotes from professional lighting designers
- Community wisdom from forums/social media
- Academic research on design as dramaturgy

### Example: "Light as Narrative" Teaching

WRONG (abstract):
> Cue is the basic unit of lighting design. Use Record Cue to save states.

RIGHT (practical):
> ### 光的敘事 — 用光說故事
> Every Cue is a sentence in your visual story. The audience reads light
> before they read text. Your job is to write light that speaks.
>
> | Design Intent | Key | Command | Result |
> |:---|:---|:---|:---|
> | Mark a story beat | R | Record Cue 1 | Freeze this moment |
> | Emotional weight | I | Time 6 / 2 | Slow rise, fast fall = tension |
> | Non-linear story | Q | Cue 10 Link To 3 | Jump back to repeat a moment |
>
> **Master Class Tip:**
> > "Augment3d allows you to insert all necessary cues before arriving
> > at the venue. With Monday editing to Friday debut, using Augment3d
> > really helped." — Emanuele Agliati, La Scala Academy

## Language Notes

- If the user works in Traditional Chinese (zh-TW), ALL output in zh-TW
- Technical terms (Cue, Palette, Effect, etc.) stay in English — they're industry standard
- Philosophical concepts get Chinese names with English in parentheses
- Use 繁體中文 for all explanatory text
