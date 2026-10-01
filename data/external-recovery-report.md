# 外链恢复实测报告

执行日期：2026-10-01。所有计数以有效正文解析、实际图片文件和明确的重定向证据为准。

原有 125 个失败 URL 中，98 个取得正文或目录，21 个短链取得真实地址，6 个原失败 URL 尚未取得原文。另把一个原先标为成功、实际为停放页的 AniFav 地址改回失败，避免误归档。

现有 250 个可解析外部内容页；新增 694 个图片文件，共 2059 个外部内容图片文件。正文已生成至 `docs/external-articles/`，原文 URL、正文来源、真实快照日期和原始缓存路径保存在 `external-captures.json`。

## 恢复手段

- 保留文章 ID 的域名、路径与 HTTPS 迁移，以及有原始资料证据的截断链接修正。
- 浏览器与 HTTP 独立回退；已实测部分 CloudFront 拒绝在现有浏览器中仍为 403。
- Internet Archive availability 查询、发布时间附近及最早快照回放；以实际重定向的时间戳为准。
- 从豆瓣源 HTML 中的明确展开地址恢复短链，并拒绝冲突证据。
- 取回日文旧编码正文，准确选择新闻锚点；按已核实的具体周榜替代动态排行榜。
- Tower Records 失效公告用明确引用原链接的电影官方转载恢复，并在正文标注转载来源。
- 同时期图片回放、HTTPS 和默认端口修正；只接受真实图片字节。

## 尚未取得原文的目标

| 原链接 | 已核实的可读内容 / 限制 |
| --- | --- |
| [http://ameblo.jp/nekokanekoneko/entry-11848710846.html](http://ameblo.jp/nekokanekoneko/entry-11848710846.html) | 原页 404；已归档的四张关联照片可读，原文未恢复。 [已归档关联照片（原文未恢复）](/Users/tautcony/Documents/repos/usagiyama-index/docs/albums/13433748.md)。 |
| [http://anifav.com/topics/20140719_3734.html](http://anifav.com/topics/20140719_3734.html) | 原站已变为停放/广告页，已检索快照未含原文。 [已归档译文](/Users/tautcony/Documents/repos/usagiyama-index/docs/notes/412701420.md)。 |
| [http://houtaruu.weblog.to/archives/6879881.html](http://houtaruu.weblog.to/archives/6879881.html) | 原页 404；可读已归档译文。 [已归档译文](/Users/tautcony/Documents/repos/usagiyama-index/docs/notes/580950328.md)。 |
| [http://houtaruu.weblog.to/archives/7271602.html](http://houtaruu.weblog.to/archives/7271602.html) | 原页 404；可读多篇报告的摘译，不能视为单篇原文。 [已归档摘译（含多篇报告，不能替代单篇原文）](/Users/tautcony/Documents/repos/usagiyama-index/docs/notes/583976644.md)。 |
| [http://keisukeyuki.blogspot.jp/2014/05/blog-post.html](http://keisukeyuki.blogspot.jp/2014/05/blog-post.html) | 原域名及迁移域名均已删除；本轮未找到可用公开快照。 |
| [http://www.asahi.com/articles/DA3S12553913.html](http://www.asahi.com/articles/DA3S12553913.html) | 找到历史付费预览，未找到完整日文正文；已有归档译文。 [已归档译文](/Users/tautcony/Documents/repos/usagiyama-index/docs/notes/581373515.md)。 |
| [https://douc.cc/3T9jc2](https://douc.cc/3T9jc2) | 短链和缓存 href 都已失效；已取回对应日期的官方发行资料，但原重定向未确认。 [同一公告的官方资料（短链原地址未确认）](/Users/tautcony/Documents/repos/usagiyama-index/docs/external-articles/www.tbs.co.jp/c7dffbdeb585a2b19181.md)。 |

Common Crawl API 多次返回 503/504，因此继续通过公开存储直接读取 2014-35、2014-42、2016-40 的索引分片；本轮检查未命中这些剩余 URL。Arquivo.pt 查询也未返回对应版本。这些结果只说明本轮未找到内容，不能证明整个互联网没有副本。查询地址、索引偏移及结果见 [审计 JSON](external-recovery-audit.json)。

## 验证

- Python 回归测试：653 项通过，1 项按测试配置排除。
- `npm run emit` 已成功生成产物。
- `npm run verify`：7/7 项通过。
- `npm run docs:build`：成功，死链校验开启。

补写替代入口时发生过一次未加载已有数据的保存错误。源数据已从 Git 恢复，新正文元数据从已验证的原始缓存重建，图片由实际文件及格式校验重建。144 篇日记、523 张相册照片及 881 条广播均已核对；原有源数据 JSON 与 Git 基线一致。
