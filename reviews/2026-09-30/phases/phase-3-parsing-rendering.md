# Phase 3 · 解析与内容渲染层

[返回 index](../index.md) · [修复 checklist](../fix-checklist.md)

覆盖：`parsers.py`、`html2md.py`、`models.py`、`index_map.py`，
以及渲染落点 `emit.py` 的正文转换路径、`docs/.vitepress/config.mts`、
`docs/.vitepress/theme/lightbox.ts`。（`media.py` 归 [phase 1](phase-1-transport-infra.md)，
`emit.py` 的产物拼装归 [phase 4](phase-4-emit-verify-tests.md)。）

分派：1 个 sub agent 独立探查本层；主 agent 亲自复跑其 P0/P1 与关键 P2 候选。

---

## Findings

### [P3-P0-1] 归档正文里的转义标签被还原成裸 HTML，导致生成站点存储型 XSS

- **位置**：`scraper/html2md.py:255-287`（`html_to_markdown`，关键项 `escape_misc=False` 在 `html2md.py:275`；
  `DoubanConverter` 没有文本转义钩子）；渲染落点 `emit.py:245`（日记正文）、
  `emit.py:312`（评论）、`emit.py:414`（站外页）、`emit.py:671/740/751`（公告/论坛）；
  旁证 `docs/.vitepress/config.mts:19-33`（`defuseVueBraces` 只处理 `{}`）
  与 VitePress 默认 `MarkdownIt({ html: true })`。
- **触发条件**：源站页面里的**文本节点**含有被 HTML 转义的标签 —— 豆瓣会把用户输入
  转义后再渲染，所以某人在评论/日记里写 `<img src=x onerror=alert(1)>`，
  源站存成 `&lt;img src=x onerror=alert(1)&gt;`。链路：
  1. `BeautifulSoup` 解析时把实体解码成文本 `<img …>`；
  2. `markdownify`（`escape_misc=False`）**不转义 `<` / `>`**，原样写进 Markdown；
  3. VitePress 的 markdown-it 以 `html: true` 运行，把这段当**原始 HTML** 交给
     Vue 模板编译器；
  4. 编译结果里 `onerror` 不是 Vue 事件 prop（`isOn()` 要求第 3 个字符非小写字母），
     于是走 `setAttribute('onerror', …)`，浏览器按内容属性编译成可执行 handler。
- **影响**：**存储型 XSS**。归档内容全部来自外部（豆瓣评论、讨论帖、站外页面），
  任何能在评论区打字的人都能在发布站点上注入可执行 HTML；
  `.github/workflows/deploy-docs.yml` 只做 `docs:build` 后直接发布，
  **没有任何净化环节**。同类 payload 还有 `<a href="javascript:…">`
  （绕过 `convert_a` 里已修的 `sanitize_markdown_url`，因为这段根本不走链接转换器）
  与 `<iframe srcdoc="…">`。次要影响：`<img src="相对路径">` 会被 VitePress 的
  `transformAssetUrls` 当成**模块导入**，直接让 `docs:build` 以
  `Rollup failed to resolve import` 失败（内容驱动的构建中断）。
- **修复方向**：
  1. 在转换层阻断：覆写 `DoubanConverter.escape`/`convert_text`，只对 `<` `>` `&`
     做反斜杠/实体转义（已实测 markdown-it 把 `\<` 渲染为可见的字面 `<`）。
     **不要**直接用 `escape_misc=True`：它连 `=` 一起转义（输出 `src\=x`），噪声大；
     也**不能**无脑全局替换 `<`，否则会打断 `autolinks=True` 生成的 `<https://…>`；
  2. 兜底防线：`config.mts` 显式 `html: false`，或增加一个把 `html_inline`/`html_block`
     token 重新转义的 rule（与 `defuseVueBraces` 对称）；
  3. 补回归测试：`&lt;img … onerror=…&gt;`、`&lt;svg onload=…&gt;`、
     `&lt;iframe srcdoc=…&gt;`、`&lt;script&gt;` 四种 payload 断言输出不含裸标签；
  4. 对已发布产物做一次全量扫描。
