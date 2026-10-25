#!/bin/bash
# Agent Migration Helper Script
# 快速检查迁移状态和常见问题

set -euo pipefail

echo "=== Agent Migration Status Check ==="
echo ""

# 检查 Herme
echo "1. Hermes Agent:"
if command -v hermes &>/dev/null; then
    hermes doctor 2>&1 | head -20
else
    echo "  ✗ Hermes 未安装"
fi
echo ""

# 检查 Claude Code
echo "2. Claude Code:"
if command -v claude &>/dev/null; then
    claude --version 2>&1 || echo "  ✗ 版本检查失败"
    claude config get defaultModel 2>&1 || echo "  - defaultModel 未设置"
else
    echo "  ✗ Claude Code 未安装"
fi
echo ""

# 检查 OpenCode
echo "3. OpenCode:"
if command -v opencode &>/dev/null; then
    opencode --version 2>&1 || echo "  ✗ 版本检查失败"
else
    echo "  ✗ OpenCode 未安装"
fi
echo ""

# 检查 Skills Router
echo "4. Skills Router:"
if command -v task-router &>/dev/null; then
    task-router health 2>&1 | head -10 || echo "  ✗ 健康检查失败"
else
    echo "  ✗ Skills Router 未安装"
fi
echo ""

# 检查配置目录
echo "5. 配置目录检查:"
for dir in ~/.hermes ~/.agents ~/.config/opencode ~/.claude ~/.local/share/skills-router ~/.local/state/skills-router; do
    if [ -d "$dir" ]; then
        size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        echo "  ✓ $dir ($size)"
    else
        echo "  ✗ $dir [不存在]"
    fi
done
echo ""

# 检查 API 金钥（不显示实际值）
echo "6. API 金钥状态:"
if [ -f ~/.hermes/.env ]; then
    echo "  ✓ ~/.hermes/.env [存在]"
else
    echo "  ✗ ~/.hermes/.env [不存在]"
fi

if [ -f ~/.claude/settings.json ]; then
    if grep -q "ANTHROPIC_AUTH_TOKEN" ~/.claude/settings.json 2>/dev/null; then
        echo "  ✓ ~/.claude/settings.json [API 金钥存在]"
    else
        echo "  ⚠ ~/.claude/settings.json [API 金钥可能缺失]"
    fi
else
    echo "  ✗ ~/.claude/settings.json [不存在]"
fi

if [ -f ~/.config/opencode/opencode.json ]; then
    key_count=$(grep -c "apiKey" ~/.config/opencode/opencode.json 2>/dev/null || echo "0")
    echo "  ✓ ~/.config/opencode/opencode.json [$key_count 个 apiKey]"
else
    echo "  ✗ ~/.config/opencode/opencode.json [不存在]"
fi
echo ""

# Skills 数量
echo "7. Skills 数量:"
hermes_skills=$(ls ~/.hermes/skills/ 2>/dev/null | wc -l | tr -d ' ')
agents_skills=$(ls ~/.agents/skills/ 2>/dev/null | wc -l | tr -d ' ')
opencode_skills=$(ls ~/.config/opencode/skills/ 2>/dev/null | wc -l | tr -d ' ')
echo "  Hermes: $hermes_skills skills"
echo "  Agents: $agents_skills skills"
echo "  OpenCode: $opencode_skills skills"
echo ""

echo "=== Check Complete ==="
echo ""
echo "建议下一步："
echo "  1. 如果 API 金钥缺失，重新输入金钥"
echo "  2. 运行 'hermes doctor' 检查完整性"
echo "  3. 测试模型调用：hermes chat -q 'test'"
