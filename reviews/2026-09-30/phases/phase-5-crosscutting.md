# Phase 5 · 交叉反证审查（差异化扫查）

[返回 index](../index.md) · [修复 checklist](../fix-checklist.md)

本 phase 不沿模块顺序，而是按 skill 要求的**六类漏检模式**横向重扫一遍全仓库，
用于找出按模块阅读时容易漏掉的跨模块问题。每条都写明"查了什么、命中了什么、
哪些确认干净"。

---

## 模式 1 · 分发入口 / 命令入口的默认分支、参数校验、失败回传

**查了**：`cli.py` 的全部子命令入口（`sync`/`emit`/`discover`/`report`/`verify`/`login`/`test`）、
`main()` 的兜底、`resolve_stages`、`_config_from_args`、9 个 `stage_*` 的无内容早退路径、
`resolver.resolve` 的四类异常分支、`progress.StageRunner.run` 的兜底分支。

**命中**：
- [P2-P2-2](phase-2-orchestration.md)：`--limit` 负数 / `--delay` 负数 / `--impersonate`
  任意值均无校验；`--limit -1` 静默丢尾项，负 `--delay` 等于关闭限速。
- [P2-P2-9](phase-2-orchestration.md)：`discover` 子命令**完全没有** robots 门槛，
  `sync --dry-run` 被显式豁免却仍会全量枚举列表页。
- [P2-P2-3](phase-2-orchestration.md)：`USAGI_ARCHIVE_ENABLED`/`USAGI_BROWSER`
  被 argparse 默认值无条件覆盖。
- [P2-INFO](phase-2-orchestration.md)：非法 `--stages` 退出码 1，argparse 自身是 2；
  `--stages ""` 静默 no-op。

**确认干净**：`main()` 的顶层 `except Exception` 记日志 + 返回 1；
`cmd_verify` 返回 `0/1`；熔断返回 3、Ctrl-C 返回 130、未读 robots 返回 2；
`resolver.resolve` 对 `CircuitBreakerOpen`/`BlockedError`/`OfflineCacheMiss`/`FetchError`
四类都有明确分支。

---

## 模式 2 · 异步链路的失败、取消、超时、幂等、上下文前提变化

**查了**：curl 侧 `_attempt` → tenacity → `_fetch_network`；Playwright 侧
`PlaywrightDriver.navigate` → `BrowserFetcher._attempt`；`_confirm_transient` 的
二次请求；`RateLimiter` 的 `wait/mark` 配对；浏览器页面崩溃/回收重建；
`media.download` 的多候选循环与 archive.org 兜底。

**命中**：
- [P1-P1-1](phase-1-transport-infra.md)：**取消语义被吞** —— `CircuitBreakerOpen`
  在 `media.download` 与 `archive.py` 里被当普通失败接住，取消信号失效。
- [P1-P1-2](phase-1-transport-infra.md)：`InvalidURL` 等异常未被归一化就逃逸。
- [P1-P2-1](phase-1-transport-infra.md)：浏览器侧把致命错误也放进重试集合。
- [P1-P2-2](phase-1-transport-infra.md)：DNS 失败被重试（与注释相反）。
- [P3-INFO-1](phase-3-parsing-rendering.md)：子页/子枚举失败只 `continue`，
  不产生任何失败记录或 warning。

**确认干净**：所有网络调用都有超时（curl 双保险、Playwright 导航超时）；
`wait()/mark()` 都在 `_attempt()` 内，重试不绕限速；`_confirm_transient` 自己失败时
沿用首次结果；浏览器崩溃监听 + 每 200 次导航回收实现了"延迟执行时上下文前提变化"的处理；
单线程设计下无并发竞态。

---

## 模式 3 · 状态写入链路的"顺序错误导致半完成状态"

**查了**：`progress.mark` 的 autosave、`StageRunner` 的 `finally: save(force=True)`、
`cmd_sync` 的四条退出路径（熔断/Ctrl-C/未预期异常/正常）、
`save_data()` 的多文件写入顺序、`_write_cache` 的 body+meta 顺序、
`migrate_flat_cache` 的移动顺序。

**命中**：
- [P2-P0-3](phase-2-orchestration.md)：**主命中** —— `progress` 先落盘、`data/*.json`
  最后写；渲染阶段异常与非 SIGINT 终止都会造成"progress 说完成、数据没落地"。
- [P1-P2-5](phase-1-transport-infra.md) / [P1-P2-6](phase-1-transport-infra.md)：
  缓存先写 body 后写 meta、迁移先移 body 后移 meta，中断后留下不一致或孤儿。

**确认干净**：`cmd_sync` 的熔断 / KeyboardInterrupt / 未预期异常三条路径都补了
`progress.save(force=True)` + `save_data()`；`data/*.json` 之间即使部分写失败，
`verify.check_counts` 会做 manifest↔data↔磁盘三方对账并报错。

---

## 模式 4 · 重建型批处理 / 清理 / 迁移链路的"先移除后重建"窗口

**查了**：`migrate_flat_cache`、`generate_site` 的"只写不删"、`build_manifest`、
`refresh_unavailable` 的跨运行合并、`refresh_album_media` 的磁盘重推、
`progress.reset`、`load_existing` 的全量恢复。

