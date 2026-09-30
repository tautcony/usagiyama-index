# Phase 1 · 传输与基础设施层

[返回 index](../index.md) · [修复 checklist](../fix-checklist.md)

覆盖：`http_client.py`、`browser.py`、`auth.py`、`archive.py`、`media.py`、
`transport.py`、`config.py`、`util.py`。

分派：1 个 sub agent 独立探查本层；主 agent 亲自复跑其全部 P0/P1 候选
（每条 finding 末尾的「核验说明」记录主 agent 的独立动作）。

---

## Findings

### [P1-P1-1] `MediaArchive.download` 吞掉 `CircuitBreakerOpen`，熔断对全部图片请求失效

- **位置**：`scraper/media.py:474-481`；异常层次 `scraper/http_client.py:274-283`；抛出点 `http_client.py:628-634`。
- **触发条件**：图片请求期间同域名连续 3 次 403/418（或浏览器后端判定落到 `sec.douban.com`）。
- **影响**：`CircuitBreakerOpen` 是 `FetchError` 子类，被 `except (BlockedError, FetchError, OfflineCacheMiss)`
  当成"候选不可用"接住 → 继续试下一个尺寸候选 → 继续处理下一张照片。
  1. 文档承诺的「连续 3 次 403/418 立即停止并保存进度」（`scraper/README.md`）在
     `notes`/`photos`/`albums`/`videos` 等以图片为主的阶段**完全不成立**；
  2. 源站已在拒绝请求，工具仍继续发出成百上千次图片请求，有把 IP 拖进黑名单的实际风险；
  3. `cli.py:1820` 的 `except CircuitBreakerOpen` 因此永不触发，失败被降级成
     "图片归档失败"的 warning；
  4. 叠加 [P2-P0-1](phase-2-orchestration.md) 后，这些照片还会被标 `unavailable` 终态。
  另注：熔断状态本身不锁存（`http_client.py:641` 只在下一次非拦截响应时归零），
  所以被吞掉后每次新请求都会再次抛 CB、再被吞掉。
- **修复方向**：`media.py:477` 之前显式 `except CircuitBreakerOpen: raise`
  （与 `resolver.py:127/179/295`、`progress.py:514` 的既有写法一致）；
  更稳的做法是在 `fetch()` 入口加粘滞 `_circuit_open` 标志，熔断后直接拒绝所有新请求。
  `archive.py:166/223/252` 同理（危害较小，见 [P1-INFO-1]）。
- **置信度**：高 · **证据类型**：测试复现。
- **核验说明**：主 agent 独立复现 —— 注入"每次取图都抛 CB"的假传输层后，
  `download` 仍把 4 个候选全部请求完才返回失败，从未冒泡。

---

### [P1-P1-2] `fetch()` 泄漏非 `FetchError` 的传输异常，破坏 `Transport` 契约

- **位置**：`scraper/http_client.py:600-609`（只 catch `_RetryableStatus` 与
  `CURL_RETRYABLE_EXCEPTIONS`）；契约声明 `scraper/transport.py:55-66`；
  消费方 `media.py:477`。
- **触发条件**：任何"URL 结构非法"的输入触发 `curl_cffi.InvalidURL`（如相对路径
  `/view/photo/raw/public/p1.jpg`）。站点的 HTML 里确实存在相对地址
  （`/pics/blank.gif`、`/widget/miniblog/…/?start=20`、`?cid=…#add_comment`），
  这些值经 `parsers.py:165`（room href）、`parsers.py:496-501`（查看原图 href）、
  `media.py:558-566`（note img src）、`parsers.py:143-145`（头像 src → `cli.py:1650`）
  原样进入抓取入参。
- **影响**：`InvalidURL`/`MissingSchema`/`TooManyRedirects` 不是 `FetchError`
  （`RequestException` 不在重试集合里），会穿透所有 `except FetchError` 的容错：
  - 在 stage 内被 `StageRunner` 的宽 `except Exception` 兜住（标记失败、继续），
    但 `media.download` 的 per-candidate 容错形同虚设；
  - 在 `generate_site`（`cli.py:1650` 的 `archive_site_asset`）内**无人兜底**，
    直接触发 [P2-P0-3](phase-2-orchestration.md) 的数据丢失窗口。
- **修复方向**：`_fetch_network` 补 `except CurlError as exc: raise FetchError(url, …)`
  （不重试、只归一化）。
- **置信度**：高 · **证据类型**：测试复现。
- **核验说明**：主 agent 复跑，`InvalidURL` 原样逃逸；同一脚本下 `not-a-url`
  反而走 `ConnectionError` 被归一化为 `FetchError`。

---

### [P1-P2-1] 浏览器重试集合含基类 `PlaywrightError`，致命错误也退避 ≈155s/URL

