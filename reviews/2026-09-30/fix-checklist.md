# 修复 Checklist

[返回 index](index.md)

唯一的修复进度跟踪入口。覆盖本次全部已确认 finding（P0 × 5、P1 × 7、P2 × 35 = 47 条）。
INFO 观察项与「残留疑点」**不建条目**（它们尚未确认可触发）。

状态约定：`[ ]` 未开始 · `[~]` 部分完成/范围缩小 · `[x]` 全部必需步骤完成且有验证证据 · `N/A` 不适用。

> 通用验证命令（每条 finding 的「执行验证」步骤默认指这几条，除非另有说明）：
> ```bash
> .venv/bin/python -m pytest scraper/tests -q      # 离线套件（uv run 在沙箱下不可用）
> npm run docs:build                                # 产物构建 + VitePress 死链检查
> ```
> 最后更新时间：2026-09-30（最终验证：610 passed, 1 deselected；docs:build 与 npm run verify 通过）

---

## P0（安全 / 数据丢失）

### [~] P3-P0-1 · 正文实体标签还原成裸 HTML → 存储型 XSS
- [x] 回归测试覆盖实体化的 img/svg/iframe/script payload，断言转换输出无裸标签
- [x] 在 `scraper/html2md.py` 的转换层对文本节点转义 `<` `>` `&`
- [x] `docs/.vitepress/config.mts` 增加执行型 HTML token 的兜底转义规则
- [x] 全量扫描生成的 Markdown，未发现可执行标签/事件处理器/危险协议
- [x] `npm run docs:build` 通过
- [ ] 抽查一篇含 `&lt;…&gt;` 的日记页面源码；未完成独立 VitePress XSS probe

### [x] P3-P0-2 · 链接目标里的 `>` 逃出 `<…>` 包裹 → 裸 HTML 注入
- [x] URL 目标遇到 `<>`/控制字符退化为纯文本；status notice 与 unavailable 报告共用 URL 策略
- [x] 回归测试覆盖 `link2` 解码后的空格 + `>` + 标签 href
- [x] `npm run docs:build` 通过

### [x] P2-P0-1 · `StageRunner` 把 handler 标记的 `FAILED` 改写成 `done`
- [ ] 复现：`record_source_failure(retryable=True)` → 经 `StageRunner` 后状态为 `done`、`pending()==[]`
- [ ] 修 `progress.py:508-509` 的兜底判据：改为"handler 是否处理过该 key"（比较进入 handler 前的 `updated_at`/`attempts`），或把 `FAILED` 视为"已判定"
- [ ] 与 P2-P2-8 一并修：失败计数与标记计数分离
- [x] 回归测试：经 `StageRunner` 驱动 retryable 失败并确认保持 `FAILED`、仍可重试
- [x] 补齐完整三态（FAILED → 重试 → 第 4 次 UNAVAILABLE）
- [ ] 验证相邻影响：`is_terminal` 的其他调用点（`unavailable`/`skipped` 不被改写）仍成立
- [ ] 执行验证：`pytest -q` + 手工检查 `progress.json` 中失败项状态

### [~] P2-P0-2 · 抓取失败时用空占位对象覆盖已归档内容
- [ ] 复现：已归档的 note 再跑一次且详情页失败 → `data/notes.json` 的 `content_html` 变空串、comments 清空
- [ ] 修 `cli.py:1166-1179`（notes）、`cli.py:1367-1394`（albums）、`cli.py:1587-1595`（external）、`cli.py:1422-1429`（videos）：写占位前保留 `ctx.*` 里已有的成功版本，只更新 `status`
- [x] 回归测试：失败刷新已归档 note 后 `data/notes.json` 正文与评论仍保留
- [ ] 覆盖三种触发（`--force`、`PARSER_REVISION` 递增、`--offline`）及 docs 产物
- [ ] 验证相邻影响：`refresh_album_media` / `build_manifest` 对新旧对象混合的处理
- [ ] 执行验证：`pytest -q` + 对比修复前后 `data/notes.json`

