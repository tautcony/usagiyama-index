# Phase 4 · 产物生成、校验与测试保障

[返回 index](../index.md) · [修复 checklist](../fix-checklist.md)

覆盖：`emit.py`（产物拼装、frontmatter、侧边栏、裸 HTML）、
`verify.py`（断链 / 图片 / 对账 / 抽查）、`scraper/tests/`（测试基建与覆盖缺口）、
`.github/workflows/deploy-docs.yml`。

分派：1 个 sub agent 独立探查本层；主 agent 亲自复跑其全部 P0/P1/P2 候选。

---

## 测试运行结果

```text
$ .venv/bin/python -m pytest scraper/tests -q
544 passed, 1 deselected in 1.04s

$ .venv/bin/python -m pytest scraper/tests -q --collect-only
544/545 tests collected (1 deselected) in 0.14s
```

说明：`uv run` 在本机沙箱下无法写 `~/.cache/uv`，改用仓库自带 `.venv`；
唯一被排除的是 `test_browser_fetcher.py::TestRealBrowser::test_launch_and_navigate`
（`@pytest.mark.browser`）。整体结论：套件**能跑、且快**，但**没有覆盖本次
发现的任何一个 P0/P1 的触发路径**（见 [P4-P2-12]）。

**健康归档上 `verify` 的实跑结论（这是本 phase 最重要的发现）**：

```text
counts       passed=False  problems=1  data/notes.json 有 145 条，manifest 有 144 条
links        passed=True
images       passed=False  problems=3  albums/.DS_Store 不是有效图片（无法识别格式）…
formats      passed=True
dupes        passed=True
frontmatter  passed=True
Verifier.run() -> False        # → cmd_verify 退出码 1（cli.py:1953-1960）
```

即：**当前 HEAD 的健康归档，`npm run verify` 必然失败**，且两条都是假警报。

---

## Findings

### [P4-P1-1] `check_counts` 与 `data/notes.json` 的 `_meta` 口径不一致：数量对账在所有健康状态下恒失败

- **位置**：`scraper/verify.py:131-134`（直接 `read_json` 后 `len(data_notes)`）
  vs `scraper/cli.py:697-710`（`save_data` 的 `stamped()` 给 dict 注入 `_meta` 键）。
  对照 `cli.py:400-410`：`load_existing` 用 `payload_of` 剥掉 `_meta`，**verify 没有**。
- **触发条件**：任意一次 sync/emit 之后执行 `verify`。
- **影响**：`data/notes.json` 顶层有 145 个键（144 篇 + `_meta`），manifest 有 144
  → 恒报 `data/notes.json 有 145 条，manifest 有 144 条`；`Verifier.run()` 汇总
  `all(passed)` → `cmd_verify` 返回 1。**校验门在所有健康状态下都是红的**，
  运维一旦习惯"反正 verify 就是红的"，真正的 md 缺失/多余、评论缺口会被噪声淹没。
  仓库里 `data/verify-report.md` 从 14:01 的"通过"到 14:43（`c043b75` 引入 `_meta`
  之后）翻红，正好印证。
- **修复方向**：`verify` 复用 `cli.payload_of`（或按 `_meta` 白名单剔除）再比长度；
  必须补一条"数据健康 → 通过"的正向用例（`check_counts` 目前**一条测试都没有**）。
- **置信度**：高 · **证据类型**：真实仓库实跑（零写入）。

---

### [P4-P1-2] 内容抽查在无缓存时静默全部跳过并判通过；albums/photos/external 从不参与比对

- **位置**：`scraper/verify.py:448-520`。候选只在 `:461-463` 从 `manifest["notes"]` 取；
  `:474` 先 `result.checked += 1`，`:476-479` 在拿不到缓存时只追加一条 note 就 `continue`
  （**不 `add_problem`**）。
- **触发条件**：
  1. `scraper/state/cache/` 被 `.gitignore:22` 忽略 → **全新 clone / CI / 清过缓存**
     的机器上，每一次抽样都走"无原始 HTML 缓存，跳过比对"，`passed` 保持 True；
  2. `manifest["external"]`（含 `content_html`）与 albums 的 caption 从不参与比对。
- **影响**：唯一校验"正文/评论是否真的被抓对"的检查，在最需要它的环境里是空操作，
  却对外报告"内容抽查 通过（检查 5 项）"—— 典型的虚假校验通过。
  `checked` 还把跳过项计进去，夸大覆盖面。
