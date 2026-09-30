# scraper 代码审查 · 2026-09-30

**一句话结论**：工具链的架构与工程习惯明显高于平均水平，但**内容渲染层对
"被转义的 HTML 还原成裸标签"完全没设防、失败路径会把"拿不到"写成"已完成"并覆盖既有归档、
校验层在健康数据上恒红** —— 三者叠加，站点已带着一个可被外部输入触发的
**存储型 XSS** 发布，而 `verify` 不会报警。

| | |
| --- | --- |
| 审查对象 | `scraper/` 全部模块（约 9,000 行）+ `docs/.vitepress/` 安全相关部分 |
| 基准 commit | `94b1950`（`main`） |
| 日期 | 2026-09-30 |
| 深度 | `systemic`（4 个 sub agent 分片 + 主 agent 独立复现） |
| 基线测试 | `544 passed, 1 deselected`（离线套件） |

## 风险统计

| 级别 | 数量 |
| --- | ---: |
| **P0**（安全 / 数据丢失） | **5** |
| **P1**（静默错误 / 可靠性 / 校验失效） | **7** |
| **P2**（正确性 / 一致性 / 健壮性） | **35** |
| **合计已确认** | **47** |

## 最紧急的问题（P0）

| ID | 问题 | 状态 |
| --- | --- | --- |
| [P3-P0-1](phases/phase-3-parsing-rendering.md) | 归档正文里的转义标签被还原成裸 HTML → **存储型 XSS**（已端到端复现） | `[ ]` 未开始 |
| [P3-P0-2](phases/phase-3-parsing-rendering.md) | 链接目标里的 `>` 逃出 `<…>` 包裹 → 同类注入（已端到端复现） | `[ ]` 未开始 |
| [P2-P0-1](phases/phase-2-orchestration.md) | 失败路径把"拿不到"写成"已完成"（`FAILED` 被兜底改写为 `done`） | `[ ]` 未开始 |
| [P2-P0-2](phases/phase-2-orchestration.md) | 抓取失败时用空占位对象覆盖已归档内容 | `[ ]` 未开始 |
| [P2-P0-3](phases/phase-2-orchestration.md) | `progress` 先落盘、`data/*.json` 最后写 → 渲染异常 / SIGTERM 丢内容 | `[ ]` 未开始 |

P1 七条见 [summary.md](summary.md#p1--建议本迭代处理)；
进度跟踪在 [fix-checklist.md](fix-checklist.md)。

## 按目的阅读

- **只想知道结论 / 汇报** → 本页 + [summary.md](summary.md)
- **开始修复** → [fix-checklist.md](fix-checklist.md)（逐条勾选）+ [fixes-plan.md](fixes-plan.md)（批次与顺序）
- **追查某条结论的证据** → 从 [summary.md](summary.md) 点进对应 phase
- **核验审查过程本身** → [agent-findings.md](agent-findings.md)（分派、采纳/调整/驳回、主 agent 复现清单）

## 目录

| 文件 | 用途 |
| --- | --- |
| [summary.md](summary.md) | 全部发现聚合、统计、跨模块系统性问题、覆盖限制 |
| [fix-checklist.md](fix-checklist.md) | **修复进度唯一跟踪入口**；覆盖全部 P0/P1/P2（47 条） |
| [fixes-plan.md](fixes-plan.md) | 按批次组织的执行计划（目标 / 复杂度 / 验证信号） |
| [agent-findings.md](agent-findings.md) | sub agent 分派记录、候选发现的采纳与驳回理由 |
| [phases/phase-0-baseline.md](phases/phase-0-baseline.md) | 范围、分层、历史审查对照、语料事实 |
| [phases/phase-1-transport-infra.md](phases/phase-1-transport-infra.md) | 传输/基础设施层（8 条） |
| [phases/phase-2-orchestration.md](phases/phase-2-orchestration.md) | 编排/枚举/状态机（14 条） |
| [phases/phase-3-parsing-rendering.md](phases/phase-3-parsing-rendering.md) | 解析与内容渲染（11 条） |
| [phases/phase-4-emit-verify-tests.md](phases/phase-4-emit-verify-tests.md) | 产物生成/校验/测试（14 条） |
| [phases/phase-5-crosscutting.md](phases/phase-5-crosscutting.md) | 交叉反证审查（六类漏检模式横向复扫） |

> **口径说明**：`fix-checklist.md` 只覆盖**已确认**的 P0/P1/P2；
> 8 组 INFO 观察项与 21 条残留疑点（未确认可触发）不建条目，
> 因此 checklist 条目数 = 47 = 各 phase 合计数。

## 未覆盖区域与验证限制（醒目提示）

- **未联网、未启动真实浏览器**：所有结论来自离线静态分析 + 离线复现。
- **未在真实 `docs/` 上跑完整 `docs:build`**：两条 XSS 结论用**仓库内独立最小站点**
  构建验证（探针已删除），真实站点构建可能还有别的死链/模板问题未被本次覆盖。
- **未审计归档内容本身**：144 篇译文的准确性、图片内容正确性均不在范围内。
- **历史审查遗留项**：`scraper/REVIEW-FINDINGS.md` 已在 `54b50f6` 删除；
  本次从 git 取回并逐条复核，结论见各 phase 的「历史遗留 SUG 复核」
  （SUG-17/18/19/20/21/22/23 中，20/21/23 只被部分修复）。

## 产物位置说明

报告落在仓库根 `reviews/2026-09-30/`，而非 skill 默认的 `docs/review-YYYY-MM-DD/`：
本仓库的 `docs/` 是**已发布的 VitePress 站点根目录**，放进去会被 `docs:build`
当成站点页面构建发布（实测会让 `verify` 多报 19 条 `.md.md` 与 5 条 frontmatter 假红）。
