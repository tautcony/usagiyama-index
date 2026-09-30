# Phase 2 · 编排、枚举与进度状态机

[返回 index](../index.md) · [修复 checklist](../fix-checklist.md)

覆盖：`cli.py`（子命令、9 个 stage、`SyncContext`、断点续跑、熔断/中断保存）、
`discover.py`、`resolver.py`、`progress.py`。

分派：1 个 sub agent 独立探查本层；主 agent 亲自复跑其 P0 与全部 P1 候选。

---

## Findings

### [P2-P0-1] `StageRunner` 兜底把 handler 明确标记的 `FAILED` 改写成 `done`，「不可信 404 → 下次重试」机制整体失效

- **位置**：`scraper/progress.py:508-509`（兜底 `if not self.store.is_terminal(key): mark_done`）、
  `progress.py:73-76`（`terminal` 只含 `done`/`unavailable`/`skipped`）、
  `cli.py:814-837`（`record_source_failure` 对 `retryable=True` 记 `FAILED`）。
- **触发条件**：任意 handler 调 `record_source_failure(..., retryable=True)`。
  这是小站 widget 间歇性 404 的**唯一**处理路径（`resolver.is_untrusted_missing`
  → `SourceStatus.retryable=True`），每个 stage 都会走到。
- **影响**：`FAILED` 不是终态 → handler 返回后兜底立即改写为 `done`。
  实测：标 `FAILED` 后经 `StageRunner` 落盘状态为 `done`、`attempts=2`、
  `pending()==[]`、`unavailable()` 为空、`result.failed=0`。
  后果：
  1. 抖动页面被永久当成已归档，**不再重试**；
  2. 不进 `data/unavailable.md`；
  3. `--recheck-unavailable` 筛不出来（它是 `done`，只有 `--force` 能救）；
  4. `RETRYABLE_MAX_ATTEMPTS=3` 的降级逻辑**永远不可达**（`cli.py:834`）。
  历史 CRIT 修的是 `is_done` 覆盖 `unavailable` 的问题，这次漏掉了
  「非终态但已被 handler 判定过」的 `FAILED`。
- **修复方向**：兜底判据改为"handler 是否处理过这个 key"（例如记录进入 handler 前的
  `updated_at`/`attempts`，未变化才补 `mark_done`），或最直接地把 `FAILED`
  也纳入"已判定"。
- **置信度**：高 · **证据类型**：测试复现。
- **核验说明**：主 agent 独立复现：

```text
handler 内部标记后： failed
StageRunner 结束后： done | attempts = 2
result.failed = 0 | result.processed = 1
pending(recheck_failed=True) = []
unavailable() = []
ItemStatus.FAILED.terminal = False
```

---

### [P2-P0-2] 抓取失败时用空占位对象覆盖已归档内容（notes / albums / external / videos）

- **位置**：`cli.py:1166-1179`（notes：`not page.has_content` 时无条件
  `ctx.notes[id] = Note(content_html="", comments=[])`）、`cli.py:1367-1394`（albums）、
  `cli.py:1587-1595`（main/external）、`cli.py:1422-1429`（videos 的 `merge_by`
  用新对象覆盖旧对象，`local_thumb=""` 会顶掉已有路径）。
  对照 `cli.py:395-470`：`load_existing()` 已把上次的好数据装进 `ctx`。
- **触发条件**：`--force`、`PARSER_REVISION` 递增、或上次 `FAILED` 的条目，
  在下一次运行时详情页拿不到（不可信 404 / 403 / 离线未命中）。
- **影响**：handler 无条件覆盖，`save_data()` 随后把空对象写进 `data/*.json`，
  `generate_site` 把对应页面重渲染成 `::: danger 原站不可访问 / 正文缺失`。
  叠加 [P2-P0-1] 后该条还会被标 `done`（或标 `unavailable` 终态），不再重试、
  不进清单 → 这份归档在工具自身状态里**永久消失**，只能靠 git 历史或
  `--force` / `--recheck-unavailable` 找回。
- **修复方向**：写占位对象前先看 `ctx.notes/albums/external/videos` 里是否已有成功版本，
  有则保留旧对象、只更新 `status`；或统一改成"仅在无历史内容时才写占位"。