- **修复方向**：缓存缺失记 problem（或至少区分退出码）；把 external 纳入候选
  （manifest 已含 `content_html`），albums 至少做 caption 抽比；
  `result.checked` 只在真正比对后自增。
- **置信度**：高 · **证据类型**：测试复现。
- **核验说明**：主 agent 用空 `cache_dir` 实跑真实 manifest：

```text
缓存为空时的内容抽查: passed = True | checked = 5 | problems = 0
   note: 抽查 649190492：无原始 HTML 缓存，跳过比对   （×5）
```

---

### [P4-P2-1] `emit_album` / `emit_home` 的裸 HTML 属性未走 `html_attr()`

- **位置**：`emit.py:360`（`<img src="{preview}"…`）、`emit.py:363`（`href="{full}"`）、
  `emit.py:533`（`<img src="{cover}">`）；对照同一函数内 `emit.py:353/357/359/367/528/529`
  对 `caption`/`tip`/`title` 都用了 `html_text`/`html_attr`，
  videos 页（`emit.py:700-704`）也都转义了。
- **触发条件**：`photo.local` / `photo.local_original` / 封面路径里出现 `"`。
  这些值来自磁盘文件名（`media.py:304/313`），文件名后缀取自源 URL
  （`media.py:280`），`correct_suffix`（`media.py:139-154`）在后缀不认识时**原样保留**。
- **影响**：属性 breakout，可向相册页注入任意 HTML 属性/标签
  （实测：`local='/media/albums/1/1.jpg"><img src=x onerror=alert(1)>'`
  → 产物里出现真实的第二个 `<img onerror=…>`）。
  从真实 HTML 端到端可达性依赖"未加引号的 `src` 且值里带 `"`"这类畸形输入，
  属低概率；但同文件既有的转义约定在这里被跳过，属防御纵深缺口。
- **修复方向**：`preview`/`full`/`cover`/`route` 一律经 `html_attr()`；
  并在 `media.py` 的文件名派生处做字符白名单（只允许 `[A-Za-z0-9._-]`）。
- **置信度**：高（注入成立）/ 中（端到端可达性）· **证据类型**：测试复现 + 静态路径。

---

### [P4-P2-2] 两处索引页链接文字漏转义方括号

- **位置**：`emit.py:635`（`notes/index.md` 的"尚子的房间"回退分区）、
  `emit.py:653`（`albums/index.md` 的相册列表）。
  对照 `emit.py:618/622/625`（同文件同函数里用了 `md_escape_link_text`）。
- **触发条件**：标题里含 `[` 或 `]`（例如 `C# [笔记] 标题`）。
- **影响**：生成 `- [C# [笔记] 标题](/notes/9)`，第一个 `]` 提前闭合链接文字，
  `](…)` 泄漏成可见文字、链接失效。当前语料 144 篇日记 + 6 个相册标题
  **均不含方括号**（主 agent 用 manifest 全量核对），属潜伏缺陷；
  但本项目是增量同步的，源站新增一篇带方括号标题的文章就会命中，
  而 VitePress 的 `ignoreDeadLinks: false` 只查死链、不查这种语法破损。
- **修复方向**：两处补 `md_escape_link_text(...)`，并加一条标题含 `[`/`]` 的用例。
- **置信度**：高 · **证据类型**：静态路径 + 语料全量核对。

---

### [P4-P2-3] `slug_anchor` 与 VitePress 的 slugify 规则不一致：首页 2/6 张分类卡片的锚点已经坏了

- **位置**：`emit.py:186-189`（`slug_anchor`：删掉所有非 `alnum` 字符）
  vs `emit.py:491-505`（首页 features 用 `link = f"/notes/#{anchor}"`）。
- **触发条件**：分组标题含全角标点（VitePress 会先 NFKD 归一，再把特殊字符**替换成 `-`**，
  而 `slug_anchor` 是**删掉**）。
