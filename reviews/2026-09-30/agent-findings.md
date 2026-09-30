# Sub agent 分派与核验记录

[返回 index](index.md) · [修复 checklist](fix-checklist.md)

本次审查为 `systemic` 深度，按 skill 要求启用并行探查。共分派 **4 个 sub agent**，
按职责切片、互不重叠；主 agent 负责范围、证据核验、去重、定级与最终结论。

| # | 切片 | 覆盖 | 结果 |
| --- | --- | --- | --- |
| A | 传输与基础设施层 | `http_client` `browser` `auth` `archive` `transport` `config` `util`（并追 `cli`/`resolver`/`discover`/`media`/`progress` 调用链） | 已返回 |
| B | 编排、枚举与状态机 | `cli` `discover` `resolver` `progress` | 已返回 |
| C | 解析与转换层 | `parsers` `html2md` `media` `models` `index_map` | 已返回 |
| D | 产物生成、校验与测试 | `emit` `verify` `tests/` `config.mts` | 已返回 |

主 agent 在 sub agent 运行期间并行完成：仓库 baseline、历史 `REVIEW-FINDINGS.md`
（已被删除，从 git 取回）逐条对照、`http_client`/`resolver`/`progress`/`cli` 同步链复读、
`media`/`emit`/`html2md` 渲染链复读、以及**独立的端到端复现**（见下）。

**分派原则的执行说明**：未向任何 sub agent 透露主 agent 已形成的怀疑结论；
A/C/D 各自独立命中了同一批问题（尤其是 XSS 一条被 C 与 D 独立发现），
构成了天然交叉验证。

---

## 主 agent 的独立复现（不依赖 sub agent 结论）

| 复现 | 手段 | 结论 |
| --- | --- | --- |
| 存储型 XSS（正文） | `html_to_markdown` 单测 + 仓库内最小 VitePress 站点构建 + 读产物 HTML | 命中，P0 |
| 存储型 XSS（链接目标） | 同上 | 命中，P0 |
| `StageRunner` 改写 `FAILED` | 直接驱动 `StageRunner` + `record_source_failure` | 命中，P0 |
| 渲染阶段数据丢失窗口 | 构造 `SyncContext` + 第 2 篇 `emit_note` 抛错 | 命中，P0 |
| `sync --offline` 不可用 | 造缓存 + `revalidate` 语义复现 | 命中，P1 |
| 熔断被吞 | 注入"每次取图都抛 CB"的假传输层 | 命中，P1 |
| `verify` 恒失败 | 真实仓库实跑 `Verifier` 各检查 | 命中，P1 |
| 无缓存时抽查"通过" | 空 `cache_dir` 实跑真实 manifest | 命中，P1 |
| 异常层次与状态码缺口 | `issubclass` / 集合比对 | 命中，P2 |
| `slug_anchor` vs VitePress | 独立最小站点构建 + 读 `<h2 id>` | 命中，P2 |
| `parse_bulletin` 错兜底 | 构造同页两条公告 | 命中，P1 |
| `parse_total_pages` / `<a><img>` / `SourceStatus(str)` | 直接调用解析器 | 命中，P2 |

---

## 候选发现的采纳 / 调整 / 驳回

### 采纳（证据由主 agent 复核）

- A 的 P1「`sync --offline` 不可用」、P1「`fetch()` 泄漏非 FetchError」、
  P1「熔断被 media/archive 吞掉」→ 分别落为 P2-P1-1、P1-P1-2、P1-P1-1。
- A 的 P2 六条（浏览器重试集合含基类、`finalize()` 非幂等、`NO_CACHE_STATUS` 缺口、
  `DNSError` 被重试、缓存口径不一致、迁移孤儿）→ 全部落为 P1-P2-*。
- B 的 P0「`StageRunner` 把 `FAILED` 改写成 `done`」→ **主 agent 独立复现后采纳**，
  落为 P2-P0-1（本次最严重的编排缺陷）。
- B 的 P1 三条（占位覆盖、`stage_albums` 空相册 `mark_done`、离线不可用）→ 落为
  P2-P0-2、P2-P1-2，离线一条与 A 合并。