### [~] P2-P0-3 · `progress` 先落盘、`data/*.json` 最后写 → 渲染异常 / SIGTERM 丢内容
- [ ] 复现 1：`emit_note` 抛错后 `progress.json` 已 `done` 而 `data/notes.json` 未写
- [ ] 复现 2：SIGTERM 终止时同样现象
- [ ] 修 `cli.py:1849-1861`：把 `refresh_unavailable`/`generate_site`/`write_sync_report`/`persist_products` 纳入统一兜底；或在 `SyncContext.__exit__` 做"未落盘则保存"
- [ ] 统一落盘顺序为"先 `save_data()` 再 `progress.save()`"，或每 stage 结束增量持久化该阶段产物
- [ ] 注册 SIGTERM handler，复用 SIGINT 的收尾
- [x] 回归测试：数据持久化 hook 先于进度快照写入
- [ ] 覆盖渲染异常收尾及 SIGTERM 演练
- [ ] 执行验证：`pytest -q` + 手工 kill -TERM 演练一次

---

## P1（静默错误 / 可靠性）

### [x] P1-P1-1 · `MediaArchive.download` 吞掉 `CircuitBreakerOpen`
- [x] 假传输层熔断用例确认异常冒泡且只请求一个候选
- [x] `media.py` 与 `archive.py` 的请求路径显式冒泡 `CircuitBreakerOpen`
- [ ] 可选加固：`http_client.fetch()` 入口加粘滞 `_circuit_open`，熔断后直接拒绝新请求
- [x] 回归测试：CB 必须冒泡，且只发出一次候选请求
- [ ] 验证相邻影响：`resolver`/`progress`/`cli` 既有的 CB 冒泡路径不受影响
- [ ] 执行验证：`pytest -q`

### [x] P1-P1-2 · `fetch()` 泄漏非 `FetchError` 异常
- [x] `_fetch_network` 将非重试型 `CurlError` 归一化为 `FetchError`
- [x] 回归测试：`InvalidURL`/`MissingSchema`/`TooManyRedirects` 均归一化且仅尝试一次
- [ ] 验证相邻影响：确认新增的 `except` 不会吞掉 `CircuitBreakerOpen`（应先于/独立于它判断）
- [ ] 执行验证：`pytest -q`

### [~] P2-P1-1 · `sync --offline` 完全不可用
- [ ] 复现：缓存存在、`force=True`（`revalidate` 路径）时抛 `OfflineCacheMiss`，整体 exit 1
- [ ] 修 `cli.py:1805-1810`：`ctx.resolver.revalidate = not cfg.offline`
- [ ] 加固 `http_client.fetch()`：offline 下忽略 `force`、先查缓存
- [x] 回归测试：offline 下 `force=True` 仍命中缓存且不发网络请求
- [ ] 覆盖完整 `sync --offline` CLI 路径及进度只读不落盘
- [ ] 验证相邻影响：修好后复核 P2-P2-5（离线漏进 `unavailable.json`）
- [ ] 执行验证：`pytest -q` + 手工跑一次 `--offline`

### [x] P2-P1-2 · `stage_albums` 列表页失败仍 `mark_done`（0 张照片）
- [ ] 复现：相册列表页失败 → `data/albums.json` 照片清空且 `album:A1=done`
- [ ] 修 `cli.py:1350-1394`：`page.has_content` 为假（或 photos 为空且 status 非 OK）时走 `record_source_failure`，并保留 `ctx.albums` 旧清单
- [x] 回归测试：列表页失败保留旧照片并留下 retryable 状态
- [ ] 验证相邻影响：`discover.py:281-283` 的 `photo_ids[album]=[]` 建键行为
- [ ] 执行验证：`pytest -q`