- **影响**：实测（独立最小站点，`vitepress build` 后读 `<h2 id=…>`）：

  | 分组标题 | `slug_anchor` 产出 | VitePress 真实 id | 结果 |
  | --- | --- | --- | --- |
  | `轻音！系列` | `轻音系列` | `轻音-系列` | 断 |
  | `玉子市场＆玉子爱情故事` | `玉子市场玉子爱情故事` | `玉子市场-玉子爱情故事` | 断 |

  而 `docs/index.md:4` 里确实写着 `"/notes/#轻音系列"` 与
  `"/notes/#玉子市场玉子爱情故事"`，`docs/notes/index.md:58/75` 的实际锚点
  是 `轻音-系列` / `玉子市场-玉子爱情故事`。首页这两张卡片点了跳不到位置（静默坏链）。
  更根本的是覆盖面缺口：`check_links` 把 `#…` 整段切掉后只验文件在不在，
  VitePress 的 dead-link 检查也在解析前剥掉 `#`，且只收集 markdown 正文的链接
  —— **锚点、frontmatter（hero/features）、sidebar 三层都不被任何检查覆盖**。
- **修复方向**：`slug_anchor` 直接对齐 VitePress 的 slugify
  （NFKD + 去组合符/控制符 + 特殊字符 → `-` + 折叠/去首尾 `-` + 数字前缀 `_` + lower）；
  `check_links` 增加锚点校验；补一条"emit 的锚点集合 == 真实渲染出的 id 集合"的测试。
- **置信度**：高 · **证据类型**：测试复现（真实 VitePress 构建）+ 真实产物已坏。

---

### [P4-P2-4] `emit_board` 只给评论首行加 `> `，多段评论脱离引用块

- **位置**：`emit.py:747-758`（`:756` 为 `f"**{head}**\n\n> {text}"`）；
  对照 `emit.py:303-320`（笔记评论用逐行 `> ` 前缀，写法正确）。
- **触发条件**：任意 `content_html` 含两段或 `<br>` 的评论（`html2md.convert_br` → `\n`）。
- **影响**：`docs/board.md` 的评论边界丢失，评论里的 `## 标题` 会变成页面级标题、
  进入 outline 与搜索索引 —— 页面结构由外部内容决定。
  当前真实 `docs/board.md` 的 5 条评论都是单段，尚未触发，但触发条件很常见。
- **修复方向**：复用笔记评论的逐行引用渲染（抽一个 helper）。
- **置信度**：高 · **证据类型**：静态路径 + sub agent 复现。

---

### [P4-P2-5] `emit_external` 的 `archivedAt` 非幂等

- **位置**：`emit.py:403`（`"archivedAt": now_iso()[:10]`），
  对照 notes/albums 走 `_archived_at`（`emit.py:557-574`，保留旧值）。
- **触发条件**：跨天重复 emit。
- **影响**：每次跨天重新生成都会重写 `docs/external/*.md`，产生无意义 diff，
  破坏"emit 幂等"的可验证性。
- **修复方向**：external 也走 `_archived_at`。
- **置信度**：高 · **证据类型**：静态路径。

---

### [P4-P2-6] `emit_unavailable_report` 只转义 `detail` 里的 `|`，表格可被撑破

- **位置**：`emit.py:926`（只对 `detail` 做 `.replace("|","\\|")`）
  与 `emit.py:930-933`（`url`/`context`/`label` 原样入行）。
- **触发条件**：`UnavailableRecord(url="https://x/?a|b", context="分组|名")`。
- **影响**：`data/unavailable.md`（人工核对补抓清单）表格错乱
  （一行被撑成 7 列）。现有测试 `test_pipe_in_detail_escaped` 恰好只断言
  被转义的那一个字段，给出"表格注入已处理"的错误印象。
- **修复方向**：对入表的每个字段统一转义（`|`→`\|`、换行→`<br>`）。
- **置信度**：高 · **证据类型**：静态路径 + sub agent 复现。

---

### [P4-P2-7] `check_links` 的路径解析缺陷：显式 `.md` 被拼成 `.md.md`（误报），相对链接按 `docs/` 根解析（误报 + 漏报）

- **位置**：`verify.py:179-199`（`_resolve_route` 无条件 `docs / f"{candidate}.md"`）、
  `verify.py:201-224`（`check_links` 不传链接所在目录）。
- **触发条件与影响**：
  1. `[b](/notes/b.md)` 且 `docs/notes/b.md` 存在 → 报
     `（期望 notes/b.md.md）` 假红。**本 phase 实跑时已复现**：审查期间新增的
     `docs/review-2026-09-30/` 让 `check_links` 多报 19 条，全部是 `.md.md` 形式；
  2. `docs/guide/deep/a.md` 里写 `[b](../b.md)`，真实目标 `docs/guide/b.md` 存在
     → 报 `（期望 ../b.md.md）`；
  3. 反向漏报：`docs/guide/a.md` 写 `[b](./b)`，`docs/guide/b.md` **不存在**
     但 `docs/b.md` 存在 → 判通过。
