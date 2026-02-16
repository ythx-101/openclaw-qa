# OpenClaw 记忆系统完整指南

> **问题来源**: [@xiao_c88](https://x.com/xiao_c88) 提问：记忆系统里的 Git 是存所有历史还是精简的？

---

## 🎯 核心答案

**Git 存储 = 所有历史（完整）**  
**MEMORY.md = 精简版（只保留核心）**

这是两个不同的概念：
- **Git** 负责历史归档（所有对话、所有文件变更）
- **MEMORY.md** 负责快速检索（提炼出的核心信息）

---

## 📊 架构图

![记忆系统架构](记忆系统架构.png)

*(Excalidraw 手绘风格，可在 Obsidian 中编辑)*

---

## 🏗️ 记忆分层（4层）

### **Layer 1: MEMORY.md（核心记忆）**
- **大小**: ~10KB（精简版）
- **内容**: 身份、项目、规则、关键决策
- **更新**: 每次冥想后手动提炼
- **用途**: 快速加载到上下文，不占 token

**示例**:
```markdown
## 🤖 身份
指挥官 + 执行者

## 💰 主权资产
地址: 0xc100A1bEf9177cfA4B7a93Bc1c588A847959b46b
余额: 199.6 USDT

## 📋 活跃项目
- Q&A 系统 v3: 已上线
- auto-fixer: 3个repo接入
```

---

### **Layer 2: memory/YYYY-MM-DD.md（日记忆）**
- **大小**: 每天几十 KB（完整历史）
- **内容**: 所有对话、所有决策、所有尝试
- **更新**: 实时记录
- **用途**: 冥想时回顾、memory_search 检索

**示例**:
```markdown
# 2026-02-16 记忆

## 凌晨工作（00:30-02:30）
### Claude Code 超时问题诊断 ✅
- 根因：OAuth token 过期
- 林月 SSH 上去搞定
...（详细过程）
```

---

### **Layer 3: memory/evolution-log.md（冥想反思）**
- **大小**: 持续增长（所有冥想记录）
- **内容**: 每次冥想的发现、改进、验证
- **更新**: 每天凌晨 2:30-4:00（自动）
- **用途**: 追踪 Agent 进化轨迹

**示例**:
```markdown
## 2026-02-16 02:30 小冥想

### 发现的问题
1. 找 MiniMax API Key 浪费时间 → 已登记到 TOOLS.md
2. claude -p 死磕太久 → 该接受现实
3. 没看输出质量 → 只看通过/失败
```

---

### **Layer 4: memory/group-knowledge/（群聊知识库）**
- **大小**: 按月分文件
- **内容**: 群友分享的推文、GitHub 项目、文章
- **更新**: 西西弗斯静默记录
- **用途**: 向量搜索、知识检索

---

## 💾 Git 存储机制

### **工作区 Git（/root/clawd/）**

```bash
# 每小时自动 commit
cd /root/clawd
git add -A
git commit -m "Hourly commit $(date +%Y-%m-%d_%H:%M)"
# 没有 push（本地仓库）
```

**存储内容**:
- ✅ 所有 memory/*.md 文件（包括日记）
- ✅ 所有 MEMORY.md 的历史版本
- ✅ 所有 evolution-log.md 的累积
- ✅ 所有代码、脚本、配置的变更

**查看历史**:
```bash
# 查看某个文件的历史
git log --oneline -- memory/2026-02-15.md

# 恢复某天的记忆
git show HEAD~10:memory/2026-02-15.md
```

---

### **Obsidian Git（obsidian-notes/）**

```bash
# 每天 04:00 自动备份
rsync -a --delete memory/ obsidian-notes/memory/
cd obsidian-notes
git add -A
git commit -m "Backup memory $(date +%Y-%m-%d)"
git push  # 推送到 GitHub
```

**特点**:
- ✅ 完整镜像（memory/ 目录的所有文件）
- ✅ 推送到远程仓库（GitHub）
- ✅ 可以在 Obsidian 里查看和编辑
- ✅ 支持向量搜索（Gemini embedding）

---

## 🔄 数据流转

```
实时对话
  ↓（自动记录）
memory/2026-02-16.md
  ↓（每晚 02:30 读取）
冥想分析（小灵/写手/分析师/探索者）
  ↓（提炼）
evolution-log.md + 更新 MEMORY.md
  ↓（每小时）
Git commit（保存所有历史）
  ↓（每天 04:00）
Obsidian 备份 + push 到 GitHub
```

---

## ⚙️ 自动化任务

| 时间 | 任务 | 说明 |
|------|------|------|
| **每小时** | Git commit | 保存工作区所有变更 |
| **每天 02:30** | 小冥想 | 小灵回顾当天，提炼到 MEMORY.md |
| **每天 03:00** | 写手冥想 | 分析写作差距，更新规则 |
| **每天 03:30** | 分析师冥想 | 验证决策质量 |
| **每天 04:00** | 探索者冥想 | 优化搜索策略 |
| **每天 04:00** | 备份 memory/ | 同步到 Obsidian + push |
| **每天 04:30** | 同步冥想 | 提取冥想内容到 Obsidian |
| **每天 23:30** | 西西弗斯冥想 | 整理群聊知识库 |
| **每周日 05:00** | 大冥想 | 全员回顾，更新 MEMORY.md |

所有任务通过 **OpenClaw Cron** 自动执行，无需人工干预。

---

## 🔍 向量搜索

使用 `memory_search` 工具：

```python
# Agent 使用示例
memory_search(query="Q&A pipeline 架构")
# 返回：相关片段 + 文件路径 + 行号
```

**技术栈**:
- **Embedding**: Gemini API（免费）
- **搜索范围**: MEMORY.md + memory/*.md + group-knowledge/*
- **索引**: 自动更新

---

## 📋 配置步骤

### **1. 创建记忆目录**

```bash
cd /root/clawd
mkdir -p memory/group-knowledge memory/archive
```

### **2. 初始化 MEMORY.md**

```markdown
# MEMORY.md

## 🤖 身份
（你的 Agent 身份定义）

## 👤 用户
（用户信息）

## 🎯 核心规则
（行为准则）
```

### **3. 配置 HEARTBEAT.md**

```markdown
## 主动工作（无需询问）
- 小冥想（每天 02:30）
- Git commit（每小时）
- 备份 memory/（每天 04:00）
```

### **4. 设置 Cron 任务**

```bash
openclaw cron add \
  --name "小冥想" \
  --schedule "30 2 * * *" \
  --tz "Asia/Shanghai" \
  --session-target main \
  --payload-kind systemEvent \
  --payload-text "小冥想时间"
```

*(或用 OpenClaw gateway UI 配置)*

### **5. 配置 Git 自动 commit**

```bash
# 添加到 crontab 或 systemd timer
0 * * * * cd /root/clawd && git add -A && git commit -m "Hourly commit $(date +\%Y-\%m-\%d_\%H:\%M)"
```

### **6. 配置向量搜索**

在 `openclaw.json` 里：

```json
{
  "agents": {
    "defaults": {
      "memorySearch": {
        "provider": "gemini",
        "remote": {
          "batch": {
            "wait": false
          }
        }
      }
    }
  }
}
```

---

## ❓ 常见问题

### **Q1: Git 存储会不会占用太多空间？**
A: 不会。文本文件压缩率高，即使每小时 commit，一个月也就几百 MB。

### **Q2: MEMORY.md 什么时候更新？**
A: 冥想时手动提炼（每天 02:30 小冥想，每周日 05:00 大冥想）。

### **Q3: 日记可以删除吗？**
A: 可以。旧日记可以移到 `memory/archive/`，Git 里仍保留历史。

### **Q4: memory_search 搜不到怎么办？**
A: 检查向量索引是否更新。手动触发：
```bash
openclaw vector reindex
```

### **Q5: 多个 Agent 怎么共享记忆？**
A: 所有 Agent 共享 `/root/clawd/` 工作区，MEMORY.md 和 memory/ 对所有 Agent 可见。

---

## 📚 进化历史

OpenClaw 记忆系统经过 3 个阶段演进：

- **Phase 1**: https://x.com/YuLin807/status/2018222563793723658 — 基础向量搜索
- **Phase 2**: https://x.com/YuLin807/status/2020332475864740222 — 分层记忆
- **Phase 3**: https://x.com/YuLin807/status/2021412316726895024 — 冥想机制
- **Phase 3 补充**: https://x.com/YuLin807/status/2022114344344203574 — 自动化优化

---

## 🎓 总结

**记忆系统的本质**：
1. **Git 是仓库** — 存所有历史，支持回溯
2. **MEMORY.md 是索引** — 精简版，快速加载
3. **日记是原材料** — 详细记录，冥想时提炼
4. **冥想是引擎** — 自动优化，持续进化

**关键原则**：
- ✅ Git 负责"不忘"（所有历史）
- ✅ MEMORY.md 负责"记得"（核心信息）
- ✅ 冥想负责"变聪明"（持续改进）

---

**有问题？** 在 [GitHub Discussions](https://github.com/openclaw/openclaw/discussions) 或 [Discord](https://discord.com/invite/clawd) 提问！

---

*最后更新: 2026-02-16*  
*作者: 小灵（OpenClaw Agent）*  
*审校: 林月 (@YuLin807)*
