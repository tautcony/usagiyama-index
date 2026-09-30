# 修复计划（按批次）

[返回 index](index.md) · [修复 checklist](fix-checklist.md)

面向执行：按"风险 × 依赖 × 成本"排序。每条给出**目标、涉及位置、复杂度、验证信号**。
逐条勾选在 [fix-checklist.md](fix-checklist.md)。

---

## 批次 0 · 先止血（当天可完成，改 3 个文件）

| 顺序 | Finding | 目标 | 复杂度 | 验证信号 |
| --- | --- | --- | --- | --- |
| 1 | [P3-P0-1](phases/phase-3-parsing-rendering.md) | 堵住正文裸 HTML 注入（转换层转义 + `html: false` 兜底） | 中（要避开 `autolinks` 与既有 144 篇产物的大改版） | 新增 4 条 payload 用例；`docs:build` 通过；产物无 `onerror=` |
| 2 | [P3-P0-2](phases/phase-3-parsing-rendering.md) | 堵住链接目标 `>` 逃逸（同一批改 `sanitize_markdown_url`/`md_safe_url`） | 低 | 同上 |
| 3 | [P2-P0-1](phases/phase-2-orchestration.md) | 让 `FAILED` 活下来（`StageRunner` 兜底判据） | 低 | 经 `StageRunner` 的 retryable 用例 |
| 4 | [P2-P0-3](phases/phase-2-orchestration.md) | 渲染阶段与 SIGTERM 也要落盘（含"先 data 后 progress"顺序） | 低-中 | 渲染异常/SIGTERM 演练后 `data/*.json` 完整 |
| 5 | [P4-P1-1](phases/phase-4-emit-verify-tests.md) | 让 `verify` 在健康归档上变绿（`_meta` 口径） | 低 | `npm run verify` 返回 0 |
| 6 | [P2-P1-1](phases/phase-2-orchestration.md) | 恢复 `sync --offline` | 低 | 有缓存时 `--offline` 走通且不写进度 |

**为什么这批优先**：1–2 是安全（站点已发布到 GitHub Pages）；3–4 是数据丢失且在真实输入上可达；
5 是"校验层被噪声淹没"的根因 —— 不修它，后面所有修复都拿不到可信的验收信号。

---

## 批次 1 · 数据完整性与合规（1–2 天）

| 顺序 | Finding | 目标 | 复杂度 | 验证信号 |
| --- | --- | --- | --- | --- |
| 1 | [P2-P0-2](phases/phase-2-orchestration.md) | 失败不再覆盖已归档内容（4 个 stage） | 中 | 三种触发下 `data/*.json` 不被清空 |
| 2 | [P2-P1-2](phases/phase-2-orchestration.md) | 相册列表页失败不得 `mark_done` | 低 | `--recheck-unavailable` 能重新选中 |
| 3 | [P1-P1-1](phases/phase-1-transport-infra.md) | 熔断在所有路径都生效（media/archive 冒泡 + 可选粘滞标志） | 低 | CB 冒泡用例；候选只请求一次 |
| 4 | [P1-P1-2](phases/phase-1-transport-infra.md) | `fetch()` 只抛 `FetchError` | 低 | 三种畸形 URL 用例 |
| 5 | [P3-P1-1](phases/phase-3-parsing-rendering.md) | 公告解析不再串内容 | 低 | 新增"页面有其它公告"用例 |
| 6 | [P2-P2-8](phases/phase-2-orchestration.md) | 重试预算不被历史成功吃掉（与批次 0 的 P2-P0-1 同批） | 低 | 3 次成功后仍有完整预算 |

---

## 批次 2 · 校验层可信化（1–2 天）