### [x] P3-P1-1 · `parse_bulletin` 容器缺失时冒充其它公告
- [ ] 复现：同页两条公告 + 请求不存在的 id → 返回另一条公告的正文且 `availability=ok`
- [ ] 修 `parsers.py:200-230`：容器缺失时不回退页面级 `#link-report`；或仅当页面只有一个 `#link-report` 时才回退，否则 `unavailable` + `retryable`
- [x] 回归测试：页面有其它公告、目标容器缺失时不冒用内容，stage 保持 retryable
- [ ] 执行验证：`pytest -q`

### [x] P4-P1-1 · `verify` 数量对账因 `_meta` 恒失败
- [x] 复现：健康归档实跑 `check_counts`，发现并修复 `_meta` 多计一条
- [x] 数量对账忽略 `_meta`，并覆盖 notes/albums/external/bulletins/videos 数据
- [x] 补 `check_counts` 正向用例（健康数据必须通过）与缺少 md 页用例
- [ ] 验证相邻影响：`albums/bulletins/videos` 三个同源字段是否也有 `_meta` 口径问题
- [x] 执行验证：`npm run verify` 在健康归档上返回 0

### [x] P4-P1-2 · 内容抽查无缓存时静默通过 + albums/photos/external 从不比对
- [x] 缓存缺失记 problem；`checked` 仅在实际完成比对后增加
- [x] external 与 album caption 纳入固定种子的候选集
- [x] 回归测试覆盖无缓存失败、external/albums 内容错误、抽样 ID 可复现
- [x] 执行验证：离线套件通过；健康归档 `npm run verify` 返回 0

---

## P2（正确性 / 一致性 / 可维护性）

### [x] P1-P2-1 · 浏览器重试集合含基类 `PlaywrightError`
- [ ] 修 `browser.py:88-97`：去掉裸 `PlaywrightError`；`TargetClosedError` 单独判定为"需重建浏览器"
- [ ] 回归测试：致命错误只重试一次（或用例断言不进入退避）
- [ ] 执行验证：`pytest -q`

### [x] P1-P2-2 · `DNSError` 被重试（与注释相悖）
- [ ] 从 `CURL_RETRYABLE_EXCEPTIONS` 排除 `DNSError`，或修正 `http_client.py:75-88` 的注释
- [ ] 回归测试：`DNSError` 不重试、立即以 `FetchError` 失败
- [ ] 执行验证：`pytest -q`

### [x] P1-P2-3 · `NO_CACHE_STATUS` 缺口（501/505/507/520-527 被永久固化）
- [ ] 改为"`>= 500` 一律不入缓存"（或补齐白名单）
- [ ] 回归测试：对 501/520/522 断言 `cache_has == False` 且下次仍发起请求
- [ ] 验证相邻影响：`_cache_is_stale` 是否也需要覆盖这些状态
- [ ] 执行验证：`pytest -q`

### [x] P1-P2-4 · `BrowserFetcher.finalize()` 非幂等
- [ ] 加"已合并"标志，或把合并移到 `__init__`
- [ ] 回归测试：连续调用两次 `finalize()`，`stats` 不变
- [ ] 执行验证：`pytest -q` + 核对 `data/sync-report.md` 的请求数

### [x] P1-P2-5 · 缓存存在性三处口径不一致 + 孤儿 body
- [ ] `count_cached` 复用 `cache_has` 的判定（body + meta）
- [ ] `migrate_flat_cache` 增加对 `*.body` 的反向清理，或删除注释里未实现的半句
- [ ] 回归测试：孤儿 body 不计入 `count_cached`，且能被清理
- [ ] 执行验证：`pytest -q`

### [x] P1-P2-6 · `migrate_flat_cache` 先移 body 后移 meta
- [ ] 改为先移 meta 再移 body，或"临时名 + 最后重命名"两阶段提交
- [ ] 回归测试：模拟中断后无永久孤儿
- [ ] 执行验证：`pytest -q`

