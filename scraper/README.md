# scraper · 抓取工具

把[豆瓣小站「兔子山的小站」](https://site.douban.com/211330/)归档为本地 Markdown 与
VitePress 站点。**这是一套长期维护的工具，不是一次性脚本** —— 原站更新后重跑即可增量同步。

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
| `test` | 跑 HTML→Markdown 转换回归测试 |

全局参数：

| 参数 | 说明 |
| --- | --- |
| `--impersonate NAME` | curl_cffi 浏览器指纹，默认 `chrome`（可选 `chrome136`、`safari18_0` 等） |
| `--offline` | 只读本地缓存，绝不联网 |
| `--no-archive` | 禁用 Internet Archive 补足 |
| `--delay N` | 请求间隔下限（秒），默认 5 |
| `--limit N` | 每阶段最多处理 N 项（冒烟测试用） |
| `-v` / `-q` | 详细 / 安静日志 |

`sync` 专属参数：

| 参数 | 说明 |
| --- | --- |
| `--dry-run` | 只预估规模与耗时，不抓取 |
| `--i-have-read-robots` | 知情门槛，见下 |
| `--stages a,b,c` | 只跑指定阶段（`rooms,bulletins,notes,photos,albums,videos,forum,miniblog`） |
| `--force` | 忽略进度，强制重抓 |
| `--recheck-unavailable` | 重新探测此前标记为不可访问的页面 |
| `--no-emit` | 只抓取，不生成站点 |
| `--no-progress` | 关闭进度条 |

---

## 采集频次与合规

**抓取前请先读这一节。**

原站 `robots.txt` 为全量禁止：

```
# https://site.douban.com/robots.txt
User-agent: *
Disallow: /
```

`www.douban.com` 则是部分禁止，并附了一条 `# Crawl-delay: 5`。

因此 `sync` 要求显式传入 `--i-have-read-robots` 才会真正发起请求。本工具的策略是
**尽可能礼貌**：

| 措施 | 默认值 |
| --- | --- |
| 并发 | **单线程**，绝不并发 |
| 请求间隔 | `5.0 ~ 7.0` 秒随机抖动（尊重 `Crawl-delay: 5`） |
| 退避重试 | 指数增长 + 抖动，5s 起，最多 5 次 |
| 熔断 | 连续 3 次 `403/418` 立即停止并保存进度 |
| 缓存 | 同 URL 二次运行**零请求** |
| 增量 | 只抓新增内容，存量不重抓 |

并且**明确不做**以下事情：不轮换 UA、不轮换代理、不做指纹伪装、不并发轰炸。
固定使用一个浏览器指纹（`curl_cffi` 的 `impersonate="chrome"`）只是因为服务端会对
TLS 指纹做校验 —— 裸 `requests` 的首个请求会连续收到 `SSLEOFError`。

请仅将归档结果用于个人保存与阅读，不要公开再分发。

### 熔断后怎么办

看到「已熔断停止」说明源站开始拒绝请求。建议**等待数小时**后重跑同一命令。
进度已保存，已完成的内容不会被重复请求。

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

这样做的好处：

- **隔离**：不同源站的缓存键空间天然分离，不会互相污染；
- **可维护**：可以按域名单独清理或检查，排查问题时定位明确；
- **可扩展**：日后接入新站点不会与既有缓存冲突。

每个条目由一对文件组成：`<sha1>.body`（原始响应体）与 `<sha1>.json`
（meta：原始 URL、状态码、Content-Type、抓取时间、内容 sha1）。
读取时会校验内容 sha1，损坏的缓存自动忽略并重新抓取。

旧版本把缓存平铺在 `state/cache/` 顶层；首次运行新版会自动迁移到
上述布局（幂等，且会清理迁移中断留下的半截文件）。

单元状态：

| 状态 | 含义 | 下次运行 |
| --- | --- | --- |
| `done` | 已成功归档 | 跳过 |
| `unavailable` | 源站与 archive.org 均不可得 | 跳过（`--recheck-unavailable` 可重探） |
| `failed` | 抓取出错 | 自动重试 |
| `skipped` | 按策略跳过 | 跳过 |

### 解析器版本号（改动解析逻辑后无需手动 --force）

`progress.py` 里有一个 `PARSER_REVISION` 常量。**修改了选择器、转换规则或
生成逻辑后把它加一**，此前标记为 `done` 的单元会自动作废并重跑一遍。

因为原始 HTML 都在磁盘缓存里，这次重跑**只走本地解析、不产生任何网络请求** ——
相当于免费地"用新解析器重刷全站"。这样就不必依赖使用者记得加 `--force`。

实测这个机制很必要：修好日记列表的选择器后，如果不作废旧进度，
那 144 篇日记会一直因为"已完成"而被跳过。

### 解析器版本号（改动解析逻辑后无需手动 --force）

`progress.py` 里有一个 `PARSER_REVISION` 常量。**修改了选择器、转换规则或
生成逻辑后把它加一**，此前标记为 `done` 的单元会自动作废并重跑一遍。

因为原始 HTML 都在磁盘缓存里，这次重跑**只走本地解析、不产生任何网络请求** ——
相当于免费地"用新解析器重刷全站"。这样就不必依赖使用者记得加 `--force`。

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
      ┌───────────────┐    ┌──────────────┐    ┌─────────────┐
      │ resolver.py   │───▶│ archive.py   │    │ http_client │
      │ 抓取+失败标记  │    │ IA 补足       │◀──▶│ 缓存/限速   │
      └───────┬───────┘    └──────────────┘    └─────────────┘
              │
              ▼
      ┌───────────────┐    ┌──────────────┐
      │ parsers.py    │───▶│ html2md.py   │
      │ HTML→数据模型  │    │ HTML→MD      │
      └───────┬───────┘    └──────┬───────┘
              │                   │
              ▼                   ▼
      ┌───────────────┐    ┌──────────────┐    ┌─────────────┐
      │ index_map.py  │───▶│ emit.py      │───▶│ verify.py   │
      │ 索引→分类      │    │ 产物生成      │    │ 校验        │
      └───────────────┘    └──────────────┘    └─────────────┘
```

### 各模块职责

| 模块 | 职责 | 关键设计 |
| --- | --- | --- |
| `config.py` | 站点常量、抓取参数、路径 | 全部可调参数集中于此，支持环境变量覆盖 |
| `http_client.py` | HTTP 传输 | curl_cffi 指纹 + tenacity 退避 + 磁盘缓存 + 熔断 |
| `archive.py` | Internet Archive 补足 | 仅用 CDX 接口（`/wayback/available` 会被限流） |
| `resolver.py` | 抓取 → 标记 → 补足 | 统一的页面解析入口，记录所有不可访问页面 |
| `discover.py` | 结构发现 | 房间 → 模块 → 分页枚举 ID 全集 |
| `parsers.py` | HTML → 数据模型 | 选择器集中，源站改版时定位点明确 |
| `html2md.py` | HTML → Markdown | 三段式流水线，见下 |
| `index_map.py` | 索引①/② → 分类 | sidebar 的唯一事实源 |
| `media.py` | 图片归档 | 尺寸升级 + magic bytes 校验 + IA 兜底 |
| `progress.py` | 进度与断点续接 | 原子写入 + 阶段执行器 |
| `emit.py` | 产物生成 | 幂等，全部以 manifest 为输入 |
| `verify.py` | 校验 | 六项检查 + 构建期死链复查 |

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
uv run python -m pytest scraper/tests -q
```

274 个单元测试，覆盖：

| 文件 | 覆盖点 |
| --- | --- |
| `test_html2md.py` | 每种 HTML 形态的转换结果 |
| `test_parsers.py` | 所有选择器（用真实结构裁剪的片段） |
| `test_index_map.py` | 索引解析、分组归属、豆列识别 |
| `test_media.py` | 格式识别、尺寸升级、路径命名 |
| `test_progress.py` | 状态机、断点续接、阶段执行器 |
| `test_http_client.py` | 缓存、限速、退避、熔断（假 session，不联网） |
| `test_emit.py` | frontmatter 转义、HTML 转义、提示块、sidebar、清单 |
| `test_verify.py` | 断链 / 图片 / frontmatter / 正文提取 |
| `test_sync_state.py` | 状态恢复、索引重建、按 ID 幂等合并 |

---

## 配置调参

常用环境变量（也可直接改 `config.py`）：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `USAGI_DELAY_MIN` / `USAGI_DELAY_MAX` | `5.0` / `7.0` | 请求间隔范围（秒） |
| `USAGI_MAX_RETRIES` | `5` | 最大重试次数 |
| `USAGI_CIRCUIT_BREAK_AFTER` | `3` | 连续被拦截多少次后熔断 |
| `USAGI_IMPERSONATE` | `chrome` | curl_cffi 指纹 |
| `USAGI_ARCHIVE_ENABLED` | `1` | 是否启用 Internet Archive 补足 |
| `USAGI_OFFLINE` | `0` | 离线模式 |

**仓库体积**：相册默认用 `large`（约 618KB/张 × 498 张 ≈ 300MB）。
若体积敏感，把 `config.py` 里的 `album_image_size` 改为 `"photo"`
（约 123KB/张，总量降至约 60MB）。
