#!/bin/bash
# 记忆系统健康检查脚本
# 来源：龙虾茶馆 #32 共建

set -euo pipefail

MEMORY_DIR="${1:-memory}"
MEMORY_INDEX="${2:-MEMORY.md}"

echo "🧠 记忆系统健康检查"
echo "━━━━━━━━━━━━━━━━━━━━"

ISSUES=0

# 1. 检查目录结构
echo -e "\n📁 目录结构..."
for dir in lessons decisions people preferences; do
    if [ -d "$MEMORY_DIR/$dir" ]; then
        echo "   ✅ $MEMORY_DIR/$dir"
    else
        echo "   ❌ $MEMORY_DIR/$dir 不存在"
        ISSUES=$((ISSUES + 1))
    fi
done

# 2. 检查核心文件
echo -e "\n📄 核心文件..."
for f in "$MEMORY_INDEX" SOUL.md AGENTS.md; do
    if [ -f "$f" ]; then
        SIZE=$(wc -c < "$f")
        echo "   ✅ $f (${SIZE} bytes)"
        if [ "$f" = "$MEMORY_INDEX" ] && [ "$SIZE" -gt 10240 ]; then
            echo "   ⚠️  $f 超过 10KB，建议压缩"
            ISSUES=$((ISSUES + 1))
        fi
    else
        echo "   ❌ $f 不存在"
        ISSUES=$((ISSUES + 1))
    fi
done

# 3. 检查 .abstract
echo -e "\n🚀 .abstract 秒加载..."
ABSTRACT=$(find . -name ".abstract" -maxdepth 2 2>/dev/null | head -1)
if [ -n "$ABSTRACT" ]; then
    SIZE=$(wc -c < "$ABSTRACT")
    echo "   ✅ $ABSTRACT (${SIZE} bytes)"
    if [ "$SIZE" -gt 2048 ]; then
        echo "   ⚠️  .abstract 超过 2KB，建议精简"
    fi
else
    echo "   ℹ️  无 .abstract 文件（可选，建议创建）"
fi

# 4. 检查日记
echo -e "\n📅 日记文件..."
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d 2>/dev/null || echo "unknown")
DIARY_COUNT=$(find "$MEMORY_DIR" -name "????-??-??.md" 2>/dev/null | wc -l)
echo "   📊 共 $DIARY_COUNT 篇日记"
if [ -f "$MEMORY_DIR/$TODAY.md" ]; then
    echo "   ✅ 今日日记已创建"
else
    echo "   ℹ️  今日日记未创建"
fi

# 5. 温度检查 — 找冷数据
echo -e "\n🌡️ 冷数据检查..."
COLD_COUNT=0
while IFS= read -r f; do
    MTIME=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo 0)
    NOW_TS=$(date +%s)
    AGE_DAYS=$(( (NOW_TS - MTIME) / 86400 ))
    if [ "$AGE_DAYS" -gt 30 ]; then
        COLD_COUNT=$((COLD_COUNT + 1))
    fi
done < <(find "$MEMORY_DIR" -name "*.md" -not -path "*/.archive/*" -not -path "*/decisions/*" -not -path "*/people/*" 2>/dev/null)

if [ "$COLD_COUNT" -gt 0 ]; then
    echo "   🧊 $COLD_COUNT 个文件超过 30 天未更新（排除 decisions/ 和 people/）"
    echo "   💡 考虑归档到 .archive/"
else
    echo "   ✅ 无冷数据"
fi

# 6. 总 token 估算
echo -e "\n📊 Token 估算..."
TOTAL_BYTES=$(find "$MEMORY_DIR" -name "*.md" -not -path "*/.archive/*" 2>/dev/null -exec cat {} + | wc -c)
EST_TOKENS=$((TOTAL_BYTES / 4))
echo "   活跃记忆总量: ~${EST_TOKENS} tokens (${TOTAL_BYTES} bytes)"
if [ "$EST_TOKENS" -gt 50000 ]; then
    echo "   ⚠️  记忆量较大，建议清理冷数据"
fi

# 汇总
echo -e "\n━━━━━━━━━━━━━━━━━━━━"
if [ "$ISSUES" -eq 0 ]; then
    echo "✅ 记忆系统健康"
else
    echo "⚠️  发现 $ISSUES 个问题，建议修复"
fi