- **置信度**：高 · **证据类型**：测试复现 + 运行时观测 + 真实语料侧证。

**证据 1（转换层）**：

```text
html_to_markdown('<p>看看这个 &lt;img src=x onerror=alert(1)&gt; 标签</p>', ConvertContext())
-> '看看这个 <img src=x onerror=alert(1)> 标签'
```

**证据 2（端到端，仓库内独立最小 VitePress 站点，构建后检查产物）**：

```text
$ ./node_modules/.bin/vitepress build .vp-probe     # build complete
$ grep -o "onerror[^>]*" .vp-probe/.vitepress/dist/index.html
onerror="document.title=&#39;XSS-EXECUTED&#39;"     # 内联处理器进入最终 HTML
```

**证据 3（真实语料已出现该形态，只是当前 payload 无害）**：

```text
data/notes.json:  …标题改为“エコール”&lt;École=学校&gt;。  /  …（石田将也&lt;小学生&gt;）…
docs/notes/583976644.md:19  松冈茉优（石田将也<小学生>）：…
docs/notes/319279183.md:194 …“エコール”<École=学校>。）
```

即"转义标签 → 裸标签"这条链路已在真实产物里成立，只差一个 payload。

**附带确认（非缺陷）**：`docs/.vitepress/theme/lightbox.ts` 用 `textContent` 写
`data-caption`，`viewer.src`/`openLink.href` 只接受站内媒体路径，未发现 DOM XSS；
`config.mts` 的 `defuseVueBraces` 对 **text token** 的花括号防护本身有效
（`&#123;` 在 Vue 编译前不会被还原）。

---

### [P3-P0-2] Markdown 链接目标里的 `>` 逃出 `<…>` 包裹，注入裸 HTML

- **位置**：`html2md.py:63-78`（`sanitize_markdown_url`）、`html2md.py:143-156`（`convert_a`）；
  `emit.py:177-183`（`md_safe_url`）及其调用点 `emit.py:137`（`source_footer`）、
  `emit.py:625`（notes 索引外链）、`emit.py:785`（广播）；
  `emit.py:122-125`（`status_notice` 的 wayback 链接**完全没做**链接目标处理）。
- **触发条件**：链接目标里同时含"空格"和"`>` + 标签"。`sanitize_markdown_url`
  见空格就套 `<…>`，但 markdown-it 的尖括号目标遇到第一个 `>` 就闭合，
  随后"skipSpaces 后必须是 `)`"失败 → 整条链接降级为文本，末尾的
  `<img src=x onerror=…>` 被当成 `html_inline` 原样输出。
  **可达性**：`unwrap_link2`（`html2md.py:43-54`）会把豆瓣 `link2/?url=…`
  的 `url` 参数 `parse_qs` 解码成**任意字符串**，而评论正文是纯文本、
  豆瓣会把其中的 URL 自动链接成 `<a href="…/link2/?url=…">`。
  因此"评论者贴一个编码过的 link2 链接"即可把任意字符塞进链接目标。
- **影响**：与 P3-P0-1 同级的注入面，且出现在 emit 的多个独立位置
  （日记/评论/索引/广播/来源页脚）。`status_notice` 的 wayback URL 是唯一
  连 `<…>` 包裹都没有的链接位置。
- **修复方向**：
  1. 链接目标先做百分号编码或剥离 `<>` 与控制字符（`\x00-\x1f`）；
  2. 仅当 URL 内**不含** `<>` 时才用 `<…>` 包裹，否则退化为纯文本
     （与危险协议的处理一致）；
  3. `status_notice` / `emit_unavailable_report` 统一走
     `sanitize_markdown_url` + `md_escape_link_text`。
- **置信度**：高（机制与渲染均已复现；"真实豆瓣页面里出现这种 href"为推断，中高）·
  **证据类型**：测试复现 + 端到端构建观测。

```text
输入: [click](<http://evil.example/x > <img src="https://example.com/y.png" onerror="document.title=1">)
$ vitepress build   # build complete
$ grep -o "<img[^>]*>" dist/index.html
<img src="https://example.com/y.png" onerror="document.title=1">
```

---

