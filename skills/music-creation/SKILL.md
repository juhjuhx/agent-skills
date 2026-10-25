---
name: music-creation
description: "AI music generation and songwriting: HeartMuLa, Suno prompts, lyrics craft. Use when: generate music, write song, Suno prompt, AI music, song lyrics, parody."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Music, Songwriting, AI-Generation, HeartMuLa, Suno, Lyrics, Creative]
    related_skills: [audiocraft-audio-generation, songsee]
---

# Music Creation

AI music generation and songwriting craft — from lyrics to finished songs.

## Section 1: AI Music Generation (HeartMuLa)

Open-source music foundation model (Apache-2.0) that generates full songs from lyrics + tags. Comparable to Suno.

### Hardware Requirements

- **Minimum:** 8GB VRAM with `--lazy_load true`
- **Recommended:** 16GB+ VRAM
- **CPU:** Possible but extremely slow (30-60+ min per song)

### Quick Start

```bash
cd ~/heartlib && . .venv/bin/activate
python ./examples/run_music_generation.py \
  --model_path=./ckpt \
  --version="3B" \
  --lyrics="./assets/lyrics.txt" \
  --tags="./assets/tags.txt" \
  --save_path="./assets/output.mp3" \
  --lazy_load true
```

### Input Format

**Tags:** `piano,happy,wedding,synthesizer,romantic`

**Lyrics:**
```
[Intro]
[Verse]
Your lyrics here...
[Chorus]
Chorus lyrics...
[Bridge]
Bridge lyrics...
[Outro]
```

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--max_audio_length_ms` | 240000 | Max length (240s = 4 min) |
| `--lazy_load` | false | Load/unload models on demand (saves VRAM) |
| `--mula_dtype` | bfloat16 | bf16 recommended |
| `--codec_dtype` | float32 | fp32 recommended for quality |

### Pitfalls

- Do NOT use bf16 for HeartCodec — degrades audio quality
- Tags may be ignored — lyrics tend to dominate
- Triton not available on macOS
- Dependency conflicts require manual patches

## Section 2: Songwriting Craft

Everything here is a GUIDELINE, not a rule. Art breaks rules on purpose.

### Song Structure

```
ABABCB  Verse/Chorus/Verse/Chorus/Bridge/Chorus    (most pop/rock)
AABA    Verse/Verse/Bridge/Verse                    (jazz standards)
AAA     Verse/Verse/Verse (strophic)                (folk, storytelling)
```

### Rhyme Types

- **Perfect:** lean/mean
- **Family:** crate/braid
- **Assonance:** had/glass (same vowels)
- **Slant:** enough to suggest connection without locking it down

Mix them. All perfect rhymes sounds like nursery rhyme. The blend is where it lives.

### Emotional Arc

```
Intro: 2-3  |  Verse: 5-6  |  Pre-Chorus: 7
Chorus: 8-9  |  Bridge: varies  |  Final Chorus: 9-10
```

The most powerful dynamic trick: **CONTRAST.** Whisper before a scream hits harder than just screaming.

### Show, Don't Tell

- "I was sad" = flat
- "Your hoodie's still on the hook by the door" = alive

## Section 3: Suno AI Prompt Engineering

### Style Description Field

Formula: Genre + Mood + Era + Instruments + Vocal Style + Production + Dynamics

```
BAD:  "sad rock song"
GOOD: "Cinematic orchestral spy thriller, 1960s Cold War era, smoky
       sultry female vocalist, big band jazz, brass section with
       trumpets and french horns, sweeping strings, minor key"
```

### Metatags (in [brackets] inside lyrics)

**Structure:** `[Intro]` `[Verse]` `[Chorus]` `[Bridge]` `[Outro]`

**Performance:** `[Whispered]` `[Belted]` `[Falsetto]` `[Raspy]` `[Soulful]`

**Dynamics:** `[High Energy]` `[Building Energy]` `[Explosive]` `[Emotional Climax]`

### Phonetic Tricks for AI Singers

- Spell words as they SOUND: "through" → "thru"
- Proper nouns have highest failure rate — test early
- ALL CAPS = louder, more intense
- Vowel extension: "lo-o-o-ove" = sustained/melisma
- Spell out numbers: "24/7" → "twenty four seven"

---

## Common Pitfalls

1. **HeartCodec needs fp32** — bf16 degrades audio quality
2. **Suno style drift** — restate genre/mood when extending
3. **Proper nouns fail** — test in short clip first
4. **Tags may be ignored** — lyrics dominate in HeartMuLa
5. **~3-5 generations per good result** — revision is normal
6. **Keep some original lines in parody** — adds recognizability
