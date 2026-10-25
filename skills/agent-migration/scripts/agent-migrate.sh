#!/bin/bash
# Agent 迁移脚本 - 从旧 MacBook 迁移至新 MacBook
# 用途：打包所有 AI Agent 相关配置、Skills、会话记录和工作区进度
#
# 用法：
#   bash agent-migrate.sh backup [--no-sessions]    # 建立备份
#   bash agent-migrate.sh verify [archive]          # 验证备份
#   bash agent-migrate.sh restore <archive>         # 恢复配置
#   bash agent-migrate.sh diff                      # 显示迁移目录大小
#   bash agent-migrate.sh clean                     # 清理旧备份

set -euo pipefail

# ==================== 配置 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/agent-migration-backup-$(date +%Y%m%d_%H%M%S)"
ARCHIVE_NAME="agent-migration-$(date +%Y%m%d_%H%M%S).tar.gz"
MANIFEST_FILE="${BACKUP_DIR}/manifest.txt"

# 需要迁移的目录
MIGRATE_DIRS=(
    # Hermes Agent 核心
    "~/.hermes"
    # Skills 源碼庫
    "~/.agents"
    # OpenCode 配置
    "~/.config/opencode"
    # Claude Code 配置
    "~/.claude"
    # Skills Router
    "~/.local/share/skills-router"
    "~/.local/state/skills-router"
)

# ==================== 函数 ====================
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

show_help() {
    cat << 'EOF'
Usage: ./agent-migrate.sh [command] [options]

Commands:
  backup    打包所有 Agent 配置（默认）
  verify    验证备份完整性
  restore   在新机器上恢复配置
  diff      显示将要迁移的目录和大小
  clean     清理旧的备份文件

Options:
  --no-sessions    不包含会话记录（减少文件大小）
  --help, -h       显示此帮助

Examples:
  ./agent-migrate.sh backup              # 建立备份
  ./agent-migrate.sh backup --no-sessions # 不包含会话记录
  ./agent-migrate.sh diff                # 查看预计迁移大小
  ./agent-migrate.sh verify              # 验证最新备份
  ./agent-migrate.sh restore archive.tar.gz  # 恢复备份
  ./agent-migrate.sh clean               # 清理旧备份
EOF
}

check_prerequisites() {
    log "检查必要工具..."
    command -v tar >/dev/null 2>&1 || { echo "需要 tar"; exit 1; }
    command -v sha256sum >/dev/null 2>&1 || { echo "需要 sha256sum (brew install coreutils)"; exit 1; }
    command -v du >/dev/null 2>&1 || { echo "需要 du"; exit 1; }
}

generate_manifest() {
    local dir="$1"
    log "生成目录清单..."
    
    {
        echo "# Agent Migration Manifest"
        echo "# Generated: $(date)"
        echo "# Source: $(hostname)"
        echo ""
        echo "## Directory Contents:"
        
        for pattern in "${MIGRATE_DIRS[@]}"; do
            local expanded="${pattern/#\~/$HOME}"
            if [ -d "$expanded" ]; then
                echo ""
                echo "### $pattern"
                local tmpfile
                tmpfile=$(mktemp)
                find "$expanded" -type f 2>/dev/null | sort > "$tmpfile"
                head -100 "$tmpfile"
                local count
                count=$(wc -l < "$tmpfile")
                echo "... (总计 $count 个文件)"
                rm -f "$tmpfile"
            else
                echo ""
                echo "### $pattern [不存在]"
            fi
        done
    } > "$MANIFEST_FILE"
    
    log "manifest 已储存至: $MANIFEST_FILE"
}

create_backup() {
    local no_sessions="$1"
    
    log "开始建立 Agent 迁移备份..."
    log "目标目录: $BACKUP_DIR"
    
    mkdir -p "$BACKUP_DIR"
    
    # 复制目录
    for pattern in "${MIGRATE_DIRS[@]}"; do
        local expanded="${pattern/#\~/$HOME}"
        local dest_dir="${BACKUP_DIR}/$(basename "$expanded")"
        
        if [ -d "$expanded" ]; then
            log "打包: $pattern"
            
            # 处理排除会话记录
            if [ "$no_sessions" = "true" ] && [[ "$expanded" == *"/.hermes/sessions"* ]]; then
                log "  跳过会话记录 (--no-sessions)"
                continue
            fi
            
            cp -R "$expanded" "$dest_dir" 2>/dev/null || {
                log "  警告: 复制失败 $pattern"
            }
        else
            log "  跳过不存在的目录: $pattern"
        fi
    done
    
    # 生成 manifest
    generate_manifest "$BACKUP_DIR"
    
    # 计算总大小
    local total_size
    total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
    log "备份总大小: $total_size"
    
    # 建立 tar.gz 压缩档
    log "压缩备份档（需要几分钟，请耐心等待）..."
    tar -czf "${SCRIPT_DIR}/${ARCHIVE_NAME}" -C "$BACKUP_DIR" . 2>/dev/null &
    local tar_pid=$!
    
    # 等待压缩完成
    while kill -0 $tar_pid 2>/dev/null; do
        sleep 5
        local progress
        progress=$(du -sh "${SCRIPT_DIR}/${ARCHIVE_NAME}" 2>/dev/null | cut -f1)
        log "  压缩进度: $progress"
    done
    wait $tar_pid 2>/dev/null
    
    # 生成 SHA256
    local archive_path="${SCRIPT_DIR}/${ARCHIVE_NAME}"
    sha256sum "$archive_path" > "${archive_path}.sha256"
    
    log ""
    log "备份完成!"
    log "  压缩档: $archive_path"
    log "  SHA256:  $(cat ${archive_path}.sha256)"
    log ""
    log "下一步：将以下文件复制到新机器："
    log "  1. $archive_path"
    log "  2. ${archive_path}.sha256"
}

