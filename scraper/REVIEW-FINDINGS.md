# Scraper 代码审查跟踪 (Code Review Findings)

> 审查范围：`scraper/` 全部模块（9,425 行，审查于 HEAD `7ce6305`，working tree 干净）
> 审查时间：2026-09-15
> 标记说明：`[ ]` 待处理 / `[x]` 已修复 / `[~]` 已确认忽略

---

## 🔴 Critical — 数据丢失 / 静默截断

- [x] **CRIT-1 崩溃后未 flush 导致批次数据丢失**
  `cli.py:1702-1749`
  `try` 只捕获 `CircuitBreakerOpen` 和 `KeyboardInterrupt`（两者都保存 progress+data）。其它异常（解析 bug、异常响应、缺字段）冒泡到 `main()` 返回 1，**未调用** `ctx.save_data()` / `ctx.progress.save(force=True)`。`mark()` 只每 20 条 autosave，最后一批仅在内存中的 notes/albums 丢失，但 `progress.json` 已标记 `done`；resume 时读到陈旧 `data/*.json` → 内容**永久缺失**。
  *修复：* 增加 `except Exception: ctx.save_data(); ctx.progress.save(force=True); raise`。
  *场景：* 抓到某条异常结构的 note 时，最后 19 条已解析内容消失且无法恢复。

- [x] **CRIT-2 论坛帖子正文丢失**
  `parsers.py:719`
  `parse_discussion` 用 diary 专用的 `#link-report` 查找作为正文（`content = _link_report(soup)`）。若页面无 `#link-report`，整篇讨论正文为空 → 渲染为"正文未能归档"。
  *修复：* 从 post 作用域提取（`_content_html(post)` / `post.decode_contents()`），仅作 fallback。
  *场景：* 讨论帖页面结构变化后，全部论坛帖子正文归档为空。

- [x] **CRIT-3 notes/comments 分页步长硬编码为 10**
  `discover.py:240`、`cli.py:1078`
  `discover_notes` 用 `start = index * NOTES_PER_PAGE`(10)，`_collect_note_comments` 用 `index * COMMENTS_PER_PAGE`(10)，忽略真实步长。相邻 album 代码（`discover.py:140`）正确使用 `parse_page_step(...)`。若源站分页非 10/页，note 与 comment 页**静默跳过或重叠**。
  *修复：* 两处均用 `parse_page_step(page.html, cfg, …)` 推导步长。
  *场景：* 源站改为 20/页时，半数 note 与 comment 未被抓取且无报错。

- [x] **CRIT-4 `--force` / `--recheck-unavailable` 仅作用于 9 个 stage 中的 3 个**
  `cli.py:1704-1715`
  dispatch 只对 `{notes, photos, main}` 传 `force`/`recheck_unavailable`；`bulletins, albums, videos, forum, miniblog` 用默认 runner → 跳过已完成项。`--force` 文档为"忽略进度，强制重抓"，但 bulletins/videos/forum 从不重抓；`--recheck-unavailable` 从不重试不可用的 bulletin/forum。
  *修复：* 在每个 stage func 传入 flags，或内部读 `args`。
  *场景：* 用户用 `--force` 想重抓失效的 forum 帖，结果 forum 仍被跳过。

---

## 🟠 Warning — 正确性 / 安全 / 效率

- [ ] **WARN-5 `raise_for_blocked` 对新鲜网络响应无效**
  `http_client.py:584-622`
  该 flag 仅在 cache-hit 路径（675 行）生效；`_fetch_network` 对新鲜 403/418/Challenge 始终抛 `BlockedError`。`fetch(url, raise_for_blocked=False)` 想拿到 403 body 去走 archive.org fallback，却拿到异常。
  *修复：* 将 `raise_for_blocked` 传入 `_fetch_network`，在 622 行 raise 处加 `if raise_for_blocked:` 守卫。

- [ ] **WARN-6 重试集合含基类 `CurlError` 掩盖致命配置**
  `http_client.py:78-85`
  `CurlError` 是 curl_cffi 异常基类的父类，`CURL_RETRYABLE_EXCEPTIONS` 会重试结构性致命错误（`ImpersonateError` 来自错误 `USAGI_IMPERSONATE`、错误 URL）。无效 impersonate 值使每个请求重试 `max_retries` 次后才失败，掩盖真实配置错误并放大约 6× 运行时间。
  *修复：* 去掉裸 `CurlError`，保留具体子类或排除 `ImpersonateError`。

- [ ] **WARN-7 `check_session` 仅信任 `status == 200`**
  `auth.py:187-202`
  `allow_redirects=True` 下，未登录请求 302 跳转到返回 200 的登录页会被判为"会话有效"，随后用失效 cookie 抓取。
  *修复：* 同时校验 `final_url` 非 passport/login 域名，或复查响应 cookie 中 `dbcl2`/`ck` 是否存在。

- [ ] **WARN-8 部分评论归档未告警**
  `emit.py:257`
  `missing_comments = note.comment_count if not note.comments else 0`。若归档评论数少于 `comment_count`（分页不全），无告警且 `## 评论（N）` 计数偏低，误导 `verify` 的源/快照比对。
  *修复：* 比较 `len(note.comments)` 与 `note.comment_count`，不一致时告警。