- **位置**：`scraper/browser.py:88-97`（`PLAYWRIGHT_RETRYABLE_EXCEPTIONS = (PlaywrightTimeoutError, PlaywrightError)`），使用点 `browser.py:360`。
- **触发条件**：浏览器进程中途死亡 / context 被关闭（`Target closed`、`Browser has been closed`）。
- **影响**：这些是**不可恢复**的致命错误，却走 `max_retries=5` 的指数退避
  （5/10/20/40/80 秒），每个 URL 白等约 155 秒。这与 curl 侧刻意去掉裸 `CurlError`
  的设计（`http_client.py:75-88`）完全相反：同一类错误在同仓库被处理了两次、结论相反。
- **修复方向**：去掉裸 `PlaywrightError`；`TargetClosedError` 应判定为"需重建浏览器"而非重试。
- **置信度**：高（基类关系与退避参数均为静态事实）· **证据类型**：静态路径。

---

### [P1-P2-2] `DNSError` 实际会被重试，与代码注释明确相反

- **位置**：`http_client.py:75-88`（注释点名 `DNSError` 属于"不该重试的致命配置错误"）
  与 `http_client.py:82-88`（重试集合含 `ConnectionError as CurlConnectionError`）。
- **触发条件**：域名解析失败（URL 写错、DNS 故障）。
- **影响**：`DNSError` 的 MRO 为 `DNSError → ConnectionError → RequestException → CurlError`，
  **命中 `CurlConnectionError`**，因此被退避重试。实测日志
  「第 1 次重试 not-a-url（下次等待 6s）」→ 每个请求白等约 155 秒。
- **修复方向**：从重试集合中排除 `DNSError`，或修正注释结论。
- **置信度**：高 · **证据类型**：测试复现。
- **核验说明**：主 agent 复跑 `issubclass(DNSError, CURL_RETRYABLE_EXCEPTIONS) == True`。

---

### [P1-P2-3] `NO_CACHE_STATUS` 覆盖不全：501/505/507/520-527 被当成确定性结论永久固化

- **位置**：`http_client.py:68-70`（`NO_CACHE_STATUS`）、`http_client.py:647-657`、
  `http_client.py:703-716`（`_cache_is_stale` 只覆盖 403/418 与不可信 404）。
- **触发条件**：源站或中间层返回 501、505、507、520-527（Cloudflare 系列）等。
- **影响**：这些状态既不在 `RETRYABLE_STATUS`（不重试）也不在 `NO_CACHE_STATUS`
  （照常写缓存），`_cache_is_stale` 也不覆盖 → **一次抖动被固化成永久结论**：
  后续运行连请求都不发，直接重放该错误页；`--recheck-unavailable` 也会被磁盘上的
  缓存顶回去（与历史修 403 重放问题时同一个坑）。注释「429/5xx 是暂时性状态，
  缓存会让下次运行永久失败」与实现不符。
- **修复方向**：改为"`>= 500` 一律不入缓存"（白名单式枚举必然遗漏），
  或至少补上 501/505/507/520-527。
- **置信度**：高 · **证据类型**：测试复现（`[501,505,507,520..527]` 全部落入缺口）。
- **核验说明**：主 agent 复跑状态码集合比对。

---

### [P1-P2-4] `BrowserFetcher.finalize()` 非幂等，同轮统计被重复计入

- **位置**：`browser.py:445-453`（每次调用都 `stats.merge(self._image_fetcher.stats)`）；
  调用点 `cli.py:1710`（`write_sync_report`）与 `cli.py:2055`（`_print_summary`）。
- **触发条件**：任意一次 `sync` 正常结束。
- **影响**：图片请求数/缓存命中/字节数在同步报告与终端摘要里被重复累计，
  报告数字不可信（`stats.elapsed` 用 `max()` 所以看不出重复，其余字段会翻倍）。
- **修复方向**：`finalize()` 加"已合并"标志，或在 `__init__` 里只合并一次。
- **置信度**：高 · **证据类型**：静态路径。
- **核验说明**：主 agent 复核两个调用点确实同轮各调一次。

---

### [P1-P2-5] 缓存"存在性"三处口径不一致，孤儿 `.body` 永不被清理

- **位置**：`http_client.py:830-832`（`count_cached` 只看 `<sha1>.body`）、
  `http_client.py:525-531`（`cache_has` 已修为 body+meta）、
  `http_client.py:488-507`（`_read_cache` 还要求 sha1 匹配）；
  孤儿来源 `http_client.py:519-521`（先 body 后 meta）与 `http_client.py:222-244`
  （注释声称清理"只有 body 或只有 meta"的半截状态，实现只遍历 `*.json`，
  **从不清理 body-only**）。
- **触发条件**：写入或迁移被中断，或出现"新 body + 旧 meta"（sha1 不符）。
- **影响**：`cache_has`/`count_cached` 可能报 True 而 `_read_cache` 返回 None
  → 调用方以为有缓存却拿不到内容。当前 `cache_has` 无生产调用方、
  `count_cached` 只用于 dry-run 显示，故影响有限，但注释自称"口径一致"，会误导后续使用。