**命中**：
- [P2-P0-2](phase-2-orchestration.md)：**主命中** —— 抓取失败时用空占位对象
  覆盖已归档内容，属于"先清空后重填、填不上就剩下空"的典型窗口。
- [P2-P2-4](phase-2-orchestration.md)：`ctx.structure = discovery.structure`
  是"整体替换而非合并"，部分 `--stages` 会抹掉 `structure.json` 的其它字段。
- [P4-P2-9](phase-4-emit-verify-tests.md)：`generate_site` 只写不删，被删条目的
  旧页面会随 `docs/` 一起发布且不被任何检查发现。

**确认干净**：`load_existing` + `merge_by` 不会产生重复页面；
`refresh_unavailable` 的合并规则（保留历史、剔除已取回、按进度补条目）逻辑自洽；
`atomic_write_*` 让半截文件无法产生。

---

## 模式 5 · 内容渲染点 / 富文本点 / 导出链路的安全边界与规模行为

**查了**：`html2md` 的全部转换钩子（`convert_a`/`convert_img`/`convert_br`/`convert_table`）、
`preprocess` 的标签处理、`emit` 的全部产物函数（note/album/home/index/sidebar/
videos/board/broadcast/external/about/unavailable/sync-report）、
`emit.html_text`/`html_attr`/`md_safe_url`/`md_escape_link_text`、
`frontmatter`/`yaml_value`、`config.mts` 的 markdown-it 配置、`lightbox.ts`。

**命中**：
- [P3-P0-1](phase-3-parsing-rendering.md)：**主命中** —— 文本节点里的实体标签
  还原成裸 HTML，经 VitePress `html: true` + Vue 模板编译成为可执行 HTML。
- [P3-P0-2](phase-3-parsing-rendering.md)：链接目标里的 `>` 逃出 `<…>` 包裹，
  同样注入裸 HTML；`status_notice` 是唯一连包裹都没有的链接位置。
- [P4-P2-1](phase-4-emit-verify-tests.md)：相册/首页裸 HTML 的 `src`/`href`
  未走 `html_attr`。
- [P4-P2-2](phase-4-emit-verify-tests.md) / [P4-P2-4](phase-4-emit-verify-tests.md) /
  [P4-P2-6](phase-4-emit-verify-tests.md)：链接文字漏转义、引用块只覆盖首行、
  表格字段转义不全。

**确认干净**：`yaml_value` 的 frontmatter 转义（`json.dumps` 兜底 + 首字符约束）
无注入面；`html_text`/`html_attr` 对 `{{ }}` 的防护有效（`&#123;` 不会在 Vue 编译前还原）；
`lightbox.ts` 全程 `textContent` + 站内媒体路径，无 DOM XSS；
危险协议白名单（`javascript:`/`data:`/`vbscript:` 及其字符实体变体）全部被拒。

---

## 模式 6 · 高杠杆工具函数的编码、时间、摘要碰撞、命名、兼容性前提

**查了**：`util.sha1_of`/`url_cache_key`/`atomic_write_*`/`read_json`/`write_json`/
`host_matches`、`http_client.cache_domain`/`cache_paths`/`decode_html`/`site_suffix`、
`emit.yaml_value`/`slug_anchor`/`_archived_at`、`media.correct_suffix`/`sniff_image`/
`basename_of`/`_find_album_file`、`parsers.parse_date`/`parse_page_step`/`parse_total_pages`、
`cli._external_page_id`、`models.to_dict`/`from_dict` 全家。

**命中**：
- [P4-P2-3](phase-4-emit-verify-tests.md)：`slug_anchor` 与 VitePress 的 slugify
  规则不一致 —— **高杠杆工具函数 + 跨语言隐式协议**的典型，已造成首页 2/6 锚点损坏。
- [P3-P2-3](phase-3-parsing-rendering.md)：`parse_total_pages` 用裸正则匹配双引号属性，
  引号/空白一变就静默退化成单页。
- [P3-P2-5](phase-3-parsing-rendering.md)：`sniff_image` 对前导 BOM/空白的图片误判。
- [P1-P2-5](phase-1-transport-infra.md)：缓存键与存在性判定三处口径不一致。
- [P3-P2-7](phase-3-parsing-rendering.md)：`to_dict`/`from_dict` 的 `waybackStatus`
  写而不读（隐式协议不对称）。

**确认干净**：`sha1` 仅用于缓存键与内容校验（非安全用途），碰撞面可忽略；
`atomic_write_*` 的同目录临时文件 + `os.replace` 语义正确，`tmp_dir` 与目标同文件系统；
`now_iso` 本地时区 + 秒精度一致；`cache_paths` 的 `<sha1>.body/.json` 命名不会与
`migrate_flat_cache` 的 `*.json` 扫描互相误伤；`host_matches` 的子域匹配正确；
`parse_date` 与源站数据 100% 一致；`_external_page_id` 无法产生 `/`，
所有业务 ID 都来自 `\d+` 正则，**未发现路径穿越**。

---

## 本 phase 的净新增发现

模式 1–6 里只有 [P4-P1-2](phase-4-emit-verify-tests.md) 的"无缓存时抽查静默通过"
是本 phase 首次定位（其余都是对前面 phase 结论的交叉确认）。此外确认了三处
"看起来可疑但实际干净"：Vue 花括号防护、frontmatter 转义、危险协议白名单。
