# 兔子山的小站 · 归档站

[原站](https://site.douban.com/211330/)（豆瓣小站「兔子山的小站」，山田尚子作品专题站）
的**完整本地化归档**，以 VitePress 重新组织呈现。

归档内容：

| 类型 | 数量 | 说明 |
| --- | ---: | --- |
| 日记 / 文章 | 144 篇 | 访谈译文、演出分析、导演寄语等正文 |
| 相册 | 6 个 / 498 张 | 海报墙、幕后周边、纪念册等 |
| 公告栏 | 7 条 | 含站长手工编排的「索引①/②」分类目录 |
| 视频 | 约 20 条 | 正片在优酷，仅归档缩略图与链接 |
| 留言板 / 广播室 | 1 帖 / 若干动态 | 论坛与日记评论均为静态渲染，可完整归档 |
| 站外页面 | 索引中指向豆瓣主站的条目 | 需登录，归入 `/external/` 路由 |

原站由 **羽音** 于 2013-05-01 创建。

---

## 设计要点

- **完全本地化**：正文与图片全部离线保存，不依赖任何外部资源。
- **保留站长编排**：侧边栏沿用原站「索引①/②」的分类结构，
  而不是按抓取顺序平铺 144 篇文章。
- **可长期维护**：抓取脚本支持增量同步，原站更新后重跑即可，
  已完成内容不会重复请求（见下）。
- **缺失内容显式标记**：无法访问的页面会在页面上显示提示块，
  并汇总到 `data/unavailable.md`。
- **真实的浏览器行为**：页面请求走无头 Chrome（Playwright 驱动系统已装的
  Chrome），以应对原站的反爬措施；登录由使用者手动完成，工具只保存会话。

---

## 快速开始

### 环境要求

- Node.js ≥ 18
- Python ≥ 3.13 与 [uv](https://docs.astral.sh/uv/)

### 安装

```bash
npm install
uv sync
```

### 抓取并生成站点

```bash
# 1. 先看规模与耗时预估（不抓取）
npm run sync:dry

# 2.（可选）先登录：有些内容未登录拿不到，工具全程不接触你的密码
npm run login

# 3. 正式抓取（首次约 1500 次请求，按 5~7 秒间隔约需 2~3 小时）
npm run sync -- --i-have-read-robots
```

抓取默认走**无头浏览器**（Playwright 驱动系统已装的 Chrome），
因为原站有反爬措施，纯 HTTP 会拿到 403 或跳转到风控页。
图片仍走 HTTP —— 静态资源不需要执行 JS。

### 预览与构建

```bash
npm run docs:dev      # 本地预览 http://localhost:5173
npm run docs:build    # 生产构建（会独立复查一遍死链）
npm run docs:preview  # 预览构建产物
```

### 校验归档结果

```bash
npm run verify
```

---

## 日常维护

### 原站更新后同步

直接重跑同一条命令即可。脚本会：

1. 重新枚举原站的内容 ID 全集；
2. 与 `scraper/state/manifest.json` 比对；
3. **只抓新增内容**，存量走本地缓存（零网络请求）；
4. 重新生成受影响的页面与侧边栏。

```bash
npm run sync -- --i-have-read-robots
```

### 中断后续跑

任意阶段被 Ctrl-C、断网或熔断打断后，**重新执行同一命令**即可：

- 已抓页面 → 命中 `scraper/state/cache/<域名>/`，不发请求
- 已完成单元 → 由 `scraper/state/progress.json` 跳过
- 已下载图片 → 按文件存在 + 格式校验跳过

进度报告：`npm run report`

### 只重新生成站点（不联网）

改了模板或想调整分类时，无需重新抓取：

```bash
npm run emit
```

`npm run sync -- --offline` 则是"只读本地缓存重跑一遍解析"，
它**不会改写进度文件**（离线时的缓存未命中只说明本地没有数据，
不代表源站不可得）。

### 重新探测此前不可访问的页面

```bash
npm run sync -- --i-have-read-robots --recheck-unavailable
```

### 改了抓取或转换逻辑之后

把 `scraper/progress.py` 里的 `PARSER_REVISION` 加一即可。旧进度会自动作废、
用新逻辑重刷全站，而原始内容都在本地缓存里，**不会产生额外网络请求**。

### 登录会话过期后

```bash
npm run login:check   # 只校验，不开浏览器
npm run login         # 重新登录并覆盖会话文件
```

会话保存在 `scraper/state/douban.auth.json`（权限 `0600`，已 gitignore）。
它等同登录凭据，**不要提交、不要分享**。

---

## 目录结构

```
├── scraper/                     抓取工具（Python，长期维护）
│   ├── config.py                站点常量、抓取参数、路径布局
│   ├── transport.py             传输层协议（HTTP / 浏览器可互换）
│   ├── http_client.py           指纹模拟 + 限速 + 退避 + 缓存 + 熔断
│   ├── browser.py               无头浏览器传输 + 风控识别 + 资源拦截
│   ├── auth.py                  登录流程与会话持久化（不接触密码）
│   ├── archive.py               Internet Archive 补足
│   ├── resolver.py              抓取 → 失败标记 → 归档补足
│   ├── discover.py              站点结构发现与分页枚举
│   ├── parsers.py               HTML → 结构化数据
│   ├── html2md.py               HTML → Markdown
│   ├── index_map.py             索引①/② → 分类映射
│   ├── media.py                 图片归档与完整性校验
│   ├── progress.py              进度记录与断点续接
│   ├── emit.py                  产物生成
│   ├── verify.py                归档校验
│   ├── cli.py                   命令行入口
│   ├── tests/                   369 个单元测试（默认零网络、零浏览器）
│   └── state/                   运行状态
│       ├── cache/<域名>/        HTML / 图片原始响应缓存
│       ├── progress.json        单元级进度（断点续接）
│       ├── manifest.json        内容级单一事实源
│       └── douban.auth.json     登录会话（0600，gitignore）
├── data/                        中间产物与报告
│   ├── notes.json  albums.json  index.json  ...
│   ├── unavailable.md           不可访问内容清单
│   ├── sync-report.md           同步报告
│   └── verify-report.md         校验报告
└── docs/                        VitePress 站点
    ├── .vitepress/
    │   ├── config.mts
    │   ├── sidebar.generated.mts   ← 由索引①/② 生成
    │   └── theme/custom.css
    ├── public/media/            全部本地化图片
    ├── index.md  about.md  videos.md  board.md  broadcast.md
    ├── notes/{noteId}.md        144 篇
    ├── albums/{albumId}.md      6 个相册
    └── external/{pageId}.md     站外页面（登录后补抓）
```

---

## 已知的内容缺失

归档过程中有些内容**确实拿不到**，页面与清单里都会显式标注，不做静默丢弃：

| 情况 | 原因 | 处理 |
| --- | --- | --- |
| `www.douban.com/topic/*` 访谈 | 未登录会 302 到风控页 | 登录后由 `main` 阶段补抓；仍拿不到则标记「需登录」并尝试 Internet Archive |
| 部分日记的 `www.douban.com/note/*` | 主站 302 跳转反爬页 | 优先走小站镜像路径 `site.douban.com/211330/widget/...` |
| 视频正片 | 托管在优酷 | 归档标题 + 缩略图 + 外链 |

不可访问页面会自动尝试从 [Internet Archive](https://web.archive.org/) 取历史快照补足
（默认关闭，用 `--archive` 开启），成功补足的页面会显示快照时间与原始链接。
完整清单见 `data/unavailable.md`。

---

## 版权

原站内容版权归原作者与译者所有。本仓库仅为个人保存与阅读用途的归档。
