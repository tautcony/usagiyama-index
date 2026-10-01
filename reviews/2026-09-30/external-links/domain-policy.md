# 外链分类与抓取准入

分类器位于 `scraper/link_policy.py`。它同时判断域名和 URL 路径，不把“同一域名”直接等同于“同一种内容”。`data/links.json` 保存 `category/action/reason`，`data/external-queue.json` 仅列出需解析、文章候选和待人工判定项。

| 分类 | 识别规则 | 动作 |
| --- | --- | --- |
| 短链接 | `douc.cc`、`dou.bz`、`t.cn` | `resolve`；取得最终地址后必须重新分类 |
| 豆瓣日记 / 话题 | 豆瓣主站 `/note/`、`/topic/` | `fetch_article` |
| 豆瓣作品 / 人物 / 搜索 | `/subject/`、`/celebrity/`、`/personage/`、`/people/`、`subject_search` | `metadata` |
| 豆列 | `/doulist/` | `metadata`，以后由集合适配器处理 |
| 百科资料 | Wikipedia、百度百科、Pixiv/Niconico 百科 | `metadata` |
| 商品 / 商店 | Amazon、京阿尼商店、Froovie、HobbyStock | `metadata` |
| 视频 / 音乐 / 社交 | 已识别的平台主机 | `metadata` |
| 图片 / 全景 | 已知图片/全景主机或常见图片扩展名 | `metadata` |
| 回链端点 | `trackback.blogsys.jp` | `skip` |
| 其他网页 | 已知博客/新闻域名的具体路径，或明确文章路径 | `fetch_article` |
| 其他可疑文章路径 | 未列入文章域名，但路径类似文章 | `review`，不能自动抓 |
| 官网首页、未知页面 | 不能从 URL 确认文章性质 | `review` / `metadata` |
| 畸形 URL | 非 HTTP(S)、无有效主机名或混入拼接文本 | `skip` |

网页首页不会因域名在博客/媒体名单中而被抓取；文章域名规则必须同时满足具体页面路径。像 `/special/`、泛 `/blog/` 这类边界路径留待人工确认。分类结果是抓取准入，不代表正文提取成功；抓取器仍须验证主内容，不能把登录页、导航页或空内容标成文章归档成功。

`external` 阶段按队列实际请求文章候选和短链，只保存原始 HTML 缓存与 `data/external-captures.json` 元信息；不提取正文。短链按响应的最终 URL 重新分类，最终不是文章的目标不保存为文章副本。请求使用现有串行传输和延迟配置。

正文抽取留待下一阶段。按域名读取并缓存 robots 规则、逐跳检查短链重定向目标仍需补充；当前运行前仍要求操作者确认已阅读目标站点的 robots 规则（`--i-have-read-robots`）。
