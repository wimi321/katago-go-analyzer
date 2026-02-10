#!/bin/bash
# OpenClaw 自动更新检查脚本
# 每天检查是否有新版本，如果有则自动更新

echo "🔍 检查 OpenClaw 更新..."

# 获取当前版本
CURRENT_VERSION=$(openclaw --version 2>/dev/null)
echo "当前版本: $CURRENT_VERSION"

# 检查最新版本
echo "查询最新版本..."
LATEST_VERSION=$(npm view openclaw version 2>/dev/null)

if [ -z "$LATEST_VERSION" ]; then
    echo "❌ 无法获取最新版本信息"
    exit 1
fi

echo "最新版本: $LATEST_VERSION"

# 比较版本
if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    echo "✅ 已是最新版本"
    exit 0
fi

echo "🆕 发现新版本: $CURRENT_VERSION → $LATEST_VERSION"
echo "开始更新..."

# 更新 OpenClaw
npm update -g openclaw

# 验证更新
NEW_VERSION=$(openclaw --version 2>/dev/null)

if [ "$NEW_VERSION" = "$LATEST_VERSION" ]; then
    echo "✅ 更新成功: $NEW_VERSION"
    echo "📝 记录更新日志..."
    
    # 记录到日志
    LOG_FILE="/Users/haoc/.openclaw/workspace/update-log.txt"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 更新: $CURRENT_VERSION → $NEW_VERSION" >> "$LOG_FILE"
    
    exit 0
else
    echo "❌ 更新失败"
    exit 1
fi
