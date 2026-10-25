---
name: agent-migration
description: "迁移 AI Agent 配置与新机器。Use when: 换新 Mac、Agent 迁移、备份恢复。"
version: 1.0.0
author: Agnes
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [migration, backup, restore, agents]
    related_skills: [hermes-agent, coding-agent-delegation]
---

# Agent Migration — 多 Agent 配置迁移

将 Hermes Agent、Claude Code、OpenCode、Skills Router 等 AI Agent 相关配置完整迁移到新机器。

## 适用场景

- 换新 MacBook（同账号或不同账号）
- 重建开发环境
- 跨机器同步 Agent 配置
- 备份与恢复 Agent 工作区

## 包含的目录

| 目录 | 内容 | 大小（典型） |
|------|------|-------------|
| `~/.hermes/` | Hermes 配置、记忆、会话、Skills、cron jobs | ~3GB |
| `~/.agents/` | Skills 源碼庫、AGENTS.md、共享记忆 | ~350MB |
| `~/.config/opencode/` | OpenCode 配置、Plugins、Skills | ~160MB |
| `~/.claude/` | Claude Code 配置、会话记录 | ~1GB |
| `~/.local/share/skills-router/` | Skills Router 共享数据 | ~170KB |
| `~/.local/state/skills-router/` | Skills Router 状态数据 | ~4MB |

## 迁移步骤

### 1. 旧机器：建立备份

```bash
# 运行迁移脚本
bash ~/agent-migrate.sh backup --no-sessions
```

生成两个文件：
- `agent-migration-YYYYMMDD_HHMMSS.tar.gz` — 压缩备份（约 1.8GB）
- `agent-migration-YYYYMMDD_HHMMSS.tar.gz.sha256` — 完整性校验

### 2. 传输到新村

使用以下任一方式：
- AirDrop
- 外部硬盘
- iCloud/Dropbox/Google Drive
- rsync 过网络

### 3. 新村：恢复配置

```bash
# 运行恢复脚本
bash agent-migrate.sh restore /path/to/agent-migration-*.tar.gz
```

### 4. 后续设置（必须手动完成）

```bash
# 检查配置完整性
hermes doctor
claude config get defaultModel
opencode --version

# 重新输入 API 金钥（出于安全考虑不会迁移）
# Hermes
hermes config set models.providers.<provider>.apiKey "your-key"

# Claude Code（编辑 ~/.claude/settings.json）
# 主要设置 ANTHROPIC_AUTH_TOKEN

# OpenCode（编辑 ~/.config/opencode/opencode.json）
# 主要设置各 provider 的 apiKey
```

## 不迁移的项目

以下项目**不会**被迁移（需手动重新配置）：

1. **API 金钥** — 安全考虑，必须在新机器重新输入
2. **大型模型文件** — `.gguf`、`.safetensors` 等
3. **媒体文件** — `.mp4`、`.mov`、`.dmg`
4. **Git 凭证** — SSH key 或 token 需重新配置
5. **Ollama 本地模型** — 需重新下载

## 自定义迁移范围

编辑 `agent-migrate.sh` 中的 `MIGRATE_DIRS` 数组：

```bash
MIGRATE_DIRS=(
    "~/.hermes"
    "~/.agents"
    "~/.config/opencode"
    "~/.claude"
    # 添加你的项目工作区
    #"~/Desktop/artfactory"
    #"~/Desktop/你要去哪裡"
)
```

## 故障排除

### 恢复后 Hermes 无法启动

```bash
# 检查配置
cat ~/.hermes/config.yaml
cat ~/.hermes/.env

# 重新安装依赖
cd ~/.hermes/hermes-agent
pip install -e .  # 或 uv sync
```

### Skills 没有加载

```bash
# 检查 skills 目录
ls ~/.hermes/skills/
ls ~/.agents/skills/
ls ~/.config/opencode/skills/

# 重新同步 skills router
task-router sync
```

### API 金钥失效

```bash
# 重新输入金钥
hermes config set models.providers.<provider>.apiKey "your-key"
```

### 压缩超时（大文件）

脚本已内置进度显示，如仍超时：
```bash
# 排除会会话记录
bash agent-migrate.sh backup --no-sessions
```

## 验证清单

恢复后检查：
- [ ] `hermes doctor` 显示正常
- [ ] `claude config get defaultModel` 返回预期模型
- [ ] Skills 已加载（`hermes skills list`）
- [ ] API 金钥已重新配置
- [ ] Git 凭证可用（`gh auth status`）

## 相关脚本

- `~/agent-migrate.sh` — 主迁移脚本
- `~/AGENT_MIGRATION_GUIDE.md` — 详细使用指南

## 版本历史

- v1.0 (2026-08-20): 初始版本，支援 Hermes/Claude Code/OpenCode/Skills Router 迁移
