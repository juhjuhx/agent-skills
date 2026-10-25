# Agent 迁移故障排除指南

## 常见问题与解决方案

### 问题 1: 恢复后 Hermes 无法启动

**症状**: `hermes` 命令无响应或报错

**解决方案**:
```bash
# 1. 检查配置
cat ~/.hermes/config.yaml
cat ~/.hermes/.env

# 2. 检查依赖
which python3
python3 --version

# 3. 重新安装 Hermes
cd ~/.hermes/hermes-agent
pip install -e .  # 或 uv sync

# 4. 测试
hermes doctor
```

### 问题 2: API 金钥失效

**症状**: 模型调用失败，提示 401 或认证错误

**原因**: 出于安全考虑，API 金钥不会自动迁移

**解决方案**:
```bash
# Hermes
hermes config set models.providers.<provider>.apiKey "your-key"

# 或编辑配置文件
vim ~/.hermes/.env
vim ~/.hermes/config.yaml

# Claude Code
# 编辑 ~/.claude/settings.json，更新 ANTHROPIC_AUTH_TOKEN

# OpenCode
# 编辑 ~/.config/opencode/opencode.json，更新各 provider 的 apiKey
```

### 问题 3: Skills 没有加载

**症状**: `hermes skills list` 显示很少或空的 skills

**解决方案**:
```bash
# 检查 skills 目录
ls -la ~/.hermes/skills/
ls -la ~/.agents/skills/
ls -la ~/.config/opencode/skills/

# 重新同步 skills router
task-router sync

# 重新建立索引
task-router regenerate
```

### 问题 4: Claude Code 配置丢失

**症状**: `claude config get defaultModel` 返回空或错误

**解决方案**:
```bash
# 检查配置
cat ~/.claude/settings.json

# 重新设置
claude config set defaultModel mimo-v2.5-pro
claude config set allowedTools '["Bash", "Edit", "Glob", "Grep", "LS", "Read", "TodoWrite", "WebFetch", "WebSearch", "Write"]'

# 检查代理设置
echo $ANTHROPIC_BASE_URL
echo $ANTHROPIC_AUTH_TOKEN
```

### 问题 5: OpenCode 配置问题

**症状**: `opencode` 命令失败或模型不工作

**解决方案**:
```bash
# 检查配置
cat ~/.config/opencode/opencode.json

# 重新安装依赖
cd ~/.config/opencode
npm install

# 测试认证
opencode auth status
```

### 问题 6: Skills Router 索引损坏

**症状**: `task-router` 命令报错或索引不同步

**解决方案**:
```bash
# 检查状态
task-router health

# 重新建立索引
task-router regenerate

# 重新同步
task-router sync
```

### 问题 7: 会话历史丢失

**症状**: `hermes sessions list` 显示为空

**解决方案**:
```bash
# 检查会话目录
ls -la ~/.hermes/sessions/
ls -la ~/.claude/sessions/

# 如果没有，会话记录已排除（--no-sessions 选项）
# 可以重新启用会话记录
```

### 问题 8: Git 凭证失效

**症状**: `git push` 或 `gh auth status` 失败

**解决方案**:
```bash
# 检查 Git 配置
git config --global user.name
git config --global user.email

# 重新配置 SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"
ssh-add ~/.ssh/id_ed25519

# 或重新登录 GitHub
gh auth login
```

### 问题 9: Ollama 本地模型需要重新下载

**症状**: 本地模型调用失败

**解决方案**:
```bash
# 列出已安装的模型
ollama list

# 重新下载需要的模型
ollama pull llama3.2
ollama pull qwen2.5

# 或手动下载大型模型文件（不会被迁移）
```

### 问题 10: 大文件排除后需要手动处理

**症状**: 某些大型文件（模型、视频）缺失

**解决方案**:
```bash
# 手动重新下载模型
# HuggingFace
huggingface-cli download <model-name>

# 或从备份恢复
rsync -avz old-machine:~/path/to/model ./
```

## 迁移前检查清单

在执行迁移前，确保：

- [ ] 旧机器上的所有 Agent 都已关闭
- [ ] 备份文件 SHA256 验证通过
- [ ] 新机器已安装必要工具（Python, Node.js, uv, npm）
- [ ] 新机器已安装 Agent 运行时（Hermes, Claude Code, OpenCode）
- [ ] 网络连接正常（用于下载依赖和模型）

## 迁移后验证清单

恢复后，按顺序检查：

1. **基础检查**
   ```bash
   hermes doctor
   claude --version
   opencode --version
   task-router health
   ```

2. **配置检查**
   ```bash
   cat ~/.hermes/config.yaml | grep -E "provider|base_url"
   cat ~/.claude/settings.json
   cat ~/.config/opencode/opencode.json | grep -A2 "apiKey"
   ```

3. **Skills 检查**
   ```bash
   hermes skills list | head -20
   ls ~/.hermes/skills/ | wc -l
   ls ~/.agents/skills/ | wc -l
   ```

4. **API 测试**
   ```bash
   hermes chat -q "test" --max-turns 1
   claude -p "say hello" --max-turns 1
   ```

## 性能优化建议

迁移完成后，建议执行以下优化：

```bash
# 清理缓存
rm -rf ~/.hermes/cache/*
rm -rf ~/.claude/cache/*

# 重建索引
task-router regenerate

# 压缩记忆
hermes memory status
# 如果超过限制，手动清理旧条目
```

## 安全注意事项

1. **不要共享备份文件** — 备份包含配置但不应包含实际 API 金钥
2. **删除旧备份** — 迁移完成后，在旧机器上删除备份文件
3. **检查权限** — 确保配置文件权限正确
   ```bash
   chmod 600 ~/.hermes/.env
   chmod 600 ~/.claude/settings.json
   ```
4. **更新凭据** — 如果怀疑旧机器泄露，考虑轮换 API 金钥

## 高级场景

### 增量迁移

如果需要多次迁移（例如从 M1 到 M3），可以：
1. 先在 M1 建立备份
2. 迁移到中间机器（M2）
3. 再从 M2 建立备份迁移到 M3
4. 最后清理 M1 和 M2 上的旧备份

### 选择性迁移

只迁移特定部分：
```bash
# 手动复制特定目录
cp -R ~/.hermes/skills/ ~/Desktop/backup/
cp -R ~/.agents/skills/ ~/Desktop/backup/

# 然后使用 restore 脚本
bash agent-migrate.sh restore ~/Desktop/backup.tar.gz
```

### 跨账号迁移

如果新机器使用不同的用户名：
```bash
# 修改配置文件中的路径
sed -i '' "s|/old/username|/new/username|g" ~/.hermes/config.yaml
sed -i '' "s|/old/username|/new/username|g" ~/.claude/settings.json
```

## 相关资源

- 主迁移脚本: `~/agent-migrate.sh`
- 详细指南: `~/AGENT_MIGRATION_GUIDE.md`
- Hermes 文档: https://hermes-agent.nousresearch.com/docs/
- Claude Code 文档: https://docs.anthropic.com/en/docs/claude-code