- **置信度**：高（赋值语句无条件，代码路径确定）· **证据类型**：静态路径
  （sub agent 另给出复现：先正常生成 `docs/notes/N1.md`，再让详情页失败一次，
  页面变为"正文缺失"、`data/notes.json` 的 `content_html` 变空串、comments 清空）。

---

### [P2-P0-3] `progress` 先落盘、`data/*.json` 最后写：渲染阶段异常与非 SIGINT 终止都会丢内容

- **位置**：`progress.py:521-524`（每个 stage 的 `finally: store.save(force=True)`；
  `mark()` 另有每 20 条自动落盘）、`cli.py:1700-1704`（`save_data()` 在整个
  `generate_site` 的最后）、`cli.py:1849-1861`（渲染阶段在崩溃兜底 `try` **之外**）、
  `cli.py:2081-2090`（只注册 SIGINT，无 SIGTERM）。
- **触发条件**（两条独立触发链，同一根因）：
  1. **渲染阶段抛异常**：`generate_site`（`cli.py:1853`）、`write_sync_report`
     （`cli.py:1854`）、`refresh_unavailable`（`cli.py:1849`）、
     `persist_products`（`cli.py:1857`）都在 `try` 之外。仓库内已确认存在真实触发源：
     `emit_note` → `html_to_markdown` 对**深度嵌套的归档 HTML** 抛 `RecursionError`；
     以及 [P1-P1-2](phase-1-transport-infra.md) 的 `InvalidURL` 经
     `cli.py:1650` 的 `archive_site_asset` 逃逸。
  2. **SIGTERM / OOM / 断电**：stage 跑完后 `progress.json` 已 `done`，而
     `data/*.json` 仍是旧快照。
- **影响**：`progress.json` 说"已完成"，`data/*.json` 却没有这批内容。下次 `sync`
  的 `load_existing()` 读回旧数据，`ProgressStore.pending` 把这些单元跳过
  → 新解析出的正文再没有机会进入"单一事实源"；`manifest.json`、sidebar、索引里
  会一直缺这些条目。**熔断 / Ctrl-C / 未预期异常三条路径都显式补了 `save_data()`**
  （`cli.py:1822/1836/1845`），唯独渲染阶段与 SIGTERM 没有。
- **修复方向**：
  1. 把渲染阶段一并纳入统一兜底（或让 `SyncContext.__exit__` 做"未落盘则保存"）；
  2. 更彻底：把落盘顺序统一成"**先 `save_data()` 再 `progress.save()`**"，
     使 `progress=done` 永远不早于 `data` 落盘；
  3. 每个 stage 结束就增量持久化该阶段的产物，把窗口从"整轮运行"压到"单个阶段"；
  4. 注册 SIGTERM handler，复用 SIGINT 的收尾。
- **置信度**：高 · **证据类型**：测试复现 + 静态路径。
- **核验说明**：主 agent 独立复现（3 篇日记标 `done`，渲染第 2 篇抛错）：

```text
generate_site 抛错： 模拟 emit 阶段异常
progress 里标记 done 的单元： ['note:111', 'note:222', 'note:333']
data/notes.json 存在： False
```

---

### [P2-P1-1] `sync --offline` 完全不可用：`revalidate=True` 让离线路径强制绕过缓存

- **位置**：`cli.py:1805-1810`（无条件 `ctx.resolver.revalidate = True` 后
  `prepare_structure`）、`resolver.py:126`（`force=(force or self.revalidate)`）、
  `http_client.py:685`（`if not force:` 才读缓存）、`http_client.py:698-699`
  （`if self.offline: raise OfflineCacheMiss`）。
- **触发条件**：`npm run sync -- --offline`（`README.md:118` 文档化的用法），
  即使缓存里**有**首页也照样触发。
- **影响**：`prepare_structure` 的第一个请求即 `OfflineCacheMiss` →
  `resolve_required` 抛 `FetchError("无法获取内容")` → 走 `cli.py:1840-1847`
  兜底 except → **退出码 1**。即离线同步一次都没成功过；
  `--offline` 的只读进度保护、resolver 的"离线未命中不记 unavailable"
  等设计在真实 CLI 路径上从未走通（只有单测直接调 resolver 覆盖过）。
  `--offline --dry-run` 反而正常（`cli.py:1788` 提前返回、未设 revalidate），
  进一步证明这是回归。
