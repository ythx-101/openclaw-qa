# 🧠 Memory Management — OpenClaw 记忆管理 Skill

> 来源：龙虾茶馆 #32 共建 | 主创：@adminlove520 | 贡献者：@fatfingererr @andyyuzy-76 @wangray
> 
> 集合了 54 条实战评论的精华，不是理论，全是踩过坑验证过的方案。

## 适用场景

当你的 Agent 出现以下症状时使用此 Skill：
- 重启后失忆，不记得上次聊了什么
- 记忆文件越来越大，启动变慢
- 重要决策被 compaction 吞掉
- 不知道该记什么、忘什么

## 四层记忆架构

```
Layer 0: .abstract (~1KB)     → 核心身份，秒加载
Layer 1: NOW.md / MEMORY.md   → 当前状态索引 (<10KB)
Layer 2: memory/YYYY-MM-DD.md → 每日日志，追加式
Layer 3: lessons/ decisions/  → 长期知识，结构化
```

### Layer 0 — .abstract 秒加载

把核心身份 + 关键人 + 关键偏好压缩到 ~1KB：

```markdown
# agent-main

**身份**: [一句话]
**性格**: [关键词]
**主人**: [名字 + 联系方式]
**核心规则**: [3-5 条]
```

启动时先读这个，0.5 秒内就知道自己是谁。

### Layer 1 — 状态索引

**MEMORY.md** — 核心知识索引，<10KB，主会话启动必读。

规则：
- 只存索引和摘要，不存原始数据
- 定期压缩，删除过时条目
- 是"目录"不是"仓库"

**NOW.md**（可选）— 当前活跃焦点，覆写式。
- ⚠️ 每次覆写前备份：`cp NOW.md NOW.md.bak`
- 适合需要"交接文档"的场景

### Layer 2 — 每日日志

```
memory/
├── 2026-03-24.md
├── 2026-03-23.md
└── ...
```

规则：
- **只追加，不修改** — 禁止 Edit 修改已有日记
- **YAML frontmatter** 存 L0 摘要，便于快速扫描
- 今天 + 昨天的日记补全启动上下文

### Layer 3 — 长期知识

```
memory/
├── lessons/      # 可复用经验
├── decisions/    # 战略决策（永不归档）
├── people/       # 人物画像（永不归档）
└── preferences/  # 用户偏好
```

## CRUD 验证流程

写入知识文件前必须验证：

```
新信息到来
  │
  ├─ 读取目标文件当前内容
  │
  ├─ 比较新知识与已有内容
  │    ├─ 无关 → ADD (追加)
  │    ├─ 重复 → NOOP (跳过)  
  │    ├─ 更新 → UPDATE (新版追加，旧版标记)
  │    └─ 矛盾 → CONFLICT (两版保留，待裁决)
  │
  └─ 更新 frontmatter 中的 last_verified
```

**关键：不要靠 Agent 自觉，用脚本自动跑。**

## 温度模型 — 自动遗忘

```
Temperature = w_age × age_score + w_ref × ref_score + w_pri × priority_score
```

| 温度 | 状态 | 处理 |
|------|------|------|
| 🔥 Hot (T > 0.7) | 活跃 | 保持索引 |
| 🌤 Warm (0.3 < T ≤ 0.7) | 降温 | 保留但降权 |
| 🧊 Cold (T ≤ 0.3) | 冷却 | 移至 .archive/ |

**豁免规则**：decisions/ 和 people/ 永不归档。

### P-Tag 生命周期

| 标签 | 保留期 | 示例 |
|------|--------|------|
| P0 | 永久 | 架构决策、核心身份 |
| P1 | 30 天 | 项目进度、阶段性结论 |
| P2 | 7 天 | 临时任务、调试记录 |

## Pre-compaction Flush

Context window 快满时，主动保存关键信息：

**触发条件**：
- 对话超过 50 轮
- 收到 compaction 信号
- 长任务即将结束

**动作**：
1. 提取当前上下文中的关键决策
2. 写入 memory/YYYY-MM-DD.md
3. 更新 MEMORY.md 索引

> "被动等 Agent 记得存 vs 主动在压力前 flush —— 后者可靠性高一个量级。" — @fatfingererr

## 启动加载策略

| Session 类型 | 加载内容 | Token 预算 |
|-------------|---------|-----------|
| 主会话 | .abstract → MEMORY.md → 今日日记 | ~3000 |
| 群聊/轻量 | .abstract → SOUL.md | ~500 |
| 子任务 | .abstract 只读 | ~200 |

## 三机制联动

| 机制 | 触发 | 职责 |
|------|------|------|
| Pre-compaction Flush | context 压力 | 关键信息不丢 |
| P-Tag 自动归档 | 每日 cron | 冷数据自动清理 |
| Heartbeat 巡查 | 每 2-3 天 | 兜底 + 健康检查 |

## 检索策略

1. **L0**: 扫 .abstract → 核心身份（~1KB）
2. **L1**: 读 MEMORY.md → 定位目标文件
3. **L2**: 直接读取目标文件
4. **L3**: memory_search 语义检索（兜底）

> memory_search 是向量语义检索，不是 grep。搜"怎么部署"能命中"VPS 安装步骤"。

## 快速上手

1. 创建目录结构：
```bash
mkdir -p memory/{lessons,decisions,people,preferences}
```

2. 写 .abstract（~1KB 核心身份）

3. 在 AGENTS.md 里加规则：
```markdown
## 记忆
- 启动先读 .abstract → MEMORY.md
- 写入前 CRUD 验证
- 日记只追加不修改
- decisions/ 和 people/ 永不归档
```

4. 设置 cron 自动归档冷数据

---

**龙虾茶馆 #32 共建成果** | 炼金工坊出品 🦞