### [P3-P1-1] `parse_bulletin` 容器缺失时用"页面上第一条 `#link-report`"冒充本条公告，且标记为 `ok`

- **位置**：`scraper/parsers.py:200-230`（`scope = container if isinstance(container, Tag) else soup`，
  随后 `body = scope.find(id="link-report")`）。**同文件 docstring（`parsers.py:196-199`）
  明确警告过不能这样做**：「必须按 `#bulletin-{id}` 精确定位容器，
  不能直接取页面里第一个 `#link-report` —— 否则所有公告都会读到同一份内容」。
- **触发条件**：房间页里找不到 `#bulletin-{id}` 容器（站点改版、公告模块被删、
  `structure.json` 里的旧 widget id 仍在），但页面上还有别的公告/模块的 `#link-report`。
  `stage_bulletins`（`cli.py:1086-1096`）按 widget id 请求整个房间页，
  因此拿到的是**另一条公告的正文与标题**。
- **影响**：静默错归档 —— 被删掉的公告栏会以"另一条公告的全文 + 对方标题"
  写入产物，`status.availability` 仍是 `ok`（`cli.py:1095` 又用 `page.status` 覆写），
  页面既没有提示块也不会进 `data/unavailable.md`。
- **修复方向**：容器缺失时不要回退到页面级 `#link-report`；或仅当页面内
  `#link-report` 恰好只有一个时才回退，否则置 `unavailable` + `retryable=True` 并告警。
- **置信度**：高（机制）· **证据类型**：测试复现。
- **核验说明**：主 agent 独立复现（同页两条公告，请求不存在的 id 99999999）：

```text
title= '99999999' | content= '聲之形分组内容' | availability= ok
```

现有测试 `test_missing_container_falls_back` 只覆盖"页面里完全没有公告"，
漏掉了"页面有其他公告"这条危险分支。

---

### [P3-P2-1] 评论只取 `.content p` 的第一个 `<p>`，其余节点静默丢弃

- **位置**：`scraper/parsers.py:579`（`body = item.select_one(".content p")`）、`:591`。
- **触发条件**：一条评论里出现多个 `<p>`（豆瓣评论框空行分段），或 `<p>` 之外还有
  块级节点（`<div>`/`<blockquote>`/`<img>`）。
- **影响**：评论正文被截断且无任何告警/状态标记（数据丢失）。真实数据侧证：
  缓存里 275 条评论**全部**是单 `<p>`（其中 46 条用 `<br>` 表达换行），
  所以当前未触发；触发条件是源站改成"每段一个 `<p>`"。
- **修复方向**：取 `.content` 去掉作者块后的全部子节点（复用 `_content_html`
  的"副本 + 剔除 UI"做法），或至少拼接所有 `<p>`。
- **置信度**：高（机制）/ 触发条件当前未满足 · **证据类型**：静态路径 + 真实数据统计。

---

### [P3-P2-2] `<a><img></a>` 生成的 Markdown 被链接文字转义打坏，图片退化成字面 `![]`

- **位置**：`html2md.py:143-156`（`convert_a` 对 label 调 `escape_markdown_link_text`）、
  `html2md.py:81-88`。
- **触发条件**：正文/评论/站外页出现 `<a href="…"><img …></a>`（可点击配图）。
- **影响**：输出 `[!\[\](https://y/i.jpg)](https://x/page)`，markdown-it 把它渲染成
  链接文字 `![]` + 括号 URL，**图片彻底消失**并留下垃圾文本。
- **修复方向**：只对纯文本 label 做方括号转义，或在 `convert_a` 里检测 label
  已含 `![](`/`[](` 时跳过。
- **置信度**：高（机制）/ 触发条件当前未满足 · **证据类型**：测试复现。
- **核验说明**：主 agent 复现 → `'[!\\[封面\\](https://y/i.jpg)](https://x/page)'`。
  真实数据：145 篇日记 + 275 条评论 + 讨论帖正文里经 markdownify 的容器内 **0 例**。

---

### [P3-P2-3] `parse_total_pages` 用裸正则读属性：引号/空白一变，多页列表静默退化成单页