verify_backup() {
    local archive="${1:-}"
    
    if [ -z "$archive" ]; then
        archive=$(ls -t "${SCRIPT_DIR}"/agent-migration-*.tar.gz 2>/dev/null | head -1)
    fi
    
    if [ -z "$archive" ] || [ ! -f "$archive" ]; then
        log "错误：找不到备份文件"
        exit 1
    fi
    
    log "验证备份完整性: $archive"
    
    if sha256sum -c "${archive}.sha256" 2>/dev/null; then
        log "✓ SHA256 校验通过"
    else
        log "✗ SHA256 校验失败！文件可能已损坏或被篡改"
        exit 1
    fi
    
    log "备份内容："
    tar -tzf "$archive" | head -50
    local total_files
    total_files=$(tar -tzf "$archive" | wc -l)
    log "  总计 $total_files 个文件/目录"
}

restore_backup() {
    local archive="${1:-}"
    
    if [ -z "$archive" ]; then
        log "错误：请指定备份文件路径"
        show_help
        exit 1
    fi
    
    if [ ! -f "$archive" ]; then
        log "错误：找不到备份文件 $archive"
        exit 1
    fi
    
    log "开始恢复 Agent 配置..."
    log "来源: $archive"
    
    # 验证
    if [ -f "${archive}.sha256" ]; then
        log "验证 SHA256..."
        sha256sum -c "${archive}.sha256" || {
            log "错误：SHA256 校验失败，请重新下载备份"
            exit 1
        }
    fi
    
    # 解压
    log "解压文件..."
    local temp_dir="/tmp/agent-migration-restore-$$"
    mkdir -p "$temp_dir"
    tar -xzf "$archive" -C "$temp_dir"
    
    # 恢复各目录
    local dirs=(
        "hermes:.hermes"
        "agents:.agents"
        "opencode:.config/opencode"
        "claude:.claude"
        "skills-router-share:.local/share/skills-router"
        "skills-router-state:.local/state/skills-router"
    )
    
    for entry in "${dirs[@]}"; do
        local src_dir="${entry/:/}"
        local dest_path="${entry%%:*}"
        
        if [ -d "$temp_dir/$src_dir" ]; then
            log "恢复: ~/$(basename "$dest_path")"
            local target="$HOME/${dest_path#*/}"
            mkdir -p "$(dirname "$target")"
            mv "$temp_dir/$src_dir" "$target"
        fi
    done
    
    # 清理
    rm -rf "$temp_dir"
    
    log ""
    log "✓ 恢复完成！"
    log ""
    log "请执行以下命令重新安装依赖："
    log "  cd ~/.hermes/hermes-agent && pip install -e .  # 或 uv sync"
    log "  cd ~/.config/opencode && npm install"
    log ""
    log "建议检查项目："
    log "  1. ~/.hermes/config.yaml - 确认模型提供者设定"
    log "  2. ~/.claude/settings.json - 确认 API 金钥"
    log "  3. ~/.config/opencode/opencode.json - 确认 API 金钥"
    log "  4. ~/.hermes/.env - 确认环境变量"
}

show_diff() {
    log "扫描将要迁移的目录..."
    echo ""
    
    local total=0
    for pattern in "${MIGRATE_DIRS[@]}"; do
        local expanded="${pattern/#\~/$HOME}"
        if [ -d "$expanded" ]; then
            local size
            size=$(du -sh "$expanded" 2>/dev/null | cut -f1)
            local file_count
            file_count=$(find "$expanded" -type f 2>/dev/null | wc -l)
            printf "%-40s %8s  (%s 个文件)\n" "$pattern" "$size" "$file_count"
            total=$((total + file_count))
        else
            printf "%-40s %8s  [不存在]\n" "$pattern" "-"
        fi
    done
    
    echo ""
    echo "预计总计: $total 个文件"
}

clean_old_backups() {
    log "清理旧备份（保留最近 5 个）..."
    local count
    count=$(ls -t "${SCRIPT_DIR}"/agent-migration-*.tar.gz 2>/dev/null | wc -l)
    
    if [ "$count" -gt 5 ]; then
        ls -t "${SCRIPT_DIR}"/agent-migration-*.tar.gz | tail -n +6 | xargs rm -f
        ls -t "${SCRIPT_DIR}"/agent-migration-*.tar.gz.sha256 | tail -n +6 | xargs rm -f
        log "已清理旧备份"
    else
        log "无需清理"
    fi
}

# ==================== 主程式 ====================
main() {
    local command="${1:-backup}"
    shift 2>/dev/null || true
    
    check_prerequisites
    
    case "$command" in
        backup)
            local no_sessions="false"
            while [[ "${1:-}" == --* ]]; do
                case "$1" in
                    --no-sessions) no_sessions="true" ;;
                    --help|-h) show_help; exit 0 ;;
                esac
                shift
            done
            create_backup "$no_sessions"
            ;;
        verify)
            verify_backup "$@"
            ;;
        restore)
            restore_backup "$@"
            ;;
        diff)
            show_diff
            ;;
        clean)
            clean_old_backups
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log "错误：未知指令 '$command'"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