- B 的 P1「progress 先落盘 / data 最后写」→ 与主 agent 独立发现的"渲染阶段异常
  丢数据"**同根因合并**为 P2-P0-3，并把 SIGTERM 触发链与异常触发链都写进同一条。
- B 的 P2 九条 → 落为 P2-P2-1 ~ P2-P2-9。
- C 的 P1「`parse_bulletin` 容器缺失时冒充其它公告」→ **主 agent 复现后采纳**，
  落为 P3-P1-1。C 的 P2 八条 → 落为 P3-P2-*。
- D 的 P0「链接目标 `>` 逃逸」→ **主 agent 端到端复现后采纳**，落为 P3-P0-2。
- D 的 P1 两条（`_meta` 对账恒失败、无缓存时抽查静默通过）→ **主 agent 在真实
  仓库与空缓存两种条件下实跑复核后采纳**，落为 P4-P1-1、P4-P1-2。
- D 的 P2 十条 → 落为 P4-P2-*。

### 调整（主 agent 下调或收窄了 sub agent 的表述）

| 原表述 | 调整 | 理由 |
| --- | --- | --- |
| A：「`InvalidURL` … **打断整轮多小时 sync**」 | 收窄为 P1-P1-2：在 stage 内被 `StageRunner` 的宽 `except Exception` 兜住、只标记失败并继续；**只有 emit 阶段无人兜底** | 主 agent 核了 `progress.py:511-518`，阶段内不会中断整轮；放大效应落在 P2-P0-3 |
| B：「熔断在图片路径被吞掉」（定级 P2） | 升级为 P1-P1-1 | 影响的是项目明确承诺的合规措施（熔断即停），失败后仍持续请求源站 |
| D：「文件名由外部 ID 拼接 → **可写出 `docs/` 之外**」（定级 P2） | 降级为**残留疑点**（不计入缺陷） | 主 agent 逐个核对 `NOTE_PATH_RE`/`PHOTO_PATH_RE`/`VIDEO_PATH_RE`/`DISCUSSION_PATH_RE` 均为 `(\d+)`，`_external_page_id` 只取路径前两段并以 `-` 连接，**当前无任何外部输入能构造出 `/`**；D 自己也标注可达性为"低" |
| D：「`emit.py` 裸 HTML 属性未转义」（可利用性中） | 保留 P4-P2-1，明确标注"函数级确定、端到端低概率" | 需要源 HTML 出现"未加引号的 `src` 且值里带 `"`"这类畸形输入 |

### 驳回 / 未采纳为缺陷的观察

- D 提到的 `emit_albums_index`/`emit_about`/`emit_board`/`emit_broadcast` 等
  「零测试引用」：其中 `emit_board` 的结构问题单独立为 P4-P2-4；
  其余"零引用"本身归入 P4-P2-12 的覆盖缺口，不重复列条目。
- B 的「`--force` 只映射 `recheck_done`，help 写'忽略进度'略有出入」：
  判为**语义不清而非缺陷**（README 另有 `--recheck-unavailable`），只记入 phase 2 观察项。
- C 的「`unquote` 幂等断言错误」中关于"不可逆改写导致数据损坏"的部分：
  真实 URL 形态未能在缓存页上验证，收窄为 P3-P2-6 的一部分并标注置信度中高。
- C/D 的多条"当前未触发"的 P2 一律**保留为缺陷但标注触发条件未满足**
  （因为本项目是增量同步的，源站改版/新增内容即可触发）。

---

## 结论一致性与口径

- phase 报告数：5（phase-0 baseline、phase-1~4 分层、phase-5 交叉反证）。
- 已确认 finding：**P0 × 5、P1 × 8、P2 × 25、INFO × 若干**（精确计数见
  [summary.md](summary.md)；`index.md` 与 `summary.md` 的统计口径一致）。
- `fix-checklist.md` 覆盖全部 P0/P1/P2；INFO 与残留疑点不建 checklist 条目。