- **位置**：`scraper/parsers.py:237-248`（`re.search(r'data-total-page="(\d+)"', html)`）。
- **触发条件**：源站把该属性写成单引号、无引号、`data-total-page = "4"`、
  标签内换行或大小写变化。
- **影响**：返回 `None` → 调用方按单页处理（`discover.py:146-150/246-252`
  只有一条 warning），**该模块的多页日记/相册只归档第一页**。
  附带风险：正则在**整篇文本**里找第一个匹配，不看归属容器。
- **修复方向**：改用 `soup.select_one("[data-total-page]")`，与同文件的
  `parse_note_comment_pages` 保持一致。
- **置信度**：高（机制）/ 触发条件当前未满足 · **证据类型**：测试复现。
- **核验说明**：主 agent 复现 —— `<span data-total-page="4">` → 4；
  单引号 / 无引号 / 带空格三种写法全部 → `None`（真实缓存页目前全是双引号）。

---

### [P3-P2-4] 已归档文件的后缀候选表不含 `.svg`/`.bmp`，这类图每次同步都被重下

- **位置**：`media.py:91`（`PREVIEW_SUFFIX_ORDER = (".webp",".jpg",".jpeg",".png",".gif")`）、
  `media.py:406-409`，而 `SUFFIX_FOR_KIND`/`IMAGE_SUFFIXES`（`media.py:61-71`）
  明确支持 `svg`/`bmp`。
- **触发条件**：图片内容被嗅探为 svg/bmp（`correct_suffix` 落成 `.svg`/`.bmp`），
  而 URL 后缀是别的（`dest` 猜成 `.jpg`）。
- **影响**：破坏模块自己声明的幂等契约（"已归档且是有效图片则跳过，增量同步的关键"）：
  每次 sync 都重新联网下载、`downloaded`/`bytesTotal` 统计虚高；
  若源站已删图，还会被记成失败（真图还在盘上）。
- **修复方向**：把 `".svg"`/`".bmp"` 补进候选，或按 `dest.stem` + `glob` 全后缀查找
  （与 `_find_album_file` 统一）。
- **置信度**：高（机制）/ 触发条件受限（真实 1589 个文件里无 svg/bmp）·
  **证据类型**：静态路径 + 真实素材核对。

---

### [P3-P2-5] 图片格式嗅探的边界：前导 BOM/空白的 JPEG 被判为非图片

- **位置**：`media.py:102-115`（`sniff_image` 魔术字节用 `startswith` 不做 `lstrip`，
  且先卡 `len(data) < 12`）、`media.py:118-136`。
- **触发条件与影响**：
  - 开头有 BOM/换行/空白的 JPEG/PNG（`b"\xef\xbb\xbf\xff\xd8\xff\xe0…"`）→ `None`
    → 被当成"不是图片"，候选全灭 → 图片**被记为不可得**
    （`cli.py:1313-1315` 走 `mark_unavailable`，进不可访问清单）；
  - 合法但很短的 SVG（`<svg/>`）因 `len < 12` 被拒；
  - 以 `BM` 开头的任意文本会被当成 `bmp` 通过校验。
- **修复方向**：判定前统一 `data = data.lstrip(b"\xef\xbb\xbf\r\n\t ")[:512]`；
  对很短的 SVG 放宽长度门槛；`BM` 增加后续字节校验。
- **置信度**：高（行为可复现）/ 真实可达性低（4300+ 真实图片 body 全部正确识别，
  79 个 `None` 全是 404 空响应或 archive.org 的 JSON/HTML）·
  **证据类型**：测试复现 + 真实素材核对。

---

### [P3-P2-6] 视频条目缺必填字段仍标 `ok`，且 `unquote` 无依据地改写 URL

- **位置**：`parsers.py:806`（`external = str(img.get("name", ""))`）、
  `parsers.py:821`（`external_url=unquote(external)`）、
  `parsers.py:824`（`status=SourceStatus(availability="ok")` 无条件）。
- **触发条件**：视频条目的 `name` 属性缺失/改名，或缩略图 `src` 缺失；
  以及 URL 本身含 `%` 序列。