- **修复方向**：`ctx.resolver.revalidate = not cfg.offline`；或让 `fetch()`
  在 offline 下忽略 `force`、先查缓存。两者都做最稳。
- **置信度**：高 · **证据类型**：测试复现。
- **核验说明**：主 agent 独立复现（缓存已存在、`cache_has=True`）：

```text
cache_has = True
  force=False -> 命中缓存 status=200
  force=True  -> OfflineCacheMiss: 离线模式下缓存未命中
```

---

### [P2-P1-2] `stage_albums` 在相册列表页拿不到时仍 `mark_done`（0 张照片）

- **位置**：`cli.py:1350-1373` + `cli.py:1392-1394`；配套 `discover.py:281-283`
  （首页拿不到就 `return []`，且不写 `album_photos`）。
- **触发条件**：某相册列表页不可用（抖动 404 / 403 / 离线未命中）→ discovery 不填
  `album_photos[album]`，但 `photo_ids[album]=[]` 仍建键 → `stage_albums` 走 fallback
  再 resolve 一次（同一个失败）→ `photos=[]` → 造一个空 `Album` 覆盖 `ctx.albums[album]`
  → 无条件 `mark_done`。
- **影响**：这是"拿不到却宣布完成"。叠加 [P2-P0-2] 后 `data/albums.json` 里的照片
  清单被清空；`album:A1` 成为 `done` 终态，`--recheck-unavailable` 也筛不出来
  → 源站恢复后相册页永远空（`refresh_album_media` 只遍历现存 photos，救不回来）。
- **修复方向**：`page.has_content` 为假（或 `photos` 为空而 `album_status` 非 OK）时
  走 `record_source_failure`，不要 `mark_done`；已有 `ctx.albums[album]` 时保留旧清单。
- **置信度**：高 · **证据类型**：静态路径（sub agent 另给出复现：3 张照片 → 0 张，
  `album:A1=done` 且 `pending(recheck_unavailable=True)==[]`）。

---

### [P2-P2-1] `--limit` 在 photos 与 albums 之间语义不一致

- **位置**：`cli.py:1264-1268`（photos 用 `album_items[:limit]`，不看 pending，
  也不把 `limit` 交给 `StageRunner`，`cli.py:1317`）+ `cli.py:1261-1263` 的注释
  自称两者"保持对齐（SUG-23）"；对照 `cli.py:1396`（albums 由
  `progress.py:470-472` 对 **pending** 集合截断）。
- **触发条件**：断点续跑 + `--limit N`。
- **影响**：photos 永远从**前 N 个相册**取照片，若它们已完成则 `todo` 为空、
  **永远推进不到后面的相册**；而 albums 按 pending 截断会继续处理第 N+1 个相册
  → 出现"相册已 emit、其照片从未归档"的状态（与 SUG-23 想避免的情形方向相反）。
  历史 WARN-11 修的正是这个模式，photos 阶段被漏掉。
- **修复方向**：photos 也把 `limit` 交给 `StageRunner`，或两边统一用
  "前 N 个 pending 相册"的选择逻辑。
- **置信度**：高 · **证据类型**：静态路径 + sub agent 复现。

---

### [P2-P2-2] 数值/字符串参数缺校验：`--limit` 负数、`--delay` 负数、`--impersonate` 任意值

- **位置**：`cli.py:226-239`（`--delay type=float`、`--limit type=int`、`--impersonate` 无 choices）、
  消费点 `progress.py:471-472`（`todo[:limit]`）、`http_client.py:411-418`。
- **触发条件与影响**：
  * `--limit -1` → `if limit:` 为真 → `todo[:-1]`，**静默丢掉最后一个待办**；
  * `--limit 0` 表示"不限量"，help 未说明；负数在 `stage_photos` 里因 `if limit > 0`
    反而完全不截断 —— 前后不一致；
  * `--delay -10` → `delay_min=-10` → `RateLimiter.wait()` 恒不睡眠，
    等于**关闭限速**，只有一行"快于 Crawl-delay"的 WARNING；
  * `--impersonate bogus` 在 `Session(...)` 构造期不报错，到请求时才抛
    `ImpersonateError`；它不是 `FetchError`，会穿透 `resolver.resolve` 的
    `except` 链（浏览器模式下页面走 Chrome、图片走该 Fetcher → 每张图失败）。
