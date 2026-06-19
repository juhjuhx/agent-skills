---
name: messaging-gateway
description: "Set up Hermes as a chatbot on messaging platforms — Telegram, LINE, Discord, iMessage, WhatsApp, WeChat, Slack, Signal, Matrix. Also covers AstrBot as an alternative frontend with Hermes MCP backend."
version: 1.0.0
---

# Messaging Gateway — Hermes Chatbot Setup

Set up Hermes Agent as a chatbot on messaging platforms, or use AstrBot as an alternative frontend with Hermes as the MCP backend.

## Quick Decision Tree

```
Want LINE support?
├── Yes → AstrBot (native LINE adapter) + Hermes MCP backend
└── No → Hermes Gateway (native)
    ├── Telegram (easiest, recommended)
    ├── Discord
    ├── WhatsApp
    ├── iMessage (needs BlueBubbles + always-on Mac)
    ├── Slack / Signal / Matrix / WeChat
    └── Others
```

## Option A: Hermes Gateway (Native)

Hermes has built-in gateway support for 15+ platforms.

### Setup

```bash
hermes gateway setup    # Interactive platform picker
hermes gateway run      # Foreground (testing)
hermes gateway install  # Background service (launchd on macOS)
hermes gateway start    # Start installed service
```

### Supported Platforms

| Platform | Adapter | Notes |
|----------|---------|-------|
| Telegram | telegram.py | Easiest setup. Create bot via @BotFather. |
| Discord | built-in | Needs bot token + intents. |
| WhatsApp | whatsapp.py | Via WhatsApp Business API. |
| iMessage | bluebubbles.py | Needs BlueBubbles Server on always-on Mac. |
| Signal | signal.py | Needs signal-cli. |
| Slack | slack.py | Needs Slack app + bot token. |
| Matrix | matrix.py | Via Matrix bot. |
| WeChat | weixin.py | WeChat Official Account. |
| LINE | NOT supported | Use AstrBot instead (see Option B). |
| DingTalk | dingtalk.py | Enterprise messaging. |
| Feishu | feishu.py | Lark/Feishu bot. |
| WeCom | wecom.py | Enterprise WeChat. |
| Email | email.py | IMAP/SMTP. |
| SMS | sms.py | Via Twilio or similar. |
| API Server | api_server.py | OpenAI-compatible HTTP API. |
| Webhooks | webhook.py | Generic webhook receiver. |

### Telegram Setup (Recommended Quick Start)

1. Open Telegram, search @BotFather
2. Send /newbot, follow prompts, get token
3. `hermes gateway setup` → select Telegram → paste token
4. `hermes gateway install` → `hermes gateway start`
5. Open Telegram, find your bot, send a message

### iMessage via BlueBubbles

Requires Mac always running with Messages.app logged in + BlueBubbles Server. Not practical for most users — Mac must be on 24/7.

## Option B: AstrBot + Hermes MCP Backend

AstrBot is an open-source chatbot framework with native LINE support and MCP integration. Use it as the messaging frontend with Hermes as the tool backend.

### Architecture

```
User (LINE/Telegram/Discord/...)
  ↕
AstrBot (messaging frontend)
  ↕ MCP protocol
Hermes Agent (tool backend: 236 skills, terminal, file ops, etc.)
```

### AstrBot Setup

```bash
# Install via uv (recommended)
uv tool install astrbot --python 3.12
astrbot init
astrbot run

# Or via Docker
docker run -d -p 6185:6185 -v astrbot-data:/app/data astrbotdevo/astrbot
```

### Connecting Hermes as MCP Backend

1. Start Hermes as MCP server: `hermes mcp serve`
2. In AstrBot WebUI (http://localhost:6185) → MCP settings → add Hermes endpoint
3. AstrBot now has access to Hermes tools via MCP

### AstrBot Platform Support (includes LINE)

| Platform | Status |
|----------|--------|
| LINE | Official — native adapter |
| Telegram | Official |
| Discord | Official |
| QQ | Official |
| WeChat Work | Official |
| Feishu | Official |
| DingTalk | Official |
| Slack | Official |
| WhatsApp | Coming Soon |

### AstrBot LLM Configuration

Supports same providers as Hermes: OpenAI, Anthropic, Gemini, MiMo (via OpenAI-compatible endpoint), Ollama, OpenRouter, SiliconFlow. Configure in AstrBot WebUI → Model Providers.

## Option C: Hybrid (AstrBot for LINE + Hermes Gateway for Others)

Run both simultaneously: AstrBot handles LINE, Hermes Gateway handles Telegram/Discord. Both connect to same LLM backend. Gives LINE + Telegram coverage with full Hermes tool access on Telegram.

## Server Hosting Options

Both Hermes Gateway and AstrBot need continuous runtime.

| Hosting | Cost | Notes |
|---------|------|-------|
| Local Mac | Free | Mac must stay on. Sleep kills service. |
| Oracle Cloud Free Tier | Free | ARM VM 4-core 24GB, always free, best option. |
| Railway | ~$5/mo free | Already used by user for ArtFactory. |
| serv00 | Free | FreeBSD, compatibility issues possible. |
| Docker on VPS | $5-10/mo | Most reliable. |

## Pitfalls

- **LINE has no Hermes adapter** — Do NOT try to configure LINE in Hermes gateway setup. Use AstrBot.
- **iMessage requires always-on Mac** — BlueBubbles Server must run continuously. Not practical for most users.
- **Gateway service dies on macOS sleep** — Mac sleep kills launchd service. Use `caffeinate` or wake-on-LAN.
- **AstrBot + Hermes MCP adds latency** — Each message goes through AstrBot → MCP → Hermes → LLM → back. For simple chat, direct AstrBot LLM connection is faster.
- **Token/cost dual tracking** — If using both AstrBot and Hermes, track costs separately.
- **No Telegram + LINE in one gateway** — Hermes handles Telegram, AstrBot handles LINE. Need both if you want both.