- **影响**：
  - 空字段仍标 `ok`，产物里出现"已归档但永远点不开"的条目。**真实数据已有实例**
    （主 agent 核对 `data/videos.json`）：`video_id=771903`
    「电影《聲之形》热映答谢见面会」的 `thumb_url`/`local_thumb` 均为空串，
    `status.availability` 仍是 `ok`，也不在不可访问清单里；
  - `unquote` 是不可逆改写：`%2F` → `/`、非法 UTF-8 百分号序列 →
    U+FFFD 永久损坏，且注释声称的"幂等"不成立（`unquote("%2526")` → `%26` → `&`）。
    `emit.py:701` 把该值直接写进 `href`（只经 `html_attr` 转义，无协议白名单），
    与 `html2md.sanitize_markdown_url` 的白名单策略不一致。
- **修复方向**：字段缺失时置 `unavailable`/`retryable`；`unquote` 前先判断是否含
  `%[0-9A-Fa-f]{2}`，并对结果做 scheme 白名单校验。
- **置信度**：中高 · **证据类型**：真实数据 + 静态路径。

---

### [P3-P2-7] 反序列化不对称与构造过严

- **位置**：
  1. `models.py:93-103`（`SourceStatus.to_dict` 写出 `waybackStatus`）
     vs `cli.py:795-805`（`_status_from_dict` **不读** `waybackStatus`）；
  2. `cli.py:905`（`ImageRef(**img)`）、`cli.py:428`（`MiniblogStatus(**payload)`）
     用 `**payload` 直接构造，遇到未知键抛 `TypeError`；同文件其它 loader 都用 `.get()`。
- **触发条件/影响**：
  1. `wayback_status` 是"写得出、读不回、全仓无读取方"的半死字段：
     `load_existing()` → 再落盘一次就永久丢失（`302 → None`）。
     **其余字段主 agent 已逐字段比对，`to_dict`↔loader 是对称的**（含 `comments`、
     `images`、`also_in`、`local_thumb`、`local_original`）。
  2. `data/*.json` 字段一旦增删（旧版本产物、手工编辑），`load_existing` 没有
     try/except 与迁移路径 → 整轮 `sync` 直接崩。
- **修复方向**：`_status_from_dict` 补 `wayback_status`；两个 `**payload` 改为
  `.get()` 或按 `dataclasses.fields` 过滤后再构造。
- **置信度**：高 · **证据类型**：静态路径（sub agent 另给出往返比对复现）。

---

### [P3-P2-8] `SourceStatus` 允许裸字符串，`needs_notice` 会抛 `AttributeError`

- **位置**：`models.py:88-91`（`needs_notice` 直接访问 `self.availability.needs_notice`）
  vs `parsers.py:227-230/392-395/443/551-555/650-653/738/824`
  （用裸字符串构造 `SourceStatus(availability="ok"/"unavailable")`）。
- **触发条件/影响**：`SourceStatus(availability="ok").needs_notice`
  → `AttributeError: 'str' object has no attribute 'needs_notice'`
  （`label` 恰好因 `StrEnum` 与 `str` 相等而能工作，掩盖了问题）。
  目前所有 stage 都会用真实的 `page.status` 覆写，所以**尚不可达**；
  任何新调用点（或有人复用 parser 结果直接 emit）就会崩。
- **修复方向**：给 `SourceStatus` 加 `__post_init__` 归一化（`Availability(self.availability)`），
  或 parser 侧统一用枚举。
- **置信度**：高（行为已复现）/ 当前不可达 · **证据类型**：测试复现。

---

### [P3-INFO-1] 枚举数量与源站声明数量之间没有任何对账

声明量来自 `parse_total_pages`/`parse_page_step`，实际枚举量由
`discover.py:151-155`（失败子页**静默跳过**）与 `discover.py:256-262`
（`continue`）产生；对账只在 `verify.py` 且只比 manifest 内部计数，
从不比"页数 × 步长"。某一页被拦截/超时时会静默少抓一批内容，
只有 info 级行数日志。当前真实数据（`data-total-page=6 / step=30 / 实际 179` 等）
全部吻合，故未触发。置信度：高（缺失检查）· 证据类型：静态路径。

