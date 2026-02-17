#!/bin/bash
# OpenClaw Q&A 更新脚本
# 用于添加新的问答，自动置顶最新内容

set -e

REPO_DIR="/root/github-repos/openclaw-qa"
HTML_FILE="$REPO_DIR/index.html"

cd "$REPO_DIR"

echo "✅ OpenClaw Q&A 更新工具"
echo "━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "当前 Q&A 数量: $(grep -c 'class="qa-item"' "$HTML_FILE" || echo 0)"
echo ""
echo "提示：最新的 Q&A 会自动置顶显示"
echo "━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "使用方法："
echo "  手动编辑 index.html，在 <div class=\"qa-list\"> 下方添加新的 qa-item"
echo "  然后运行: git add -A && git commit -m '新增 Q&A' && git push"
echo ""
