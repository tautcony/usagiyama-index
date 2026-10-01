# scraper · 抓取工具

把[豆瓣小站「兔子山的小站」](https://site.douban.com/211330/)归档为本地 Markdown 与
VitePress 站点。原站更新后重跑即可增量同步。

---

## 命令一览

```bash
uv run python -m scraper.cli <子命令> [参数]
```

| 子命令 | 作用 |
| --- | --- |
| `sync` | 抓取 + 生成站点（增量；已完成单元自动跳过） |
| `emit` | 仅根据已有数据重新生成产物（离线，零网络请求） |
| `discover` | 只枚举站点结构，不抓详情 |
| `report` | 输出进度报告 |
| `verify` | 校验归档结果（断链 / 图片 / 对账 / 抽查） |
| `login` | 打开浏览器完成豆瓣登录并保存会话（工具不接触密码） |
| `test` | 跑 HTML→Markdown 转换回归测试 |

全局参数：

| 参数 | 说明 |
| --- | --- |
| `--impersonate NAME` | curl_cffi 浏览器指纹，默认 `chrome`（可选 `chrome136`、`safari18_0` 等） |
| `--offline` | 只读本地缓存，绝不联网 |
| `--archive` / `--no-archive` | 启用 / 关闭 Internet Archive 补足（**默认关闭**） |
| `--browser` / `--no-browser` | 用无头浏览器抓页面 / 退回纯 HTTP（**默认启用浏览器**） |
| `--speed NAME` | 请求间隔档位：`cautious`(5~7s，默认) / `normal`(2~3s) / `fast`(1~2s) |
| `--delay N` | 请求间隔下限（秒），上限为 `N+2`；精确覆盖档位（与 `--speed` 互斥），默认 5 |
| `--limit N` | 每阶段最多处理 N 项（冒烟测试用） |
| `-v` / `-q` | 详细 / 安静日志 |

`sync` 专属参数：

| 参数 | 说明 |
| --- | --- |
| `--dry-run` | 只预估规模与耗时，不抓取 |
| `--i-have-read-robots` | 知情门槛，见下 |
| `--stages a,b,c` | 只跑指定阶段（`rooms,bulletins,notes,photos,albums,videos,forum,miniblog,main,external`） |
| `--skip-domain DOMAIN` | 外链阶段跳过指定域名及其子域名；可重复传入，例如 `--skip-domain dou.bz` |
| `--skip-failed` | 外链阶段跳过以前失败的页面和图片，继续抓取其他项目；默认会重试失败项 |
| `--concurrency N` | 外链阶段并发 worker 数，默认 `1`；其他阶段仍串行，请逐步提高 |
| `--force` | 全站忽略进度并重新请求页面；联网时跳过 HTTP 响应缓存 |
| `--full-check-note NOTE_ID` | 全量检查指定豆瓣日记；可重复传入多个 ID |
| `--recheck-unavailable` | 重新探测此前标记为不可访问的页面 |
| `--external-pages-only` | external 阶段只恢复页面，暂缓图片，可随后续抓 |
| `--no-emit` | 只抓取，不生成站点 |
| `--progress` / `--no-progress` | 显示 / 隐藏进度条 |

普通 `sync` 每次从 room 和各模块列表重新发现内容 ID，并合并标题、日期、回应数和模块归属等列表元数据；再补抓新发现、上次失败或明确要求重试的项目。已完成文章详情会跳过，不会因为列表页有变化就全量重抓所有文章。需要重新检查单篇时，使用 `--full-check-note NOTE_ID`。例如：

外部文章原始响应使用独立阶段，不解析正文。先运行 `emit` 更新按域名分类的清单，再只预演/执行该阶段：

```sh
npm run emit
uv run python -m scraper.cli sync --stages external --dry-run --i-have-read-robots
uv run python -m scraper.cli sync --stages external --limit 2 --i-have-read-robots
uv run python -m scraper.cli sync --stages external --skip-domain dou.bz --i-have-read-robots
uv run python -m scraper.cli sync --stages external --skip-domain dou.bz --skip-failed --speed fast --concurrency 3 --i-have-read-robots
uv run python -m scraper.cli sync --stages external --concurrency 3 --i-have-read-robots
```

确认小批次结果后可去掉 `--limit 2` 续跑。符合文章条件的页面原始 HTML 保存在 `scraper/state/cache/`，抓取元数据在 `data/external-captures.json`；短链会读取重定向最终地址并重新分类。`metadata`、`review` 和 `skip` 不会进入该阶段。正文提取、评论、媒体处理由后续解析阶段负责。

外链失败恢复会依次检查保留文章 ID 的发布站迁移地址、HTTPS 地址、浏览器与 HTTP 传输。通过正文选择器和错误页检查后才记为成功；HTTP 200 的密码页、空壳页不会作为文章。

启用 `--archive` 时，外链阶段通过 Internet Archive 的 availability 接口查询公开历史快照，再获取 `id_` 原始响应。查询接口漏报时会直接请求邻近快照回放，并以最终重定向地址中的真实时间戳为准。该路径独立于小站阶段的 CDX 补足，因此 CDX 暂时不可用时仍可恢复外链。快照图片优先取同一时期的 `im_` 响应。每次尝试的地址、状态、失败原因及成功来源保存在 `external-captures.json` 的 `recoveryAttempts`、`captureUrl`、`snapshot`；生成页明确展示历史快照日期。失效短链还会从已缓存的豆瓣源页面提取明确的展开地址，并记录证据文件；存在冲突或只有文字线索时不会猜测地址。

```sh
uv run python -m scraper.cli sync --stages external --archive --recheck-unavailable --i-have-read-robots
```

京阿尼 2020 年改版后的日记重新分配了文章 ID，不能把旧 `?p=ID` 直接替换为 `/diary/archives/ID`。旧文章从原地址的历史快照恢复，避免归档同号的另一篇文章。纯离线运行不会查询恢复接口或改写进度。

对已核实的官方转载，抓取器要求转载正文明确引用原地址，并在生成页标注“官方转载”。动态排行榜只在原引用明确对应已核实的历史周榜时恢复到该周页面，不把今天的排行当成历史内容。原文不可得但已有译文或摘译时，外链索引另列可读版本，保留原链接失败状态。

`--skip-domain` 可重复指定；域名本身及其子域名都会跳过。跳过只对本次运行生效，不会把目标写成永久完成，移除参数后仍可续抓。
`--skip-failed` 仅影响本次 external 阶段的失败项选择；失败状态保留在进度记录中，去掉参数后仍可重试。它同时适用于文章原始抓取和图片抓取。

`--concurrency` 只并行处理互相独立的外链目标及其图片；每个 worker 使用独立传输会话，并共享请求间隔限制。外部文章页按域名保存在 `docs/external-articles/<域名>/<文章ID>.md`；图片保存在 `docs/public/media/external-articles/<域名>/<文章ID>/`，成功归档后页面引用本地图片。默认仍为单 worker。

```sh
npm run sync -- --i-have-read-robots --full-check-note 261864994
```

对 room 列表中的文章，该选项重新请求正文、配图和评论分页，并在联网时绕过这些资源的 HTTP 缓存；对外链形式的 `/note/{ID}/`，会强制刷新对应的主站归档页。配图刷新失败时继续使用旧归档图。`--force` 保留为全站强制重抓操作。

`npm run report` 生成的 `data/progress-report.md` 分开显示整体累计成功数和当前续跑状态。累计数按唯一 key 计数，项目成功归档后不会因重试失败或解析器版本变化而回退。

`login` 专属参数：

| 参数 | 说明 |
| --- | --- |
| `--check` | 只校验已保存的会话是否有效，不打开浏览器 |
| `--timeout N` | 等待登录的超时秒数（默认 300） |

---

## 采集频次与合规

抓取前请阅读本节。

原站 `robots.txt` 为全量禁止：

```
# https://site.douban.com/robots.txt
User-agent: *
Disallow: /
```

`www.douban.com` 则是部分禁止，并附了一条 `# Crawl-delay: 5`。

因此 `sync` 要求显式传入 `--i-have-read-robots` 才会发起请求。默认配置如下：

| 措施 | 默认值 |
| --- | --- |
| 并发 | 默认单 worker；仅外链阶段可用 `--concurrency N` 并发 |
| 请求间隔 | `5.0 ~ 7.0` 秒随机抖动（尊重 `Crawl-delay: 5`） |
| 退避重试 | 指数增长 + 抖动，5s 起，最多 5 次 |
| 熔断 | 连续 3 次 `403/418` 立即停止并保存进度 |
| 缓存 | 同 URL 二次运行**零请求** |
| 增量 | 只抓新增内容，存量不重抓 |

请求间隔有三档可选（`--speed`）：

| 档位 | 间隔 | 说明 |
| --- | --- | --- |
| `cautious` | `5 ~ 7` 秒 | **默认**，下限正好是 `Crawl-delay: 5` |
| `normal` | `2 ~ 3` 秒 | 明确快于 robots.txt 的建议值 |
| `fast` | `1 ~ 2` 秒 | 同上，更适合本地反复调试 |

后两档会在 robots 提示与抓取开始的日志里各提醒一次（快于 `Crawl-delay`），然后继续执行。
`--delay N` 是精确覆盖（间隔 `N ~ N+2` 秒），与 `--speed` 互斥；
`USAGI_DELAY_MIN` / `USAGI_DELAY_MAX` 环境变量同样直接写入间隔，优先级低于命令行。

`sync --dry-run` 会按当前档位给出耗时预估，换档前后可以先看一眼差多少。

关于指纹与 UA：

- 浏览器模式下**不伪造版本号**：只在无头启动导致 UA 里出现 `HeadlessChrome`
  时，把它替换回浏览器**自己上报的真实版本**（`Chrome/152.0.7977.83`）。
- `navigator.webdriver` **不做处理** —— 那是真正的自动化标记，不属于"还原成有头行为"的范畴。
- 图片请求按**浏览器加载 `<img>` 时的样子**发：`Accept: image/avif,image/webp,…`、
  `Sec-Fetch-Dest: image`、`Sec-Fetch-Mode: no-cors`、`Sec-Fetch-Site: cross-site`，
  并去掉只属于导航的 `Sec-Fetch-User` / `Upgrade-Insecure-Requests`。
  curl_cffi 的 `impersonate` 默认给的是**导航**的头（`Accept: text/html,…`、
  `Sec-Fetch-Dest: document`），拿它要 jpg 属于自己写错了，与风控无关；
  `User-Agent` / `Sec-Ch-Ua*` / TLS 指纹仍全部来自同一份 `impersonate` 配置，没有伪造。

并且**明确不做**：不轮换 UA、不轮换代理、不并发轰炸、不做验证码绕过。

请仅将归档结果用于个人保存与阅读，不要公开再分发。

### 熔断后怎么办

看到「已熔断停止」说明源站开始拒绝请求。建议**等待数小时**后重跑同一命令。
进度已保存，已完成的内容不会被重复请求。

如果日志里同时出现「登录态已失效」，说明熔断的原因不是频率而是会话过期：
重跑 `npm run login` 后再同步即可。

---

## 浏览器抓取（默认启用）

小站有反爬措施，纯 HTTP 会拿到 403 / 302 到风控页，且需要登录的内容拿不到。
因此**所有页面请求默认走真实 Chrome**：

| 项目 | 做法 |
| --- | --- |
| 引擎 | Playwright 驱动**系统已装的 Chrome**（`channel="chrome"`），无需 `playwright install` |
| 无头 | 抓取时无头；`login` 子命令强制有头 |
| 等待策略 | `domcontentloaded`（不等图片/字体，省时间且不影响正文） |
| 资源拦截 | 拦截图片/媒体/字体与统计域名（`hm.baidu.com`、`googletagmanager.com` 等） |
| 页面回收 | 每 200 次导航重建 `page`，避免长时间运行内存增长 |
| 崩溃恢复 | 监听 `page.crash`，自动重建 page 后继续 |

**风控识别**：导航后若最终落在 `sec.douban.com`，说明触发了风控。
这类响应**不会被缓存**（否则会永久污染缓存），而是抛出 `ChallengeError` 并计入熔断。

**图片仍走 HTTP**：图片是静态资源、不需要 JS，走浏览器只会更慢。
所以浏览器模式内部仍保留一个 curl_cffi 传输层专门下图片，两者共用同一份磁盘缓存。

想退回纯 HTTP（快、轻，但拿不到需登录内容）：

```bash
uv run python -m scraper.cli sync --no-browser --i-have-read-robots
```

---

## 登录与会话

有些内容（`www.douban.com/note/*`、`/topic/*`）未登录会 302 到风控页。
本工具提供登录流程，但**全程不接触密码**：

```bash
npm run login          # 打开 Chrome，你手动登录，工具只保存会话
npm run login:check    # 只校验会话是否还有效
```

流程：

1. 启动一个有头 Chrome，打开豆瓣登录页；
2. 你在窗口里完成登录（扫码 / 短信 / 账号密码 / 图形验证码都行）；
3. 工具轮询 `www.douban.com/mine/`，一旦返回 200 就判定登录成功；
4. 把 `storage_state`（cookie + localStorage）写入 `scraper/state/douban.auth.json`，
   权限 `0600`，并已在 `.gitignore` 中排除；
5. 关闭窗口。

会话文件等同登录凭据，不要提交或分享。

`--check` 不需要浏览器：它把 cookie 注入 curl_cffi 会话后请求 `/mine/`，
200 即有效，403 即过期。所以可以在跑长任务前快速确认。

登录后，`sync` 的 `main` 阶段会补抓索引①/② 里指向豆瓣主站的页面，
归入 `/external/{page_id}` 路由，并接入侧边栏。

**已经被标成「需要登录，无法归档」的，怎么重新补抓？** 登录一次，再让 `main` 阶段
重新探测这一批：

```bash
npm run login:check                                            # 先确认会话还有效
npm run sync -- --i-have-read-robots --recheck-unavailable --stages main
```

`--recheck-unavailable` 把进度里 `unavailable` 的条目重新选出来（已归档的照旧跳过），
`--stages main` 限定只跑"需要登录"这一个阶段。**不需要手工删缓存**：被拒绝（403/418）
的响应虽然写进了缓存，但联网时不会重放 —— 见上面「哪些响应不该进缓存」。
补回来的条目会从 `data/unavailable.md` 与站点上的不可访问清单里消失。

仍然拿不到的那些（话题已删除、被设为私密）会留在清单里、带着原来的标记 ——
那不是没试，是源站不给。

---

## 断点续接

三份持久化状态互相配合，任意时刻中断都能精确续跑：

| 文件 | 作用 | 续跑时 |
| --- | --- | --- |
| `state/cache/<域名>/` | HTML / 图片原始响应缓存 | 命中则零网络请求 |
| `state/progress.json` | 每个抓取单元的状态机 | 已完成项直接跳过 |
| `state/manifest.json` | 内容级单一事实源 | 决定产物如何重新生成 |

`progress.json` 采用**原子写入**（同目录临时文件 + `os.replace`），
因此 Ctrl-C、断网、熔断都不会损坏状态文件。

### 图片临时文件放在 `public/` 之外

图片同样走原子写入，但临时文件落在 `docs/.vitepress/.tmp/`，
而不是目标目录 `docs/public/media/.../`。

原因：Vite 拷贝 `public/` 用的是

```js
for (const file of fs.readdirSync(srcDir)) {   // 先取名字快照
  const stat = fs.statSync(srcFile);           // 再逐个 stat
  fs.copyFileSync(srcFile, destFile);          // 再逐个拷贝
}
```

只要临时文件落在 `public/` 里，就会被 `readdirSync` 列进名单，
而随后的 `os.replace` 会把这个名字移走 —— 构建于是**随机**地以
`ENOENT ... copyfile` 失败。把临时文件挪出 `public/` 从根上消除了这个竞态。

`docs/.vitepress/.tmp/` 与 `docs/public/` 在同一文件系统，所以
`os.replace` 仍然是原子的（跨设备会报 `EXDEV`）。

> 顺带一提：不要在构建的同时开着 `vitepress dev`。旧进程会持有
> `docs/.vitepress/dist`，导致构建以 `ENOTEMPTY` 失败、产出残缺。

**正文里的花括号**：归档内容什么字符都可能有，而 VitePress 把每篇 markdown
编译成 Vue 组件，`{{ … }}` 会被当成插值表达式 —— 轻则这段文字消失，重则
（括号不配对时）整个站点构建失败。两道防线：markdown 正文由
`config.mts` 里的 `defuseVueBraces` 换成实体，scraper 直接生成的裸 HTML
（相册卡片等）由 `emit.html_text()` 换成实体，页面上显示的仍是花括号本身。

### 缓存按域名隔离

缓存按 URL 的**主机名**分目录存放，不同源站互不干扰：

```
scraper/state/cache/
├── site.douban.com/         小站页面（房间 / 公告 / 日记 / 相册）
├── img1.doubanio.com/       图片（按实际 CDN 主机分列）
├── img3.doubanio.com/
├── www.douban.com/          主站页面（豆列等）
├── archive.org/             CDX 查询
└── web.archive.org/         历史快照正文与图片
```

这样可以：

- **隔离**：不同源站的缓存键空间天然分离，不会互相污染；
- **可维护**：可以按域名单独清理或检查，排查问题时定位明确；
- **可扩展**：日后接入新站点不会与既有缓存冲突。

每个条目由一对文件组成：`<sha1>.body`（原始响应体）与 `<sha1>.json`
（meta：原始 URL、状态码、Content-Type、抓取时间、内容 sha1）。
读取时会校验内容 sha1，损坏的缓存自动忽略并重新抓取。

**哪些响应不该进缓存**：429/5xx 这类暂时性失败不写（否则一次抖动会被固化成永久结论）；
**2xx 但零字节也不写** —— 空 200 不是可用内容，缓存下来会让这个 URL 变成"永久失败"：
之后的运行连网络请求都不发，直接重放那份空内容，日志里只能看到「0B」而无从判断。
反过来，调用方发现"缓存里的东西不可用"时（例如 2xx 却是一张 HTML 错误页），
用 `invalidate_cache(url)` 丢掉该条目，下次运行自然重新请求，不需要 `--force`。

**403/418 会被写进缓存，但不会被重放**。写是有意的 —— 免得同一个 URL 反复冲击源站；
不重放也是必须的 —— "此刻被拒绝"不是"内容不存在"，登录态、风控窗口、防盗链请求头
任一条变了它就不成立。联网时读到这类条目一律重新请求一次（离线时没有别的办法，
照旧使用）。少了这条规则，`--recheck-unavailable` 会变成一句空话：条目被重新选出来，
请求还没出门就被磁盘上的 403 顶回去，日志与上次一模一样，只能手工删缓存文件才能重置。

旧版本把缓存平铺在 `state/cache/` 顶层；首次运行新版会自动迁移到
上述布局（幂等，且会清理迁移中断留下的半截文件）。

单元状态：

| 状态 | 含义 | 下次运行 |
| --- | --- | --- |
| `done` | 已成功归档 | 跳过 |
| `unavailable` | 源站与 archive.org 均不可得 | 跳过（`--recheck-unavailable` 可重探） |
| `failed` | 抓取出错 | 自动重试 |
| `skipped` | 按策略跳过 | 跳过 |

**不可信的 404**：小站的 widget 后端时不时对**确实存在**的页面返回 404
（同一个地址几分钟后又正常，页面里还会渲染出字面量 `<img src="None">`）。
这种 404 一个字都不写进缓存，本次先用一次强制的复查请求确认；仍然只拿到 404 的，
按 `failed` 记（而不是 `unavailable`），同一地址最多重试
`RETRYABLE_MAX_ATTEMPTS`（3）次才落进 `data/unavailable.md` ——
源站的抖动不该被固化成归档里的一个空洞。受影响的域名由
`Config.untrusted_404_hosts` 指定。

三种终态（`done` / `unavailable` / `skipped`）都由**阶段执行器**统一保护：
handler 主动标记后，兜底逻辑不会再把它改写成 `done`。
（早期版本用 `is_done` 判断，会把 `unavailable` 覆盖成 `done`，
于是 `--recheck-unavailable` 永远筛不出这些条目、不可访问清单也会变空。）

### `--offline` 是只读模式

离线运行时，"缓存未命中"只说明**本地还没有这份数据**，并不代表源站不可得。
因此离线模式下的进度库是只读的：照常读取已有进度（已完成项照常跳过），
但任何标记都不落盘。

否则一次 `sync --offline` 就会把整站写成"原站不可访问"，
既污染进度、又让后续的 `--recheck-unavailable` 失去意义。

`report` 子命令同样是只读的 —— 一个查询命令不该反过来改写进度文件。

> 注意：离线运行仍会**重新生成站点产物**。若缓存不完整，产出的页面会带上
> "离线模式且无缓存"的提示块，`data/unavailable.md` 也会列出这些条目。
> 想要完整产物，请在缓存完整时使用离线模式，或直接联网跑一次。

### 评论也要能从产物里还原

评论是归档内容的一部分，因此 `_note_from_dict` / `_discussion_from_dict`
必须把 `comments` 一并还原。漏还原会在"日记已 `done`、本次被跳过"时
静默丢掉全部评论 —— 而评论去重正是依赖 `comment_id` 的。

### 解析器版本号（改动解析逻辑后无需手动 --force）

`progress.py` 里有一个 `PARSER_REVISION` 常量。**修改了选择器、转换规则或
生成逻辑后把它加一**，此前标记为 `done` 的单元会自动作废并重跑一遍。

原始 HTML 在磁盘缓存中，重跑只做本地解析，不会联网，也不需要 `--force`。

实测这个机制很必要：修好日记列表的选择器后，如果不作废旧进度，
那 144 篇日记会一直因为"已完成"而被跳过。

---

## 架构

```
                    ┌─────────────┐
                    │  cli.py     │  编排各阶段
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
      ┌───────────────┐         ┌──────────────┐
      │ discover.py   │         │ progress.py  │  进度与断点续接
      │ 结构发现       │         └──────────────┘
      └───────┬───────┘
              │
              ▼
      ┌───────────────┐    ┌──────────────┐    ┌─────────────────┐
      │ resolver.py   │───▶│ archive.py   │    │ transport.py    │
      │ 抓取+失败标记  │    │ IA 补足       │    │ Transport 协议   │
      └───────┬───────┘    └──────────────┘    └────────┬────────┘
              │                                          │
              │                          ┌───────────────┴───────────────┐
              │                          ▼                               ▼
              │                  ┌──────────────┐                ┌──────────────┐
              │                  │http_client.py│                │ browser.py   │
              │                  │curl_cffi+缓存 │                │Playwright    │
              │                  └──────────────┘                └──────┬───────┘
              │                                                         │
              │                                                  ┌──────┴───────┐
              │                                                  │  auth.py     │
              │                                                  │ 登录与会话    │
              │                                                  └──────────────┘
              ▼
      ┌───────────────┐    ┌──────────────┐
      │ parsers.py    │───▶│ html2md.py   │
      │ HTML→数据模型  │    │ HTML→MD      │
      └───────┬───────┘    └──────┬───────┘
              │                   │
              ▼                   ▼
      ┌───────────────┐    ┌──────────────┐    ┌─────────────┐
      │ index_map.py  │───▶│ emit.py      │───▶│ verify.py   │
      │ 源拓扑 / 引用  │    │ 统一结构投影  │    │ 校验        │
      └───────────────┘    └──────────────┘    └─────────────┘
```

### 各模块职责

| 模块 | 职责 | 实现方式 |
| --- | --- | --- |
| `config.py` | 站点常量、抓取参数、路径 | 全部可调参数集中于此，支持环境变量覆盖 |
| `transport.py` | 传输层抽象 | `runtime_checkable` Protocol，HTTP 与浏览器可互换 |
| `http_client.py` | HTTP 传输 | curl_cffi 指纹 + tenacity 退避 + 磁盘缓存 + 熔断 + 限速 |
| `browser.py` | 浏览器传输 | Playwright + 系统 Chrome，风控识别、资源拦截、page 回收 |
| `auth.py` | 登录与会话 | 手动登录 + `storage_state` 持久化（0600），工具不接触密码 |
| `archive.py` | Internet Archive 补足 | 仅用 CDX 接口（`/wayback/available` 会被限流） |
| `resolver.py` | 抓取 → 标记 → 补足 | 统一的页面解析入口，记录所有不可访问页面 |
| `discover.py` | 结构发现 | 房间 → 模块 → 分页枚举 ID 全集 |
| `parsers.py` | HTML → 数据模型 | 选择器集中，源站改版时定位点明确 |
| `html2md.py` | HTML → Markdown | 三段式流水线，见下 |
| `index_map.py` | 索引①/② → 人工引用视图 | 保留来源公告、组顺序、标签和重复引用；不决定文章源归属 |
| `media.py` | 图片归档 | 尺寸升级 + magic bytes 校验 + IA 兜底 |
| `progress.py` | 进度与断点续接 | 原子写入 + 阶段执行器 |
| `emit.py` | 产物生成 | 幂等，全部以 manifest 为输入 |
| `verify.py` | 校验 | 六项检查 + 构建期死链复查 |

### 为什么抽出 `Transport` 协议

`resolver.py` / `media.py` 只依赖 `Transport` 协议，不关心底层是 curl_cffi 还是浏览器：

```python
@runtime_checkable
class Transport(Protocol):
    cfg: Config
    stats: FetchStats
    def fetch(self, url, *, referer=None, force=False, raise_for_blocked=True) -> CachedResponse: ...
    def get_html(self, url, **kw) -> str: ...
    def get_bytes(self, url, **kw) -> bytes: ...
    def get_image(self, url, **kw) -> bytes: ...
    def close(self) -> None: ...
```

切换传输层时无需改业务代码，测试也可以直接注入假实现。
`Fetcher` 与 `BrowserFetcher` 都继承 `BaseFetcher`，共享限速、重试、缓存、
熔断与离线判定，只在 `_attempt()`（真正发请求）和 `_classify_blocked()`
（判定是否被拦截）两个点上分叉。

---

## 转换流水线（`html2md.py`）

豆瓣正文的形态很特殊：**裸文本 + 大量 `<br>`，没有 `<p>` 包裹**，图片被
`<div class="cc"><table>...` 骨架包着，所有外链都套了一层
`https://www.douban.com/link2/?url=...` 跳转。因此不能直接丢给转换库，采用三段式：

```
原始 HTML
  → [A] BeautifulSoup 预处理   拆表格骨架、清空 div、去 script
  → [B] markdownify 子类化转换  精确控制 <br> / <a> / <img> / <table>
  → [C] 正则后处理             归一化空行、清理空链接
```

关键映射：

| 输入 | 输出 |
| --- | --- |
| 单个 `<br>` | 换行（由 VitePress `markdown.breaks = true` 渲染为折行） |
| 连续 `<br><br>` | 段落分隔 |
| `<div class="cc"><table>...<img></table></div>` | 仅保留 `![](...)` |
| `link2/?url=<encoded>` | 解码为真实地址 |
| 站内 note 链接 | 重写为 VitePress 路由 `/notes/{id}` |
| 未归档的图片 | 丢弃（避免留裂图），并在清单里记录 |

回归测试在 `tests/test_html2md.py`，把每种形态都钉死了，源站改版时能立刻定位破坏点。

### 为什么 `docs/notes/{noteId}.md` 而不是中文标题

最长标题有 70+ 个中文字符（>210 字节），中文 slug 存在**超长与冲突**风险。
`noteId` 稳定、无冲突、天然支持增量同步；标题通过 frontmatter、sidebar 与搜索呈现。

---

## 测试

```bash
uv run python -m pytest scraper/tests -q          # 默认：零网络、零浏览器
uv run python -m pytest scraper/tests -m browser  # 只跑真实浏览器冒烟
uv run python -m pytest scraper/tests -m network  # 只跑真实联网测试
```

387 个单元测试（默认执行 386 个，浏览器冒烟被排除），覆盖：

| 文件 | 覆盖点 |
| --- | --- |
| `test_html2md.py` | 每种 HTML 形态的转换结果 |
| `test_parsers.py` | 所有选择器（用真实结构裁剪的片段） |
| `test_index_map.py` | 索引解析、分组归属、豆列识别 |
| `test_media.py` | 格式识别、尺寸升级、路径命名、临时文件不落 public/ |
| `test_progress.py` | 状态机、断点续接、阶段执行器、终态不被兜底覆盖、只读模式 |
| `test_http_client.py` | 缓存、限速、退避、熔断（假 session，不联网） |
| `test_browser_fetcher.py` | 风控识别、缓存、熔断、page 回收、UA 归一、路由拦截 |
| `test_auth.py` | 会话存取、权限 0600、脱敏、登录态判定 |
| `test_comments.py` | 评论解析（含去重） |
| `test_external_pages.py` | 站外页面 ID、目标枚举、解析、路由、sidebar |
| `test_emit.py` | frontmatter 转义、HTML 转义、提示块、sidebar、清单 |
| `test_verify.py` | 断链 / 图片 / frontmatter / 正文提取 |
| `test_sync_state.py` | 状态恢复、索引重建、按 ID 幂等合并、评论还原、离线只读 |

### 默认零网络是怎么保证的

不靠"记得注入 fake"的约定，而是由 `conftest.py` 里的 autouse 夹具**强制**：

- 未标记的测试里，`Fetcher._build_session` 被换成一个**允许构造、但任何 `.get()` 都抛
  `AssertionError`** 的占位会话 —— 所以"只是构造 `SyncContext`"的测试照常通过，
  而真的想联网的测试会立刻失败并提示正确做法；
- `PlaywrightDriver.__init__` 直接替换为抛错函数；
- `WaybackClient.cdx_search` 直接替换为抛错函数。

拦在"构造点"而不是 socket 层，是因为 curl_cffi 走 libcurl（C 层）、
Playwright 走独立子进程，**两者都绕过 Python 的 socket 模块** ——
拦 socket 只会给出虚假的安全感。

需要真实网络的测试必须显式标记 `@pytest.mark.network`（HTTP）或
`@pytest.mark.browser`（浏览器），两者都被 `addopts` 默认排除。

---

## 配置调参

常用环境变量（也可直接改 `config.py`）：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `USAGI_DELAY_MIN` / `USAGI_DELAY_MAX` | `5.0` / `7.0` | 请求间隔范围（秒），相当于默认档 |
| `USAGI_MAX_RETRIES` | `5` | 最大重试次数 |
| `USAGI_CIRCUIT_BREAK_AFTER` | `3` | 连续被拦截多少次后熔断 |
| `USAGI_IMPERSONATE` | `chrome` | curl_cffi 指纹 |
| `USAGI_ARCHIVE_ENABLED` | `0` | 是否启用 Internet Archive 补足 |
| `USAGI_OFFLINE` | `0` | 离线模式 |
| `USAGI_BROWSER` | `1` | 是否用无头浏览器抓取 |
| `USAGI_BROWSER_CHANNEL` | `chrome` | 用哪个浏览器（`chrome` / `msedge` / `chromium`） |
| `USAGI_BROWSER_HEADLESS` | `1` | 是否无头（`login` 子命令会强制有头） |
| `USAGI_BROWSER_LOGIN_TIMEOUT` | `300` | 等待登录的超时秒数 |
| `USAGI_BROWSER_PAGE_RECYCLE` | `200` | 每 N 次导航重建 page |
| `USAGI_BROWSER_NAV_TIMEOUT_MS` | `45000` | 浏览器导航超时（毫秒） |
| `USAGI_BROWSER_NORMALIZE_UA` | `1` | 把 `HeadlessChrome` 还原为真实版本号 |

**仓库体积**：相册默认存两份 —— 预览图用 `large`（约 618KB/张 × 498 张 ≈ 300MB），
原图是"查看原图"的 `raw` 尺寸（上传时的原文件，单张常在 1~3MB）。
只有照片详情页会给出这个链接，拿不到就不存，存多少完全由源站决定。
若体积敏感，把 `media.py` 里的 `ALBUM_SIZE_ORDER` 改以 `"photo"` 打头
（约 123KB/张）；原图不受这档偏好影响，不想存就在 `stage_photos` 里
去掉 `_archive_photo_original` 的调用 —— 预览图与页面都会自动退回到原样。