- **修复方向**：argparse 层拒绝 `limit < 0`、`delay <= 0`；`--impersonate` 用
  curl_cffi 合法列表做 `choices` 或启动时校验一次；`--limit 0` 语义写进 help。
- **置信度**：高（静态路径；`--impersonate` 部分为局部复现）· **证据类型**：静态路径。

---

### [P2-P2-3] `USAGI_ARCHIVE_ENABLED` / `USAGI_BROWSER` 环境变量经 CLI 时恒被覆盖

- **位置**：`cli.py:2036-2039`（`overrides["archive_enabled"] = bool(getattr(args, "archive", False))`、
  `overrides["browser_enabled"] = bool(getattr(args, "browser", True))`）
  对照 `config.py:122-124`、`config.py:176-178` 的 `_env_bool` 默认值。
- **触发条件**：只用环境变量、不传 CLI 开关，例如
  `USAGI_BROWSER=0 uv run python -m scraper.cli sync …`。
- **影响**：未传开关时 argparse 默认值（`False`/`True`）被无条件写入覆盖，
  环境变量失效。与 `--offline`（只在 `True` 时覆盖，`cli.py:2034-2035`）写法不一致。
- **修复方向**：改成 `argparse.SUPPRESS` 的三态判定，仅在命令行显式出现时覆盖。
- **置信度**：高 · **证据类型**：静态路径。

---

### [P2-P2-4] 部分 `--stages` / `--dry-run` 用发现结果整体替换 `ctx.structure`，抹掉 `structure.json` 其它字段

- **位置**：`cli.py:1019`（`ctx.structure = discovery.structure` 无条件覆盖
  `load_existing` 恢复的结构）、`cli.py:730`（`save_data` 写回）、
  `cli.py:1922`（dry-run 直接写 `structure.to_dict()`）。
- **触发条件**：`sync --stages notes`（`discover_photos/forum/videos` 不执行）。
- **影响**：`structure.json` 的 `photoIds`/`albumTitles`/`forumTopics` 被清空；
  若本次日记列表页不可用，`noteEntries` 也会被清空。
  `_restore_structure` 的 docstring 明确警告过"漏还原哪个字段，跑一次 emit
  就会把它从磁盘上抹掉" —— 现在从另一条路发生了。站点渲染不依赖它，
  所以是**静默降级**、不报错；受影响的是依赖 `structure.json` 的
  `data/unavailable.md` 展示与人工排查。
- **修复方向**：把 discovery 结果**合并**进已恢复的 structure，而不是替换；
  dry-run 不要覆盖既有 `structure.json`。
- **置信度**：高 · **证据类型**：静态路径 + sub agent 复现。

---

### [P2-P2-5] 离线缓存未命中经"内存进度"漏进 `data/unavailable.json`

- **位置**：`cli.py:587-600`（`refresh_unavailable` 从 `progress.unavailable()`
  取内存态补条目）、`cli.py:731-738`（落盘）、`progress.py:117-123`（只读模式的设计意图）。
- **触发条件**：离线且部分缓存缺失时跑到 stage —— 今天被 [P2-P1-1] 挡住，
  修好它之后立刻成立。handler 在 `not page.has_content` 时无条件
  `record_source_failure` → `mark_unavailable`（只读库只改内存）
  → `refresh_unavailable` 把它当成"源站不可得"写盘。
- **影响**：`progress.json` 确实没写（只读生效），但 `data/unavailable.json`
  出现整条记录，detail 写着"离线模式且无缓存" —— 正是 `ProgressStore` 只读
  想避免的"一次离线运行把整站标成源站不可访问"，从进度文件漏到了归档清单。
- **修复方向**：`refresh_unavailable` 只采信本次 resolver 的明细记录 + 磁盘历史，
  离线产生的内存 `mark_*` 不参与；或给 `ItemRecord` 加 `provisional` 标记。
- **置信度**：高 · **证据类型**：静态路径 + sub agent 复现（依赖 P2-P1-1 先修）。

---

### [P2-P2-6] `report` 在 `parserRevision` 落后时输出全空报告