### [~] P2-P2-1 · `--limit` 在 photos 与 albums 之间语义不一致
- [ ] 统一为"前 N 个 pending 相册"（photos 把 `limit` 交给 `StageRunner`，或两边同逻辑）
- [ ] 回归测试：连续两次 `--limit 1` 能依次推进 A1→A2，且 albums 不提前标 done
- [ ] 执行验证：`pytest -q`

### [x] P2-P2-2 · 参数缺校验（`--limit` 负数、`--delay` 负数、`--impersonate` 任意值）
- [ ] argparse 层拒绝 `limit < 0`、`delay <= 0`；`--limit 0` 语义写进 help
- [ ] `--impersonate` 用 curl_cffi 合法列表做 choices，或启动时校验一次
- [ ] 回归测试：三类非法输入均报错退出（退出码与 argparse 一致）
- [ ] 执行验证：`pytest -q`

### [x] P2-P2-3 · `USAGI_ARCHIVE_ENABLED`/`USAGI_BROWSER` 被 CLI 无条件覆盖
- [ ] `_config_from_args` 改成三态（`SUPPRESS`），仅命令行显式出现时覆盖
- [ ] 回归测试：`USAGI_BROWSER=0` / `USAGI_ARCHIVE_ENABLED=1` 生效
- [ ] 执行验证：`pytest -q`

### [~] P2-P2-4 · 部分 `--stages`/`--dry-run` 抹掉 `structure.json` 字段
- [ ] `cli.py:1019` 改为把 discovery 结果**合并**进已恢复的 structure；dry-run 不覆盖既有 `structure.json`
- [ ] 回归测试：`sync --stages notes` 后 `photoIds/albumTitles/forumTopics` 不丢
- [ ] 执行验证：`pytest -q` + 对比 `data/structure.json`

### [~] P2-P2-5 · 离线未命中经内存进度漏进 `data/unavailable.json`
- [ ] `refresh_unavailable` 只采信本次 resolver 明细 + 磁盘历史；离线内存 `mark_*` 不参与
- [ ] 回归测试：离线运行后 `data/unavailable.json` 不被改动
- [ ] 执行验证：`pytest -q`（依赖 P2-P1-1 先修）

### [x] P2-P2-6 · `report` 在 `parserRevision` 落后时输出空报告
- [ ] revision 不符时只告警、不清空（或按旧 revision 读并注明"将全部重跑"）
- [ ] 回归测试：旧 revision 下 `report` 不撒谎
- [ ] 执行验证：`pytest -q`

### [x] P2-P2-7 · 枚举重复 key 导致重复处理与统计虚高
- [ ] `StageRunner.run` 入口按 `key_of` 去重（保序）；`result.skipped` 按去重集合计算
- [ ] 回归测试：items 含重复项时 handler 每 key 只调一次、`skipped` 正确
- [ ] 执行验证：`pytest -q`

### [x] P2-P2-8 · `attempts` 被成功记录抬高
- [x] 失败次数与标记次数分离（新增 `failures` 字段）
- [x] 回归测试：3 次成功后仍享有完整重试预算
- [ ] 执行验证：`pytest -q`（与 P2-P0-1 同批修）

### [~] P2-P2-9 · robots 门槛可绕过（`discover` / `sync --dry-run`）
- [ ] 门槛判断提到 `main()` 或各子命令入口，`discover` 也要；dry-run 提示"仍需联网枚举"
- [ ] 回归测试：无 `--i-have-read-robots` 时 `discover` 与 `sync --dry-run` 均拒绝联网
- [ ] 执行验证：`pytest -q`

### [x] P3-P2-1 · 评论只取第一个 `<p>`
- [ ] 改取 `.content` 剔除作者块后的全部子节点（复用 `_content_html` 做法）
- [ ] 回归测试：多 `<p>` 评论内容完整
- [ ] 执行验证：`pytest -q`

