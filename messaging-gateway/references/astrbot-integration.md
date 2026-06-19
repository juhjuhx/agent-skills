# AstrBot + Hermes MCP Integration Notes

## AstrBot Overview

- GitHub: https://github.com/astrbotdevs/astrbot
- Version: v4.25.5 (as of 2026-06)
- License: AGPL-3.0
- Docs: https://docs.astrbot.app
- Python 3.12+ required

## Why AstrBot over Hermes Gateway

User's specific need: LINE messaging support. Hermes has no LINE adapter.
AstrBot has official LINE adapter + 1000+ plugins + WebUI management.

## Key AstrBot Commands

```bash
uv tool install astrbot --python 3.12  # Install
astrbot init                           # First-time setup
astrbot run                            # Start (foreground)
uv tool upgrade astrbot --python 3.12  # Update
```

Docker alternative:
```bash
docker run -d -p 6185:6185 -v astrbot-data:/app/data astrbotdevo/astrbot
```

## AstrBot WebUI

Default: http://localhost:6185
Features: Platform config, plugin management, knowledge base, model provider settings, MCP server config.

## Hermes MCP Server Mode

```bash
hermes mcp serve    # Start Hermes as MCP server
hermes mcp add      # Add MCP server to Hermes
hermes mcp list     # List configured MCP servers
hermes mcp test     # Test connection
```

## Integration Flow

1. Install and start AstrBot
2. Configure LINE bot in AstrBot WebUI
3. Start Hermes MCP server: `hermes mcp serve`
4. In AstrBot WebUI → MCP settings → add Hermes endpoint
5. Test: send message on LINE → AstrBot receives → routes to Hermes MCP → Hermes processes with tools → response back

## Desktop App Alternative

AstrBot also has a desktop app for local testing without Docker/CLI:
https://github.com/AstrBotDevs/AstrBot-desktop

## User's Hosting Constraint

User cannot keep Mac running 24/7. Recommended: Oracle Cloud Free Tier (ARM VM, always free) or Railway (already used for ArtFactory project).