- **位置**：`progress.py:154-167`（revision 不符 → 内存 items 清空 + `save(force=True)`）、
  `cli.py:1940-1950`（`report` 用 `readonly=True`）。
- **触发条件**：`PARSER_REVISION` 递增后先跑 `report`（README 推荐的流程）。
- **影响**：只读库下 `totals()` 全 0、`report()` 输出"已记录单元：0"，
  磁盘进度文件仍是旧 revision，因此**报告会一直空到下一次 sync 为止**。
  用户此刻唯一想知道的"还缺哪些页面"得到的是"什么都没缺"。
  进度文件本身没被改动（只读生效，符合预期）。
- **修复方向**：`report` 对 revision 不符只告警、不清空（或按旧 revision 读
  并在报告里注明"将全部重跑"）。
- **置信度**：高 · **证据类型**：静态路径 + sub agent 复现。

---

### [P2-P2-7] 枚举重复 key：重复处理、`skipped` 统计虚高、`--limit` 配额被吃掉

- **位置**：`progress.py:460-468`（`pending_keys` 是 set，`result.skipped = len(items) - len(pending_keys)`；
  `todo` 保留重复项）、`discover.py:254-264`（`entries.extend` 不去重）、
  `discover.py:267-273`（日志自称"含重复"）。
- **触发条件**：同一篇日记被多个 notes widget 列出（作者已确认会发生）。
- **影响**：items = `["a","a","b"]` + `--limit 2` → handler 对 a 调用两次、
  `processed=2`、`skipped=1`（实际没有任何一项因进度被跳过）
  → `data/sync-report.md` 的"跳过已完成"虚高，重复项白吃 limit 配额。
- **修复方向**：`StageRunner.run` 入口按 `key_of` 去重（保留顺序）；
  或 `result.skipped` 按去重集合计算。
- **置信度**：高 · **证据类型**：静态路径 + sub agent 复现。

---

### [P2-P2-8] `attempts` 被成功记录抬高，重试预算会被历史成功吃掉

- **位置**：`cli.py:833-834`（`attempts = record.attempts; if status.retryable and attempts < RETRYABLE_MAX_ATTEMPTS`）、
  `progress.py:262`（`mark()` 对所有状态都 `attempts += 1`）。
- **触发条件**：同一 key 被成功标记 ≥3 次（两次 `--force`，或两次 parserRevision
  递增重跑），之后遇到一次 retryable 抖动。
- **影响**：3 次 `mark_done` 后 `attempts=3`，再来一次 retryable 失败会**直接**
  `unavailable`（应为 `FAILED` 待重试），重试保护被历史成功静默耗尽。
  今天因 [P2-P0-1] 把 `FAILED` 全改写成 `done` 而不可见，**修好 P2-P0-1 后立刻生效**，
  必须一起修。
- **修复方向**：把"失败次数"与"标记次数"分开（如 `failures` 字段），或只在
  `mark_failed` 时递增。
- **置信度**：高（依赖 P2-P0-1 修复后可达）· **证据类型**：静态路径 + sub agent 复现。

---

### [P2-P2-9] robots 知情门槛可绕过：`discover` 子命令无门槛，`sync --dry-run` 豁免却仍全量枚举列表页

- **位置**：`cli.py:1775`（`if not args.i_have_read_robots and not cfg.offline and not args.dry_run`）、
  `cli.py:1749-1768`（`cmd_discover` 无任何门槛）、`package.json:12`（`sync:dry`）、`README.md:52`。
- **触发条件**：`python -m scraper.cli discover`，或 `npm run sync:dry`。
- **影响**：两条路径都会真实抓取首页 + 全部列表页（默认 5~7 秒间隔，可能上百次请求），
  却不需要 `--i-have-read-robots`；README 还把 `sync:dry` 描述成"不抓取"。
  `--offline` 豁免合理（离线不联网），`--dry-run` 豁免不合理。
- **修复方向**：门槛判断提到 `main()` 或各子命令入口（`discover` 也要）；
  dry-run 至少在提示里说明"仍需联网枚举列表页"。
- **置信度**：高 · **证据类型**：静态路径。

---

### [P2-INFO-1] 文档与产物数量漂移

- `README.md:175` 写「`scraper/tests/` 369 个单元测试」，实际 `pytest --collect-only`
  为 **545 个（544 通过 / 1 取消）**；