- [ ] **WARN-9 不可信 URI 未净化即写入 Markdown（XSS）**
  `html2md.py:93-118`、`emit.py:554,761,419,673,724`
  归档评论为外部不可信内容，`convert_a` 将 `href` 原样插入。评论含 `javascript:alert(1)` → 可点击 XSS 链接；含 `)` 的 URL 破坏链接语法。标题含 `[`/`]`（如 "C# [笔记]"）会提前闭合链接括号。
  *修复：* 拒绝非 `http(s)` 协议；含空格/`)` 的 URL 用 `<…>` 包裹；链接文本中转义 `[`/`]`。

- [ ] **WARN-10 `parse_total_pages` 静默返回 1**
  `parsers.py:242-244`
  `data-total-page` 缺失（畸形/被拦截页）时假定单页，无信号地截断多页列表。
  *修复：* 返回 `None`/抛 "undetermined"，让调用方重试/记录。

- [ ] **WARN-11 `--limit` 在 resume 过滤前截断 → 无法推进**
  `cli.py:1165,1267,1280,1350,1388`
  `items = entries[:limit]` 截断全量列表，再经 `StageRunner` 过滤 pending。resume 时前 `limit` 项已 `done` 被跳过，固定 `--limit N` 永远卡在前 N 项。
  *修复：* 对 pending key 集合（或 `todo`）应用 `limit`，而非全量列表。

- [ ] **WARN-12 album 列表页每次 sync 抓取两次**
  `discover.py:270` ↔ `cli.py:1298`
  `discover_photos`→`enumerate_album_photos` 已抓每 album 列表页，随后 `stage_albums` 对相同 album 再次调用（即便有磁盘缓存也冗余）。
  *修复：* 持久化/复用 discovery 的枚举结果到 `stage_albums`。

- [ ] **WARN-13 `stage_rooms`/`stage_albums`/`stage_miniblog` 忽略 resume**
  `cli.py:1005,1273,1394`
  未使用 `StageRunner`，从不查询 `progress` → 每次全量重解析（无跳过、无 `recheck`）。效率损失且无法一致地 force/limit。
  *修复：* 经 `StageRunner` 路由并带 `recheck_done`/`recheck_unavailable`。

---

## 🟡 Suggestion — 质量 / 次要

- [ ] **SUG-14** `parsers.py:813` — `unquote()` 死代码：`external or unquote(external)` 短路到 `external`，youku `%xx` 链接永不解码。改为 `unquote(external)`。
- [ ] **SUG-15** `media.py:118-133` — `read_kind`/`is_valid_image` 仅读 32 字节；带 XML prolog 的 SVG 需 ≥512 字节 → 误判"非图片"并重下载/标记无效。
- [ ] **SUG-16** `html2md.py:48-50` — `urlparse`/`parse_qs` 周围 `try/except ValueError` 永不触发，删除。
- [ ] **SUG-17** `emit.py:547-564` vs `757-773` — 重复路由解析逻辑，抽取 `_resolve_entry_route(entry)`。
- [ ] **SUG-18** `browser.py:475` — `detect_chrome_ua` 缓存 `HeadlessChrome` UA（误导）；缓存前归一化 `HeadlessChrome`→`Chrome`。
- [ ] **SUG-19** `http_client.py:721/449` — `finalize().elapsed` 未计入 image fetcher 时钟 → 运行时间低估。
- [ ] **SUG-20** `http_client.py:522-523` — `cache_has` 只查 body，`_read_cache` 需 body+meta → 半迁移 body 使 `count_cached` 高估。
- [ ] **SUG-21** `verify.py:448-518` — `check_content_sample` 仅抽样 `ok` 笔记；Wayback/ARCHIVED 笔记及全部 albums/photos/external 从不比对 → 损坏归档未捕获。
- [ ] **SUG-22** `cli.py:1014,1414` — miniblog/rooms 每轮无条件 `mark_done`（attempts/updatedAt 噪声）；参照 `StageRunner` 用 `is_terminal` 守卫。
- [ ] **SUG-23** `cli.py:1267` vs `1280` — `stage_photos` 限制*图片对*，`stage_albums` 限制*album id*；小 `--limit` 下可能处理其图片从未下载的 album。

---

## 已确认干净（无需处理）

- `transport.py`（纯 `Protocol` 定义）、`models.py`（纯 dataclass）、`config.py`（`frozen=True`，无共享可变状态）
- `http_client.py` 的 TLS/impersonate 逻辑正确；`RateLimiter` 正确串行化 browser + curl 请求（单线程设计，无竞态）

---

## 优先级建议

1. **CRIT-1**（崩溃 → 静默永久数据丢失）与 **CRIT-3**（分页步长）→ 均可能无报错丢失内容，最优先。
2. **CRIT-2**、**CRIT-4** → 强制重抓/正文正确性缺口。
3. 建议首批修复批次：`CRIT-1` + `CRIT-2` + `CRIT-3`。