| 顺序 | Finding | 目标 | 复杂度 | 验证信号 |
| --- | --- | --- | --- | --- |
| 1 | [P4-P1-2](phases/phase-4-emit-verify-tests.md) | 内容抽查不再"无缓存也通过"，并纳入 external/albums | 中 | 空缓存必须不判通过 |
| 2 | [P4-P2-8](phases/phase-4-emit-verify-tests.md) | 图片检查跳过点文件 | 低 | 健康归档 images 通过 |
| 3 | [P4-P2-7](phases/phase-4-emit-verify-tests.md) | 断链解析按所在目录 + 不重复追加后缀 | 低 | 三种链接场景用例 |
| 4 | [P4-P2-9](phases/phase-4-emit-verify-tests.md) | albums/external 纳入三方对账 | 中 | stale 页面能被发现 |
| 5 | [P4-P2-10](phases/phase-4-emit-verify-tests.md) | 抽样可复现 | 低 | 两次运行抽样一致 |
| 6 | [P4-P2-12](phases/phase-4-emit-verify-tests.md) | CI 增加 `pytest` + `verify` 门禁 | 低 | 注入回归后 CI 变红 |

---

## 批次 3 · 生成产物正确性（1–2 天）

| 顺序 | Finding | 目标 | 复杂度 | 验证信号 |
| --- | --- | --- | --- | --- |
| 1 | [P4-P2-3](phases/phase-4-emit-verify-tests.md) | `slug_anchor` 对齐 VitePress（**首页 2/6 锚点已坏**） | 中（要复刻 VitePress slugify） | 锚点集合 == 渲染 id 集合 |
| 2 | [P4-P2-1](phases/phase-4-emit-verify-tests.md) | 裸 HTML 属性统一转义 + 文件名白名单 | 低 | 含 `"` 的路径不 breakout |
| 3 | [P4-P2-4](phases/phase-4-emit-verify-tests.md) | `emit_board` 引用块覆盖整段 | 低 | 多段评论用例 |
| 4 | [P4-P2-2](phases/phase-4-emit-verify-tests.md) | 索引页链接文字转义 | 低 | 标题含 `[`/`]` 用例 |
| 5 | [P4-P2-6](phases/phase-4-emit-verify-tests.md) | `unavailable.md` 表格字段全转义 | 低 | `url`/`context` 含 `|` 用例 |
| 6 | [P4-P2-5](phases/phase-4-emit-verify-tests.md) | external 的 `archivedAt` 幂等 | 低 | 跨天 emit 不变 |

---

## 批次 4 · 传输与状态一致性（2–3 天）

| 顺序 | Finding | 目标 | 复杂度 | 验证信号 |
| --- | --- | --- | --- | --- |
| 1 | [P1-P2-3](phases/phase-1-transport-infra.md) | `>= 500` 一律不入缓存 | 低 | 501/520 用例 |
| 2 | [P1-P2-1](phases/phase-1-transport-infra.md) | 去掉 `PlaywrightError` 基类 | 低 | 致命错误不空等 |
| 3 | [P1-P2-2](phases/phase-1-transport-infra.md) | `DNSError` 不重试 | 低 | 用例 + 注释一致 |
| 4 | [P1-P2-4](phases/phase-1-transport-infra.md) | `finalize()` 幂等 | 低 | 连续两次调用 stats 不变 |
| 5 | [P1-P2-5](phases/phase-1-transport-infra.md) | 缓存存在性口径统一 + 孤儿清理 | 低 | 孤儿用例 |
| 6 | [P1-P2-6](phases/phase-1-transport-infra.md) | 迁移两阶段提交 | 低 | 中断演练 |
| 7 | [P2-P2-4](phases/phase-2-orchestration.md) | `structure` 改为合并；dry-run 不覆盖 | 中 | `--stages notes` 后字段不丢 |
| 8 | [P2-P2-7](phases/phase-2-orchestration.md) | `StageRunner` 按 key 去重 | 低 | 重复项用例 |
| 9 | [P2-P2-5](phases/phase-2-orchestration.md) | 离线不写 `unavailable.json` | 中 | 离线演练（依赖批次 0 的 P2-P1-1） |

---

## 批次 5 · 解析健壮性与参数面（2–3 天）