- `README.md:11` 写「相册 6 个 / 498 张」，`manifest.json` 的 `counts.photos` 为 **523**；
- `README.md:12` 写「视频约 20 条」，manifest 为 12 条（用"约"，可接受）。

---

### [P2-INFO-2] 其他观察项

- `cli.py:1898-1912`：`count_cached` 的结果 `cached` 算完**从不打印**（dry-run 白扫缓存）。
- `cli.py:378`：`_prev_manifest` 赋值后全仓库无引用。
- `cli.py:326-331`：`--stages ""` 被接受 → 不跑任何 stage 却照常 `generate_site`；
  `--stages notes,notes` 会重复跑同一 stage 并把两条 `StageResult` 写进报告。
- `cli.py:1147/1272/1333/1408/1491/1568-1570`：无内容时提前 `return StageResult(...)`
  但**不 append 到 `ctx.results`**，`data/sync-report.md` 静默漏掉该阶段。
- `progress.py:205`：`ItemStatus(record.status)` 对未知状态串抛 `ValueError`，
  `load()` 不校验 `status`。
- `progress.py:70/295`：`ItemStatus.SKIPPED` 在生产代码里**没有任何写入点**。
- `cli.py:330`：非法 `--stages` 抛 `SystemExit(str)` → 退出码 1，而 argparse
  自身的参数错误是 2，同类输入错误退出码不一致。

---

## 残留疑点

1. **`parse_page_step` 兜底常量 + 固定页数上限的尾截断**：`discover.py:151-155/256-262`
   的循环上界固定为 `data-total-page`，起始偏移是 `index*step`。数学上要覆盖到第
   `P*C` 条需 `step ≥ 真实每页条数`；`parsers.py:255-278` 的 docstring
   「取最小间距是有意的、步长只要不超过页容量就不会漏抓」**结论是反的**
   （step 偏小时尾部 `(P-1)(C-step)` 条枚举不到）。无法确认真实站点的最小间距
   会小于页容量（现有 fixture 都相等），故列疑点。
   可确定的小问题：走兜底时**没有任何日志**（`parse_total_pages` 为 None 会 warning）。
2. **`enumerate_notes`/`enumerate_album_photos` 子页失败只 `continue`**
   （`discover.py:154/260-261`），无失败记录也无 warning（首页失败会 warning）。
3. **`--stages` 组合下 structure 被替换对 `main` 阶段的连带影响**未逐阶段验证。

---

## 漏检复盘（本层已主动排查、未发现新问题的模式）

- **终态保护**：`is_terminal` 已挡住"终态被改写成 done"的方向（但漏了 `FAILED`，
  见 P2-P0-1）；`--force`/`--recheck-unavailable` 对 9 个 stage 的 `recheck_*`
  传参**一致**（逐 stage 读过）；`attempts < 3` 的边界值与测试一致。
- **离线只读**：`progress.json` 在离线**从不**被写（含 revision 失效路径，
  `progress.py:171-174` 早退）；`report` 只读；resolver 层"离线未命中不记
  unavailable"已堵死（`resolver.py:131-140`）。漏口见 P2-P2-5。
- **分页枚举**：无 off-by-one（首页单独 absorb，`range(1,total_pages)` 覆盖 2..N，
  空/1 页不额外请求）；`data-total-page` 缺失 → warning + 单页；
  相册跨页按 `photo_id` 去重。日记跨页不去重（见 P2-P2-7）。
- **异常传播**：逐处核了 `except Exception`/`pass`；`cmd_sync` 兜底会 `raise`、
  `main` 记日志返回 1；熔断 × KeyboardInterrupt 顺序正确；
  `OfflineCacheMiss` 是 `FetchError` 子类、`_confirm_transient` 能正确兜住。
  漏点见 phase 1 与 P2-P0-3。
- **重复运行幂等**：`merge_by` 按 ID 覆盖并顺手修历史重复；图片按文件存在 +
  magic bytes 跳过；key 稳定。但"不降级"不成立（P2-P0-2）。
- **资源**：`SyncContext`/`cmd_discover`/`cmd_emit`/`check_session`/`run_login_flow`
  都在 `with`/`finally` 里释放；Chrome 懒启动；未发现泄漏。