- **影响**：任何手写/新增到 `docs/` 的 Markdown（相对链接、`.md` 后缀是 VitePress
  官方写法）会制造假红，或因解析错基准而漏掉真死链。
- **修复方向**：以"链接所在文件的目录"为基准；先按原样、再按补 `.md`、再按
  `index.md` 的顺序探测；对已带 `.md`/`.html` 后缀的目标不要重复追加。
- **置信度**：高 · **证据类型**：测试复现（含本仓库实跑）。

---

### [P4-P2-8] `check_images` 把 `.DS_Store` 当图片：本机 `verify` 的"图片完整性"必然失败

- **位置**：`verify.py:236-248`（`rglob("*") + is_file()` 即检查），
  对照 `verify.py:272`（`check_media_formats` 有 `path.name.startswith(".")` 跳过）。
- **触发条件**：`docs/public/media/` 下存在 macOS 元数据文件
  （当前仓库有 3 个：`albums/.DS_Store`、`albums/13432051/.DS_Store`、
  `albums/13433748/.DS_Store`；`.gitignore:26` 已忽略但既有文件仍在）。
- **影响**：本机 `verify` 必报 3 个"不是有效图片"；CI 在 Linux 上不会出现
  `.DS_Store` → **本机红、CI 绿，结果不可复现**。`check_duplicate_images`
  也把点文件读进内存参与哈希。
- **修复方向**：三个媒体检查统一跳过点文件（或只对已知图片后缀做完整性校验）。
- **置信度**：高 · **证据类型**：真实仓库实跑。

---

### [P4-P2-9] 对账与清理只覆盖 notes：albums/external 的残留页面永不被发现

- **位置**：`verify.py:136-143`（只 `notes_dir.glob("*.md")`）；
  `cli.py:1622-1705`（`generate_site` 只写不删）。
- **触发条件**：删除/重命名某个相册或站外页面后重新 emit。
- **影响**：`docs/albums/999-STALE.md`、`docs/external/topic-999-STALE.md`
  这类旧页面会随 `docs/` 一起发布，而 `check_counts` 仍判通过
  （notes 有双向对账兜底，albums/external 没有）；
  `data/albums.json`/`external.json` 的计数也从不与 manifest 对账。
- **修复方向**：把 albums/external（以及 videos/board 等生成页）纳入同一套
  manifest↔data↔磁盘三方对账；或在 emit 前显式清理被删条目。
- **置信度**：高 · **证据类型**：静态路径 + sub agent 复现。

---

### [P4-P2-10] `check_content_sample` 的抽样不可复现

- **位置**：`verify.py:468`（`random.sample(candidates, …)`，无种子）。
- **影响**：同一份归档跑两次 `verify` 可能一次过、一次不过（相似度阈值 0.9，
  `verify.py:515`）；报告只写标题、不记录抽样集合，失败后无法原样重放，
  也难以判断是"真的退化"还是"抽到了边界样本"。
- **修复方向**：把抽样结果（note_id 列表）写进报告；或支持 `--seed` /
  固定顺序抽样（按 id 排序后等距取样）。
- **置信度**：高 · **证据类型**：静态路径。

---

### [P4-P2-11] 测试守卫 `forbid_real_transport` 有绕过口子，且守卫失败会被业务代码吞掉

- **位置**：`tests/conftest.py:58-121` 只 patch `Fetcher._build_session`
  与 `PlaywrightDriver.__init__` 两个**调用点**。绕过口子：
  1. `auth.py:178-183` `check_session()` 默认自建 `curl_cffi.requests.Session`
     并 `session.get(SESSION_PROBE_URL)`；`auth.py:212` 的 `except Exception`
     还会把守卫的 `AssertionError` 变成"会话校验出错"返回；
  2. `browser.py:476-488` `detect_chrome_ua()` 直接 `sync_playwright().launch(...)`，
     `except Exception` → 回退配置 UA；
  3. `auth.py:284-288` `run_login_flow()` 直接 `sync_playwright()`（**有头**），
     目前靠 `test_auth.py` 自己 monkeypatch 才安全，守卫并不兜底。
  另外 `resolver.py:293-299` 的 `resolve_optional` 宽 `except Exception`
  会把守卫的 `AssertionError` 降级成一条 warning 并返回 `None`。