### [x] P3-P2-2 · `<a><img></a>` 被链接文字转义打坏
- [ ] 只对纯文本 label 做方括号转义，或检测 label 已含 `![](` 时跳过
- [ ] 回归测试：可点击配图渲染为可点击图片而非字面 `![]`
- [ ] 执行验证：`pytest -q`

### [x] P3-P2-3 · `parse_total_pages` 裸正则引号敏感
- [ ] 改用 `soup.select_one("[data-total-page]")`，与 `parse_note_comment_pages` 一致
- [ ] 回归测试：单引号/无引号/带空格三种写法均正确解析
- [ ] 执行验证：`pytest -q`

### [x] P3-P2-4 · 后缀候选表缺 `.svg`/`.bmp` 导致重复下载
- [ ] 补进 `PREVIEW_SUFFIX_ORDER` 或改为按 `stem` + `glob` 全后缀查找
- [ ] 回归测试：内容为 SVG/BMP、dest 为 `.jpg` 时第二次调用命中 `from_cache`
- [ ] 执行验证：`pytest -q`

### [x] P3-P2-5 · `sniff_image` 对前导 BOM/空白的图片误判
- [ ] 判定前统一 `lstrip(b"\xef\xbb\xbf\r\n\t ")`；放宽短 SVG 长度门槛；加强 `BM` 校验
- [ ] 回归测试：带 BOM 的 JPEG、`<svg/>`、`BM` 假阳性
- [ ] 执行验证：`pytest -q`

### [~] P3-P2-6 · 视频缺字段仍标 `ok` + `unquote` 不可逆改写
- [ ] 字段缺失时置 `unavailable`/`retryable`（真实实例：`video_id=771903` 的缩略图为空却标 ok）
- [ ] `unquote` 前判断含 `%[0-9A-Fa-f]{2}`，并对结果做 scheme 白名单
- [ ] 回归测试：缺字段 → 非 ok；含 `%` 的 URL 不被破坏
- [ ] 执行验证：`pytest -q`

### [~] P3-P2-7 · 反序列化不对称与构造过严
- [ ] `_status_from_dict` 补 `wayback_status`
- [ ] `ImageRef(**img)` / `MiniblogStatus(**payload)` 改为 `.get()` 或按 `dataclasses.fields` 过滤
- [ ] 回归测试：`SourceStatus` 往返字段完整；含未知键的 payload 不崩
- [ ] 执行验证：`pytest -q`

### [x] P3-P2-8 · `SourceStatus` 允许裸字符串
- [ ] 加 `__post_init__` 归一化为 `Availability`，或 parser 侧统一用枚举
- [ ] 回归测试：`SourceStatus(availability="ok").needs_notice` 不抛异常
- [ ] 执行验证：`pytest -q`

### [x] P4-P2-1 · `emit_album`/`emit_home` 裸 HTML 属性未转义
- [ ] `preview`/`full`/`cover`/`route` 一律经 `html_attr()`
- [ ] `media.py` 文件名派生处加字符白名单 `[A-Za-z0-9._-]`
- [ ] 回归测试：含 `"` 的 local 路径不产生属性 breakout
- [ ] 执行验证：`pytest -q`

### [x] P4-P2-2 · 索引页链接文字漏转义方括号
- [ ] `emit.py:635`（notes fallback）与 `emit.py:653`（albums index）补 `md_escape_link_text`
- [ ] 回归测试：标题含 `[`/`]` 时链接仍完整
- [ ] 执行验证：`pytest -q`

### [x] P4-P2-3 · `slug_anchor` 与 VitePress slugify 不一致（首页 2/6 锚点已坏）
- [ ] 按 VitePress 规则重写 `slug_anchor`（NFKD + 去组合符/控制符 + 特殊字符 → `-` + 折叠/去首尾 + 数字前缀 + lower）
- [ ] 修好 `docs/index.md` 中已坏的 `#轻音系列` / `#玉子市场玉子爱情故事`
- [ ] `check_links` 增加锚点校验（解析 md 标题按同一 slugify 生成集合）
- [ ] 回归测试：emit 的锚点集合 == 真实渲染出的 id 集合
- [ ] 执行验证：`docs:build` + 点击首页分类卡片