- **修复方向**：三处共用同一判定函数；`migrate_flat_cache` 增加对 `*.body` 的反向清理。
- **置信度**：高 · **证据类型**：静态路径。

---

### [P1-P2-6] `migrate_flat_cache` 先移 body 后移 meta：中断后留下永久孤儿

- **位置**：`http_client.py:240-252`。
- **触发条件**：首次运行新版时的迁移过程被 Ctrl-C / 断电打断。
- **影响**：顶层 meta 被 `body_path.is_file()` 判为"半截"而删除（`http_client.py:242-243`），
  已移到目标目录的 body 成为**永远不会被清理**的孤儿（`migrate_flat_cache`
  只遍历顶层 `*.json`，再也看不到它）。幂等性只对"完整迁移"成立。
- **修复方向**：先移 meta 再移 body，或迁移时用"临时名 + 最后重命名"的两阶段提交。
- **置信度**：中高 · **证据类型**：静态路径（sub agent 复现，主 agent 核对代码路径）。

---

### [P1-INFO-1] `archive.py` 同样吞掉熔断

`archive.py:166/223/252` 与 `media.py:477` 是同一模式，用的是 archive.org 专用
fetcher（`archive.py:125-129`），危害限于"archive.org 被拒后仍继续查询"。
置信度：中 · 证据类型：静态路径。

---

### [P1-INFO-2] `decode_html` 对带引号的 charset 只靠兜底生效

`http_client.py:336-345`：`charset="gb2312"` 得到 `'"gb2312"'` → `LookupError`
→ 静默回退 utf-8，中文变替换字符且无告警。豆瓣实际响应不带引号，故仅观察项。
修复：取到 charset 后 `strip('"\'')`。

---

## 残留疑点（未确认触发条件，不计入缺陷）

1. **curl 后端丢弃 `final_url`、不识别 200 人机校验页**：`http_client.py:809` 取了
   `final_url` 但 `_fetch_network` 从不使用；`--no-browser` 下若被 302 到
   `sec.douban.com` 且该页返回 200，会被当正文缓存并在线重放
   （`http_client.py:624-625` 的注释本身承认此风险）。默认走浏览器，未观测到实例。
2. **浏览器 `status=0` 被当确定性结论**：`browser.py:303-305`（`page.goto` 返回 None
   时 status=0）会进入缓存判定，0 既非 2xx 也非 403/404，可能被缓存成永久结论。
3. **Wayback 快照 HTML 不校验 `resp.ok`**：`archive.py:219-225`（图片路径 `:255` 却校验了）。
   真实缓存 20 条快照全为 200，未观察到问题。
4. **`cache_domain` 不净化 hostname**：`http_client.py:192-202`，
   `https://../x` 这类畸形 URL 会让 `cfg.cache_dir / "../<sha1>.body"` 逃出缓存目录。
   正常 URL 不会出现，可达性未确认。
5. **`int(meta["status"])` 对损坏 meta 抛 `ValueError`**：`http_client.py:502`
   不在 `except (OSError, json.JSONDecodeError)` 的覆盖内。
6. **`session_expired` 置位后不复位**：`browser.py:366`，跨阶段持续影响提示文案。
7. **`url_variants` 对相对 URL 生成无意义变体**。

---

## 漏检复盘（本层已主动排查、未发现新问题的模式）

- **资源释放**：`PlaywrightDriver.__init__` 启动失败时 `close()`（`browser.py:227-230`，
  避免孤儿 Node 进程）、`close()` 幂等与逐步兜底（`browser.py:315-329`）、
  页面崩溃重建（`browser.py:265-280`）、`atomic_write_*` 在 `BaseException` 下删临时文件
  （`util.py:70-71/94-95`）；未发现泄漏。
- **超时与挂死**：curl 侧 `Session(timeout=)` + 每次 `get(timeout=)`（`http_client.py:770/797`）、
  Playwright 侧 `browser_nav_timeout_ms`（`browser.py:298`）；所有网络调用都有超时，无 `networkidle`。
- **限速与并发**：`RateLimiter.wait()/mark()` 都在 `_attempt()` 内（`http_client.py:790-791`），
  重试不绕限速；浏览器与 curl 图片后端共享同一实例（`cli.py:351-358`）；全程单线程，未发现竞态。
- **熔断计数**：不被缓存命中或重试污染。
- **凭据卫生**：`auth.py` 的 0600 + 原子写入（`:63-72`）、`redact_state` 绝不打印 cookie
  值（`:109-122`）、缓存 meta 不含 cookie/token、无 `shell=True`
  （`cli.py:2018-2023` 用列表形式）。
- **缓存内容校验**：sha1 校验、`NO_CACHE_STATUS`（除 P1-P2-3 的缺口）、空 200 不缓存、
  不可信 404 不写不取。