- **触发条件**：未来任何人写 `check_session(cfg)` / `detect_chrome_ua(cfg)` 的测试。
- **影响**：`conftest.py:5-7/60-66` 承诺的"强制零网络/零浏览器"不成立：
  这些路径会真的构造 Session、真的请求 `www.douban.com/mine/`、真的拉起 Chrome，
  而且失败还可能被静默吞掉。
- **修复方向**：把守卫做成"传输层统一出口"——patch `curl_cffi.requests.Session`
  （类级）与 `playwright.sync_api.sync_playwright`（模块级）；
  宽 `except` 里对 `AssertionError` 重新抛出；再加一条"守卫自测"
  （故意走直连路径并断言它抛错）。
- **置信度**：高（口子均为静态事实；`check_session` 与 `resolve_optional`
  已由 sub agent 用反向探针复现）· **证据类型**：静态路径 + 测试复现。

---

### [P4-P2-12] 覆盖缺口：本次全部 P0/P1 都没有测试拦住，且 CI 从不跑 pytest / verify

- **位置**：`scraper/tests/`、`.github/workflows/deploy-docs.yml`（只有
  `npm ci` → `docs:build` → 自动 deploy，没有 test job，也没有 verify）。
- **缺口清单**（每条都对应一个已确认缺陷）：
  1. [P3-P0-1]/[P3-P0-2]：没有任何用例把实体化/带 `>` 的危险 payload 喂给
     `html_to_markdown` 并断言输出不含裸标签（`test_html2md.py:37-58` 反而断言了
     `<…>` 包裹是"对的"）；
  2. [P2-P0-1]：没有用例**经 `StageRunner`** 驱动 `record_source_failure(retryable=True)`
     （`test_sync_state.py`/`test_progress.py` 都直接调函数 —— 正是 P0 的藏身处）；
  3. [P2-P0-2]：没有"已归档条目在源站失败一次后 data/docs 不被清空"的用例；
  4. [P2-P0-3]：没有"渲染阶段抛异常 / 非 SIGINT 终止时 progress 与 data 一致"的用例；
  5. [P2-P1-1]：没有 `sync --offline`（非 dry-run、有缓存）能走通的用例；
  6. [P2-P1-2]：没有"相册列表页失败不得 mark_done"的用例；
  7. [P4-P1-1]：`check_counts` **一条测试都没有**；
  8. [P4-P1-2]：没有"无缓存时抽查不得判通过"、也没有 external/albums 参与比对的用例；
  9. [P1-P1-1]：没有"图片层熔断必须冒泡"的用例；
  10. [P4-P2-3]：`slug_anchor` 只有一条 `slug_anchor("聲之形") == "聲之形"`，
      恰好是两套规则一致的输入，等于没测。
- **影响**：P0/P1 全部回归都无法被自动拦住，而部署是 push 即发。
- **修复方向**：按上面 10 条补失败路径用例；CI 增加 `pytest` 与 `verify` 步骤
  （verify 至少在 P4-P1-1/2、P4-P2-8 修好后以"红即阻断部署"运行）。
- **置信度**：高 · **证据类型**：静态路径 + 测试运行统计。

---

### [P4-INFO-1] `Note.index_order` 是死状态

`cli.py:1640` 写入、`models.py:142` 定义、`cli.py:900` 还原，但**全仓库没有任何
排序读取它**。分类内顺序实际由 `emit_sidebar`/`emit_notes_index` 直接遍历
`IndexGroup.entries`（`emit.py:818`、`emit.py:611`）保证，因此**行为正确**，
只是多了一份不参与决策的持久化字段。可删除或补上排序用途。

---

### [P4-INFO-2] 测试基建的优点（正面结论）

- `conftest.forbid_real_transport`（`conftest.py:58-105`）把拦截点放在
  "创建 session / 启动 driver"而不是拦 socket，理由正确（libcurl 与 Playwright
  都绕过 Python socket 层），覆盖了大部分"未标记测试偷偷联网"的路径
  （绕过口子见 P4-P2-11）。