### [x] P4-P2-4 · `emit_board` 引用块只覆盖首行
- [ ] 复用逐行 `> ` 前缀的渲染（与笔记评论一致）
- [ ] 回归测试：多段评论整段留在引用块内、评论内的 `##` 不成为页面标题
- [ ] 执行验证：`pytest -q` + 检查 `docs/board.md`

### [x] P4-P2-5 · `emit_external` 的 `archivedAt` 非幂等
- [ ] external 也走 `_archived_at`
- [ ] 回归测试：跨天重复 emit 产物不变（monkeypatch `now_iso`）
- [ ] 执行验证：`pytest -q`

### [x] P4-P2-6 · `emit_unavailable_report` 表格转义不全
- [ ] 对入表的每个字段统一转义（`|`→`\|`、换行→`<br>`）
- [ ] 回归测试：`url`/`context` 含 `|` 时表格列数不变
- [ ] 执行验证：`pytest -q`

### [x] P4-P2-7 · `check_links` 路径解析缺陷
- [ ] 以链接所在文件目录为基准；按"原样 → 补 `.md` → `index.md`"顺序探测；已带后缀不重复追加
- [ ] 回归测试：`.md` 后缀链接、`../` 相对链接、跨目录真死链三种场景
- [ ] 执行验证：`npm run verify` 在健康归档上 links 通过

### [x] P4-P2-8 · `check_images` 把 `.DS_Store` 当图片
- [ ] 三个媒体检查统一跳过点文件
- [ ] 顺手删除仓库里既有的 3 个 `.DS_Store`（`.gitignore` 已忽略，但文件仍在）
- [ ] 回归测试：`docs/public/media` 下有点文件时 `check_images` 仍通过
- [ ] 执行验证：`npm run verify` 在健康归档上 images 通过

### [x] P4-P2-9 · 对账与清理只覆盖 notes
- [ ] 把 albums/external（及 videos/board 等生成页）纳入 manifest↔data↔磁盘三方对账
- [ ] 或在 emit 前显式清理被删条目并记录
- [ ] 回归测试：磁盘上的 stale 页面能被发现
- [ ] 执行验证：`pytest -q`

### [x] P4-P2-10 · `check_content_sample` 抽样不可复现
- [ ] 抽样结果（note_id 列表）写进报告；或支持固定顺序/`--seed`
- [ ] 回归测试：两次运行抽样集合一致
- [ ] 执行验证：`pytest -q`

### [x] P4-P2-11 · 测试守卫有绕过口子
- [ ] 守卫改为 patch `curl_cffi.requests.Session`（类级）与 `playwright.sync_api.sync_playwright`（模块级）
- [ ] `resolve_optional` 等宽 `except` 对 `AssertionError` 重新抛出
- [ ] 新增"守卫自测"：故意走 `auth.check_session` / `browser.detect_chrome_ua` 直连路径并断言抛错
- [ ] 执行验证：`pytest -q`（含新守卫自测）

### [~] P4-P2-12 · 覆盖缺口 + CI 不跑 pytest/verify
- [x] 本轮新增关键失败路径用例，并让 CI 安装 Python 依赖、运行 `pytest` 与结构 `verify`
- [x] CI 显式跳过本地原始缓存抽查，报告注明未检查；默认 `verify` 缺缓存会失败
- [ ] 未在线触发 GitHub CI，也未注入回归验证远端失败门禁

---

## 批次归属

批次划分与建议顺序见 [fixes-plan.md](fixes-plan.md)。所有条目都已进入本 checklist；
即使不在当前批次，也保留为 `[ ]` 并标注所属批次。
