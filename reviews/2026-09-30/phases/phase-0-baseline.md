# Phase 0 · Baseline

[返回 index](../index.md) · [修复 checklist](../fix-checklist.md)

## 审查对象与范围

- **对象**：`scraper/` 全部 Python 模块（约 9,000 行源码 + 约 6,000 行测试），
  外加与产物安全直接相关的 `docs/.vitepress/config.mts`、`docs/.vitepress/theme/lightbox.ts`。
- **不含**：`docs/` 下的归档内容本身（只作为证据语料）、`data/`（只读证据）、`node_modules/`、`.venv/`。
- **深度**：`systemic`（跨模块）。审阅基准 commit：`94b1950`（`main`），working tree 仅
  `data/progress-report.md` 有改动（与代码无关）。
- **日期**：2026-09-30。

## 技术栈与运行方式

| 项 | 值 |
| --- | --- |
| 语言 | Python ≥ 3.13（`uv` 管理，`.venv` 已就绪） |
| 传输层 | `curl_cffi`（TLS 指纹）+ Playwright 驱动系统 Chrome |
| 解析 | BeautifulSoup4 + lxml + markdownify |
| 重试 | tenacity |
| 产物 | VitePress 1.6.4 静态站 |
| 测试 | pytest，544 通过 / 1 取消（默认排除 `network`、`browser` 标记） |

验证命令与结果：

```bash
# uv 在本机沙箱下无法写 ~/.cache/uv，改用仓库自带 venv
.venv/bin/python -m pytest scraper/tests -q
# → 544 passed, 1 deselected in 1.04s
```

## 分层与 phase 划分

本仓库不是前端/后端式分层，而是「抓取工具链」。按**职责**映射：

| 通用分层 | 本仓库模块 | phase |
| --- | --- | --- |
| 接入 / 边界 | `cli.py` 参数面、`discover.py` 站点发现、`transport.py` | P2 |
| 应用编排 | `cli.py` stage 编排、`SyncContext`、`resolver.py`、`progress.py` | P2 |
| 领域与状态 | `models.py`、`index_map.py`、`progress.py` 状态机 | P3 |
| 基础设施与集成 | `http_client.py`、`browser.py`、`auth.py`、`archive.py`、`media.py`、`util.py` | P1 |
| 平台与运行时 | `config.py`、`ensure_dirs`、Playwright 生命周期 | P1 |
| 横切保障 | 缓存、限速、熔断、日志、异常处理、路径与转义 | P1 / P3 / P4 |
| 产物与校验 | `emit.py`、`html2md.py`、`verify.py`、`.vitepress` 主题 | P3 / P4 |
| 测试与验证 | `scraper/tests/`、`conftest.forbid_real_transport` | P4 |

并行分派（4 个独立 sub agent，互不重叠）：传输/基础设施层、编排/枚举层、
解析/转换层、生成/校验/测试层。主 agent 自行复读核心调用链并核验全部候选发现
（见 [agent-findings.md](../agent-findings.md)）。

## 已知背景与历史结论对照

仓库曾在 2026-09-15 做过一次审查，产物 `scraper/REVIEW-FINDINGS.md` 已在
`54b50f6` 中被删除，其内容可由 git 取回。历史状态：

- **CRIT-1 ~ CRIT-4、WARN-5 ~ WARN-13 已修复**（对应提交 `f2f606c`、`9997ff5`、`8089994`）。
  本次审查**不重复报告**这些已修复项，但会检查其修复是否完整（例如 CRIT-1 的兜底
  只覆盖了 stage 循环，未覆盖 emit 阶段 —— 见 [phase-2](phase-2-orchestration.md)）。
- **SUG-14 ~ SUG-23 当时未处理**。本次逐条复核其现状，结论记入对应 phase 的
  「历史遗留复核」小节。

## 本次审查优先排查的高风险类型（写下来避免漏检）

1. 默认分支 / 未知输入 / 非法状态（参数、分页字段、图片格式）
2. 异步失败路径与异常传播（熔断异常被杀掉、emit 阶段无兜底）
3. 持久化与派生状态之间的**半完成状态窗口**
   （`progress.json` 已 `done` 而 `data/*.json` 还是旧快照）
4. 内容渲染链路（不可信 HTML → Markdown → Vue 模板 → 静态 HTML）
5. 隐式协议：缓存键、`sha1`、`Content-Type`、ID 正则、`_meta` 包装

## 语料事实（用于判定可达性）

- `docs/notes/*.md` 共 144 篇，`docs/albums/*.md` 6 个，`docs/external/*.md` 1 个。
- `manifest.json`：523 张照片、275 条评论、12 条视频、0 条 unavailable。
- 归档正文中**确实存在**被源站转义的 HTML（`&lt;…&gt;`），生成的 Markdown 会把它
  还原成裸 `<…>`，例如 `docs/notes/583976644.md:19` 的 `<小学生>`、
  `docs/notes/319279183.md:194` 的 `<École=学校>`。这是
  [P3-P0-1](phase-3-parsing-rendering.md) 可达性的直接证据。

## 输出位置说明

本次报告落在仓库根的 **`reviews/2026-09-30/`**，而不是 skill 默认的
`docs/review-YYYY-MM-DD/`。原因：本仓库的 `docs/` 是**已发布的 VitePress 站点根目录**，
把审查 markdown 放进去会被 `docs:build` 当成站点页面一起构建和发布。
实测：放进 `docs/` 期间 `verify` 的 `check_links` 多报 19 条 `.md.md` 假红、
`check_frontmatter` 多报 5 条"缺少 frontmatter"；移出后两者恢复通过。

## 未覆盖 / 限制

- 未做联网抓取、未启动真实浏览器；所有结论均为离线静态分析 + 离线复现。
- 未整体重建 VitePress 站点（`npm run docs:build`）；XSS 结论使用**独立最小站点**
  在仓库内构建验证，探针已删除。
- 未审计 `docs/` 归档内容自身的准确性，也未逐篇校对 144 篇译文。