| 顺序 | Finding | 目标 | 复杂度 | 验证信号 |
| --- | --- | --- | --- | --- |
| 1 | [P3-P2-3](phases/phase-3-parsing-rendering.md) | `parse_total_pages` 改用 soup | 低 | 三种引号写法用例 |
| 2 | [P3-P2-1](phases/phase-3-parsing-rendering.md) | 评论取全部子节点 | 低 | 多段评论用例 |
| 3 | [P3-P2-2](phases/phase-3-parsing-rendering.md) | `<a><img></a>` 不再被打坏 | 低 | 可点击配图用例 |
| 4 | [P3-P2-4](phases/phase-3-parsing-rendering.md) | 后缀候选补 `.svg`/`.bmp` | 低 | `from_cache` 用例 |
| 5 | [P3-P2-5](phases/phase-3-parsing-rendering.md) | 嗅探前 lstrip + 短 SVG | 低 | 三种边界用例 |
| 6 | [P3-P2-6](phases/phase-3-parsing-rendering.md) | 视频缺字段不标 ok + `unquote` 收敛 | 低-中 | 771903 不再标 ok |
| 7 | [P3-P2-7](phases/phase-3-parsing-rendering.md) | 反序列化补字段 + `**payload` 收敛 | 低 | 往返用例 |
| 8 | [P3-P2-8](phases/phase-3-parsing-rendering.md) | `SourceStatus` 归一化 | 低 | 裸字符串用例 |
| 9 | [P2-P2-1](phases/phase-2-orchestration.md) | `--limit` 语义统一 | 中 | 连续 `--limit 1` 推进 |
| 10 | [P2-P2-2](phases/phase-2-orchestration.md) | 参数下界校验 | 低 | 非法输入报错 |
| 11 | [P2-P2-3](phases/phase-2-orchestration.md) | env 覆盖语义 | 低 | env 用例 |
| 12 | [P2-P2-6](phases/phase-2-orchestration.md) | `report` 不再空报告 | 低 | 旧 revision 用例 |
| 13 | [P2-P2-9](phases/phase-2-orchestration.md) | robots 门槛覆盖 `discover`/`dry-run` | 低 | 用例 |
| 14 | [P4-P2-11](phases/phase-4-emit-verify-tests.md) | 测试守卫结构性加固 | 中 | 守卫自测 |

---

## 批次 6 · 清理与文档（随做随清）

- [P2-INFO-1](phases/phase-2-orchestration.md)：README 的测试数（369→544）、照片数（498→523）。
- [P4-INFO-1](phases/phase-4-emit-verify-tests.md)：`Note.index_order` 死状态，删除或补用途。
- phase 2 的 INFO 观察项：`count_cached` 结果未使用、`_prev_manifest` 死状态、
  `--stages ""` 静默 no-op、早退路径不 append `ctx.results`、`SKIPPED` 死代码、
  非法 `--stages` 退出码不一致。
- 各 phase 的「残留疑点」：**不建 checklist 条目**，建议在批次 1/4 落地后各复核一次
  （多数依赖"源站改版"才会触发）。

---

## 不修也行的取舍建议

如果时间有限，以下 P2 可以**明确延后**，理由是触发条件依赖源站改版或仅影响调试体验：

- [P3-P2-4](phases/phase-3-parsing-rendering.md)、[P3-P2-5](phases/phase-3-parsing-rendering.md)：
  真实素材中 svg/bmp 为 0、4300+ 图片 body 全部识别正确。
- [P3-P2-1](phases/phase-3-parsing-rendering.md)、[P3-P2-2](phases/phase-3-parsing-rendering.md)：
  真实语料中多段评论与 `<a><img></a>` 均为 0 例。
- [P1-P2-6](phases/phase-1-transport-infra.md)：迁移只发生一次，且已有幂等兜底。
- phase 2 的 INFO 观察项。

**不建议延后**的是批次 0 与批次 1 的全部条目 —— 它们要么是安全，要么是数据丢失，
要么决定后续验收信号是否可信。