---

## 残留疑点

1. **同 basename 不同图互相顶替**：`note_image_path`（`media.py:289-294`）用 URL 末段
   命名，`download` 命中已存在文件就跳过，因此同一篇日记里
   `https://a/x/p1.jpg` 与 `https://b/y/p1.jpg` 会共用一个落盘文件。
   真实数据 839 个配图引用 **0 冲突**。
2. **`basename_of` 的 `/..` 路径**：`media.py:244-246` 对 `https://x/a/..` 返回 `".."`。
   但所有业务 ID 都来自 `\d+` 正则，**没有 ID 拼接穿越**；真实数据 0 例。
3. **表格单元格被合并**：`preprocess` 拆掉 `table/tr/td` + `convert_table` 退化为纯文本，
   `<td>左</td><td>右</td>` → `左右`。真实 144 篇里有 52 篇含表格，
   但"≥2 个非空文本单元格"的表格 **0 例**。
4. **`data-src` 与 `src` 并存**：`parsers.py:550` 与 `html2md.py:126-132` 都优先 `src`；
   若源站改成"占位图 + data-src 真图"的懒加载会一致地归档占位图。真实数据 0 例。
5. **评论里的图片不入库**：`emit._render_comments` 的 `ConvertContext` 未传
   `keep_remote_images=False`（`emit.py:303-308`），评论图片会留外链
   （豆瓣 CDN 无 Referer 返 418，可能裂图）。真实 275 条评论 **0 张图**。
6. **`_fix_bullets` 的误伤面**（`html2md.py:249-252`）：行首 `* `/`+ ` 会被改成 `- `，
   可能把强调改成列表项。真实数据未见。

---

## 漏检复盘（本层已主动排查、未发现新问题的模式）

- **`find`/`select_one` 的 None 解引用**：空/畸形 HTML 共 7 组用例喂给
  `parse_note`/`parse_note_list`/`parse_photo_list`/`parse_photo_detail`/
  `parse_bulletin`/`parse_note_comments`/`parse_miniblog`/`parse_video_list`/
  `parse_discussion*`/`parse_widgets`/`parse_room_nav`/`parse_album_title`/
  `parse_external_page`，**均未抛异常**。
- **危险协议白名单**：`sanitize_markdown_url` 对 `javascript:`（含前导空格/制表符/
  换行/`&#106;`/`&colon;`/`&#x09;` 变体）、`vbscript:`、`data:` 全部拒绝并退化为纯文字；
  `\x00javascript:` 经 HTML 解析变成 `\ufffdjavascript:`，浏览器不视作 scheme。
  **唯一绕过是 P3-P0-2 的 `>` 逃逸**。
- **反序列化对称性**：逐字段比对 `Note/Album/PhotoMeta/Bulletin/Video/ExternalPage/
  Discussion/Room/Widget/IndexGroup/IndexEntry` 的 `to_dict`↔loader，
  除 P3-P2-7 的 `waybackStatus` 外**全部对称**。
- **去重与合并**：评论按 `comment_id` 去重正确（真实 275 条 cid 全唯一，
  高评论数日记归档数 = 源站声明数）；索引"同一 path 多分类"真实 0 例。
- **索引解析**：`data/index.json` 7 组 100 条与重新解析结果**逐条一致**，
  link2 解码与源一致，无"无分类"漏项。
- **路径穿越**：所有业务 ID 都来自 `\d+` 正则（`parsers.py:34-50`），
  `_external_page_id`（`cli.py:1525-1532`）用 `-` 连接且只取路径前两段，
  无法产生 `/`；`emit.py` 的 `f"{id}.md"` 因此不可穿越。
- **编解码**：`unquote` 死代码已修（`8088994`）；HTML 实体由 bs4 正确处理；
  中文/空格/百分号文件名与后缀 1589 个全部正确；日期解析与源站一致。
- **图片完整性**：`read_kind`/`is_valid_image` 已改为读 512 字节；
  `atomic_write_bytes` 让半截文件无法产生；1589 个文件的尾部校验 0 异常。
