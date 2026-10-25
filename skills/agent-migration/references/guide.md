# Agent 迁移使用指南

## 概述

这个指南介绍了如何使用迁移脚本将 AI Agent 配置从一台 Mac 迁移到另一台 Mac。

## 快速开始

### 1. 在旧机器上建立备份

```bash
# 查看将要迁移的目录大小
bash agent-migrate.sh diff

# 建立备份（推荐排除会话记录以减小文件大小）
bash agent-migrate.sh backup --no-sessions
```

这会产生两个文件：
- `agent-migration-YYYYMMDD_HHMMSS.tar.gz` — 压缩备份（约 1.8GB）
- `agent-migration-YYYYMMDD_HHMMSS.tar.gz.sha256` — SHA256 校验和

### 2. 传输到新机器

使用以下任一方式：
- AirDrop
- 外部硬盘
- iCloud/Dropbox
- rsync 过网络

### 3. 在新机器上恢复

```bash
# 运行恢复脚本
bash agent-migrate.sh restore /path/to/agent-migration-*.tar.gz
```

### 4. 后续设置

恢复后需要手动处理：

#### Hermes Agent
```bash
# 检查配置
cat ~/.hermes/config.yaml
cat ~/.hermes/.env  # 确认 API 金钥

# 如果需要重新安装
cd ~/.hermes/hermes-agent
pip install -e .  # 或使用 uv
```

#### Claude Code
```bash
# 检查配置
cat ~/.claude/settings.json
# 需要重新输入 API 金钥（基于安全考虑，不会迁移）
claude config set defaultModel mimo-v2.5-pro
```

#### OpenCode
```bash
# 检查配置
cat ~/.config/opencode/opencode.json
# 需要重新输入 API 金钥
cd ~/.config/opencode
npm install
```

## 包含的目录

| 目录 | 内容 |
|------|------|
| `~/.hermes/` | Hermes Agent 配置、记忆、会话、Skills |
| `~/.agents/` | Skills 源码库、AGENTS.md |
| `~/.config/opencode/` | OpenCode 配置、Plugins、Skills |
| `~/.claude/` | Claude Code 配置、会话记录 |
| `~/.local/share/skills-router/` | Skills Router 共享数据 |
| `~/.local/state/skills-router/` | Skills Router 状态数据 |

## 注意事项

### 不迁移的项目

以下项目**不会**被迁移（需要在新机器上重新设置）：
- API 金钥（基于安全考虑，建议手动输入）
- 大型模型文件（.gguf, .safetensors）
- 媒体文件（.mp4, .mov, .dmg）

### 需要手动处理的

1. **API 金钥**：
   - `~/.hermes/.env`
   - `~/.claude/settings.json` 中的 `ANTHROPIC_AUTH_TOKEN`
   - `~/.config/opencode/opencode.json` 中的各 provider apiKey

2. **模型提供者配置**：
   - 检查 `~/.hermes/config.yaml` 中的 base_url 是否对应新机器的环境

3. **Python/Node.js 依赖**：
   ```bash
   # Hermes
   brew install uv
   cd ~/.hermes/hermes-agent && uv sync
   
   # OpenCode
   cd ~/.config/opencode && npm install
   ```

4. **Git 凭证**：
   - 如果 Agent 需要访问 GitHub，需要重新配置 SSH key 或 token

## 验证迁移

恢复后，运行以下命令验证：

```bash
# Hermes
hermes doctor
hermes model

# Claude Code
claude config get defaultModel

# OpenCode
opencode --version

# Skills Router
task-router health
```

## 清理旧备份

```bash
bash agent-migrate.sh clean
```

这会保留最近 5 个备份，删除旧的。

## 故障排除

### 问题：恢复后 Hermes 无法启动
```bash
# 检查配置
cat ~/.hermes/config.yaml
# 重新安装
cd ~/.hermes/hermes-agent && pip install -e .
```

### 问题：Skills 没有加载
```bash
# 检查 skills 目录
ls ~/.hermes/skills/
ls ~/.agents/skills/
# 重新同步
bash ~/.hermes/skills/sync-skills.sh  # 如果有这个脚本
```

### 问题：API 金钥失效
```bash
# 重新输入金钥
hermes config set models.providers.<provider>.apiKey "your-key"
claude config set auth.token "your-token"
```

## 版本历史

- v1.0 (2026-08-20): 初始版本，支援基本迁移
