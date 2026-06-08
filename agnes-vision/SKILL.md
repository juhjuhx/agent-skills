---
name: agnes-vision
description: "Agnes AI vision models for image analysis when the main model lacks image support. Use when: 看圖片、分析圖片、describe image、analyze screenshot、read text from image、image recognition、圖像分析、視覺分析。"
version: 1.0.0
---

# Agnes Vision

Use this skill ONLY when the currently active model cannot process images directly. The current model is text-only.

## API Configuration

```
Base URL: https://apihub.agnes-ai.com/v1
API Key: stored in opencode.json provider config
```

## Available Models

| Model | Purpose |
|-------|---------|
| `agnes-2.0-flash` | Text + Image analysis ✅ |
| `agnes-1.5-flash` | Pure text (lighter, faster) |

## How to Use

### Image Analysis (via curl)
```bash
curl -s --max-time 60 https://apihub.agnes-ai.com/v1/chat/completions \
  -H "Authorization: Bearer sk-A5O6uBsigOKqkrMmPmWnCuInOkqmKngQH0WXio2jEbkfVXs4" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agnes-2.0-flash",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "Describe this image in detail"},
          {"type": "image_url", "image_url": {"url": "IMAGE_URL_OR_DATA_URI"}}
        ]
      }
    ],
    "max_tokens": 1000
  }'
```

### For local images, convert to base64 first:
```bash
BASE64=$(base64 -i /path/to/image.jpg)
```
Then use `"url": "data:image/jpeg;base64,$BASE64"`

## When to Load This Skill

- User shares an image URL or uploads an image file
- User asks to describe/interpret a screenshot
- User asks to read text from an image (OCR)
- User asks to analyze a chart, graph, or diagram
- User mentions 看圖片 / 分析圖片 / 查看報表

## Error Handling

- 401: Invalid API key — check opencode.json provider config
- 404: Model not found — fall back to `agnes-2.0-flash`
- 429: Rate limited — wait and retry
- Timeout: Use `--max-time 60` for images

## Notes

- Image analysis takes 20-60 seconds — use long timeout
- `agnes-2.0-flash` handles both text and vision
- For pure text, `agnes-1.5-flash` is faster
- DO NOT load this skill if the currently active model already supports image recognition
