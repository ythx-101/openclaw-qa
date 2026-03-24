#!/usr/bin/env python3
"""
记忆自动归档脚本 — 基于温度模型 + P-Tag
来源：龙虾茶馆 #32 共建

用法：
  python3 memory_archive.py [memory_dir]
  python3 memory_archive.py memory/ --dry-run  # 只预览不操作
"""

import os
import sys
import shutil
import time
import re
from pathlib import Path
from datetime import datetime, timedelta

MEMORY_DIR = Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "memory")
DRY_RUN = "--dry-run" in sys.argv
ARCHIVE_DIR = MEMORY_DIR / ".archive"

# 豁免目录 — 永不归档
EXEMPT_DIRS = {"decisions", "people", ".archive"}

# P-Tag 保留期（天）
PTAG_RETENTION = {
    "P0": float("inf"),  # 永久
    "P1": 30,
    "P2": 7,
}

# 温度权重
W_AGE = 0.4
W_REF = 0.3
W_PRI = 0.3

def get_file_age_days(path):
    mtime = os.path.getmtime(path)
    return (time.time() - mtime) / 86400

def get_ptag(path):
    """从 frontmatter 提取 P-Tag"""
    try:
        with open(path) as f:
            content = f.read(500)
        match = re.search(r'p-?tag:\s*(P\d)', content, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    except:
        pass
    return None

def calculate_temperature(path):
    """计算记忆温度"""
    age_days = get_file_age_days(path)
    
    # Age score: 越新越热
    if age_days < 3: age_score = 1.0
    elif age_days < 7: age_score = 0.8
    elif age_days < 14: age_score = 0.5
    elif age_days < 30: age_score = 0.3
    else: age_score = 0.1
    
    # Reference score: 文件大小作为参考频率的粗略估计
    size = os.path.getsize(path)
    if size > 5000: ref_score = 0.8
    elif size > 1000: ref_score = 0.5
    else: ref_score = 0.3
    
    # Priority score: P-Tag
    ptag = get_ptag(path)
    if ptag == "P0": pri_score = 1.0
    elif ptag == "P1": pri_score = 0.6
    elif ptag == "P2": pri_score = 0.3
    else: pri_score = 0.5  # 默认中等
    
    return W_AGE * age_score + W_REF * ref_score + W_PRI * pri_score

def should_archive(path):
    """判断是否需要归档"""
    # 检查豁免
    for exempt in EXEMPT_DIRS:
        if exempt in path.parts:
            return False, "exempt_dir"
    
    # P-Tag 检查
    ptag = get_ptag(path)
    if ptag:
        retention = PTAG_RETENTION.get(ptag, 30)
        age = get_file_age_days(path)
        if age > retention:
            return True, f"{ptag} expired ({age:.0f}d > {retention}d)"
        return False, f"{ptag} active"
    
    # 温度检查
    temp = calculate_temperature(path)
    if temp <= 0.3:
        return True, f"cold (T={temp:.2f})"
    return False, f"warm (T={temp:.2f})"

def archive_file(path):
    """归档文件"""
    rel = path.relative_to(MEMORY_DIR)
    dest = ARCHIVE_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if DRY_RUN:
        print(f"  [DRY RUN] 归档: {rel} → .archive/{rel}")
    else:
        shutil.move(str(path), str(dest))
        print(f"  ✅ 归档: {rel} → .archive/{rel}")

def main():
    if not MEMORY_DIR.exists():
        print(f"❌ 目录不存在: {MEMORY_DIR}")
        sys.exit(1)
    
    print(f"🧠 记忆归档{'（预览模式）' if DRY_RUN else ''}")
    print(f"   目录: {MEMORY_DIR}")
    print("━━━━━━━━━━━━━━━━━━━━")
    
    archived = 0
    kept = 0
    
    for path in sorted(MEMORY_DIR.rglob("*.md")):
        if ".archive" in path.parts:
            continue
        
        do_archive, reason = should_archive(path)
        rel = path.relative_to(MEMORY_DIR)
        
        if do_archive:
            archive_file(path)
            archived += 1
        else:
            kept += 1
    
    print(f"\n━━━━━━━━━━━━━━━━━━━━")
    print(f"📊 结果: 保留 {kept}, 归档 {archived}")
    if DRY_RUN and archived > 0:
        print(f"💡 去掉 --dry-run 执行实际归档")

if __name__ == "__main__":
    main()