- `forbid_archive_network`（`conftest.py:108-121`）单独拦住 `cdx_search`。
- `cfg` fixture（`conftest.py:30-50`）把所有路径指向 `tmp_path` 并把延时归零；
  `Config` 是 `frozen=True` 且字段全是标量/tuple，**测试间无共享可变状态**。
- 全仓库只有 1 个 `network`/`browser` 标记用例，没有 `skip`/`xfail` 掩盖路径。

---

### [P4-INFO-3] 历史遗留 SUG 复核（生成/校验侧）

| 历史项 | 现状 | 结论 |
| --- | --- | --- |
| SUG-17 `emit.py` 重复路由解析 | `_resolve_entry_route` 已抽出（`emit.py:576-587`）；`emit_notes_index`/`emit_sidebar` 残留的是**展示**分支重复，行为差异是有意设计 | 复核通过 |
| SUG-21 `check_content_sample` 只抽 `ok` 笔记 | 已修（`verify.py:457-463` 改看 `content_html` 是否存在，ARCHIVED 已纳入）；albums/photos/external 仍缺 → [P4-P1-2] | 部分修复 |
| SUG-22 miniblog/rooms 无条件 `mark_done` | 已修（均经 `StageRunner` + `is_terminal` 守卫） | 复核通过 |
| SUG-23 photos/albums 的 `--limit` 语义 | 部分修复，仍不一致 → [P2-P2-1](phase-2-orchestration.md) | 未完全修复 |

---

## 残留疑点

1. **`check_frontmatter` 的 JSON 兜底很脆**：`json.loads("{" + block.replace("\n", ",") + "}")`
   对"合法 JSON 但非法 YAML"或反之的输入会静默走逐行解析、只看 key 是否存在
   → **不会发现 frontmatter 根本不是合法 YAML**，要等 VitePress 构建才炸。
2. **`Verifier.run()` 无逐项异常隔离**：`manifest.json` 被换成合法 JSON 数组等畸形
   输入时 `check_counts` 会 `AttributeError` 直接冒泡，报告完全不生成。
3. **`emit_home` 硬编码 `/albums/13432051`**（`emit.py:480`）：该相册当前存在，
   但无存在性守卫；一旦删除，首页会出现死链，而 verify（不读 frontmatter）与
   VitePress（dead-link 只看 markdown 正文）都不会报。
4. **`FALLBACK_CATEGORY` 命名冲突**：若原站索引里出现名为"尚子的房间"的分组，
   `generate_site` 会把该组条目同时算进 `fallback_ids`，输出两个同名分组。
   当前真实分组列表里没有该名字。
5. **`config.mts` 的 `defuseVueBraces` 对 `code_inline` 无效**：实测
   `` md.render('`{{ (}}`') `` → `<code>{{ (}}</code>`，Vue 编译报错 → 整站构建失败。
   真实归档里未找到带不配对花括号的行内代码实例，故列为疑点。

---

## 漏检复盘（本层已主动排查、未发现新问题的模式）

- **YAML frontmatter 转义**：`yaml_value`（`emit.py:68-88`）对任何"非纯 ASCII 标识符"
  走 `json.dumps`，`---`、换行、冒号、引号、`#` 都无法越出标量；
  `_PLAIN_SCALAR_RE` 的"首字符必须是字母"挡住了数字/日期被 YAML 重新解释。
  **未发现** frontmatter 注入。
- **`html_text`/`html_attr` 对 `{{ }}` 的防护有效**：`&#123;` 在 Vue 模板编译前
  不会被还原成 `{`，实测编译成静态字符串而非插值表达式。
  问题只出在"没走 `html_text` 的地方"（P3-P0-1/P4-P2-1）。
- **重复 ID**：manifest/data 以 ID 为 dict key，`merge_by`（`cli.py:773-792`）
  按 key 去重且会修历史重复 → 不会产生重复页面；有测试覆盖。
- **`emit_sidebar` 的空/缺失分类**：空分组不产出空 items（`emit.py:832`），
  未归档条目不带 `link`（正确规避 VitePress 的无效路由），fallback 分组
  `collapsed=True`；无分类/无相册时只是空数组，不产生非法 TS。
- **verify 的退出码语义**：`run()` 汇总 `all(passed)` → `cmd_verify` 返回 0/1，
  语义正确；问题在"内容"与"假警报"（P4-P1-1/2、P4-P2-8）。
