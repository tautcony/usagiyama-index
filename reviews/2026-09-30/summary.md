# 审查汇总

[返回 index](index.md) · [修复 checklist](fix-checklist.md) · [修复计划](fixes-plan.md)

- **审查对象**：`scraper/` 全部模块（约 9,000 行源码 + 约 6,000 行测试）
  及与产物安全相关的 `docs/.vitepress/`
- **基准**：commit `94b1950`（`main`），working tree 仅 `data/progress-report.md` 有改动
- **日期**：2026-09-30 · **深度**：`systemic`
- **方法**：4 个 sub agent 分片并行探查 + 主 agent 独立复现全部 P0/P1
  （见 [agent-findings.md](agent-findings.md)）
- **基线测试**：`.venv/bin/python -m pytest scraper/tests -q` → `544 passed, 1 deselected`

## 统计

| 级别 | 数量 | 含义 |
| --- | ---: | --- |
| **P0** | 5 | 安全漏洞（存储型 XSS）与静默数据丢失 |
| **P1** | 7 | 静默错误归档、可靠性缺陷、校验层失效 |
| **P2** | 35 | 正确性 / 一致性 / 健壮性 / 可维护性 |
| INFO | 8 组 | 观察项（含 3 组正面结论） |
| 残留疑点 | 21 | 未确认可触发，不计入缺陷 |
| **合计已确认** | **47** | |

各 phase 的 finding 数（口径一致校验）：

| phase | P0 | P1 | P2 | 小计 |
| --- | ---: | ---: | ---: | ---: |
| phase 1 传输与基础设施 | 0 | 2 | 6 | 8 |
| phase 2 编排与状态机 | 3 | 2 | 9 | 14 |
| phase 3 解析与渲染 | 2 | 1 | 8 | 11 |
| phase 4 产物、校验与测试 | 0 | 2 | 12 | 14 |
| **合计** | **5** | **7** | **35** | **47** |

phase 0 是 baseline、phase 5 是交叉反证，均不新增独立条目；
INFO（8 组）与残余疑点（21 条）不计入 47。
上表合计与 [index.md](index.md) 的统计完全一致。

## 一句话结论

工具链的**架构与工程习惯明显高于平均水平**（原子写入、断点续传、缓存隔离、
熔断与限速、离线只读、测试守卫都做得认真），但**三条防线同时失效**：
内容渲染层对"被转义的 HTML 还原成裸标签"完全没有设防（安全）；
失败路径会把"拿不到"写成"已完成"并覆盖既有归档（数据完整性）；
校验层因为在健康数据上恒红而在实践中失去信号（可观测性）。
三者叠加的后果是：**站点已经带着一个可被外部输入触发的存储型 XSS 发布，
而 `verify` 不会报警。**

---

## P0 · 必须优先处理

### 1. [P3-P0-1](phases/phase-3-parsing-rendering.md) 归档正文里的转义标签被还原成裸 HTML → 存储型 XSS
`html2md` 的 `escape_misc=False`（`html2md.py:275`）不转义 `<`/`>`，而 VitePress 的
markdown-it 以 `html: true` 运行并把结果交给 Vue 模板编译。豆瓣会把用户输入转义后
再渲染，因此"评论里写一个 `<img src=x onerror=…>`"就会在发布站点上变成可执行 HTML。
**已端到端复现**（仓库内最小 VitePress 站点构建后产物里带 `onerror`），
且真实语料已经具备该形态（`docs/notes/583976644.md:19` 的 `<小学生>`）。
CI 只做 `docs:build` 后直接发布，无净化环节。

### 2. [P3-P0-2](phases/phase-3-parsing-rendering.md) 链接目标里的 `>` 逃出 `<…>` 包裹 → 同类注入
`sanitize_markdown_url` 见空格就套 `<…>`，但目标里若有 `>` 会让 markdown-it 提前闭合，
整条链接降级为文本、末尾的标签被当 `html_inline` 输出。`unwrap_link2` 能把
`link2/?url=…` 解码成任意字符串，所以"评论者贴一个编码过的链接"即可构造。
**已端到端复现**；`emit.status_notice` 是唯一连包裹都没有的位置。

### 3. [P2-P0-1](phases/phase-2-orchestration.md) 失败路径把"拿不到"写成"已完成"
`StageRunner` 的兜底用 `is_terminal` 判断，而 `FAILED` 不是终态
（`progress.py:73-76/508-509`）→ handler 明确标记的 `FAILED` 被立刻改写成 `done`。
"小站间歇性 404 → 下次重试"这条**唯一**的容错机制因此完全失效，
`RETRYABLE_MAX_ATTEMPTS` 永远不可达，抖动页面被永久当成已归档且不进不可访问清单。
**已独立复现**。

### 4. [P2-P0-2](phases/phase-2-orchestration.md) 抓取失败时用空占位对象覆盖已归档内容
notes/albums/external/videos 四个 stage 在 `not page.has_content` 时无条件
`ctx.xxx[id] = 空对象`（`cli.py:1166-1179` 等），把 `load_existing()` 刚恢复的好数据
覆盖成空，再写进 `data/*.json`。配合上一条，这份归档在工具自身状态里永久消失。

### 5. [P2-P0-3](phases/phase-2-orchestration.md) `progress` 先落盘、`data/*.json` 最后写
渲染阶段（`generate_site`/`write_sync_report`/`refresh_unavailable`/`persist_products`）
在崩溃兜底 `try` **之外**，且只注册了 SIGINT。
渲染阶段抛异常（真实触发源：深层嵌套 HTML 让 `html_to_markdown` 抛 `RecursionError`；
或 `InvalidURL` 经 `archive_site_asset` 逃逸）或收到 SIGTERM 时，
`progress.json` 已 `done` 而 `data/*.json` 未更新 → 续跑直接跳过 → 内容永久缺失。
历史 CRIT-1 修的是同一类问题，但只覆盖了 stage 循环。**已独立复现两条触发链**。

