#!/bin/bash
#
# OpenClaw 守护进程
# 功能：检测 OpenClaw 是否存活，挂了自动用 doctor --fix 修复
#

LOG_FILE="$HOME/.openclaw/guardian.log"
MAX_RESTARTS=3
RESTART_COUNT=0

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_alive() {
    pgrep -f "openclaw-gateway" > /dev/null 2>&1
}

fix_openclaw() {
    log "⚠️ OpenClaw 挂了，执行 doctor --fix..."
    cd ~/.openclaw/workspace
    
    # 执行 doctor --fix 修复
    openclaw doctor --fix
    
    sleep 3
    
    # 尝试启动
    openclaw gateway start
    
    sleep 5
    
    if check_alive; then
        log "✅ 修复成功，OpenClaw 已恢复运行"
        RESTART_COUNT=0
        return 0
    else
        log "❌ 修复失败，请手动检查"
        RESTART_COUNT=$((RESTART_COUNT + 1))
        return 1
    fi
}

log "🛡️ OpenClaw 守护进程启动"

while true; do
    if check_alive; then
        # 每 30 秒检查一次
        sleep 30
    else
        log "❌ 检测到 OpenClaw 已停止"
        
        if [ $RESTART_COUNT -ge $MAX_RESTARTS ]; then
            log "🚫 已达到最大修复次数 ($MAX_RESTARTS)，停止自动修复"
            log "请手动执行: openclaw doctor --fix"
            exit 1
        fi
        
        fix_openclaw
    fi
done