---

## P1 · 建议本迭代处理

| ID | 摘要 |
| --- | --- |
| [P1-P1-1](phases/phase-1-transport-infra.md) | `MediaArchive.download` 吞掉 `CircuitBreakerOpen` → 熔断对全部图片请求失效，源站已在拒绝时仍持续发请求（违背 README 的合规承诺） |
| [P1-P1-2](phases/phase-1-transport-infra.md) | `fetch()` 泄漏 `InvalidURL` 等非 `FetchError` → `media.download` 的 per-candidate 容错失效，并成为 P2-P0-3 的触发源 |
| [P2-P1-1](phases/phase-2-orchestration.md) | `sync --offline` **100% 失败**（`revalidate=True` + `force` 绕过缓存读），README 文档化的离线重跑从未走通 |
| [P2-P1-2](phases/phase-2-orchestration.md) | `stage_albums` 列表页拿不到仍 `mark_done`（0 张照片），`--recheck-unavailable` 也救不回 |
| [P3-P1-1](phases/phase-3-parsing-rendering.md) | `parse_bulletin` 容器缺失时回退页面第一个 `#link-report` → **静默归档成另一条公告**且标 `ok`（同文件 docstring 明确禁止这样做） |
| [P4-P1-1](phases/phase-4-emit-verify-tests.md) | `check_counts` 与 `_meta` 口径不一致 → **健康归档 `verify` 必然 exit 1** |
| [P4-P1-2](phases/phase-4-emit-verify-tests.md) | 内容抽查在无缓存（全新 clone/CI）时**静默全部跳过并判通过**；albums/photos/external 从不比对 |

---

## 跨模块系统性问题（比单个缺陷更值得关注）

1. **"失败"没有一等公民地位。**
   `FAILED` 被兜底吞掉（P2-P0-1）、失败时覆盖好数据（P2-P0-2）、
   拿不到却宣布完成（P2-P1-2、P3-P1-1）、失败清单被离线内存态污染（P2-P2-5）——
   同一类语义漏洞出现在四个独立位置。根因是"状态/数据写入"缺少
   "只在确有内容时才推进"的统一不变量。**建议**：把"写占位/标记完成"收敛到
   一个受保护的 API，并要求"无内容时不得进入终态、不得覆盖非空历史"。

2. **渲染层的安全边界是空的，而且测试把假设当成了断言。**
   `test_html2md.py` 断言了 `<…>` 包裹"是对的"，却没有一条用例问"URL 里本来就有 `>` 会怎样"；
   544 条测试从没把"真标签"送进 `html_to_markdown`。**建议**：把
   "不可信内容 → 产物"当作一条独立管线，加入"注入语料"回归集
   （实体标签、`>` in URL、`javascript:`、花括号、方括号标题）。

3. **校验层在健康数据上恒红，于是失去了信号。**
   `_meta` 口径（P4-P1-1）与 `.DS_Store`（P4-P2-8）让 `verify` 永远失败；
   内容抽查在没有缓存的环境里是空操作（P4-P1-2）；`checked` 计数把跳过项算进去
   制造"已比对 5 篇"的错觉。**建议**：先让"健康 = 绿"成为可断言的不变量
   （补正向用例），再加 CI 门禁。

4. **两个"事实源"的口径靠人肉记忆维持。**
   `data/*.json` 的 `_meta` 包装、`manifest.json` 的 counts、`structure.json` 的字段集、
   `progress.json` 的终态集合，四者由不同模块读写，契约只写在注释里
   （`_restore_structure` 的 docstring 甚至明确警告过"漏还原哪个字段就会被抹掉"，
   结果问题从另一条路发生了 —— P2-P2-4）。
   **建议**：为这几个文件各写一个 `schema + loader` 单点，读写都经过它。

5. **同一类错误在仓库里被处理了两次、结论相反。**
   curl 侧刻意去掉裸 `CurlError`，浏览器侧却把基类 `PlaywrightError` 放进重试集合
   （P1-P2-1）；`resolver`/`progress` 刻意 re-raise `CircuitBreakerOpen`，
   `media` 却把它当普通失败吞掉（P1-P1-1）；`sanitize_markdown_url` 有协议白名单，
   `emit.py:701` 的 `href` 与 `parsers.unquote` 的结果却没有（P3-P2-6）。
   **建议**：把"该冒泡的异常""该白名单的 URL"抽成共享常量/函数，而不是各写一份。

---

## 覆盖范围与限制

**已覆盖**：`scraper/` 全部 20 个模块、`scraper/tests/` 全部 19 个测试文件、
`docs/.vitepress/config.mts` 与 `theme/lightbox.ts`、CI 工作流、`README.md` 的声明对照。

**未覆盖 / 限制**：
- 未做联网抓取、未启动真实浏览器；全部结论来自离线静态分析 + 离线复现。
- 未整体重建真实站点（`npm run docs:build` 未在 `docs/` 上跑）；两条 XSS 结论使用
  **仓库内独立最小站点**构建验证，探针已删除。
- 未审计 144 篇归档内容自身的翻译/排版准确性。
- 未对多进程并发运行做审查（工具本身不提供该模式）。
- `.venv` 之外的依赖版本差异未评估；`uv run` 在本机沙箱不可用，测试改用 `.venv/bin/python`。
