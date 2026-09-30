# docs Markdown 外部链接清单

以当前 `docs/**/*.md` 为准；排除构建产物和 `public`。不读取 `data/*.json`。
用 VitePress 解析 Markdown 和裸 HTML，统计可点击链接及可见正文中的纯文本 URL。
原站 `site.douban.com/211330`、图片资源、frontmatter 来源另列，不混入外部资料数量。
仅移除 fragment 做请求目标去重；保留 query、HTTP/HTTPS、www、尾斜杠差异，未联网确认等价。
因此数量表示不同 URL 请求目标，并非已证明互不相同的文章。所有可达性均为未检查。

```json
{
  "markdownFiles": 255,
  "externalTargets": 842,
  "externalOccurrences": 1112,
  "externalHosts": 114,
  "clickableTargets": 621,
  "textOnlyTargets": 221,
  "originalSiteTargets": 169,
  "originalSiteOccurrences": 177,
  "remoteImageTargets": 0,
  "frontmatterUrls": 151,
  "flaggedTargets": 3
}
```

## 类型

| 类别 | 目标 URL | 引用次数 |
| --- | ---: | ---: |
| 音乐平台 | 3 | 6 |
| 商品 / 商店 | 24 | 33 |
| 豆瓣日记 / 话题 | 2 | 3 |
| 豆瓣作品 / 人物 / 搜索 | 73 | 117 |
| 豆列 | 6 | 12 |
| 豆瓣其他页面 | 1 | 1 |
| 百科资料 | 29 | 38 |
| 畸形地址，禁止直接抓取 | 1 | 1 |
| 图片 / 全景资料链接 | 9 | 10 |
| 回链服务端点 | 1 | 1 |
| 短链接，待解析 | 334 | 373 |
| 社交帖子 / 个人主页 | 24 | 27 |
| 视频平台 | 66 | 105 |
| 其他网页（文章 / 官网 / 博客，需细分） | 269 | 385 |

## 异常地址

保留原始证据，先修正/确认后再入抓取队列。

- `http://2017年3月31日/` — invalid_hostname；docs/broadcast/page/5.md:26
- `https://img3.doubanio.com/view/note/large/public/p29295562.jpg%5B/img%5D` — bbcode_in_url；docs/notes/519165447.md:77
- `http://tamakolovestory.com/special/interview/今回は「映画」ということをだいぶ意識` — possible_concatenated_prose；docs/broadcast/page/67.md:30

## 域名

| 域名 | 目标 URL | 引用次数 |
| --- | ---: | ---: |
| douc.cc | 326 | 359 |
| movie.douban.com | 71 | 115 |
| v.youku.com | 52 | 87 |
| www.kyotoanimation.co.jp | 52 | 58 |
| priority1.blog51.fc2.com | 45 | 70 |
| twitter.com | 22 | 25 |
| www.amazon.co.jp | 19 | 22 |
| koenokatachi-movie.com | 18 | 24 |
| ameblo.jp | 16 | 53 |
| d.hatena.ne.jp | 14 | 18 |
| zh.wikipedia.org | 11 | 12 |
| baike.baidu.com | 10 | 14 |
| www.douban.com | 9 | 16 |
| ch.nicovideo.jp | 8 | 9 |
| ja.wikipedia.org | 8 | 12 |
| tamakolovestory.com | 8 | 17 |
| dou.bz | 7 | 11 |
| www.nicovideo.jp | 7 | 7 |
| anime-eupho.com | 6 | 9 |
| www.excite.co.jp | 6 | 8 |
| natalie.mu | 5 | 7 |
| htt123.blog.jp | 4 | 4 |
| isladelpescado.com | 4 | 4 |
| www.bilibili.com | 4 | 8 |
| kyoanido-event.com | 3 | 4 |
| mantan-web.jp | 3 | 3 |
| realsound.jp | 3 | 3 |
| www.hanakotoba.name | 3 | 5 |
| animeanime.jp | 2 | 4 |
| blog.livedoor.jp | 2 | 3 |
| cgi2.nhk.or.jp | 2 | 2 |
| houtaruu.weblog.to | 2 | 2 |
| kyoanishop.com | 2 | 5 |
| music.douban.com | 2 | 2 |
| nuruwota.blog4.fc2.com | 2 | 2 |
| p.twipple.jp | 2 | 2 |
| tehepero-tini.hatenablog.jp | 2 | 2 |
| weibo.com | 2 | 2 |
| www.animatetimes.com | 2 | 3 |
| www.tudou.com | 2 | 2 |
| 2017年3月31日 | 1 | 1 |
| aiko.com | 1 | 1 |
| anifav.com | 1 | 2 |
| ar-flower.com | 1 | 1 |
| birthofblues.livedoor.biz | 1 | 1 |
| blog.sina.com.cn | 1 | 1 |
| chusingura.hatenablog.jp | 1 | 1 |
| cinemacity.co.jp | 1 | 1 |
| columii.jp | 1 | 1 |
| crea.bunshun.jp | 1 | 1 |
| cycle-junrei.hatenablog.jp | 1 | 1 |
| dengekionline.com | 1 | 1 |
| dic.nicovideo.jp | 1 | 1 |
| dic.pixiv.net | 1 | 1 |
| eco.mtk.nao.ac.jp | 1 | 2 |
| froovie.jp | 1 | 2 |
| gd.qq.com | 1 | 1 |
| hatenanews.com | 1 | 1 |
| heike-anime.asmik-ace.co.jp | 1 | 2 |
| httesora.blog.fc2.com | 1 | 1 |
| img3.douban.com | 1 | 1 |
| img3.doubanio.com | 1 | 1 |
| j-mediaarts.jp | 1 | 1 |
| kansai.pia.co.jp | 1 | 1 |
| keisukeyuki.blogspot.jp | 1 | 1 |
| liz-bluebird.com | 1 | 4 |
| minamiruruka.seesaa.net | 1 | 1 |
| mirrorring.doorblog.jp | 1 | 1 |
| moca-news.net | 1 | 1 |
| music.163.com | 1 | 4 |
| music.baidu.com | 1 | 1 |
| my.tv.sohu.com | 1 | 1 |
| nazism.cocolog-nifty.com | 1 | 2 |
| news.mynavi.jp | 1 | 1 |
| news.qq.com | 1 | 1 |
| news.walkerplus.com | 1 | 2 |
| qrion.net | 1 | 3 |
| rdm.ne.jp | 1 | 1 |
| rubeusu-trend.com | 1 | 1 |
| sensesapporo.bandcamp.com | 1 | 1 |
| shimirubon.jp | 1 | 1 |
| shine.web.wox.cc | 1 | 1 |
| t.cn | 1 | 3 |
| tamakomarket.com | 1 | 1 |
| theta360.com | 1 | 1 |
| tokyo-anime-news.jp | 1 | 2 |
| trackback.blogsys.jp | 1 | 1 |
| we-love-brass.jp | 1 | 1 |
| ww3.sinaimg.cn | 1 | 1 |
| www.agraph.jp | 1 | 1 |
| www.amazon.com | 1 | 1 |
| www.animate.tv | 1 | 1 |
| www.anime-recorder.com | 1 | 2 |
| www.artsbj.com | 1 | 1 |
| www.asahi.com | 1 | 1 |
| www.chatterbox.tips | 1 | 1 |
| www.cinematoday.jp | 1 | 1 |
| www.e-switch.jp | 1 | 1 |
| www.hatago.co.jp | 1 | 1 |
| www.hisaz.com | 1 | 1 |
| www.hobbystock.jp | 1 | 3 |
| www.jfd.or.jp | 1 | 1 |
| www.korg.com | 1 | 1 |
| www.lmaga.jp | 1 | 1 |
| www.nao.ac.jp | 1 | 2 |
| www.okuru-hana.com | 1 | 1 |
| www.recosuke.com | 1 | 3 |
| www.shuwa-island.jp | 1 | 1 |
| www.tbs.co.jp | 1 | 1 |
| www.uji-genji.jp | 1 | 1 |
| www.watch-watcher.xyz | 1 | 1 |
| www42.atwiki.jp | 1 | 1 |
| wx4.sinaimg.cn | 1 | 1 |
| zyunko.kyoto-yoroken.com | 1 | 1 |

## 完整目标列表

每个 URL 列出首个引用标签和全部来源页面；精确位置、原始 URL、上下文见 `inventory.json`。

### 2017年3月31日

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [&lt;a href=&quot;http://2017年3月31日&quot;&gt;http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1865&lt;/a&gt; 大家好！ 春天的气息已经相当浓郁了呢。 各位近来可好？ 我不知是感冒还是怎么了，嗓子变得怪怪的，现](<http://2017年3月31日/>)<br>`http://2017年3月31日/` | 畸形地址，禁止直接抓取 / 纯文本 | docs/broadcast/page/5.md:26 |

### aiko.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://aiko.com/](<http://aiko.com/>)<br>`http://aiko.com/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/575910736.md:56 |

### ameblo.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://ameblo.jp/clown-happy/entry-11835509608.html](<http://ameblo.jp/clown-happy/entry-11835509608.html>)<br>`http://ameblo.jp/clown-happy/entry-11835509608.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:141<br>docs/albums/13433748.md:142 |
| [http://ameblo.jp/clown-happy/entry-11840684002.html](<http://ameblo.jp/clown-happy/entry-11840684002.html>)<br>`http://ameblo.jp/clown-happy/entry-11840684002.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:127 |
| [http://ameblo.jp/clown-happy/entry-11840707028.html](<http://ameblo.jp/clown-happy/entry-11840707028.html>)<br>`http://ameblo.jp/clown-happy/entry-11840707028.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:128<br>docs/albums/13433748.md:129<br>docs/albums/13433748.md:130<br>docs/albums/13433748.md:131<br>docs/albums/13433748.md:132<br>docs/albums/13433748.md:133<br>docs/albums/13433748.md:134 |
| [http://ameblo.jp/clown-happy/entry-11841575269.html](<http://ameblo.jp/clown-happy/entry-11841575269.html>)<br>`http://ameblo.jp/clown-happy/entry-11841575269.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:96<br>docs/albums/13433748.md:97<br>docs/albums/13433748.md:98<br>docs/albums/13433748.md:99<br>docs/albums/13433748.md:100<br>docs/albums/13433748.md:101<br>docs/albums/13433748.md:102<br>docs/albums/13433748.md:103 |
| [http://ameblo.jp/clown-happy/entry-11844054985.html](<http://ameblo.jp/clown-happy/entry-11844054985.html>)<br>`http://ameblo.jp/clown-happy/entry-11844054985.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:90<br>docs/albums/13433748.md:91<br>docs/albums/13433748.md:92<br>docs/albums/13433748.md:93<br>docs/albums/13433748.md:94<br>docs/albums/13433748.md:95 |
| [http://ameblo.jp/clown-happy/entry-11847287088.html](<http://ameblo.jp/clown-happy/entry-11847287088.html>)<br>`http://ameblo.jp/clown-happy/entry-11847287088.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:76 |
| [http://ameblo.jp/clown-happy/entry-11854359420.html](<http://ameblo.jp/clown-happy/entry-11854359420.html>)<br>`http://ameblo.jp/clown-happy/entry-11854359420.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:68<br>docs/albums/13433748.md:69<br>docs/albums/13433748.md:70<br>docs/albums/13433748.md:71<br>docs/albums/13433748.md:72<br>docs/albums/13433748.md:73<br>docs/albums/13433748.md:74<br>docs/albums/13433748.md:75 |
| [洲崎、小川、山田、瀬波、田丸 http://ameblo.jp/clown-happy/entry-11867283126.html](<http://ameblo.jp/clown-happy/entry-11867283126.html>)<br>`http://ameblo.jp/clown-happy/entry-11867283126.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:61 |
| [http://ameblo.jp/clown-happy/entry-11929027655.html 《玉子爱情故事》CAST评论音轨收录现场](<http://ameblo.jp/clown-happy/entry-11929027655.html>)<br>`http://ameblo.jp/clown-happy/entry-11929027655.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:50<br>docs/albums/13433748.md:51 |
| [http://ameblo.jp/clown-happy/entry-11935023504.html 洲崎綾、田丸篤志](<http://ameblo.jp/clown-happy/entry-11935023504.html>)<br>`http://ameblo.jp/clown-happy/entry-11935023504.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:53<br>docs/albums/13433748.md:54<br>docs/albums/13433748.md:55 |
| [映画「けいおん！」のポストカードについて考察](<http://ameblo.jp/cola-tea/entry-11136952940.html>)<br>`http://ameblo.jp/cola-tea/entry-11136952940.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:38 |
| [バトントワリング振り付け 本庄千穂 http://ameblo.jp/diva1976/entry-11850240528.html](<http://ameblo.jp/diva1976/entry-11850240528.html>)<br>`http://ameblo.jp/diva1976/entry-11850240528.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:66 |
| [http://ameblo.jp/kyousei-t/entry-11837726745.html](<http://ameblo.jp/kyousei-t/entry-11837726745.html>)<br>`http://ameblo.jp/kyousei-t/entry-11837726745.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:124<br>docs/albums/13433748.md:125<br>docs/albums/13433748.md:126 |
| [3年2組の女の子たち](<http://ameblo.jp/mangatimekirara/>)<br>`http://ameblo.jp/mangatimekirara/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:44 |
| [http://ameblo.jp/nekokanekoneko/entry-11847828802.html](<http://ameblo.jp/nekokanekoneko/entry-11847828802.html>)<br>`http://ameblo.jp/nekokanekoneko/entry-11847828802.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:81<br>docs/albums/13433748.md:82<br>docs/albums/13433748.md:84 |
| [http://ameblo.jp/nekokanekoneko/entry-11848710846.html](<http://ameblo.jp/nekokanekoneko/entry-11848710846.html>)<br>`http://ameblo.jp/nekokanekoneko/entry-11848710846.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:77<br>docs/albums/13433748.md:78<br>docs/albums/13433748.md:79<br>docs/albums/13433748.md:80<br>docs/albums/13433748.md:83 |

### anifav.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://anifav.com/topics/20140719_3734.html 这是个电影奇迹。 这句话出自评论家浅田彰所写的散文《电影奇迹》的第一行，我看到《玉子爱情故事》时最先联想到的，就是这个“电影奇迹”所指的温·韦德斯导演的《柏林苍穹下》（1987年...](<http://anifav.com/topics/20140719_3734.html>)<br>`http://anifav.com/topics/20140719_3734.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/broadcast/page/55.md:28<br>docs/notes/412701420.md:11 |

### anime-eupho.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [《吹响悠风号》（響け！ユーフォニアム） http://anime-eupho.com/ 导演：石原立也，系列演出：山田尚子，2015年4月开播。](<http://anime-eupho.com/>)<br>`http://anime-eupho.com/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/albums/13432051.md:19<br>docs/albums/13432051.md:20<br>docs/albums/13432051.md:21<br>docs/rooms/2794117.md:38 |
| [『劇場版 響け！ユーフォニアム～北宇治高校吹奏楽部へようこそ～』Blu-ray &amp; DVD2016年9月7日(水)発売決定！詳しくは、公式ＨＰをチェック！ http://anime-eupho.com/bd-dvd/](<http://anime-eupho.com/bd-dvd/>)<br>`http://anime-eupho.com/bd-dvd/` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13431950.md:16 |
| [生日](<http://anime-eupho.com/character/>)<br>`http://anime-eupho.com/character/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/493628625.md:26 |
| [人物关系图](<http://anime-eupho.com/character/chart/>)<br>`http://anime-eupho.com/character/chart/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/496259160.md:43 |
| [Fan Book 2015年9月23日发售 http://anime-eupho.com/news/?id=53](<http://anime-eupho.com/news/?id=53>)<br>`http://anime-eupho.com/news/?id=53` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13431950.md:62 |
| [评语](<http://anime-eupho.com/story/01/>)<br>`http://anime-eupho.com/story/01/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/493628625.md:68 |

### animeanime.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [「たまこラブストーリー」山田尚子監督インタビュー 第18回文化庁メディア芸術祭アニメーション部門新人賞受賞](<http://animeanime.jp/article/2015/01/29/21773.html>)<br>`http://animeanime.jp/article/2015/01/29/21773.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:57 |
| [映画「聲の形」牛尾憲輔インタビュー 山田尚子監督とのセッションが形づくる音楽 http://animeanime.jp/article/2016/09/16/30521.html](<http://animeanime.jp/article/2016/09/16/30521.html>)<br>`http://animeanime.jp/article/2016/09/16/30521.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/albums/190597061.md:77<br>docs/albums/190597061.md:78<br>docs/notes/582498318.md:12 |

### ar-flower.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [解释](<http://ar-flower.com/nanohana7/>)<br>`http://ar-flower.com/nanohana7/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/506916664.md:119 |

### baike.baidu.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [“镰鼬”](<http://baike.baidu.com/subview/320673/5241275.htm>)<br>`http://baike.baidu.com/subview/320673/5241275.htm` | 百科资料 / 可点击 | docs/notes/576189949.md:26 |
| [鲤鱼跳龙门](<http://baike.baidu.com/subview/72970/5093616.htm>)<br>`http://baike.baidu.com/subview/72970/5093616.htm` | 百科资料 / 可点击 | docs/notes/550509861.md:14 |
| [约瑟夫·科苏斯](<http://baike.baidu.com/view/10036659.htm>)<br>`http://baike.baidu.com/view/10036659.htm` | 百科资料 / 可点击 | docs/notes/582498318.md:46 |
| [《少女新娘物语》](<http://baike.baidu.com/view/2045773.htm>)<br>`http://baike.baidu.com/view/2045773.htm` | 百科资料 / 可点击 | docs/notes/575910736.md:34 |
| [《这本漫画真厉害！》](<http://baike.baidu.com/view/4880989.htm>)<br>`http://baike.baidu.com/view/4880989.htm` | 百科资料 / 可点击 | docs/notes/569286438.md:97 |
| [松冈茉优](<http://baike.baidu.com/view/6201506.htm>)<br>`http://baike.baidu.com/view/6201506.htm` | 百科资料 / 可点击 | docs/notes/569110361.md:27<br>docs/notes/569286438.md:95<br>docs/notes/572997848.md:73 |
| [麦金托什](<http://baike.baidu.com/view/6785272.htm>)<br>`http://baike.baidu.com/view/6785272.htm` | 百科资料 / 可点击 | docs/about.md:28<br>docs/notes/577308827.md:17<br>docs/rooms/2793793.md:146 |
| [百科](<http://baike.baidu.com/view/746588.htm>)<br>`http://baike.baidu.com/view/746588.htm` | 百科资料 / 可点击 | docs/notes/525677843.md:144 |
| [马塞尔·杜尚](<http://baike.baidu.com/view/89347.htm>)<br>`http://baike.baidu.com/view/89347.htm` | 百科资料 / 可点击 | docs/notes/582498318.md:46 |
| [乔治·莫兰迪](<http://baike.baidu.com/view/89365.htm>)<br>`http://baike.baidu.com/view/89365.htm` | 百科资料 / 可点击 | docs/notes/582498318.md:43 |

### birthofblues.livedoor.biz

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [③](<http://birthofblues.livedoor.biz/archives/51638698.html>)<br>`http://birthofblues.livedoor.biz/archives/51638698.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/584217092.md:12 |

### blog.livedoor.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [《电影 轻音！》京都见面会](<http://blog.livedoor.jp/ht29_mymr/archives/65685595.html>)<br>`http://blog.livedoor.jp/ht29_mymr/archives/65685595.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/519165447.md:52<br>docs/rooms/2794136.md:57 |
| [「たまこラブストーリー」ひなこの歌の秘密について](<http://blog.livedoor.jp/tapiokasan/archives/53077277.html>)<br>`http://blog.livedoor.jp/tapiokasan/archives/53077277.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:60 |

### blog.sina.com.cn

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [诗人与世界的约定@任知的BLOG](<http://blog.sina.com.cn/s/blog_4ff891ac01013qjx.html>)<br>`http://blog.sina.com.cn/s/blog_4ff891ac01013qjx.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/314598362.md:16 |

### cgi2.nhk.or.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [ha](<https://cgi2.nhk.or.jp/signlanguage/enquete.cgi?md=syllabary&dno=26>)<br>`https://cgi2.nhk.or.jp/signlanguage/enquete.cgi?md=syllabary&dno=26` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/584217092.md:31 |
| [ba](<https://cgi2.nhk.or.jp/signlanguage/enquete.cgi?md=syllabary&dno=63>)<br>`https://cgi2.nhk.or.jp/signlanguage/enquete.cgi?md=syllabary&dno=63` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/584217092.md:31 |

### ch.nicovideo.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [たまこラブストーリーレビュー ～鴨川のうねりは流れゆく～（前編）](<http://ch.nicovideo.jp/animaimchan/blomaga/ar477417>)<br>`http://ch.nicovideo.jp/animaimchan/blomaga/ar477417` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:49 |
| [たまこラブストーリーレビュー ～鴨川の流れはうねりゆく～（後編）](<http://ch.nicovideo.jp/animaimchan/blomaga/ar580045>)<br>`http://ch.nicovideo.jp/animaimchan/blomaga/ar580045` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:50 |
| [ブロマガ版もぶおん学～けいおん！モブキャラ？](<http://ch.nicovideo.jp/mobonsociety/blomaga/ar140012>)<br>`http://ch.nicovideo.jp/mobonsociety/blomaga/ar140012` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:45 |
| [ブロマガ版もぶおん学～岡田春菜](<http://ch.nicovideo.jp/mobonsociety/blomaga/ar227153>)<br>`http://ch.nicovideo.jp/mobonsociety/blomaga/ar227153` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:46 |
| [けいおん！3年2組クラスメイト登場回数の分析](<http://ch.nicovideo.jp/mobonsociety/blomaga/ar344666>)<br>`http://ch.nicovideo.jp/mobonsociety/blomaga/ar344666` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:47 |
| [『たまこまーけっと』の魅力を語る](<http://ch.nicovideo.jp/wagwag/blomaga/ar121434>)<br>`http://ch.nicovideo.jp/wagwag/blomaga/ar121434` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/274238773.md:11<br>docs/rooms/2794121.md:23 |
| [『京都アニメーション』と『総合舞台芸術』](<http://ch.nicovideo.jp/wagwag/blomaga/ar183809>)<br>`http://ch.nicovideo.jp/wagwag/blomaga/ar183809` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:24 |
| [日常アニメの中のニーチェ](<http://ch.nicovideo.jp/wagwag/blomaga/ar580871>)<br>`http://ch.nicovideo.jp/wagwag/blomaga/ar580871` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:48 |

### chusingura.hatenablog.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [『たまこラブストーリー』に見た「映画」へのこだわり](<http://chusingura.hatenablog.jp/entry/2014/04/30/222041>)<br>`http://chusingura.hatenablog.jp/entry/2014/04/30/222041` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:51 |

### cinemacity.co.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [左より、山田尚子監督、音響家の増旭さん、鶴岡音響監督、音楽の牛尾憲輔さん http://cinemacity.co.jp/wp/ccnews/shape_of_voice_goku-on2/](<http://cinemacity.co.jp/wp/ccnews/shape_of_voice_goku-on2/>)<br>`http://cinemacity.co.jp/wp/ccnews/shape_of_voice_goku-on2/` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:16 |

### columii.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [聴覚障がい者の少女との交流描く『聲の形』 映画化への期待 http://columii.jp/movie/column/article-841.html](<http://columii.jp/movie/column/article-841.html>)<br>`http://columii.jp/movie/column/article-841.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:158 |

### crea.bunshun.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [https://crea.bunshun.jp/articles/59960](<https://crea.bunshun.jp/articles/59960>)<br>`https://crea.bunshun.jp/articles/59960` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/external/topic-499780453.md:12 |

### cycle-junrei.hatenablog.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [「たまこラブストーリー」の現実世界における時間軸の考察](<http://cycle-junrei.hatenablog.jp/entry/2014/06/16/225425>)<br>`http://cycle-junrei.hatenablog.jp/entry/2014/06/16/225425` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:52 |

### d.hatena.ne.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [少女たちの小さな秘密——山田尚子監督『映画 けいおん！』](<http://d.hatena.ne.jp/SomeCameRunning/touch/20111203>)<br>`http://d.hatena.ne.jp/SomeCameRunning/touch/20111203` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:37 |
| [音楽視点で見る「けいおん！」の世界1～「映画けいおん！」BGMの元ネタ集あれこれ](<http://d.hatena.ne.jp/los_endos/20130212/1360679189>)<br>`http://d.hatena.ne.jp/los_endos/20130212/1360679189` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:35 |
| [音楽視点で見る「けいおん！」の世界２～TVシリーズ・映画に登場した音楽ネタの徹底紹介！](<http://d.hatena.ne.jp/los_endos/20130217/1361107173>)<br>`http://d.hatena.ne.jp/los_endos/20130217/1361107173` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/429473097.md:12<br>docs/rooms/2794136.md:36 |
| [原画：山田尚子。山田非常喜欢小江（详见： http://d.hatena.ne.jp/los_endos/20131201/13859 ）。](<http://d.hatena.ne.jp/los_endos/20131201/13859>)<br>`http://d.hatena.ne.jp/los_endos/20131201/13859` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13431950.md:124 |
| [京都动画活动CTFK会场内设置的人像](<http://d.hatena.ne.jp/los_endos/20131201/1385905981>)<br>`http://d.hatena.ne.jp/los_endos/20131201/1385905981` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/347460778.md:29<br>docs/rooms/2794121.md:63 |
| [「たまこまーけっと」おさらい上映会＆制作スタッフ・トークイベント（山田尚子監督・小川太一さん・竹田明代さん）レポート](<http://d.hatena.ne.jp/los_endos/20140420/1398003204>)<br>`http://d.hatena.ne.jp/los_endos/20140420/1398003204` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/347460778.md:10<br>docs/rooms/2794121.md:65 |
| [【小論】映画「たまこラブストーリー」公開によせて ～フィルムと糸電話、時間と空間をつなぐもの](<http://d.hatena.ne.jp/los_endos/20140425/1398352708>)<br>`http://d.hatena.ne.jp/los_endos/20140425/1398352708` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:28 |
| [映画「たまこラブストーリー」で「星とピエロ」店内に登場するレコード・ジャケットのご紹介＋α](<http://d.hatena.ne.jp/los_endos/20140429/1398701112>)<br>`http://d.hatena.ne.jp/los_endos/20140429/1398701112` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:54 |
| [映画「たまこラブストーリー」大ヒット御礼 スタッフ舞台挨拶（山田尚子監督・小川太一さん・瀬波里梨P）レポート](<http://d.hatena.ne.jp/los_endos/20140601/1401549063>)<br>`http://d.hatena.ne.jp/los_endos/20140601/1401549063` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:67 |
| [映画『たまこラブストーリー』パッケージ発売記念上映&amp;スタッフ舞台挨拶レポート（山田尚子監督・中村伸一P・瀬波里梨P）](<http://d.hatena.ne.jp/los_endos/20141013/1413126122>)<br>`http://d.hatena.ne.jp/los_endos/20141013/1413126122` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:68 |
| [映画『たまこラブストーリー』第18回文化庁メディア芸術祭新人賞受賞記念：高橋良輔監督×山田尚子監督対談レポート](<http://d.hatena.ne.jp/los_endos/20150215/1424009846>)<br>`http://d.hatena.ne.jp/los_endos/20150215/1424009846` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:69 |
| [第２回京アニ＆Ｄｏファン感謝イベント：監督対談！＆山田尚子監督サイン会レポート](<http://d.hatena.ne.jp/los_endos/20151114/1447511739>)<br>`http://d.hatena.ne.jp/los_endos/20151114/1447511739` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/525677843.md:11<br>docs/rooms/2794121.md:70 |
| [「氷菓」14話を観て――山田尚子のカッティング・イン・マジック](<http://d.hatena.ne.jp/tatsu2/20120724/p1>)<br>`http://d.hatena.ne.jp/tatsu2/20120724/p1` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794117.md:55 |
| [『境界の彼方』5話 山田尚子演出を見る](<http://d.hatena.ne.jp/ukkah/20131105/p1>)<br>`http://d.hatena.ne.jp/ukkah/20131105/p1` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794117.md:57 |

### dengekionline.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [⑤](<http://dengekionline.com/elem/000/001/370/1370095/>)<br>`http://dengekionline.com/elem/000/001/370/1370095/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/583976644.md:12 |

### dic.nicovideo.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [「けいおん！モブキャラ」ニコニコ大百科](<http://dic.nicovideo.jp/id/4349661>)<br>`http://dic.nicovideo.jp/id/4349661` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:42 |

### dic.pixiv.net

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [「けいおん！！3年2組」ピクシブ百科事典](<http://dic.pixiv.net/a/%E3%81%91%E3%81%84%E3%81%8A%E3%82%93!!3%E5%B9%B42%E7%B5%84>)<br>`http://dic.pixiv.net/a/%E3%81%91%E3%81%84%E3%81%8A%E3%82%93!!3%E5%B9%B42%E7%B5%84` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:43 |

### dou.bz

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [电影《聲之形》9月17日上映！导演：山田尚子，剧本：吉田玲子，角色设计：西屋太志，制作：京都动画，官网：https://dou.bz/3ysQT1，官推：https://dou.bz/3yQaKK，特报：https://dou.bz/0vMqgF](<https://dou.bz/0vMqgF>)<br>`https://dou.bz/0vMqgF` | 短链接，待解析 / 纯文本 | docs/albums/13432051.md:15<br>docs/albums/13432051.md:16 |
| [山田的这张照片是在岐阜县的主题公园“养老天命反转地”取材时拍摄的。关于“养老天命反转地”可以看一下这篇介绍： https://dou.bz/0wRXIb 360°全景照： https://dou.bz/1vpgzh 这是作品中将也与硝子约会的地方。](<https://dou.bz/0wRXIb>)<br>`https://dou.bz/0wRXIb` | 短链接，待解析 / 纯文本 | docs/albums/190597061.md:79 |
| [【第2回 京アニ＆Do ファン感謝イベント 2015.10.31】今天的山田尚子，米色黑圆点连衣裙。（图by twitter ID: honekawap）（帽子好像是这顶→ https://dou.bz/1pDOrE ）](<https://dou.bz/1pDOrE>)<br>`https://dou.bz/1pDOrE` | 短链接，待解析 / 纯文本 | docs/albums/13433748.md:21<br>docs/albums/13433748.md:22 |
| [山田的这张照片是在岐阜县的主题公园“养老天命反转地”取材时拍摄的。关于“养老天命反转地”可以看一下这篇介绍： https://dou.bz/0wRXIb 360°全景照： https://dou.bz/1vpgzh 这是作品中将也与硝子约会的地方。](<https://dou.bz/1vpgzh>)<br>`https://dou.bz/1vpgzh` | 短链接，待解析 / 纯文本 | docs/albums/190597061.md:79 |
| [日本瑞穗金融集团 CM 电影《聲之形》篇 30秒 https://dou.bz/3fRkJT](<https://dou.bz/3fRkJT>)<br>`https://dou.bz/3fRkJT` | 短链接，待解析 / 纯文本 | docs/albums/190597061.md:17 |
| [电影《聲之形》9月17日上映！导演：山田尚子，剧本：吉田玲子，角色设计：西屋太志，制作：京都动画，官网：https://dou.bz/3ysQT1，官推：https://dou.bz/3yQaKK，特报：https://dou.bz/0vMqgF](<https://dou.bz/3yQaKK>)<br>`https://dou.bz/3yQaKK` | 短链接，待解析 / 纯文本 | docs/albums/13432051.md:15<br>docs/albums/13432051.md:16 |
| [电影《聲之形》9月17日上映！导演：山田尚子，剧本：吉田玲子，角色设计：西屋太志，制作：京都动画，官网：https://dou.bz/3ysQT1，官推：https://dou.bz/3yQaKK，特报：https://dou.bz/0vMqgF](<https://dou.bz/3ysQT1>)<br>`https://dou.bz/3ysQT1` | 短链接，待解析 / 纯文本 | docs/albums/13432051.md:15<br>docs/albums/13432051.md:16 |

### douc.cc

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [山田尚子与索菲亚·科波拉 https://douc.cc/0MItgA 山田曾在访谈中说过自己喜欢导演索菲亚·科波拉的作品（ https://douc.cc/00eIqo ）。在最新的《中二戀》ED中也能窥见索菲亚对山田的影响（截图出自索菲亚·科波拉的代表作 《处女之死》）。](<https://douc.cc/00eIqo>)<br>`https://douc.cc/00eIqo` | 短链接，待解析 / 纯文本 | docs/broadcast/page/80.md:30 |
| [【重新推荐下这四篇访谈（必读！）】官网导演访谈（上映前） https://douc.cc/01SUy9 https://douc.cc/1eIOys excite导演访谈（上映后） https://douc.cc/4hTTqG https://douc.cc/3Jc6Wt # 玉](<https://douc.cc/01SUy9>)<br>`https://douc.cc/01SUy9` | 短链接，待解析 / 纯文本 | docs/broadcast/page/49.md:26 |
| [舞台挨拶&amp;プリンシプルについて](<https://douc.cc/01fLZk>)<br>`https://douc.cc/01fLZk` | 短链接，待解析 / 可点击 | docs/broadcast/page/65.md:26 |
| [《轻音!!》Blu-ray BOX展开图公开，设计风格与一期BDBOX相同。 https://douc.cc/02QoCw](<https://douc.cc/02QoCw>)<br>`https://douc.cc/02QoCw` | 短链接，待解析 / 纯文本 | docs/broadcast/page/45.md:30 |
| [电影《声之形》首张宣传画浅谈](<https://douc.cc/02l4zD>)<br>`https://douc.cc/02l4zD` | 短链接，待解析 / 可点击 | docs/broadcast/page/24.md:26 |
| [https://douc.cc/043kin](<https://douc.cc/043kin>)<br>`https://douc.cc/043kin` | 短链接，待解析 / 纯文本 | docs/broadcast/page/82.md:32 |
| [电影《聲之形》京阿尼shop!周边商品已开通网购预定 https://douc.cc/4m8QGF ，重点是官方设定集。 https://douc.cc/04ea5n # 声之形 #](<https://douc.cc/04ea5n>)<br>`https://douc.cc/04ea5n` | 短链接，待解析 / 纯文本 | docs/broadcast/page/11.md:20 |
| [そうだ たまこラブストーリー、観よう。](<https://douc.cc/053ccv>)<br>`https://douc.cc/053ccv` | 短链接，待解析 / 可点击 | docs/broadcast/page/67.md:28 |
| [【たまこラブストーリー】 読解メモ 08](<https://douc.cc/05r9Ez>)<br>`https://douc.cc/05r9Ez` | 短链接，待解析 / 可点击 | docs/broadcast/page/62.md:18 |
| [兔子山的视频《asaichi》2016年9月2日 电影《声之形》宣传视频](<https://douc.cc/05uEfy>)<br>`https://douc.cc/05uEfy` | 短链接，待解析 / 可点击 | docs/broadcast/page/17.md:24 |
| [「たまこラブストーリー」オリジナルポップコーンセット発売決定！！ https://douc.cc/07OHDB](<https://douc.cc/07OHDB>)<br>`https://douc.cc/07OHDB` | 短链接，待解析 / 纯文本 | docs/broadcast/page/74.md:28 |
| [「たまこラブストーリー」第３週目 入場者プレゼント 配布決定！ https://douc.cc/0A8LSE](<https://douc.cc/0A8LSE>)<br>`https://douc.cc/0A8LSE` | 短链接，待解析 / 纯文本 | docs/broadcast/page/71.md:28 |
| [《玉子爱情故事》的Blu-ray＆DVD将于10月4日在新宿Piccadilly举行的发售纪念活动会场上先行发售 https://douc.cc/0AvELN](<https://douc.cc/0AvELN>)<br>`https://douc.cc/0AvELN` | 短链接，待解析 / 纯文本 | docs/broadcast/page/53.md:24 |
| [正解は、金沢駅でした♪](<https://douc.cc/0BY0hr>)<br>`https://douc.cc/0BY0hr` | 短链接，待解析 / 可点击 | docs/broadcast/page/58.md:26 |
| [兔子山的视频『響け！ユーフォニアム』番宣CM](<https://douc.cc/0C7U4M>)<br>`https://douc.cc/0C7U4M` | 短链接，待解析 / 可点击 | docs/broadcast/page/39.md:22 |
| [兔子山的视频KAエスマ文庫『たまこラブストーリー ノベライズ』 TVCM2](<https://douc.cc/0CB5j3>)<br>`https://douc.cc/0CB5j3` | 短链接，待解析 / 可点击 | docs/broadcast/page/58.md:18 |
| [【声优广播】洲崎绫和林原惠美的童话故事【微笑背后的辛酸】&#91;中文字幕&#93;](<https://douc.cc/0CzfUs>)<br>`https://douc.cc/0CzfUs` | 短链接，待解析 / 可点击 | docs/broadcast/page/51.md:26 |
| [アニメ『けいおん！』5周年アニバーサリーを記念して、コルグ「RK-100S けいおん！スペシャル」の誕生です。](<https://douc.cc/0DTHoZ>)<br>`https://douc.cc/0DTHoZ` | 短链接，待解析 / 可点击 | docs/broadcast/page/43.md:26 |
| [【京阿尼Shop】《玉子爱情故事》2015年月历已开通预定 https://douc.cc/0DgxVZ](<https://douc.cc/0DgxVZ>)<br>`https://douc.cc/0DgxVZ` | 短链接，待解析 / 纯文本 | docs/broadcast/page/51.md:18 |
| [兔子山的视频洲崎綾「本物だ～」林原めぐみ「動いてるよ！」（2014年4月）](<https://douc.cc/0ETAWA>)<br>`https://douc.cc/0ETAWA` | 短链接，待解析 / 可点击 | docs/broadcast/page/61.md:32 |
| [【山田尚子作品考】 「映画けいおん！」「たまこラブストーリー」そして…](<https://douc.cc/0FBrUw>)<br>`https://douc.cc/0FBrUw` | 短链接，待解析 / 可点击 | docs/broadcast/page/61.md:20 |
| [(仮) 映画「たまこラブストーリー」オリジナル・サウンドトラック 2014年7月16日発売予定 https://douc.cc/0FgYWt](<https://douc.cc/0FgYWt>)<br>`https://douc.cc/0FgYWt` | 短链接，待解析 / 纯文本 | docs/broadcast/page/64.md:26 |
| [祝けいおん！５周年☆パピコ](<https://douc.cc/0IRjQR>)<br>`https://douc.cc/0IRjQR` | 短链接，待解析 / 可点击 | docs/broadcast/page/84.md:24 |
| [短篇《南国之岛的小德拉》将与《玉子爱情故事》同时上映！该短篇将描绘从兔子山商店街回到南国后的德拉，以及他与王子和乔伊温暖喧闹的日常。 https://douc.cc/0IW5Dj](<https://douc.cc/0IW5Dj>)<br>`https://douc.cc/0IW5Dj` | 短链接，待解析 / 纯文本 | docs/broadcast/page/79.md:26 |
| [饼藏正努力成为Mars=男人=大人，ED最后闪耀在青空中的是Venus——启明星=金星。本作正是描写站在宇宙的入口感到胆怯的玉子，最终成为闪耀在宇宙中的一颗星（金星）的故事——少年少女成为男人女人、成为大人的故事。 https://douc.cc/0KSdUc # 玉子爱情故事 ](<https://douc.cc/0KSdUc>)<br>`https://douc.cc/0KSdUc` | 短链接，待解析 / 纯文本 | docs/broadcast/page/48.md:32<br>docs/broadcast/page/49.md:14 |
| [情人节企划，附饼藏文件夹的预售票发售决定，详见： https://douc.cc/0LAcPz https://douc.cc/1XKYAg](<https://douc.cc/0LAcPz>)<br>`https://douc.cc/0LAcPz` | 短链接，待解析 / 纯文本 | docs/broadcast/page/79.md:16 |
| [兔子山的视频『たまこラブストーリー』特報第2弾 たまこ CM](<https://douc.cc/0LuWql>)<br>`https://douc.cc/0LuWql` | 短链接，待解析 / 可点击 | docs/broadcast/page/79.md:20 |
| [山田尚子与索菲亚·科波拉 https://douc.cc/0MItgA 山田曾在访谈中说过自己喜欢导演索菲亚·科波拉的作品（ https://douc.cc/00eIqo ）。在最新的《中二戀》ED中也能窥见索菲亚对山田的影响（截图出自索菲亚·科波拉的代表作 《处女之死》）。](<https://douc.cc/0MItgA>)<br>`https://douc.cc/0MItgA` | 短链接，待解析 / 纯文本 | docs/broadcast/page/80.md:30 |
| [兔子山的视频《吹响悠风号2》PV第2弹](<https://douc.cc/0NIhmG>)<br>`https://douc.cc/0NIhmG` | 短链接，待解析 / 可点击 | docs/broadcast/page/15.md:30 |
| [第二届京阿尼＆Do答谢会官网活动报告 https://douc.cc/0NLJgs](<https://douc.cc/0NLJgs>)<br>`https://douc.cc/0NLJgs` | 短链接，待解析 / 纯文本 | docs/broadcast/page/27.md:32 |
| [【たまこラブストーリー】 読解メモ 03 追補](<https://douc.cc/0Nzw8k>)<br>`https://douc.cc/0Nzw8k` | 短链接，待解析 / 可点击 | docs/broadcast/page/67.md:14 |
| [【自翻】【一之濑六树】玉子的爱情故事/Tamako love story-轻之国度](<https://douc.cc/0O8XU1>)<br>`https://douc.cc/0O8XU1` | 短链接，待解析 / 可点击 | docs/broadcast/page/32.md:20 |
| [映画興行成績：GW新作トップは「テルマエ・ロマエ2」](<https://douc.cc/0OASzl>)<br>`https://douc.cc/0OASzl` | 短链接，待解析 / 可点击 | docs/broadcast/page/68.md:16 |
| [「Free!ES」第12話！絵コンテ・演出／山田尚子を堪能する!! その２](<https://douc.cc/0QtHPA>)<br>`https://douc.cc/0QtHPA` | 短链接，待解析 / 可点击 | docs/broadcast/page/54.md:30 |
| [站在宇宙入口的3名少女的故事——《玉子爱情故事》小说7月发售决定！其中包含电影剧情的“玉子”及“小绿”视点篇，凝聚了电影中所未能讲述的两人的情感，此外还收录原创故事“乔伊篇”，描写在南国之岛为寻找王妃而奔走的乔伊的恋心。小说官网： https://douc.cc/0QuvAq](<https://douc.cc/0QuvAq>)<br>`https://douc.cc/0QuvAq` | 短链接，待解析 / 纯文本 | docs/broadcast/page/74.md:26 |
| [『たまこラブストーリー』 「もち蔵」という名前の意味と、山田監督が言う「映画」と、あんこちゃんがやたらエロいのは恋愛年齢が高いから](<https://douc.cc/0Tl2BW>)<br>`https://douc.cc/0Tl2BW` | 短链接，待解析 / 可点击 | docs/broadcast/page/67.md:20 |
| [【考察】 続・空の向こう、星の彼方](<https://douc.cc/0UbAym>)<br>`https://douc.cc/0UbAym` | 短链接，待解析 / 可点击 | docs/broadcast/page/82.md:20 |
| [じんわりほっこり](<https://douc.cc/0WV2iC>)<br>`https://douc.cc/0WV2iC` | 短链接，待解析 / 可点击 | docs/broadcast/page/69.md:22 |
| [「日常系ダイアリー――アニメ批評のためのメモランダム」第06回 うさぎ山商店街・天使の詩――『たまこラブストーリー』試論（前編）／文：高瀬司（アニメルカ）](<https://douc.cc/0Xz8hN>)<br>`https://douc.cc/0Xz8hN` | 短链接，待解析 / 可点击 | docs/broadcast/page/57.md:24 |
| [兔子山的视频电影《声之形》TVCM 2](<https://douc.cc/0bDB0V>)<br>`https://douc.cc/0bDB0V` | 短链接，待解析 / 可点击 | docs/broadcast/page/16.md:20 |
| [兔子山的视频『たまこラブストーリー ノベライズ』 TV CM](<https://douc.cc/0bpg30>)<br>`https://douc.cc/0bpg30` | 短链接，待解析 / 可点击 | docs/broadcast/page/73.md:28 |
| [TVアニメ『たまこまーけっと』キャラソンリミックス「omochi-tronica EP plus」４月９日発売決定！ https://douc.cc/0dxXj7](<https://douc.cc/0dxXj7>)<br>`https://douc.cc/0dxXj7` | 短链接，待解析 / 纯文本 | docs/broadcast/page/76.md:14 |
| [劇場販売商品 https://douc.cc/0eCWQw](<https://douc.cc/0eCWQw>)<br>`https://douc.cc/0eCWQw` | 短链接，待解析 / 纯文本 | docs/broadcast/page/75.md:32 |
| [『たまこラブストーリー』 公開初日の京都に行ってみた](<https://douc.cc/0eHYUd>)<br>`https://douc.cc/0eHYUd` | 短链接，待解析 / 可点击 | docs/broadcast/page/69.md:14 |
| [电影 轻音！全程解说](<https://douc.cc/0eT1J7>)<br>`https://douc.cc/0eT1J7` | 短链接，待解析 / 可点击 | docs/broadcast/page/83.md:30 |
| [《玉子爱情故事》主题歌CD信息公开，4月30日发售 https://douc.cc/0eaK0C](<https://douc.cc/0eaK0C>)<br>`https://douc.cc/0eaK0C` | 短链接，待解析 / 纯文本 | docs/broadcast/page/77.md:32 |
| [【たまこラブストーリー】 読解メモ 06](<https://douc.cc/0hJWqk>)<br>`https://douc.cc/0hJWqk` | 短链接，待解析 / 可点击 | docs/broadcast/page/63.md:20 |
| [# 吹响悠风号 # 官网更新第1集STAFF评语 https://douc.cc/0hLsQZ 系列演出山田尚子的评语翻译如上](<https://douc.cc/0hLsQZ>)<br>`https://douc.cc/0hLsQZ` | 短链接，待解析 / 纯文本 | docs/broadcast/page/37.md:30<br>docs/broadcast/page/38.md:18 |
| [兔子山的视频电影《聲之形》特集（《闹钟电视》20160927）](<https://douc.cc/0hr9ek>)<br>`https://douc.cc/0hr9ek` | 短链接，待解析 / 可点击 | docs/broadcast/page/10.md:30 |
| [「たまこラブストーリー」が、傑作だと確信できたのはなぜか](<https://douc.cc/0ilPva>)<br>`https://douc.cc/0ilPva` | 短链接，待解析 / 可点击 | docs/broadcast/page/70.md:32 |
| [《玉子爱情故事》特报第2弹公开 https://douc.cc/0iq7ao](<https://douc.cc/0iq7ao>)<br>`https://douc.cc/0iq7ao` | 短链接，待解析 / 纯文本 | docs/broadcast/page/79.md:24 |
| [映画けいおん！時系列順作品解説（2013ver.） https://douc.cc/0jhA26 旧版刚翻完大半又冒出个2013ver.…orz](<https://douc.cc/0jhA26>)<br>`https://douc.cc/0jhA26` | 短链接，待解析 / 纯文本 | docs/broadcast/page/84.md:22 |
| [第４回：対談 片岡知子＋山口優（後編）～全編にちりばめられた80′sっぽさ &#124; マニュエラだから作れた『たまこまーけっと』の音楽 &#124; RandoM](<https://douc.cc/0kUWI1>)<br>`https://douc.cc/0kUWI1` | 短链接，待解析 / 可点击 | docs/broadcast/page/86.md:32 |
| [【たまこラブストーリー】 感想その２ 『本作の作劇はいかにして携帯を克服したかｗ』 【感想】](<https://douc.cc/0nayuz>)<br>`https://douc.cc/0nayuz` | 短链接，待解析 / 可点击 | docs/broadcast/page/59.md:14 |
| [高橋良輔監督×山田尚子監督対談レポート](<https://douc.cc/0oNLii>)<br>`https://douc.cc/0oNLii` | 短链接，待解析 / 可点击 | docs/broadcast/page/39.md:30 |
| [第二届京阿尼＆Do答谢会上出售的商品京阿尼商店已开通网购预定，12月13日截单，2016年2月中旬发货。 https://douc.cc/0ouLFE](<https://douc.cc/0ouLFE>)<br>`https://douc.cc/0ouLFE` | 短链接，待解析 / 纯文本 | docs/broadcast/page/28.md:16 |
| [电影《玉子爱情故事》官网开放 https://douc.cc/2hhDGR 特报第1弹公开 https://douc.cc/0rpuuO # tamakolovestory #](<https://douc.cc/0rpuuO>)<br>`https://douc.cc/0rpuuO` | 短链接，待解析 / 纯文本 | docs/broadcast/page/84.md:16 |
| [けいおん！3年2組クラスメイト登場回数の分析](<https://douc.cc/0s574h>)<br>`https://douc.cc/0s574h` | 短链接，待解析 / 可点击 | docs/broadcast/page/78.md:24 |
| [电影《玉子爱情故事》今日公映，场刊等剧场贩售商品已开通网购 https://douc.cc/0sPwnp](<https://douc.cc/0sPwnp>)<br>`https://douc.cc/0sPwnp` | 短链接，待解析 / 纯文本 | docs/broadcast/page/72.md:16 |
| [兔子山的视频TVアニメ『響け！ユーフォニアム』PV](<https://douc.cc/0uEumE>)<br>`https://douc.cc/0uEumE` | 短链接，待解析 / 可点击 | docs/broadcast/page/40.md:32 |
| [兔子山的视频电影《声之形》正式版预告片（日文字幕）](<https://douc.cc/0udTzf>)<br>`https://douc.cc/0udTzf` | 短链接，待解析 / 可点击 | docs/broadcast/page/18.md:28 |
| [电影《声之形》9月17日上映！导演：山田尚子，剧本：吉田玲子，角色设计：西屋太志，制作：京都动画，官网： https://douc.cc/3ysQT1 ，官推： https://douc.cc/3yQaKK ，特报： https://douc.cc/0vMqgF](<https://douc.cc/0vMqgF>)<br>`https://douc.cc/0vMqgF` | 短链接，待解析 / 纯文本 | docs/broadcast/page/25.md:16 |
| [明日はproject758のニコ生です☆](<https://douc.cc/0vVkNC>)<br>`https://douc.cc/0vVkNC` | 短链接，待解析 / 可点击 | docs/broadcast/page/52.md:26 |
| [山田的这张照片（图1）是在岐阜县的主题公园“养老天命反转地”（图2）取材时拍摄的。关于“养老天命反转地”可以看一下这篇介绍： https://douc.cc/0wRXIb 360°全景照： https://douc.cc/1vpgzh 这是作品中将也与硝子约会的地方（图3）。 #](<https://douc.cc/0wRXIb>)<br>`https://douc.cc/0wRXIb` | 短链接，待解析 / 纯文本 | docs/broadcast/page/13.md:30 |
| [电影《声之形》NHK报道 4分钟新画面公开（asaichi 20160902）](<https://douc.cc/0xHGtX>)<br>`https://douc.cc/0xHGtX` | 短链接，待解析 / 可点击 | docs/broadcast/page/17.md:28 |
| [《声之形》2016年秋季上映。 来源：松竹电影新闻网站 https://douc.cc/0xXPdW](<https://douc.cc/0xXPdW>)<br>`https://douc.cc/0xXPdW` | 短链接，待解析 / 纯文本 | docs/broadcast/page/27.md:22 |
| [兔子山的视频『たまこラブストーリー』TVスポット](<https://douc.cc/0zyH0C>)<br>`https://douc.cc/0zyH0C` | 短链接，待解析 / 可点击 | docs/broadcast/page/76.md:30 |
| [昨天说的25万的吉他（限定生产55把）已经卖完了w https://douc.cc/10HJnT](<https://douc.cc/10HJnT>)<br>`https://douc.cc/10HJnT` | 短链接，待解析 / 纯文本 | docs/broadcast/page/43.md:16 |
| [映画『たまこラブストーリー』 評判良すぎいいいいいい！ 「青春期の恋愛映画としては、お手本になるかのような作り」 女性客も多め！](<https://douc.cc/10nNGU>)<br>`https://douc.cc/10nNGU` | 短链接，待解析 / 可点击 | docs/broadcast/page/71.md:14 |
| [たまこラブストーリースタッフさん舞台挨拶](<https://douc.cc/10vIt5>)<br>`https://douc.cc/10vIt5` | 短链接，待解析 / 可点击 | docs/broadcast/page/60.md:16 |
| [兔子山的视频电影《聲之形》公映纪念特别节目～电影《聲之形》的制作历程～ 加长版](<https://douc.cc/11E3dN>)<br>`https://douc.cc/11E3dN` | 短链接，待解析 / 可点击 | docs/broadcast/page/11.md:24 |
| [『たまこラブストーリー』がミニシアターランキングで3週連続１位に！評判良すぎいいいいい](<https://douc.cc/13BUQp>)<br>`https://douc.cc/13BUQp` | 短链接，待解析 / 可点击 | docs/broadcast/page/63.md:22 |
| [【新增小学生将也cv.松冈茉优相关感言】电影《声之形》配音完成感想 https://douc.cc/13b68D # 声之形 #](<https://douc.cc/13b68D>)<br>`https://douc.cc/13b68D` | 短链接，待解析 / 纯文本 | docs/broadcast/page/20.md:28 |
| [「たまこまーけっと」おさらい上映会＆制作スタッフ・トークイベント（山田尚子監督・小川太一さん・竹田明代さん）レポート](<https://douc.cc/13l2fN>)<br>`https://douc.cc/13l2fN` | 短链接，待解析 / 可点击 | docs/broadcast/page/74.md:16 |
| [《Free! Eternal Summer》第12话演出分析](<https://douc.cc/15PU7d>)<br>`https://douc.cc/15PU7d` | 短链接，待解析 / 可点击 | docs/broadcast/page/54.md:20 |
| [【たまこラブストーリー】京アニショップ！限定・堀口悠紀子描き下ろし「“たまこ・あんこ”ラバーストラップ」付きオリジナルイラスト前売券 予約受付開始！専用窓口⇒ https://douc.cc/3M2zO1 特設サイト⇒ https://douc.cc/16CyJf](<https://douc.cc/16CyJf>)<br>`https://douc.cc/16CyJf` | 短链接，待解析 / 纯文本 | docs/broadcast/page/78.md:20 |
| [京都！](<https://douc.cc/16ddCB>)<br>`https://douc.cc/16ddCB` | 短链接，待解析 / 可点击 | docs/broadcast/page/66.md:26 |
| [たまこラブストーリーを褒める](<https://douc.cc/1732Ot>)<br>`https://douc.cc/1732Ot` | 短链接，待解析 / 可点击 | docs/broadcast/page/68.md:14 |
| [しゅがーちゅーん。名古屋と大阪。2014.08.30 Saturday](<https://douc.cc/173qI8>)<br>`https://douc.cc/173qI8` | 短链接，待解析 / 可点击 | docs/broadcast/page/56.md:18 |
| [幕后](<https://douc.cc/18KnGD>)<br>`https://douc.cc/18KnGD` | 短链接，待解析 / 可点击 | docs/broadcast/page/88.md:24 |
| [【たまこラブストーリー】 読解メモ 09](<https://douc.cc/1CvfMS>)<br>`https://douc.cc/1CvfMS` | 短链接，待解析 / 可点击 | docs/broadcast/page/61.md:28 |
| [映画☆パピコ](<https://douc.cc/1DNxmN>)<br>`https://douc.cc/1DNxmN` | 短链接，待解析 / 可点击 | docs/broadcast/page/57.md:26 |
| [5月15日は高坂麗奈の誕生日なのです！！おめでとう麗奈！ということで、石原監督が現場で即興で描いてくださいました！！久美子の後ろ姿ww https://douc.cc/1FFTJy # 吹响悠风号 #](<https://douc.cc/1FFTJy>)<br>`https://douc.cc/1FFTJy` | 短链接，待解析 / 纯文本 | docs/broadcast/page/36.md:24 |
| [兔子山的视频『たまこラブストーリー』特報第1弾](<https://douc.cc/1JWKVR>)<br>`https://douc.cc/1JWKVR` | 短链接，待解析 / 可点击 | docs/broadcast/page/83.md:32 |
| [【きゃにめ.jp限定特典】「たまこラブストーリー」 Blu-ray&amp;DVD発売告知ポスター https://douc.cc/1KeStY](<https://douc.cc/1KeStY>)<br>`https://douc.cc/1KeStY` | 短链接，待解析 / 纯文本 | docs/broadcast/page/56.md:22 |
| [劇場版アニメ『たまこラブストーリー』がついに公開。公開初日には洲崎綾・田丸篤志・...](<https://douc.cc/1Kg2lW>)<br>`https://douc.cc/1Kg2lW` | 短链接，待解析 / 可点击 | docs/broadcast/page/70.md:30 |
| [たまこラブストーリー舞台探訪記〜前編〜](<https://douc.cc/1LktvO>)<br>`https://douc.cc/1LktvO` | 短链接，待解析 / 可点击 | docs/broadcast/page/61.md:18 |
| [「たまこまーけっと」とジャンプカット](<https://douc.cc/1LyX1P>)<br>`https://douc.cc/1LyX1P` | 短链接，待解析 / 可点击 | docs/broadcast/page/86.md:24 |
| [山田監督、おめでとうございます♪](<https://douc.cc/1MDXF8>)<br>`https://douc.cc/1MDXF8` | 短链接，待解析 / 可点击 | docs/broadcast/page/42.md:26 |
| [兔子山的视频TVアニメ『たまこまーけっと』Blu-ray Box PV](<https://douc.cc/1N97vc>)<br>`https://douc.cc/1N97vc` | 短链接，待解析 / 可点击 | docs/broadcast/page/41.md:22 |
| [幕后](<https://douc.cc/1NPZ6Q>)<br>`https://douc.cc/1NPZ6Q` | 短链接，待解析 / 可点击 | docs/broadcast/page/88.md:14 |
| [《玉子爱情故事》预告片](<https://douc.cc/1OeUww>)<br>`https://douc.cc/1OeUww` | 短链接，待解析 / 可点击 | docs/broadcast/page/77.md:18 |
| [《剧场版 # 吹响悠风号 #～欢迎来到北宇治高中吹奏乐部～》Blu-ray &amp; DVD 2016年9月7日发售，详情见官网： https://douc.cc/1PMxu5](<https://douc.cc/1PMxu5>)<br>`https://douc.cc/1PMxu5` | 短链接，待解析 / 纯文本 | docs/broadcast/page/21.md:22 |
| [《玉子爱情故事》官网更新，故事简介公开 https://douc.cc/1QsVCH](<https://douc.cc/1QsVCH>)<br>`https://douc.cc/1QsVCH` | 短链接，待解析 / 纯文本 | docs/broadcast/page/83.md:26 |
| [映画『たまこラブストーリー』パッケージ発売記念上映&amp;スタッフ舞台挨拶レポート（山田尚子監督・中村伸一P・瀬波里梨P）](<https://douc.cc/1R2NDD>)<br>`https://douc.cc/1R2NDD` | 短链接，待解析 / 可点击 | docs/broadcast/page/48.md:20 |
| [THEATER &#124; 『たまこラブストーリー』公式サイト](<https://douc.cc/1RbQlm>)<br>`https://douc.cc/1RbQlm` | 短链接，待解析 / 可点击 | docs/broadcast/page/52.md:18 |
| [兔子山的视频『たまこラブストーリー』特報第2弾](<https://douc.cc/1SIgSR>)<br>`https://douc.cc/1SIgSR` | 短链接，待解析 / 可点击 | docs/broadcast/page/79.md:22 |
| [《剧场版 吹响悠风号～欢迎来到北宇治高中吹奏乐部～》新海报公布！附赠情人节主题双面B2海报（三种随机发放）的预售票2月14日起发售！ https://douc.cc/1SKW10 # 吹响悠风号 #](<https://douc.cc/1SKW10>)<br>`https://douc.cc/1SKW10` | 短链接，待解析 / 纯文本 | docs/broadcast/page/26.md:20<br>docs/broadcast/page/28.md:22<br>docs/broadcast/page/29.md:28<br>docs/broadcast/page/39.md:18<br>docs/broadcast/page/40.md:20<br>docs/broadcast/page/40.md:24<br>docs/broadcast/page/41.md:14 |
| [「たまこラブストーリー」山田尚子監督インタビュー 第18回文化庁メディア芸術祭ア...](<https://douc.cc/1SRP5j>)<br>`https://douc.cc/1SRP5j` | 短链接，待解析 / 可点击 | docs/broadcast/page/40.md:22 |
| [兔子山的视频『たまこラブストーリー』特報第2弾 もち蔵 CM](<https://douc.cc/1UC3QQ>)<br>`https://douc.cc/1UC3QQ` | 短链接，待解析 / 可点击 | docs/broadcast/page/79.md:18 |
| [【限定生産55本】けいおん！／平沢唯レプリカギター Limited Edition https://douc.cc/1UDJcL 价格和剧中一样是25万w，能还价到5万吗www](<https://douc.cc/1UDJcL>)<br>`https://douc.cc/1UDJcL` | 短链接，待解析 / 纯文本 | docs/broadcast/page/43.md:20 |
| [《玉子爱情故事》荣获第18届文化厅媒体艺术节动画部门新人奖，高桥良辅致颁奖词 https://douc.cc/1ULxAC](<https://douc.cc/1ULxAC>)<br>`https://douc.cc/1ULxAC` | 短链接，待解析 / 纯文本 | docs/broadcast/page/42.md:30 |
| [https://douc.cc/1UMqh3](<https://douc.cc/1UMqh3>)<br>`https://douc.cc/1UMqh3` | 短链接，待解析 / 纯文本 | docs/broadcast/page/50.md:32 |
| [「たまこラブストーリー」総論：「橋」の物語としてのたまラブ](<https://douc.cc/1UTfuN>)<br>`https://douc.cc/1UTfuN` | 短链接，待解析 / 可点击 | docs/broadcast/page/63.md:24 |
| [映画『たまこラブストーリー』山田尚子 監督インタビュー（後編）](<https://douc.cc/1VZRQC>)<br>`https://douc.cc/1VZRQC` | 短链接，待解析 / 可点击 | docs/broadcast/page/73.md:24 |
| [【たまこラブストーリー】 読解メモ 05](<https://douc.cc/1Vwzvq>)<br>`https://douc.cc/1Vwzvq` | 短链接，待解析 / 可点击 | docs/broadcast/page/64.md:32 |
| [情人节企划，附饼藏文件夹的预售票发售决定，详见： https://douc.cc/0LAcPz https://douc.cc/1XKYAg](<https://douc.cc/1XKYAg>)<br>`https://douc.cc/1XKYAg` | 短链接，待解析 / 纯文本 | docs/broadcast/page/79.md:16 |
| [出町桝形商店街 Demachi Masugata Shotengai](<https://douc.cc/1XPnAz>)<br>`https://douc.cc/1XPnAz` | 短链接，待解析 / 可点击 | docs/broadcast/page/72.md:28 |
| [山田尚子さんの発言から - la banane brûléeの日記](<https://douc.cc/1XtmXX>)<br>`https://douc.cc/1XtmXX` | 短链接，待解析 / 可点击 | docs/broadcast/page/84.md:32 |
| [舞台挨拶～母の日編～](<https://douc.cc/1Z1tJY>)<br>`https://douc.cc/1Z1tJY` | 短链接，待解析 / 可点击 | docs/broadcast/page/61.md:26 |
| [兔子山的视频TVアニメ『響け！ユーフォニアム』PV第2弾](<https://douc.cc/1ZJmy8>)<br>`https://douc.cc/1ZJmy8` | 短链接，待解析 / 可点击 | docs/broadcast/page/38.md:24 |
| [兔子山的视频《聲之形》ZIP!特集（20161027）](<https://douc.cc/1ZVxqJ>)<br>`https://douc.cc/1ZVxqJ` | 短链接，待解析 / 可点击 | docs/broadcast/page/8.md:14 |
| [山田的桌子上挂着饼藏的照片，上面放着堀口悠纪子画的玉子和饼藏。还有在京阿尼答谢会（ https://douc.cc/1b5rD3 ）上展示过的耳机AKG K404。](<https://douc.cc/1b5rD3>)<br>`https://douc.cc/1b5rD3` | 短链接，待解析 / 纯文本 | docs/broadcast/page/13.md:22 |
| [4/19《玉子市场》温习上映会&amp;制作人员漫谈会活动报告](<https://douc.cc/1ciLTh>)<br>`https://douc.cc/1ciLTh` | 短链接，待解析 / 可点击 | docs/broadcast/page/67.md:18 |
| [兔子山的视频电影《声之形》公映纪念特别节目～电影《声之形》的制作历程～](<https://douc.cc/1dMRvN>)<br>`https://douc.cc/1dMRvN` | 短链接，待解析 / 可点击 | docs/broadcast/page/13.md:24 |
| [【重新推荐下这四篇访谈（必读！）】官网导演访谈（上映前） https://douc.cc/01SUy9 https://douc.cc/1eIOys excite导演访谈（上映后） https://douc.cc/4hTTqG https://douc.cc/3Jc6Wt # 玉](<https://douc.cc/1eIOys>)<br>`https://douc.cc/1eIOys` | 短链接，待解析 / 纯文本 | docs/broadcast/page/49.md:26 |
| [『境界の彼方』5話 山田尚子演出を見る - OTALLICA](<https://douc.cc/1gAMfz>)<br>`https://douc.cc/1gAMfz` | 短链接，待解析 / 可点击 | docs/broadcast/page/85.md:24 |
| [《玉子爱情故事》第2周早期入场特典明信片。与第1周玉子写给乔伊的明信片（ https://douc.cc/1gRFRG https://douc.cc/21vtfQ ）相呼应，这次是乔伊给玉子的回信。文中的错别字非常可爱——“たもこ”、“たくちんたくちんありもす”…](<https://douc.cc/1gRFRG>)<br>`https://douc.cc/1gRFRG` | 短链接，待解析 / 纯文本 | docs/broadcast/page/66.md:20 |
| [ただいま！](<https://douc.cc/1isFCB>)<br>`https://douc.cc/1isFCB` | 短链接，待解析 / 可点击 | docs/broadcast/page/66.md:24 |
| [ありがとうございました。](<https://douc.cc/1jLuHq>)<br>`https://douc.cc/1jLuHq` | 短链接，待解析 / 可点击 | docs/broadcast/page/63.md:14 |
| [兔子山的视频声優の洲崎綾、中学時代に林原めぐみにラジオで電話相談した音声（ＮＨＫラジオ「土曜わくわくラジオ・子供夢質問箱（電話相談）」2003年９月放送分より抜粋）](<https://douc.cc/1joM7H>)<br>`https://douc.cc/1joM7H` | 短链接，待解析 / 可点击 | docs/broadcast/page/62.md:16 |
| [映画「聲の形」主題歌はaiko！取り乱すほど歓喜「とてもとても幸せです！」](<https://douc.cc/1kP3rr>)<br>`https://douc.cc/1kP3rr` | 短链接，待解析 / 可点击 | docs/broadcast/page/22.md:22 |
| [《无彩限的怪灵世界》第6集分镜：山田尚子 https://douc.cc/1lufc8](<https://douc.cc/1lufc8>)<br>`https://douc.cc/1lufc8` | 短链接，待解析 / 纯文本 | docs/broadcast/page/26.md:22 |
| [山田尚子監督と髙橋良輔監督が「たまこラブストーリー」について語っているのを聴いてきました](<https://douc.cc/1mmkG1>)<br>`https://douc.cc/1mmkG1` | 短链接，待解析 / 可点击 | docs/broadcast/page/39.md:32 |
| [《电影 声之形 Making Book》已在京阿尼shop!开通预定，10月30日截止。 https://douc.cc/1mrvkv # 声之形 #](<https://douc.cc/1mrvkv>)<br>`https://douc.cc/1mrvkv` | 短链接，待解析 / 纯文本 | docs/broadcast/page/13.md:20 |
| [映画「たまこラブストーリー」 &#91;Blu-ray&#93; https://douc.cc/1oeqHk](<https://douc.cc/1oeqHk>)<br>`https://douc.cc/1oeqHk` | 短链接，待解析 / 纯文本 | docs/broadcast/page/57.md:30 |
| [アニメ「けいおん！」の体重こそがリアル女子の真実！](<https://douc.cc/1oqrod>)<br>`https://douc.cc/1oqrod` | 短链接，待解析 / 可点击 | docs/broadcast/page/77.md:28 |
| [《玉子爱情故事》Blu-ray&amp;DVD 京阿尼Shop独家特典公开：STAFF恋文集（内容为主要制作人员的情书风格寄语＋作画监督修正集）。预定截止日为2014年9月15日。 https://douc.cc/1p1UFg](<https://douc.cc/1p1UFg>)<br>`https://douc.cc/1p1UFg` | 短链接，待解析 / 纯文本 | docs/broadcast/page/57.md:16 |
| [【第2回 京アニ＆Do ファン感謝イベント 2015.10.31】今天的山田尚子，米色黑圆点连衣裙。（图by twitter ID: honekawap）（帽子好像是这顶→ https://douc.cc/1pDOrE ）](<https://douc.cc/1pDOrE>)<br>`https://douc.cc/1pDOrE` | 短链接，待解析 / 纯文本 | docs/broadcast/page/30.md:14 |
| [松竹的购物网站Froovie已开通了电影《声之形》周边商品网购（重点是场刊）。 https://douc.cc/1pRc8S # 声之形 #](<https://douc.cc/1pRc8S>)<br>`https://douc.cc/1pRc8S` | 短链接，待解析 / 纯文本 | docs/broadcast/page/13.md:18 |
| [商店街日常](<https://douc.cc/1r3T6r>)<br>`https://douc.cc/1r3T6r` | 短链接，待解析 / 可点击 | docs/broadcast/page/62.md:30 |
| [『たまこラブストーリー』 若者から絶大な支持を集めたアニメ映画が映画初日満足度ランキング第1位に！](<https://douc.cc/1uaaS8>)<br>`https://douc.cc/1uaaS8` | 短链接，待解析 / 可点击 | docs/broadcast/page/70.md:16 |
| [山田的这张照片（图1）是在岐阜县的主题公园“养老天命反转地”（图2）取材时拍摄的。关于“养老天命反转地”可以看一下这篇介绍： https://douc.cc/0wRXIb 360°全景照： https://douc.cc/1vpgzh 这是作品中将也与硝子约会的地方（图3）。 #](<https://douc.cc/1vpgzh>)<br>`https://douc.cc/1vpgzh` | 短链接，待解析 / 纯文本 | docs/broadcast/page/13.md:30 |
| [NO ANIME, NO LIFE.“TOWERanime ♡ たまこラブストーリー” タワーレコード渋谷店・京都店限定で4/19～5/16の期間開催決定！ https://douc.cc/1xU0hw](<https://douc.cc/1xU0hw>)<br>`https://douc.cc/1xU0hw` | 短链接，待解析 / 纯文本 | docs/broadcast/page/76.md:18 |
| [兔子山的视频【けいおん!!】けいおん学講義 第６回～輝く未来へ～](<https://douc.cc/1yNANc>)<br>`https://douc.cc/1yNANc` | 短链接，待解析 / 可点击 | docs/broadcast/page/87.md:22 |
| [C87京阿尼摊位贩售物公开！玉子市场&amp;玉子爱情故事的相关商品为“宇宙的入口套装”，包含《TAMAKO MEMORIES NOTE》、名场面相片集、橡胶杯垫及特制提袋，售价为5000日元。 https://douc.cc/20XK4X](<https://douc.cc/20XK4X>)<br>`https://douc.cc/20XK4X` | 短链接，待解析 / 纯文本 | docs/broadcast/page/41.md:32 |
| [第５回：対談 ゲイリー芦屋＋山口優（前編）〜タイムマシンを作っていたようなものです &#124; マニュエラだから作れた『たまこまーけっと』の音楽 &#124; RandoM](<https://douc.cc/21O92J>)<br>`https://douc.cc/21O92J` | 短链接，待解析 / 可点击 | docs/broadcast/page/86.md:30 |
| [《玉子市场》插图&amp;设定资料集 KyoaniShop已上架 https://douc.cc/21oQrz](<https://douc.cc/21oQrz>)<br>`https://douc.cc/21oQrz` | 短链接，待解析 / 纯文本 | docs/broadcast/page/81.md:16 |
| [《玉子爱情故事》第2周早期入场特典明信片。与第1周玉子写给乔伊的明信片（ https://douc.cc/1gRFRG https://douc.cc/21vtfQ ）相呼应，这次是乔伊给玉子的回信。文中的错别字非常可爱——“たもこ”、“たくちんたくちんありもす”…](<https://douc.cc/21vtfQ>)<br>`https://douc.cc/21vtfQ` | 短链接，待解析 / 纯文本 | docs/broadcast/page/66.md:20 |
| [たまこたまこ☆パピコ](<https://douc.cc/22XE3T>)<br>`https://douc.cc/22XE3T` | 短链接，待解析 / 可点击 | docs/broadcast/page/75.md:26 |
| [アニメ 響け！ユーフォニアム オフィシャルファンブック「青春の軌跡がここに――」...](<https://douc.cc/238Q58>)<br>`https://douc.cc/238Q58` | 短链接，待解析 / 可点击 | docs/broadcast/page/31.md:32 |
| [兔子山的视频『たまこラブストーリー』Blu-ray &amp; DVD CM](<https://douc.cc/24h79n>)<br>`https://douc.cc/24h79n` | 短链接，待解析 / 可点击 | docs/broadcast/page/57.md:28 |
| [兔子山的视频电影《聲之形》热映答谢见面会（2016.10.01）](<https://douc.cc/24w98c>)<br>`https://douc.cc/24w98c` | 短链接，待解析 / 可点击 | docs/broadcast/page/9.md:30 |
| [【たまらぶ】初見感想 そのいち 『まずは総論みたいなのｗ』](<https://douc.cc/279x99>)<br>`https://douc.cc/279x99` | 短链接，待解析 / 可点击 | docs/broadcast/page/70.md:18 |
| [（前編）たまこラブストーリーレビュー ～鴨川のうねりは流れゆく～](<https://douc.cc/27deYn>)<br>`https://douc.cc/27deYn` | 短链接，待解析 / 可点击 | docs/broadcast/page/54.md:18 |
| [しあわせ](<https://douc.cc/27soV5>)<br>`https://douc.cc/27soV5` | 短链接，待解析 / 可点击 | docs/broadcast/page/61.md:24 |
| [たまこラブストーリー☆パピコ](<https://douc.cc/28vCKc>)<br>`https://douc.cc/28vCKc` | 短链接，待解析 / 可点击 | docs/broadcast/page/60.md:26 |
| [《轻音！！》片尾“Listen!!”解析](<https://douc.cc/2A0jof>)<br>`https://douc.cc/2A0jof` | 短链接，待解析 / 可点击 | docs/broadcast/page/19.md:28 |
| [相册](<https://douc.cc/2DrjXP>)<br>`https://douc.cc/2DrjXP` | 短链接，待解析 / 可点击 | docs/broadcast/page/84.md:30 |
| [『たまこラブストーリー』に見た「映画」へのこだわり](<https://douc.cc/2EO3OJ>)<br>`https://douc.cc/2EO3OJ` | 短链接，待解析 / 可点击 | docs/broadcast/page/67.md:30 |
| [Free!-Eternal Summer- 12話 脚本：横谷昌宏 絵コンテ・演出：山田尚子 作画監督：瀬崎利恵 作画監督補佐：池田晶子 https://douc.cc/2FAbgJ](<https://douc.cc/2FAbgJ>)<br>`https://douc.cc/2FAbgJ` | 短链接，待解析 / 纯文本 | docs/broadcast/page/55.md:22 |
| [第９回：対談 山田尚子＋山口優（前編）〜監督はいちいち言葉で何でも説明しないタイプ &#124; マニュエラだから作れた『たまこまーけっと』の音楽 &#124; RandoM](<https://douc.cc/2FrSUn>)<br>`https://douc.cc/2FrSUn` | 短链接，待解析 / 可点击 | docs/broadcast/page/86.md:16 |
| [饼藏从“星星与小丑”出来后，在踏脚石处仰望天空时又出现了鸟。飞向天空的鸟象征饼藏打算飞向梦想的心。然后他跳到比告白时所站的位置更前面的踏脚石上，那是他抛开对玉子的眷恋，决心前往下一个世界的身影。 https://douc.cc/2GT2s7 # 玉子爱情故事 #](<https://douc.cc/2GT2s7>)<br>`https://douc.cc/2GT2s7` | 短链接，待解析 / 纯文本 | docs/broadcast/page/47.md:16<br>docs/broadcast/page/47.md:18 |
| [山田尚子監督からキャスト５人へのお手紙書き起こし https://douc.cc/2GcDUr](<https://douc.cc/2GcDUr>)<br>`https://douc.cc/2GcDUr` | 短链接，待解析 / 纯文本 | docs/broadcast/page/86.md:28 |
| [劇場版 たまこラブストーリーBD発売 「何度観ても心が温まります」 https://douc.cc/2Gym3q](<https://douc.cc/2Gym3q>)<br>`https://douc.cc/2Gym3q` | 短链接，待解析 / 纯文本 | docs/broadcast/page/51.md:14 |
| [「けいおん！」Blu-ray Box 店舗オリジナル特典一覧発表！ https://douc.cc/2HvcCe](<https://douc.cc/2HvcCe>)<br>`https://douc.cc/2HvcCe` | 短链接，待解析 / 纯文本 | docs/broadcast/page/81.md:18 |
| [兔子山的视频『たまこラブストーリー』TVスポット 上映中15ver.](<https://douc.cc/2HyM48>)<br>`https://douc.cc/2HyM48` | 短链接，待解析 / 可点击 | docs/broadcast/page/68.md:22 |
| [京都アニメーションの新たな代表作「たまこラブストーリー」ロングランの秘密。山田尚...](<https://douc.cc/2IaKa2>)<br>`https://douc.cc/2IaKa2` | 短链接，待解析 / 可点击 | docs/broadcast/page/58.md:28 |
| [藤津亮太のアニメ時評四代目 アニメの門 第10回『たまこラブストーリー』](<https://douc.cc/2JT8kE>)<br>`https://douc.cc/2JT8kE` | 短链接，待解析 / 可点击 | docs/broadcast/page/64.md:22 |
| [【たまこラ】 PV第一弾解禁！ここまでの作品考察、推察のまとめ https://douc.cc/2LZUsd](<https://douc.cc/2LZUsd>)<br>`https://douc.cc/2LZUsd` | 短链接，待解析 / 纯文本 | docs/broadcast/page/77.md:14 |
| [史织在这个场景中看破了玉子的真心，并将之化作言语——“你喜欢他啊”。之后立刻响起了上课铃声，这个铃声宣告着开始与终结——玉子恋慕饼藏的开始，小绿爱慕玉子的终结。 https://douc.cc/2LdDuQ # 玉子爱情故事 #](<https://douc.cc/2LdDuQ>)<br>`https://douc.cc/2LdDuQ` | 短链接，待解析 / 纯文本 | docs/broadcast/page/49.md:30 |
| [アニメ監督の山田尚子ってかなりの逸材だよな](<https://douc.cc/2NFlN9>)<br>`https://douc.cc/2NFlN9` | 短链接，待解析 / 可点击 | docs/broadcast/page/54.md:26 |
| [《玉子爱情故事》官网更新，山田尚子导演访谈（后篇）公开 https://douc.cc/2NJQVW](<https://douc.cc/2NJQVW>)<br>`https://douc.cc/2NJQVW` | 短链接，待解析 / 纯文本 | docs/broadcast/page/77.md:16<br>docs/broadcast/page/78.md:14 |
| [【考察】「けいおん！」のその先を描く物語としての「たまこラブストーリー」](<https://douc.cc/2QePC2>)<br>`https://douc.cc/2QePC2` | 短链接，待解析 / 可点击 | docs/broadcast/page/78.md:30 |
| [【第2回 京アニ＆Do ファン感謝イベント 2015.10.31】山田提到自己从事动画制作的契机是因为在深夜电视上观看了杨·史云梅耶导演的《爱丽丝》这部电影（ https://douc.cc/2RSFlv ）。武本（康弘）说那是他有生以来看过的最恐怖的一部电影。](<https://douc.cc/2RSFlv>)<br>`https://douc.cc/2RSFlv` | 短链接，待解析 / 纯文本 | docs/broadcast/page/30.md:16 |
| [大森祥子：ブログ更新しました。『けいおん!!』Blu-ray BOX発売です。](<https://douc.cc/2St1gh>)<br>`https://douc.cc/2St1gh` | 短链接，待解析 / 可点击 | docs/broadcast/page/43.md:28 |
| [たまこラブストーリー 上映劇場一覧](<https://douc.cc/2V2SxV>)<br>`https://douc.cc/2V2SxV` | 短链接，待解析 / 可点击 | docs/broadcast/page/64.md:30 |
| [相册](<https://douc.cc/2V9Vz1>)<br>`https://douc.cc/2V9Vz1` | 短链接，待解析 / 可点击 | docs/broadcast/page/22.md:28 |
| [兔子山的视频【けいおん!!】けいおん学講義 第３回～キャラクターとキーアイテム(前)～](<https://douc.cc/2VETg3>)<br>`https://douc.cc/2VETg3` | 短链接，待解析 / 可点击 | docs/broadcast/page/87.md:28 |
| [『たまこまーけっと』の新作は劇場版！？ 山田監督「たまこをパワーアップさせてます」 https://douc.cc/2VuJuH](<https://douc.cc/2VuJuH>)<br>`https://douc.cc/2VuJuH` | 短链接，待解析 / 纯文本 | docs/broadcast/page/85.md:22 |
| [【磁极，反转的磁带与传声筒】 https://douc.cc/2W1jHM 反转同一盘磁带，用自己的磁力分别记录正反两面。豆大与雏子因此互相传达了彼此的爱意。而那正是招牌前玉子与饼藏的站位与回忆场景相反=反转的理由。 # 玉子爱情故事 #](<https://douc.cc/2W1jHM>)<br>`https://douc.cc/2W1jHM` | 短链接，待解析 / 纯文本 | docs/broadcast/page/46.md:28 |
| [第６回：対談 ゲイリー芦屋＋山口優（後編）〜キャラソンとか劇伴、OP・EDとはまた別の宇宙が、ここにある &#124; マニュエラだから作れた『たまこまーけっと』の音楽 &#124; RandoM](<https://douc.cc/2XF7KD>)<br>`https://douc.cc/2XF7KD` | 短链接，待解析 / 可点击 | docs/broadcast/page/86.md:26 |
| [相册](<https://douc.cc/2XRkor>)<br>`https://douc.cc/2XRkor` | 短链接，待解析 / 可点击 | docs/broadcast/page/27.md:18 |
| [【たまこラブストーリー】 読解メモ 03](<https://douc.cc/2XipSr>)<br>`https://douc.cc/2XipSr` | 短链接，待解析 / 可点击 | docs/broadcast/page/67.md:22 |
| [《玉子爱情故事》预告片公开 https://douc.cc/2b9fIW](<https://douc.cc/2b9fIW>)<br>`https://douc.cc/2b9fIW` | 短链接，待解析 / 纯文本 | docs/broadcast/page/77.md:20 |
| [第２回：インタビュー 山口優（後編）〜お琴バージョンでも成り立つ曲を作りたい &#124; マニュエラだから作れた『たまこまーけっと』の音楽 &#124; RandoM](<https://douc.cc/2cPWe6>)<br>`https://douc.cc/2cPWe6` | 短链接，待解析 / 可点击 | docs/broadcast/page/87.md:16 |
| [昨日の続きだよん](<https://douc.cc/2d88lw>)<br>`https://douc.cc/2d88lw` | 短链接，待解析 / 可点击 | docs/broadcast/page/62.md:26 |
| [『たまこラブストーリー』ミニシアターランキングで２週連続１位！](<https://douc.cc/2em5q4>)<br>`https://douc.cc/2em5q4` | 短链接，待解析 / 可点击 | docs/broadcast/page/65.md:22 |
| [第８回：鼎談 藤本功一＋宮川弾＋山口優（後編）〜男がメロディを作るとき &#124; マニュエラだから作れた『たまこまーけっと』の音楽 &#124; RandoM](<https://douc.cc/2gyX7V>)<br>`https://douc.cc/2gyX7V` | 短链接，待解析 / 可点击 | docs/broadcast/page/86.md:20 |
| [昨晚# 玉子爱情故事 #在新宿Piccadilly重映，洲崎绫（玉子）与田丸笃志（饼藏）也前去观看了，同行的还有洲崎的经纪人以及《玉爱》主题曲作曲者藤本功一。这张照片是洲崎主动请当时偶遇两人的一位粉丝拍摄的，两人还与那位粉丝握了手。 https://douc.cc/2h0vGN](<https://douc.cc/2h0vGN>)<br>`https://douc.cc/2h0vGN` | 短链接，待解析 / 纯文本 | docs/broadcast/page/34.md:16 |
| [『たまこラブストーリー』脚本家の花田十輝さんと、禁書などの監督・錦織博さんも大絶賛！ 「やられたよ‼︎ 完敗だよ！」「ステキな映画でした」](<https://douc.cc/2h6aYR>)<br>`https://douc.cc/2h6aYR` | 短链接，待解析 / 可点击 | docs/broadcast/page/65.md:14 |
| [『たまこラブストーリー』の美意識 山田尚子監督の美意識 - OTALLICA](<https://douc.cc/2hKHCt>)<br>`https://douc.cc/2hKHCt` | 短链接，待解析 / 可点击 | docs/broadcast/page/67.md:16 |
| [电影《玉子爱情故事》官网开放 https://douc.cc/2hhDGR 特报第1弹公开 https://douc.cc/0rpuuO # tamakolovestory #](<https://douc.cc/2hhDGR>)<br>`https://douc.cc/2hhDGR` | 短链接，待解析 / 纯文本 | docs/broadcast/page/84.md:16 |
| [映画「たまこラブストーリー」で「星とピエロ」店内に登場するレコード・ジャケットのご紹介](<https://douc.cc/2i8NSJ>)<br>`https://douc.cc/2i8NSJ` | 短链接，待解析 / 可点击 | docs/broadcast/page/69.md:28 |
| [劇場版『たまこラブストーリー』たまこの恋愛相手はやっぱりもち蔵かよ！ https://douc.cc/2iNWt8 传声筒、录像带和舞棒是电影的关键道具，一心一意的感情是萌点。](<https://douc.cc/2iNWt8>)<br>`https://douc.cc/2iNWt8` | 短链接，待解析 / 纯文本 | docs/broadcast/page/80.md:24 |
| [自分が死んだ後も、作品は残る 名作を生んだ京アニの監督3人が語るアニメのあれこれ](<https://douc.cc/2jhVcU>)<br>`https://douc.cc/2jhVcU` | 短链接，待解析 / 可点击 | docs/broadcast/page/83.md:28 |
| [兔子山的视频ボルヴィックCM『飲む自然』篇](<https://douc.cc/2k57Tc>)<br>`https://douc.cc/2k57Tc` | 短链接，待解析 / 可点击 | docs/broadcast/page/34.md:18 |
| [《玉子市场》&amp;《玉子爱情故事》精选歌集“Everybody Loves Somebody”封面&amp;曲目公开 https://douc.cc/2leoZd](<https://douc.cc/2leoZd>)<br>`https://douc.cc/2leoZd` | 短链接，待解析 / 纯文本 | docs/broadcast/page/39.md:26<br>docs/broadcast/page/42.md:18 |
| [一张图说明山田尚子有多么可怕w https://douc.cc/2mFrm0 # 玉子爱情故事 #](<https://douc.cc/2mFrm0>)<br>`https://douc.cc/2mFrm0` | 短链接，待解析 / 纯文本 | docs/broadcast/page/48.md:16 |
| [兔子山的视频J-WAVE「AVALON」20160912（主持：松冈茉优 嘉宾：入野自由）](<https://douc.cc/2o5GZd>)<br>`https://douc.cc/2o5GZd` | 短链接，待解析 / 可点击 | docs/broadcast/page/14.md:32<br>docs/broadcast/page/15.md:14 |
| [兔子山的视频中二病也要谈恋爱！ED「INSIDE IDENTITY」](<https://douc.cc/2oMFnQ>)<br>`https://douc.cc/2oMFnQ` | 短链接，待解析 / 可点击 | docs/broadcast/page/81.md:32 |
| [《吹响悠风号》石原立也导演访谈（《Animedia》2015年8月号）](<https://douc.cc/2onCas>)<br>`https://douc.cc/2onCas` | 短链接，待解析 / 可点击 | docs/broadcast/page/33.md:20 |
| [「たまこメモリーズノート」(品番：KYOG-TM58) 誤植のお詫びと訂正のお知らせ https://douc.cc/2qxquy](<https://douc.cc/2qxquy>)<br>`https://douc.cc/2qxquy` | 短链接，待解析 / 纯文本 | docs/broadcast/page/40.md:18 |
| [開催概要 ： 『京アニ＆Do C・T・F・K 2013』特設サイト &#124; 京都アニ...](<https://douc.cc/2rGieb>)<br>`https://douc.cc/2rGieb` | 短链接，待解析 / 可点击 | docs/broadcast/page/85.md:14 |
| [大ヒット御礼！ 山田尚子監督を始めとする制作陣が登壇した『たまこラブストーリー』スタッフ舞台挨拶をレポート！](<https://douc.cc/2rYVHg>)<br>`https://douc.cc/2rYVHg` | 短链接，待解析 / 可点击 | docs/broadcast/page/59.md:30 |
| [ムギの『Diaryはフォルテシモ』に、あの曲が入ってた](<https://douc.cc/2rkSg5>)<br>`https://douc.cc/2rkSg5` | 短链接，待解析 / 可点击 | docs/broadcast/page/74.md:22 |
| [たまこともち蔵の恋する過程をまっすぐに「たまこラブストーリー」山田尚子監督に聞く2](<https://douc.cc/2sosWj>)<br>`https://douc.cc/2sosWj` | 短链接，待解析 / 可点击 | docs/broadcast/page/58.md:24 |
| [兔子山的视频电影《声之形》正式版预告片](<https://douc.cc/2tUTKh>)<br>`https://douc.cc/2tUTKh` | 短链接，待解析 / 可点击 | docs/broadcast/page/22.md:14 |
| [兔子山的视频《聲之形》ZIP!特集（20160920）](<https://douc.cc/2tXL8l>)<br>`https://douc.cc/2tXL8l` | 短链接，待解析 / 可点击 | docs/broadcast/page/12.md:16 |
| [兔子山的视频【たまこラブストーリー】出町桝形商店街“標語”再現メイキング映像](<https://douc.cc/2u0HhG>)<br>`https://douc.cc/2u0HhG` | 短链接，待解析 / 可点击 | docs/broadcast/page/51.md:20 |
| [小绿在片中的最后一个镜头，是与树上的神奈一起，在树下迎风眺望远方。联系之前蒲公英绒毛与小绿相重叠的镜头，她也一定会乘着风飞往新世界。 https://douc.cc/2uFYef # 玉子爱情故事 #](<https://douc.cc/2uFYef>)<br>`https://douc.cc/2uFYef` | 短链接，待解析 / 纯文本 | docs/broadcast/page/46.md:14 |
| [兔子山的视频『たまこラブストーリー』本予告](<https://douc.cc/2vF6Mt>)<br>`https://douc.cc/2vF6Mt` | 短链接，待解析 / 可点击 | docs/broadcast/page/76.md:32 |
| [《吹响悠风号2》PV第2弹公开，第1集时长1小时。 https://douc.cc/0NIhmG 另外官网还更新了新角色，详见： https://douc.cc/2w66oi # 吹响悠风号 #](<https://douc.cc/2w66oi>)<br>`https://douc.cc/2w66oi` | 短链接，待解析 / 纯文本 | docs/broadcast/page/15.md:30 |
| [■たまこラブストーリー ノベライズ【文庫本】※7月4日(金)より随時発送](<https://douc.cc/2xwRLT>)<br>`https://douc.cc/2xwRLT` | 短链接，待解析 / 可点击 | docs/broadcast/page/59.md:24 |
| [たまこラブストーリー舞台探訪記〜後編〜](<https://douc.cc/2yLhw0>)<br>`https://douc.cc/2yLhw0` | 短链接，待解析 / 可点击 | docs/broadcast/page/61.md:16 |
| [兔子山的视频TAMAKO MEMORY&#x27;S NOTE PV](<https://douc.cc/2z8ez3>)<br>`https://douc.cc/2z8ez3` | 短链接，待解析 / 可点击 | docs/broadcast/page/41.md:28 |
| [https://douc.cc/304n9D](<https://douc.cc/304n9D>)<br>`https://douc.cc/304n9D` | 短链接，待解析 / 纯文本 | docs/broadcast/page/44.md:16 |
| [兔子山的视频【けいおん!!】けいおん学講義 第４回～キャラクターとキーアイテム(後)～](<https://douc.cc/330K1O>)<br>`https://douc.cc/330K1O` | 短链接，待解析 / 可点击 | docs/broadcast/page/87.md:26 |
| [https://douc.cc/33VITp 吉他预约再开（？），制作过程介绍。](<https://douc.cc/33VITp>)<br>`https://douc.cc/33VITp` | 短链接，待解析 / 纯文本 | docs/broadcast/page/43.md:14 |
| [HOBBY STOCK × ALTER企画として、TVアニメ「たまこまーけっと」から「北白川あんこ」と「デラ・モチマッヅィ」がセットでPVC塗装済完成品として商品化決定! 2015年発売予定 https://douc.cc/33wTvd](<https://douc.cc/33wTvd>)<br>`https://douc.cc/33wTvd` | 短链接，待解析 / 纯文本 | docs/broadcast/page/57.md:18 |
| [小说《电影 声之形》（上）封面公开，9月16日发售，作者川崎美羽。 https://douc.cc/34pZpA # 声之形 #](<https://douc.cc/34pZpA>)<br>`https://douc.cc/34pZpA` | 短链接，待解析 / 纯文本 | docs/broadcast/page/16.md:18 |
| [兔子山的视频TVアニメ『響け！ユーフォニアム』 ＰＶ（ロングver）](<https://douc.cc/35G0M0>)<br>`https://douc.cc/35G0M0` | 短链接，待解析 / 可点击 | docs/broadcast/page/40.md:24 |
| [(仮) TVアニメ「たまこまーけっと」,映画「たまこラブストーリー」劇中曲コンピレーションCD 2014年7月16日発売予定 https://douc.cc/35YXYm](<https://douc.cc/35YXYm>)<br>`https://douc.cc/35YXYm` | 短链接，待解析 / 纯文本 | docs/broadcast/page/64.md:24 |
| [「見てくれた方々の勇気の一つに」 映画『たまこラブストーリー』初日舞台挨拶レポー...](<https://douc.cc/3618y0>)<br>`https://douc.cc/3618y0` | 短链接，待解析 / 可点击 | docs/broadcast/page/71.md:24 |
| [たまこラブストーリー、京都駅 新幹線ホームに見る謎のこだわり演出](<https://douc.cc/36HO4r>)<br>`https://douc.cc/36HO4r` | 短链接，待解析 / 可点击 | docs/broadcast/page/67.md:32 |
| [『京アニ感謝祭』イベントレポ https://douc.cc/37J6wy](<https://douc.cc/37J6wy>)<br>`https://douc.cc/37J6wy` | 短链接，待解析 / 纯文本 | docs/broadcast/page/85.md:20 |
| [【4.19】「たまこまーけっと」おさらい上映会＆スタッフトークショーレポ【京都文博】](<https://douc.cc/37y5XR>)<br>`https://douc.cc/37y5XR` | 短链接，待解析 / 可点击 | docs/broadcast/page/73.md:22 |
| [兔子山的视频《聲之形》ZIP!特集（20160920）](<https://douc.cc/38aVgK>)<br>`https://douc.cc/38aVgK` | 短链接，待解析 / 可点击 | docs/broadcast/page/11.md:30 |
| [「京アニ&amp;Do C･T･F･K 2013」〜監督対談！レポート（石原立也・武本康...](<https://douc.cc/38f1le>)<br>`https://douc.cc/38f1le` | 短链接，待解析 / 可点击 | docs/broadcast/page/85.md:18 |
| [アニメ質問状：「響け！ユーフォ二アム」 キャラ一人一人の思いが本当にいじらしい ...](<https://douc.cc/38y9Af>)<br>`https://douc.cc/38y9Af` | 短链接，待解析 / 可点击 | docs/broadcast/page/36.md:16 |
| [舞台挨拶～つづき～](<https://douc.cc/39OArJ>)<br>`https://douc.cc/39OArJ` | 短链接，待解析 / 可点击 | docs/broadcast/page/65.md:20 |
| [松岡茉優：話題のアニメ「聲の形」で男の子役の声優挑戦 “師”山寺宏一への思いも ...](<https://douc.cc/39bw6J>)<br>`https://douc.cc/39bw6J` | 短链接，待解析 / 可点击 | docs/broadcast/page/15.md:26 |
| [兔子山的视频林原めぐみのHeartful Stationに現役声優さんから感謝のおたより（2013年8月）](<https://douc.cc/3AJm57>)<br>`https://douc.cc/3AJm57` | 短链接，待解析 / 可点击 | docs/broadcast/page/62.md:14 |
| [《玉子爱情故事》Blu-ray&amp;DVD封面、展开图公开 https://douc.cc/3AsVca](<https://douc.cc/3AsVca>)<br>`https://douc.cc/3AsVca` | 短链接，待解析 / 纯文本 | docs/broadcast/page/55.md:24 |
| [视频: 『たまこラブストーリー』TVCM (KOI NO UTA ver.)](<https://douc.cc/3BvKuH>)<br>`https://douc.cc/3BvKuH` | 短链接，待解析 / 可点击 | docs/broadcast/page/68.md:18<br>docs/broadcast/page/68.md:20 |
| [电影《声之形》官网更新，新宣传图公开，主角声优公布（入野自由&amp;早见沙织），附赠特典透明文件夹的预售票6月4日开始发售。 https://douc.cc/3BxK2N # 声之形 #](<https://douc.cc/3BxK2N>)<br>`https://douc.cc/3BxK2N` | 短链接，待解析 / 纯文本 | docs/broadcast/page/23.md:14 |
| [アニメBD/DVDデイリーで『映画 たまこラブストーリー』がBD/DVD共に１位を獲得！ たまこの時代きたわ・・・](<https://douc.cc/3DwyqQ>)<br>`https://douc.cc/3DwyqQ` | 短链接，待解析 / 可点击 | docs/broadcast/page/50.md:26 |
| [【たまこラブストーリー】 読解メモ 10](<https://douc.cc/3F8ayw>)<br>`https://douc.cc/3F8ayw` | 短链接，待解析 / 可点击 | docs/broadcast/page/58.md:30 |
| [兔子山的视频映画「聲の形」完成披露上映会（2016.8.24）](<https://douc.cc/3FNd8J>)<br>`https://douc.cc/3FNd8J` | 短链接，待解析 / 可点击 | docs/broadcast/page/18.md:30 |
| [兔子山的视频『たまこラブストーリー』TVスポット](<https://douc.cc/3FWbNd>)<br>`https://douc.cc/3FWbNd` | 短链接，待解析 / 可点击 | docs/broadcast/page/68.md:24 |
| [【京阿尼Shop】玉子市场&amp;玉子爱情故事官方导视书《TAMAKO MEMORIES NOTE》开通预约 https://douc.cc/3FmXau](<https://douc.cc/3FmXau>)<br>`https://douc.cc/3FmXau` | 短链接，待解析 / 纯文本 | docs/broadcast/page/45.md:32 |
| [# 吹响悠风号 # 第四回故事梗概、制作人员、先行画面公开 https://douc.cc/3FoYnp 脚本：花田十輝 絵コンテ：石原立也、山田尚子 演出：雪村 愛 作画監督：植野千世子](<https://douc.cc/3FoYnp>)<br>`https://douc.cc/3FoYnp` | 短链接，待解析 / 纯文本 | docs/broadcast/page/37.md:18 |
| [最終回：対談 山田尚子＋山口優（後編）〜私、音楽になってみたいのかもしれません。 &#124; マニュエラだから作れた『たまこまーけっと』の音楽 &#124; RandoM](<https://douc.cc/3G0tSH>)<br>`https://douc.cc/3G0tSH` | 短链接，待解析 / 可点击 | docs/broadcast/page/86.md:14 |
| [兔子山的视频たまこまーけっと キャラクターソング「きっとね、ずっとね、よろしくね。」PV](<https://douc.cc/3G1jrs>)<br>`https://douc.cc/3G1jrs` | 短链接，待解析 / 可点击 | docs/broadcast/page/89.md:14 |
| [劇場版 『たまこラブストーリー』 舞台探訪(聖地巡礼)](<https://douc.cc/3HuPI4>)<br>`https://douc.cc/3HuPI4` | 短链接，待解析 / 可点击 | docs/broadcast/page/68.md:32 |
| [映画『たまこラブストーリー』山田尚子 監督インタビュー（前編）](<https://douc.cc/3Iw3Zq>)<br>`https://douc.cc/3Iw3Zq` | 短链接，待解析 / 可点击 | docs/broadcast/page/73.md:26 |
| [【重新推荐下这四篇访谈（必读！）】官网导演访谈（上映前） https://douc.cc/01SUy9 https://douc.cc/1eIOys excite导演访谈（上映后） https://douc.cc/4hTTqG https://douc.cc/3Jc6Wt # 玉](<https://douc.cc/3Jc6Wt>)<br>`https://douc.cc/3Jc6Wt` | 短链接，待解析 / 纯文本 | docs/broadcast/page/49.md:26 |
| [【たまこラブストーリー】京アニショップ！限定・堀口悠紀子描き下ろし「“たまこ・あんこ”ラバーストラップ」付きオリジナルイラスト前売券 予約受付開始！専用窓口⇒ https://douc.cc/3M2zO1 特設サイト⇒ https://douc.cc/16CyJf](<https://douc.cc/3M2zO1>)<br>`https://douc.cc/3M2zO1` | 短链接，待解析 / 纯文本 | docs/broadcast/page/78.md:20 |
| [“一歩を踏み出す勇気”がテーマ 「たまこラブストーリー」山田尚子監督に聞く : ...](<https://douc.cc/3NQU00>)<br>`https://douc.cc/3NQU00` | 短链接，待解析 / 可点击 | docs/broadcast/page/73.md:30 |
| [TV版《玉子市场》Blu-ray BOX 2015年3月18日发售决定！新特典包括：广播剧CD（前日谈，讲述玉子&amp;小绿与神奈相遇的故事）、第2话和第9话的分镜集、新绘制的相片卡，另外收录了山田导演与洲崎绫新录制的评论音轨（2话）。 https://douc.cc/3ONx8f](<https://douc.cc/3ONx8f>)<br>`https://douc.cc/3ONx8f` | 短链接，待解析 / 纯文本 | docs/broadcast/page/42.md:20 |
| [4/19 たまこまーけっと上映会ゲストトークまとめ](<https://douc.cc/3OlSG0>)<br>`https://douc.cc/3OlSG0` | 短链接，待解析 / 可点击 | docs/broadcast/page/74.md:18 |
| [【たまこラブストーリー】 読解メモ 02 追補](<https://douc.cc/3P93PQ>)<br>`https://douc.cc/3P93PQ` | 短链接，待解析 / 可点击 | docs/broadcast/page/67.md:24 |
| [「けいおん!!」Blu-ray BOX発売決定!! 2014年11月19日発売予定! https://douc.cc/3T9jc2](<https://douc.cc/3T9jc2>)<br>`https://douc.cc/3T9jc2` | 短链接，待解析 / 纯文本 | docs/broadcast/page/57.md:14 |
| [《小林家的龙女仆》第8集 分镜、演出：山田尚子 https://douc.cc/3UGKd6](<https://douc.cc/3UGKd6>)<br>`https://douc.cc/3UGKd6` | 短链接，待解析 / 纯文本 | docs/broadcast/page/6.md:14 |
| [京都动画C85商品详情公开 https://douc.cc/3UvDFp 《玉子市场》相关商品：插画&amp;设定资料集、2014年A4日历、电影《玉子爱情故事》预售双人票（附特制文件夹）。 # tamakolovestory #](<https://douc.cc/3UvDFp>)<br>`https://douc.cc/3UvDFp` | 短链接，待解析 / 纯文本 | docs/broadcast/page/84.md:18 |
| [【CD情報更新】 ・オリジナル・サウンドトラックと劇中曲コンピレーションＣＤの、ジャケットと情報を公開しました！ https://douc.cc/3WRUn8](<https://douc.cc/3WRUn8>)<br>`https://douc.cc/3WRUn8` | 短链接，待解析 / 纯文本 | docs/broadcast/page/58.md:32 |
| [https://douc.cc/3WnRTA](<https://douc.cc/3WnRTA>)<br>`https://douc.cc/3WnRTA` | 短链接，待解析 / 纯文本 | docs/broadcast/page/50.md:28 |
| [小律生日快乐！ https://douc.cc/3WxegX](<https://douc.cc/3WxegX>)<br>`https://douc.cc/3WxegX` | 短链接，待解析 / 纯文本 | docs/broadcast/page/56.md:26 |
| [第３回：対談 片岡知子＋山口優（前編）〜淡々とした女の子らしさで、フランス近代や教会音楽をイメージ &#124; マニュエラだから作れた『たまこまーけっと』の音楽 &#124; RandoM](<https://douc.cc/3X0kB0>)<br>`https://douc.cc/3X0kB0` | 短链接，待解析 / 可点击 | docs/broadcast/page/87.md:14 |
| [『たまこまーけっと』『たまこラブストーリー』アイテム特集 TVアニメ『たまこまー...](<https://douc.cc/3XKwY2>)<br>`https://douc.cc/3XKwY2` | 短链接，待解析 / 可点击 | docs/broadcast/page/40.md:14 |
| [たまこまーけっと もちもちトーク＆ライブイベント 簡易レポ!! https://douc.cc/3YoBq0 ←ノベライズ２巻＆新作アニメ企画進行中](<https://douc.cc/3YoBq0>)<br>`https://douc.cc/3YoBq0` | 短链接，待解析 / 纯文本 | docs/broadcast/page/87.md:32 |
| [# 声之形 # 昨天池袋的上映后见面会上，山田导演提到自己为最后一个场景发愁过，然后在去看京阿尼附近的牙医的路上突然找到了灵感。（山田在2015年8月的日记中提到年内要去拔智齿。 https://douc.cc/3ZGlb2 ）](<https://douc.cc/3ZGlb2>)<br>`https://douc.cc/3ZGlb2` | 短链接，待解析 / 纯文本 | docs/broadcast/page/12.md:26 |
| [『中二病でも恋がしたい！戀』 第5話「幻想の・・・ 昼寝迷宮 ( シエスタ・ラビリンス ) 」 脚本：花田十輝 絵コンテ：山田尚子、内海紘子 演出：小川太一 演出補佐：藤田春香 作画監督：西屋太志 https://douc.cc/3aowDg](<https://douc.cc/3aowDg>)<br>`https://douc.cc/3aowDg` | 短链接，待解析 / 纯文本 | docs/broadcast/page/80.md:26 |
| [【『たまこラブストーリー』レビュー】恋をする全ての人へ、この映画を贈る](<https://douc.cc/3aub4M>)<br>`https://douc.cc/3aub4M` | 短链接，待解析 / 可点击 | docs/broadcast/page/62.md:28 |
| [兔子山的视频『たまこラブストーリー』ロングPV](<https://douc.cc/3bICGD>)<br>`https://douc.cc/3bICGD` | 短链接，待解析 / 可点击 | docs/broadcast/page/64.md:20 |
| [お昼寝もちたま夫婦 &#124; ももせ &#91;pixiv&#93; https://douc.cc/3cerPp](<https://douc.cc/3cerPp>)<br>`https://douc.cc/3cerPp` | 短链接，待解析 / 纯文本 | docs/broadcast/page/44.md:32 |
| [【小論】映画「たまこラブストーリー」公開によせて ～フィルムと糸電話、時間と空間をつなぐもの](<https://douc.cc/3cgBNC>)<br>`https://douc.cc/3cgBNC` | 短链接，待解析 / 可点击 | docs/broadcast/page/72.md:24 |
| [《轻音!!》Blu-ray BOX展示图（Amazon大图） https://douc.cc/3dcnkw](<https://douc.cc/3dcnkw>)<br>`https://douc.cc/3dcnkw` | 短链接，待解析 / 纯文本 | docs/broadcast/page/45.md:26 |
| [兔子山的视频瑞穗金融集团 CM 电影《聲之形》篇 30秒](<https://douc.cc/3fRkJT>)<br>`https://douc.cc/3fRkJT` | 短链接，待解析 / 可点击 | docs/broadcast/page/7.md:26 |
| [珍しい組み合わせ！](<https://douc.cc/3gUiJQ>)<br>`https://douc.cc/3gUiJQ` | 短链接，待解析 / 可点击 | docs/broadcast/page/58.md:22 |
| [「けいおん！！」Blu-ray Box 店舗オリジナル特典一覧発表！](<https://douc.cc/3ikwTG>)<br>`https://douc.cc/3ikwTG` | 短链接，待解析 / 可点击 | docs/broadcast/page/52.md:16 |
| [『けいおん』の京アニ・山田尚子監督「Free!の江ちゃんは最高に可愛かったですよね！」](<https://douc.cc/3io9VJ>)<br>`https://douc.cc/3io9VJ` | 短链接，待解析 / 可点击 | docs/broadcast/page/80.md:28 |
| [兔子山的视频【けいおん!!】けいおん学講義 第５回～広がる世界と変わらぬ心～](<https://douc.cc/3kIU0V>)<br>`https://douc.cc/3kIU0V` | 短链接，待解析 / 可点击 | docs/broadcast/page/87.md:24 |
| [北白川たまこ役・洲崎綾さんが”P&#x27;sLIVE!02 ～LOVE＆P&#x27;s～”に出演決定！](<https://douc.cc/3moe9N>)<br>`https://douc.cc/3moe9N` | 短链接，待解析 / 可点击 | docs/broadcast/page/42.md:22 |
| [（後編）たまこラブストーリーレビュー ～鴨川の流れはうねりゆく～](<https://douc.cc/3n0o65>)<br>`https://douc.cc/3n0o65` | 短链接，待解析 / 可点击 | docs/broadcast/page/54.md:16 |
| [映画充☆パピコ](<https://douc.cc/3nwEW2>)<br>`https://douc.cc/3nwEW2` | 短链接，待解析 / 可点击 | docs/broadcast/page/56.md:20 |
| [兔子山的视频电影《声之形》特报](<https://douc.cc/3ofi6w>)<br>`https://douc.cc/3ofi6w` | 短链接，待解析 / 可点击 | docs/broadcast/page/25.md:14 |
| [兔子山的视频电影《声之形》加长版PV](<https://douc.cc/3oni6W>)<br>`https://douc.cc/3oni6W` | 短链接，待解析 / 可点击 | docs/broadcast/page/16.md:16 |
| [【たまこラブストーリー】 読解メモ 07](<https://douc.cc/3p9420>)<br>`https://douc.cc/3p9420` | 短链接，待解析 / 可点击 | docs/broadcast/page/63.md:16 |
| [聴覚障がい者の少女との交流描く『聲の形』 映画化への期待｜dメニュー映画×コラミ...](<https://douc.cc/3pqa1m>)<br>`https://douc.cc/3pqa1m` | 短链接，待解析 / 可点击 | docs/broadcast/page/23.md:22 |
| [「たまこラブストーリー」スタッフ舞台挨拶 決定！](<https://douc.cc/3qCVFZ>)<br>`https://douc.cc/3qCVFZ` | 短链接，待解析 / 可点击 | docs/broadcast/page/61.md:14 |
| [テレビ史上初！ 『けいおん！』全シリーズを1月23日午前11時から24時間一挙放送！ メインキャストから愛情たっぷりのコメントも到着](<https://douc.cc/3stCCi>)<br>`https://douc.cc/3stCCi` | 短链接，待解析 / 可点击 | docs/broadcast/page/26.md:30 |
| [ｗ https://douc.cc/3vicON](<https://douc.cc/3vicON>)<br>`https://douc.cc/3vicON` | 短链接，待解析 / 纯文本 | docs/broadcast/page/54.md:14 |
| [兔子山的视频【画像90枚】けいおん！ラッピング電車 HO-KAGO TEA TIME TRAIN](<https://douc.cc/3wFOQD>)<br>`https://douc.cc/3wFOQD` | 短链接，待解析 / 可点击 | docs/broadcast/page/51.md:30 |
| [《玉子市场》Blu-ray BOX京阿尼Shop预约开始，独家特典：Creator Book「How we made Tamako Market」，2015年2月22日截订。 https://douc.cc/3wgEt4](<https://douc.cc/3wgEt4>)<br>`https://douc.cc/3wgEt4` | 短链接，待解析 / 纯文本 | docs/broadcast/page/41.md:18 |
| [兔子山的视频电影《聲之形》主题歌PV](<https://douc.cc/3wtqum>)<br>`https://douc.cc/3wtqum` | 短链接，待解析 / 可点击 | docs/broadcast/page/10.md:24 |
| [电影《声之形》9月17日上映！导演：山田尚子，剧本：吉田玲子，角色设计：西屋太志，制作：京都动画，官网： https://douc.cc/3ysQT1 ，官推： https://douc.cc/3yQaKK ，特报： https://douc.cc/0vMqgF](<https://douc.cc/3yQaKK>)<br>`https://douc.cc/3yQaKK` | 短链接，待解析 / 纯文本 | docs/broadcast/page/25.md:16 |
| [☆ 京アニ&amp;Do CTFK2013 感想・レポ ★ https://douc.cc/3ymZKn 这篇更详细，推荐。](<https://douc.cc/3ymZKn>)<br>`https://douc.cc/3ymZKn` | 短链接，待解析 / 纯文本 | docs/broadcast/page/84.md:26 |
| [电影《声之形》官网更新，新宣传图、全角色、正式版预告片解禁，CAST寄语公开！ https://douc.cc/3ysQT1 https://douc.cc/2tUTKh # 声之形 #](<https://douc.cc/3ysQT1>)<br>`https://douc.cc/3ysQT1` | 短链接，待解析 / 纯文本 | docs/broadcast/page/22.md:16<br>docs/broadcast/page/25.md:16 |
| [WebNewtype-山田監督の山ごもりの成果!? 映画「たまこラブストーリー」...](<https://douc.cc/3zcO1g>)<br>`https://douc.cc/3zcO1g` | 短链接，待解析 / 可点击 | docs/broadcast/page/59.md:32 |
| [ぎりぎり間に合った～～～っ！](<https://douc.cc/40XKgI>)<br>`https://douc.cc/40XKgI` | 短链接，待解析 / 可点击 | docs/broadcast/page/50.md:24 |
| [兔子山的视频【けいおん!!】けいおん学講義 第１回～けいおんのテーマとは～](<https://douc.cc/40jG2r>)<br>`https://douc.cc/40jG2r` | 短链接，待解析 / 可点击 | docs/broadcast/page/88.md:22 |
| [『たまこラブストーリー』16日間 興収１億２千万円](<https://douc.cc/41N4ZM>)<br>`https://douc.cc/41N4ZM` | 短链接，待解析 / 可点击 | docs/broadcast/page/63.md:18 |
| [兔子山的视频《STAND UP》20160915 电影《声之形》相关报道](<https://douc.cc/41nKVC>)<br>`https://douc.cc/41nKVC` | 短链接，待解析 / 可点击 | docs/broadcast/page/14.md:18 |
| [兔子山的视频【AnimeJapan2014】たまこラブストーリー【ぽにきゃんブース1日】](<https://douc.cc/42FPKY>)<br>`https://douc.cc/42FPKY` | 短链接，待解析 / 可点击 | docs/broadcast/page/76.md:24 |
| [映画「聲の形」 松岡茉優 早見沙織 山田尚子監督 ZIP! (08.25)](<https://douc.cc/43dvPt>)<br>`https://douc.cc/43dvPt` | 短链接，待解析 / 可点击 | docs/broadcast/page/18.md:16 |
| [「たまこラブストーリー」は「恋」による「変化」を描いた青春映画の傑作。](<https://douc.cc/43ecke>)<br>`https://douc.cc/43ecke` | 短链接，待解析 / 可点击 | docs/broadcast/page/70.md:26 |
| [兔子山的视频电影《声之形》TVCM 1](<https://douc.cc/44Z2EM>)<br>`https://douc.cc/44Z2EM` | 短链接，待解析 / 可点击 | docs/broadcast/page/16.md:22 |
| [【たまらぶ】 読解メモ 02](<https://douc.cc/45Q2KT>)<br>`https://douc.cc/45Q2KT` | 短链接，待解析 / 可点击 | docs/broadcast/page/69.md:16 |
| [【这个反常识的建筑，多年后却成为奇特的乐园】来自刻画视频 - 微博](<https://douc.cc/45dR9p>)<br>`https://douc.cc/45dR9p` | 短链接，待解析 / 可点击 | docs/broadcast/page/3.md:32 |
| [劇場版「たまこラブストーリー」BD アニメイト・ゲーマーズ・とらのあな・ソフマッ...](<https://douc.cc/46ywkQ>)<br>`https://douc.cc/46ywkQ` | 短链接，待解析 / 可点击 | docs/broadcast/page/48.md:14 |
| [【たまこラブストーリー】出町桝形商店街“標語”再現メイキングレポート](<https://douc.cc/47UF7v>)<br>`https://douc.cc/47UF7v` | 短链接，待解析 / 可点击 | docs/broadcast/page/51.md:22 |
| [【ED】最后两朵挨在一起蒲公英，对应花语“真心的爱”。 https://douc.cc/47UkK9 # 玉子爱情故事 #](<https://douc.cc/47UkK9>)<br>`https://douc.cc/47UkK9` | 短链接，待解析 / 纯文本 | docs/broadcast/page/46.md:20 |
| [正当饼藏准备拿出传声筒告白时玉子捡起了年糕石，饼藏一时放弃了告白。这块石头象征“年糕”，也就是母亲雏子。玉子险些摔倒时顺势丢下了石头，这是母亲的存在一时从玉子心中消失的暗喻。饼藏在那一刻告白了，因而这一击自然是相当强力的。 https://douc.cc/48zAx7 # 玉子爱](<https://douc.cc/48zAx7>)<br>`https://douc.cc/48zAx7` | 短链接，待解析 / 纯文本 | docs/broadcast/page/48.md:28 |
| [「けいおん!」監督、最新作『たまこラブストーリー』初日に熱い思いを語る！](<https://douc.cc/49MqFL>)<br>`https://douc.cc/49MqFL` | 短链接，待解析 / 可点击 | docs/broadcast/page/71.md:32 |
| [♡たまこラブストーリー♡](<https://douc.cc/4BDRFM>)<br>`https://douc.cc/4BDRFM` | 短链接，待解析 / 可点击 | docs/broadcast/page/65.md:16 |
| [ザ・テレビジョンに『けいおん！』新規描き下ろしイラストが掲載されてるぞ！！ 可愛すぎる・・・・! https://douc.cc/4BsiBV](<https://douc.cc/4BsiBV>)<br>`https://douc.cc/4BsiBV` | 短链接，待解析 / 纯文本 | docs/broadcast/page/80.md:32 |
| [第１回：インタビュー 山口優（前編）〜渋谷系ではなく、ソフトロックなんです &#124; マニュエラだから作れた『たまこまーけっと』の音楽 &#124; RandoM](<https://douc.cc/4EFOwC>)<br>`https://douc.cc/4EFOwC` | 短链接，待解析 / 可点击 | docs/broadcast/page/87.md:18 |
| [电影《声之形》新画面公开，入场者赠品Special book发放决定。 https://douc.cc/4FDmKI # 声之形 #](<https://douc.cc/4FDmKI>)<br>`https://douc.cc/4FDmKI` | 短链接，待解析 / 纯文本 | docs/broadcast/page/17.md:30 |
| [电影《聲之形》Blu-ray＆DVD 5月17日发售决定！ https://douc.cc/4FGBFU # 声之形 #](<https://douc.cc/4FGBFU>)<br>`https://douc.cc/4FGBFU` | 短链接，待解析 / 纯文本 | docs/broadcast/page/6.md:20 |
| [舞台挨拶いっくよー！](<https://douc.cc/4Fvaa7>)<br>`https://douc.cc/4Fvaa7` | 短链接，待解析 / 可点击 | docs/broadcast/page/63.md:32 |
| [《玉子爱情故事》Blu-ray&amp;DVD 店铺特典情报更新 https://douc.cc/4GiJZ8](<https://douc.cc/4GiJZ8>)<br>`https://douc.cc/4GiJZ8` | 短链接，待解析 / 纯文本 | docs/broadcast/page/56.md:32 |
| [『たまこラブストーリー』を観に行け！ と急かす話](<https://douc.cc/4d31uw>)<br>`https://douc.cc/4d31uw` | 短链接，待解析 / 可点击 | docs/broadcast/page/71.md:26 |
| [Tamako Love Story Premiere, Afterparty a...](<https://douc.cc/4dDM5c>)<br>`https://douc.cc/4dDM5c` | 短链接，待解析 / 可点击 | docs/broadcast/page/69.md:32 |
| [兔子山的视频【けいおん!!】けいおん学講義 第2回～けいおんと暗喩～](<https://douc.cc/4dXqwz>)<br>`https://douc.cc/4dXqwz` | 短链接，待解析 / 可点击 | docs/broadcast/page/88.md:20 |
| [# 吹响悠风号 # 響け!ユーフォニアム GUIDEBOOK【予約品】【2015年4月15日出荷開始予定】 https://douc.cc/4hO1Ch](<https://douc.cc/4hO1Ch>)<br>`https://douc.cc/4hO1Ch` | 短链接，待解析 / 纯文本 | docs/broadcast/page/38.md:16 |
| [【重新推荐下这四篇访谈（必读！）】官网导演访谈（上映前） https://douc.cc/01SUy9 https://douc.cc/1eIOys excite导演访谈（上映后） https://douc.cc/4hTTqG https://douc.cc/3Jc6Wt # 玉](<https://douc.cc/4hTTqG>)<br>`https://douc.cc/4hTTqG` | 短链接，待解析 / 纯文本 | docs/broadcast/page/49.md:26 |
| [シネマサンシャインかほく https://douc.cc/4heYta](<https://douc.cc/4heYta>)<br>`https://douc.cc/4heYta` | 短链接，待解析 / 纯文本 | docs/broadcast/page/59.md:16 |
| [もち蔵からの☆パピコ](<https://douc.cc/4iLUV3>)<br>`https://douc.cc/4iLUV3` | 短链接，待解析 / 可点击 | docs/broadcast/page/78.md:28 |
| [《吹响悠风号》官网更新 https://douc.cc/1SKW10 番宣CM公开 https://douc.cc/4jGqTg](<https://douc.cc/4jGqTg>)<br>`https://douc.cc/4jGqTg` | 短链接，待解析 / 纯文本 | docs/broadcast/page/39.md:18 |
| [第７回：鼎談 藤本功一＋宮川弾＋山口優（前編）〜噂では振付しながら歌詞を考えるそうだけど？ &#124; マニュエラだから作れた『たまこまーけっと』の音楽 &#124; RandoM](<https://douc.cc/4jISkK>)<br>`https://douc.cc/4jISkK` | 短链接，待解析 / 可点击 | docs/broadcast/page/86.md:22 |
| [【コラム】日常アニメの中のニーチェ](<https://douc.cc/4m3559>)<br>`https://douc.cc/4m3559` | 短链接，待解析 / 可点击 | docs/broadcast/page/55.md:18 |
| [电影《聲之形》京阿尼shop!周边商品已开通网购预定 https://douc.cc/4m8QGF ，重点是官方设定集。 https://douc.cc/04ea5n # 声之形 #](<https://douc.cc/4m8QGF>)<br>`https://douc.cc/4m8QGF` | 短链接，待解析 / 纯文本 | docs/broadcast/page/11.md:20 |
| [【映画読解】 空の向こう、星の彼方](<https://douc.cc/4mGAV7>)<br>`https://douc.cc/4mGAV7` | 短链接，待解析 / 可点击 | docs/broadcast/page/83.md:16 |
| [【たまらぶ】 読解メモ 01](<https://douc.cc/4nJ7tH>)<br>`https://douc.cc/4nJ7tH` | 短链接，待解析 / 可点击 | docs/broadcast/page/70.md:14 |
| [【たまらぶ】 読解メモ 01追補](<https://douc.cc/4nX0mX>)<br>`https://douc.cc/4nX0mX` | 短链接，待解析 / 可点击 | docs/broadcast/page/69.md:30 |
| [「Free!」第7話！絵コンテ・演出／山田尚子を堪能する!!](<https://douc.cc/4nxl34>)<br>`https://douc.cc/4nxl34` | 短链接，待解析 / 可点击 | docs/broadcast/page/85.md:32 |
| [关于“结絃梦中的鸽子与硝子”再做几点补充 https://douc.cc/4serzG 补充内容如图（剧透注意） # 声之形 #](<https://douc.cc/4serzG>)<br>`https://douc.cc/4serzG` | 短链接，待解析 / 纯文本 | docs/broadcast/page/4.md:26<br>docs/broadcast/page/4.md:28 |
| [兔子山的视频映画『たまこラブストーリー』主題歌「プリンシプル」試聴動画](<https://douc.cc/4styZs>)<br>`https://douc.cc/4styZs` | 短链接，待解析 / 可点击 | docs/broadcast/page/76.md:22 |
| [映画「たまこラブストーリー」大ヒット御礼 スタッフ舞台挨拶（山田尚子監督・小川太一さん・瀬波里梨P）レポート](<https://douc.cc/4tGg4u>)<br>`https://douc.cc/4tGg4u` | 短链接，待解析 / 可点击 | docs/broadcast/page/60.md:14 |
| [「日常系ダイアリー――アニメ批評のためのメモランダム」第07回 うさぎ山商店街・天使の詩――『たまこラブストーリー』試論（後編）／文：高瀬司（アニメルカ）](<https://douc.cc/4tyQLP>)<br>`https://douc.cc/4tyQLP` | 短链接，待解析 / 可点击 | docs/broadcast/page/57.md:22 |
| [新宿ピカデリーの「たまこラブストーリー」パッケージ発売記念イベントに行ってきました](<https://douc.cc/4uRNEc>)<br>`https://douc.cc/4uRNEc` | 短链接，待解析 / 可点击 | docs/broadcast/page/52.md:28 |
| [思い立って](<https://douc.cc/4uZbhM>)<br>`https://douc.cc/4uZbhM` | 短链接，待解析 / 可点击 | docs/broadcast/page/69.md:20 |
| [兔子山的视频松冈茉优×早见沙织电视采访（「おはようコールABC」20160913）](<https://douc.cc/4vD6tr>)<br>`https://douc.cc/4vD6tr` | 短链接，待解析 / 可点击 | docs/broadcast/page/15.md:16 |
| [ラブしてます☆パピコ](<https://douc.cc/4vz8hC>)<br>`https://douc.cc/4vz8hC` | 短链接，待解析 / 可点击 | docs/broadcast/page/81.md:14 |
| [映画「聲の形」大今良時が入野自由の声を聞き「将也を主人公にしてくれた」](<https://douc.cc/4xHm89>)<br>`https://douc.cc/4xHm89` | 短链接，待解析 / 可点击 | docs/broadcast/page/21.md:18 |

### eco.mtk.nao.ac.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [【暦計算室】](<http://eco.mtk.nao.ac.jp/koyomi/>)<br>`http://eco.mtk.nao.ac.jp/koyomi/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/curated/index.md:155<br>docs/rooms/2793793.md:109 |

### froovie.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [电影《聲之形》场刊](<http://froovie.jp/shop/g/g2809320/>)<br>`http://froovie.jp/shop/g/g2809320/` | 商品 / 商店 / 可点击 | docs/notes/620639436.md:12<br>docs/notes/620796838.md:12 |

### gd.qq.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [威廉·哈默休伊](<http://gd.qq.com/a/20160812/022984.htm>)<br>`http://gd.qq.com/a/20160812/022984.htm` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/582498318.md:43 |

### hatenanews.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [京アニ八田社長が語る“ヒットの理由”とは？「けいおん！」監督も登場した講演レポート](<http://hatenanews.com/articles/201010/1809>)<br>`http://hatenanews.com/articles/201010/1809` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:49 |

### heike-anime.asmik-ace.co.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [《平家物语》](<https://heike-anime.asmik-ace.co.jp/>)<br>`https://heike-anime.asmik-ace.co.jp/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/about.md:14<br>docs/rooms/2793793.md:132 |

### houtaruu.weblog.to

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [響け！ユーフォニアム【山田尚子＆石原立也 舞台挨拶】](<http://houtaruu.weblog.to/archives/6879881.html>)<br>`http://houtaruu.weblog.to/archives/6879881.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/580950328.md:13 |
| [①](<http://houtaruu.weblog.to/archives/7271602.html>)<br>`http://houtaruu.weblog.to/archives/7271602.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/583976644.md:12 |

### htt123.blog.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [「たまこまーけっと」セレクション上映 スタッフ舞台挨拶レポート(登壇者：山田尚子、西屋太志、小川太一)](<http://htt123.blog.jp/archives/1060754985.html>)<br>`http://htt123.blog.jp/archives/1060754985.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:71 |
| [②](<http://htt123.blog.jp/archives/1061217653.html>)<br>`http://htt123.blog.jp/archives/1061217653.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/583976644.md:12 |
| [③](<http://htt123.blog.jp/archives/1061263102.html>)<br>`http://htt123.blog.jp/archives/1061263102.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/583976644.md:12 |
| [①](<http://htt123.blog.jp/archives/1061271619.html>)<br>`http://htt123.blog.jp/archives/1061271619.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/584217092.md:12 |

### httesora.blog.fc2.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [☆ 京アニ&amp;Do CTFK2013 感想・レポ ★](<http://httesora.blog.fc2.com/blog-entry-14.html>)<br>`http://httesora.blog.fc2.com/blog-entry-14.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:64 |

### img3.douban.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [官网首页图第2弹](<http://img3.douban.com/view/photo/raw/public/p2173264901.jpg>)<br>`http://img3.douban.com/view/photo/raw/public/p2173264901.jpg` | 图片 / 全景资料链接 / 可点击 | docs/notes/338329832.md:110 |

### img3.doubanio.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://img3.douban.com/view/note/large/public/p29295562.jpg&#91;/img&#93;](<https://img3.doubanio.com/view/note/large/public/p29295562.jpg%5B/img%5D>)<br>`https://img3.doubanio.com/view/note/large/public/p29295562.jpg%5B/img%5D` | 图片 / 全景资料链接 / 可点击 | docs/notes/519165447.md:77 |

### isladelpescado.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [网站](<http://isladelpescado.com/item/succulents/euphorbia.html>)<br>`http://isladelpescado.com/item/succulents/euphorbia.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/502853776.md:21 |
| [贵青玉（Euphorbia meloformis）](<http://isladelpescado.com/item/succulents/euphorbia/euphorbia_meloformis.html>)<br>`http://isladelpescado.com/item/succulents/euphorbia/euphorbia_meloformis.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/502853776.md:21 |
| [布纹球（Euphorbia obesa）](<http://isladelpescado.com/item/succulents/euphorbia/euphorbia_obesa.html>)<br>`http://isladelpescado.com/item/succulents/euphorbia/euphorbia_obesa.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/502853776.md:21 |
| [这颗品种未知的Euphorbia](<http://isladelpescado.com/item/succulents/euphorbia/euphorbia_sp_ball_type_a.html>)<br>`http://isladelpescado.com/item/succulents/euphorbia/euphorbia_sp_ball_type_a.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/502853776.md:21 |

### j-mediaarts.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [第18回文化庁メディア芸術祭 アニメーション部門 新人賞](<http://j-mediaarts.jp/awards/new_face_award?section_id=3&locale=ja>)<br>`http://j-mediaarts.jp/awards/new_face_award?section_id=3&locale=ja` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/460892811.md:10 |

### ja.wikipedia.org

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [YMO](<http://ja.wikipedia.org/wiki/%E3%82%A4%E3%82%A8%E3%83%AD%E3%83%BC%E3%83%BB%E3%83%9E%E3%82%B8%E3%83%83%E3%82%AF%E3%83%BB%E3%82%AA%E3%83%BC%E3%82%B1%E3%82%B9%E3%83%88%E3%83%A9>)<br>`http://ja.wikipedia.org/wiki/%E3%82%A4%E3%82%A8%E3%83%AD%E3%83%BC%E3%83%BB%E3%83%9E%E3%82%B8%E3%83%83%E3%82%AF%E3%83%BB%E3%82%AA%E3%83%BC%E3%82%B1%E3%82%B9%E3%83%88%E3%83%A9` | 百科资料 / 可点击 | docs/about.md:26<br>docs/rooms/2793793.md:144 |
| [《時間ですよ》](<http://ja.wikipedia.org/wiki/%E6%99%82%E9%96%93%E3%81%A7%E3%81%99%E3%82%88>)<br>`http://ja.wikipedia.org/wiki/%E6%99%82%E9%96%93%E3%81%A7%E3%81%99%E3%82%88` | 百科资料 / 可点击 | docs/notes/347460778.md:82 |
| [電気グルーヴ](<http://ja.wikipedia.org/wiki/%E9%9B%BB%E6%B0%97%E3%82%B0%E3%83%AB%E3%83%BC%E3%83%B4>)<br>`http://ja.wikipedia.org/wiki/%E9%9B%BB%E6%B0%97%E3%82%B0%E3%83%AB%E3%83%BC%E3%83%B4` | 百科资料 / 可点击 | docs/about.md:26<br>docs/rooms/2793793.md:144 |
| [BUCK-TICK](<http://ja.wikipedia.org/wiki/BUCK-TICK>)<br>`http://ja.wikipedia.org/wiki/BUCK-TICK` | 百科资料 / 可点击 | docs/about.md:26<br>docs/rooms/2793793.md:144 |
| [Wikipedia](<https://ja.wikipedia.org/wiki/%E3%81%91%E3%81%84%E3%81%8A%E3%82%93!>)<br>`https://ja.wikipedia.org/wiki/%E3%81%91%E3%81%84%E3%81%8A%E3%82%93!` | 百科资料 / 可点击 | docs/rooms/2794136.md:17 |
| [Wikipedia](<https://ja.wikipedia.org/wiki/%E3%81%9F%E3%81%BE%E3%81%93%E3%81%BE%E3%83%BC%E3%81%91%E3%81%A3%E3%81%A8>)<br>`https://ja.wikipedia.org/wiki/%E3%81%9F%E3%81%BE%E3%81%93%E3%81%BE%E3%83%BC%E3%81%91%E3%81%A3%E3%81%A8` | 百科资料 / 可点击 | docs/rooms/2794121.md:17 |
| [运动短裤](<https://ja.wikipedia.org/wiki/%E3%83%96%E3%83%AB%E3%83%9E%E3%83%BC>)<br>`https://ja.wikipedia.org/wiki/%E3%83%96%E3%83%AB%E3%83%9E%E3%83%BC` | 百科资料 / 可点击 | docs/notes/525677843.md:193 |
| [Wikipedia](<https://ja.wikipedia.org/wiki/%E5%B1%B1%E7%94%B0%E5%B0%9A%E5%AD%90>)<br>`https://ja.wikipedia.org/wiki/%E5%B1%B1%E7%94%B0%E5%B0%9A%E5%AD%90` | 百科资料 / 可点击 | docs/about.md:7<br>docs/rooms/2793793.md:125 |

### kansai.pia.co.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [琵雅关西版WEB](<http://kansai.pia.co.jp/interview/cinema/2016-10/koenokatachi-movie.html>)<br>`http://kansai.pia.co.jp/interview/cinema/2016-10/koenokatachi-movie.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/586529041.md:12 |

### keisukeyuki.blogspot.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [雑記 たまこラブストーリー](<http://keisukeyuki.blogspot.jp/2014/05/blog-post.html>)<br>`http://keisukeyuki.blogspot.jp/2014/05/blog-post.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:53 |

### koenokatachi-movie.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [《聲之形》](<http://koenokatachi-movie.com/>)<br>`http://koenokatachi-movie.com/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/about.md:14<br>docs/albums/190597061.md:86<br>docs/notes/550509861.md:12<br>docs/notes/575910736.md:10<br>docs/rooms/2793793.md:132<br>docs/rooms/3598399.md:17 |
| [【川井美树 cv.潘惠美】](<http://koenokatachi-movie.com/character/kawai/>)<br>`http://koenokatachi-movie.com/character/kawai/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/572997848.md:63 |
| [【真柴智 cv.丰永利行】](<http://koenokatachi-movie.com/character/mashiba/>)<br>`http://koenokatachi-movie.com/character/mashiba/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/572997848.md:68 |
| [【永束友宏 cv.小野贤章】](<http://koenokatachi-movie.com/character/nagatsuka/>)<br>`http://koenokatachi-movie.com/character/nagatsuka/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/572997848.md:52 |
| [【佐原美世子 cv.石川由依】](<http://koenokatachi-movie.com/character/sahara/>)<br>`http://koenokatachi-movie.com/character/sahara/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/572997848.md:59 |
| [【西宫硝子 cv.早见沙织】](<http://koenokatachi-movie.com/character/shoko/>)<br>`http://koenokatachi-movie.com/character/shoko/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/572997848.md:32 |
| [电影《聲之形》官网](<http://koenokatachi-movie.com/character/shoya/>)<br>`http://koenokatachi-movie.com/character/shoya/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/569110361.md:10<br>docs/notes/572997848.md:17 |
| [石田将也（小学生）](<http://koenokatachi-movie.com/character/shoya_s/>)<br>`http://koenokatachi-movie.com/character/shoya_s/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/572997848.md:73 |
| [【植野直花 cv.金子有希】](<http://koenokatachi-movie.com/character/ueno/>)<br>`http://koenokatachi-movie.com/character/ueno/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/572997848.md:56 |
| [【西宫结絃 cv.悠木碧】](<http://koenokatachi-movie.com/character/yuzuru/>)<br>`http://koenokatachi-movie.com/character/yuzuru/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/572997848.md:48 |
| [牛尾宪辅](<http://koenokatachi-movie.com/music/>)<br>`http://koenokatachi-movie.com/music/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/575910736.md:14 |
| [補聴器メーカー シバントス株式会社とのタイアップが決定！ http://koenokatachi-movie.com/news/?id=11](<http://koenokatachi-movie.com/news/?id=11>)<br>`http://koenokatachi-movie.com/news/?id=11` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:151 |
| [电影《聲之形》爆米花特典文件夹图 http://koenokatachi-movie.com/news/?id=35](<http://koenokatachi-movie.com/news/?id=35>)<br>`http://koenokatachi-movie.com/news/?id=35` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:96 |
| [见面会](<http://koenokatachi-movie.com/news/?id=94>)<br>`http://koenokatachi-movie.com/news/?id=94` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/604396376.md:18 |
| [电影《聲之形》官网](<http://koenokatachi-movie.com/special/01comment/>)<br>`http://koenokatachi-movie.com/special/01comment/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/520557685.md:13 |
| [电影《聲之形》官网](<http://koenokatachi-movie.com/special/04castcomment/>)<br>`http://koenokatachi-movie.com/special/04castcomment/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/569286438.md:10 |
| [电影《聲之形》官网](<http://koenokatachi-movie.com/special/05report/>)<br>`http://koenokatachi-movie.com/special/05report/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/572997848.md:11 |
| [aiko](<http://koenokatachi-movie.com/themesong/>)<br>`http://koenokatachi-movie.com/themesong/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/575910736.md:38 |

### kyoanido-event.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [京阿尼＆Do答谢会](<http://kyoanido-event.com/>)<br>`http://kyoanido-event.com/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/525677843.md:12 |
| [第二届京阿尼＆Do答谢会官网活动报告 http://kyoanido-event.com/2015/report/](<http://kyoanido-event.com/2015/report/>)<br>`http://kyoanido-event.com/2015/report/` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:19<br>docs/albums/13433748.md:20 |
| [对谈和签名会](<http://kyoanido-event.com/stage/>)<br>`http://kyoanido-event.com/stage/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/525677843.md:36 |

### kyoanishop.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [【KyoaniShop!】](<http://kyoanishop.com/>)<br>`http://kyoanishop.com/` | 商品 / 商店 / 可点击 | docs/curated/index.md:152<br>docs/rooms/2793793.md:109 |
| [《电影 聲之形 Making Book》](<http://kyoanishop.com/shopdetail/000000000984/>)<br>`http://kyoanishop.com/shopdetail/000000000984/` | 商品 / 商店 / 可点击 | docs/notes/623079239.md:12<br>docs/notes/623264433.md:12<br>docs/notes/624120737.md:12 |

### liz-bluebird.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [《丽兹与青鸟》](<http://liz-bluebird.com/>)<br>`http://liz-bluebird.com/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/about.md:14<br>docs/albums/13432051.md:13<br>docs/notes/649190492.md:15<br>docs/rooms/2793793.md:132 |

### mantan-web.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [访谈](<http://mantan-web.jp/2015/05/30/20150529dog00m200066000c.html>)<br>`http://mantan-web.jp/2015/05/30/20150529dog00m200066000c.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/505913072.md:49 |
| [MANTANWEB](<http://mantan-web.jp/2016/09/11/20160910dog00m200008000c.html>)<br>`http://mantan-web.jp/2016/09/11/20160910dog00m200008000c.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/569110361.md:34 |
| [http://mantan-web.jp/2016/09/17/20160917dog00m200025000c.html](<http://mantan-web.jp/2016/09/17/20160917dog00m200025000c.html>)<br>`http://mantan-web.jp/2016/09/17/20160917dog00m200025000c.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:55 |

### minamiruruka.seesaa.net

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [南瑠霞](<http://minamiruruka.seesaa.net/article/441458062.html>)<br>`http://minamiruruka.seesaa.net/article/441458062.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/584217092.md:27 |

### mirrorring.doorblog.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [④](<http://mirrorring.doorblog.jp/archives/52220732.html>)<br>`http://mirrorring.doorblog.jp/archives/52220732.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/583976644.md:12 |

### moca-news.net

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [劇場版アニメ『たまこラブストーリー』がついに公開。公開初日には洲崎綾・田丸篤志・山田尚子監督らによる舞台挨拶を実施 http://moca-news.net/article/20140427/201404271222a/01/?afid=difa](<http://moca-news.net/article/20140427/201404271222a/01/?afid=difa>)<br>`http://moca-news.net/article/20140427/201404271222a/01/?afid=difa` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:145 |

### movie.douban.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [罗伊·安德森](<http://movie.douban.com/celebrity/1000561/>)<br>`http://movie.douban.com/celebrity/1000561/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:16<br>docs/rooms/2793793.md:134 |
| [诺曼·麦克拉伦](<http://movie.douban.com/celebrity/1000797/>)<br>`http://movie.douban.com/celebrity/1000797/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:143 |
| [亚历桑德罗·佐杜洛夫斯基](<http://movie.douban.com/celebrity/1004767/>)<br>`http://movie.douban.com/celebrity/1004767/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:16<br>docs/rooms/2793793.md:134 |
| [德里克·贾曼](<http://movie.douban.com/celebrity/1007155/>)<br>`http://movie.douban.com/celebrity/1007155/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:143 |
| [肯尼思·安格](<http://movie.douban.com/celebrity/1007163/>)<br>`http://movie.douban.com/celebrity/1007163/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:143 |
| [谢尔盖·帕拉杰诺夫](<http://movie.douban.com/celebrity/1014248/>)<br>`http://movie.douban.com/celebrity/1014248/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:16<br>docs/notes/410464332.md:16<br>docs/rooms/2793793.md:134 |
| [吉力·唐卡](<http://movie.douban.com/celebrity/1033076/>)<br>`http://movie.douban.com/celebrity/1033076/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:143 |
| [小津安二郎](<http://movie.douban.com/celebrity/1036727/>)<br>`http://movie.douban.com/celebrity/1036727/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:16<br>docs/rooms/2793793.md:134 |
| [寺山修司](<http://movie.douban.com/celebrity/1037316/>)<br>`http://movie.douban.com/celebrity/1037316/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/531685883.md:124 |
| [吉利·巴塔](<http://movie.douban.com/celebrity/1037370/>)<br>`http://movie.douban.com/celebrity/1037370/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:143 |
| [米歇尔·冈瑞](<http://movie.douban.com/celebrity/1044932/>)<br>`http://movie.douban.com/celebrity/1044932/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:143 |
| [尤里·诺尔施泰因](<http://movie.douban.com/celebrity/1050787/>)<br>`http://movie.douban.com/celebrity/1050787/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:143 |
| [索菲亚·科波拉](<http://movie.douban.com/celebrity/1054399/>)<br>`http://movie.douban.com/celebrity/1054399/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:16<br>docs/rooms/2793793.md:134 |
| [杨·史云梅耶](<http://movie.douban.com/celebrity/1054506/>)<br>`http://movie.douban.com/celebrity/1054506/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:16<br>docs/notes/525677843.md:139<br>docs/rooms/2793793.md:134 |
| [克里斯·坎宁安](<http://movie.douban.com/celebrity/1179951/>)<br>`http://movie.douban.com/celebrity/1179951/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:143 |
| [奎氏兄](<http://movie.douban.com/celebrity/1295047/>)<br>`http://movie.douban.com/celebrity/1295047/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:143 |
| [弟](<http://movie.douban.com/celebrity/1295056/>)<br>`http://movie.douban.com/celebrity/1295056/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:143 |
| [Pao](<http://movie.douban.com/photos/photo/2198139096/>)<br>`http://movie.douban.com/photos/photo/2198139096/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/410073605.md:24<br>docs/notes/430242140.md:25 |
| [《氷菓》](<http://movie.douban.com/subject/10001418/>)<br>`http://movie.douban.com/subject/10001418/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:87 |
| [《中二病でも恋がしたい！》](<http://movie.douban.com/subject/11226092/>)<br>`http://movie.douban.com/subject/11226092/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:76 |
| [《境界の彼方》](<http://movie.douban.com/subject/11226094/>)<br>`http://movie.douban.com/subject/11226094/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:92 |
| [《弗兰西丝·哈》](<http://movie.douban.com/subject/11527487/>)<br>`http://movie.douban.com/subject/11527487/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/notes/536415117.md:14<br>docs/rooms/2793793.md:136 |
| [《龙猫》](<http://movie.douban.com/subject/1291560/>)<br>`http://movie.douban.com/subject/1291560/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/rooms/2793793.md:136 |
| [《风之谷》](<http://movie.douban.com/subject/1291585/>)<br>`http://movie.douban.com/subject/1291585/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/rooms/2793793.md:136 |
| [《迷失东京》](<http://movie.douban.com/subject/1291835/>)<br>`http://movie.douban.com/subject/1291835/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/notes/525677843.md:143<br>docs/rooms/2793793.md:136 |
| [《柏林苍穹下》](<http://movie.douban.com/subject/1292504/>)<br>`http://movie.douban.com/subject/1292504/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/412701420.md:13 |
| [《天外来客》](<http://movie.douban.com/subject/1293443/>)<br>`http://movie.douban.com/subject/1293443/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/536415117.md:40 |
| [《寅次郎的故事》](<http://movie.douban.com/subject/1298487/>)<br>`http://movie.douban.com/subject/1298487/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:214 |
| [《回到未来》](<http://movie.douban.com/subject/1300555/>)<br>`http://movie.douban.com/subject/1300555/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:116 |
| [《坏血》](<http://movie.douban.com/subject/1301678/>)<br>`http://movie.douban.com/subject/1301678/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/notes/536415117.md:18<br>docs/rooms/2793793.md:136 |
| [《石榴的颜色》](<http://movie.douban.com/subject/1303542/>)<br>`http://movie.douban.com/subject/1303542/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/notes/410464332.md:20<br>docs/notes/531685883.md:126<br>docs/rooms/2793793.md:136 |
| [《爱丽丝》](<http://movie.douban.com/subject/1305817/>)<br>`http://movie.douban.com/subject/1305817/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/notes/525677843.md:140<br>docs/rooms/2793793.md:136 |
| [《死者田园祭》](<http://movie.douban.com/subject/1366165/>)<br>`http://movie.douban.com/subject/1366165/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/531685883.md:124 |
| [《圣山》](<http://movie.douban.com/subject/1401905/>)<br>`http://movie.douban.com/subject/1401905/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/notes/410095370.md:12<br>docs/rooms/2793793.md:136 |
| [《黑暗 光明 黑暗》](<http://movie.douban.com/subject/1422233/>)<br>`http://movie.douban.com/subject/1422233/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:148 |
| [《纯真》](<http://movie.douban.com/subject/1444232/>)<br>`http://movie.douban.com/subject/1444232/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/notes/520941015.md:28<br>docs/notes/521041733.md:15<br>docs/rooms/2793793.md:136 |
| [同名电影](<http://movie.douban.com/subject/1452648/>)<br>`http://movie.douban.com/subject/1452648/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/429473097.md:13<br>docs/notes/429716807.md:12 |
| [《フルメタル・パニック？ふもっふ》](<http://movie.douban.com/subject/1463762/>)<br>`http://movie.douban.com/subject/1463762/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:84 |
| [《フルメタル・パニック！The Second Raid》](<http://movie.douban.com/subject/1463764/>)<br>`http://movie.douban.com/subject/1463764/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:85 |
| [《瑞典爱情故事》](<http://movie.douban.com/subject/1463934/>)<br>`http://movie.douban.com/subject/1463934/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/rooms/2793793.md:136 |
| [《对话的可能性》](<http://movie.douban.com/subject/1464067/>)<br>`http://movie.douban.com/subject/1464067/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:147 |
| [《荒唐童话》](<http://movie.douban.com/subject/1467638/>)<br>`http://movie.douban.com/subject/1467638/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:146 |
| [《女优灵》](<http://movie.douban.com/subject/1764253/>)<br>`http://movie.douban.com/subject/1764253/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:141 |
| [《涼宮ハルヒの憂鬱》](<http://movie.douban.com/subject/1810517/>)<br>`http://movie.douban.com/subject/1810517/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:70 |
| [《Kanon》](<http://movie.douban.com/subject/1959005/>)<br>`http://movie.douban.com/subject/1959005/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:71 |
| [《AIR》](<http://movie.douban.com/subject/1980737/>)<br>`http://movie.douban.com/subject/1980737/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:69 |
| [《玉子市场》](<http://movie.douban.com/subject/20514713/>)<br>`http://movie.douban.com/subject/20514713/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:14<br>docs/notes/525677843.md:98<br>docs/rooms/2793793.md:132 |
| [《CHECKERS in TANTAN たぬき》](<http://movie.douban.com/subject/2222954/>)<br>`http://movie.douban.com/subject/2222954/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/rooms/2793793.md:136 |
| [《らき☆すた》](<http://movie.douban.com/subject/2224505/>)<br>`http://movie.douban.com/subject/2224505/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:86 |
| [《CLANNAD》](<http://movie.douban.com/subject/2277181/>)<br>`http://movie.douban.com/subject/2277181/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:72 |
| [《佐杜洛夫斯基的沙丘》](<http://movie.douban.com/subject/24312655/>)<br>`http://movie.douban.com/subject/24312655/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/410095370.md:11 |
| [《玉子爱情故事》](<http://movie.douban.com/subject/25796222/>)<br>`http://movie.douban.com/subject/25796222/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:14<br>docs/notes/525677843.md:99<br>docs/rooms/2793793.md:132 |
| [《甘城ブリリアントパーク》](<http://movie.douban.com/subject/25812280/>)<br>`http://movie.douban.com/subject/25812280/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:88 |
| [《劇場版 境界の彼方 -I&#x27;LL BE HERE- 過去編](<http://movie.douban.com/subject/25918693/>)<br>`http://movie.douban.com/subject/25918693/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:93 |
| [《吹响悠风号》](<http://movie.douban.com/subject/26169716/>)<br>`http://movie.douban.com/subject/26169716/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/485196288.md:16<br>docs/notes/525677843.md:77 |
| [未来編》](<http://movie.douban.com/subject/26273481/>)<br>`http://movie.douban.com/subject/26273481/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:93 |
| [《映画 ハイ☆スピード！-Free! Starting Days-》](<http://movie.douban.com/subject/26350389/>)<br>`http://movie.douban.com/subject/26350389/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:89 |
| [《無彩限のファントムワールド》](<http://movie.douban.com/subject/26591951/>)<br>`http://movie.douban.com/subject/26591951/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:78 |
| [《CLANNAD～AFTER STORY～》](<http://movie.douban.com/subject/3230813/>)<br>`http://movie.douban.com/subject/3230813/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:73 |
| [《けいおん！》](<http://movie.douban.com/subject/3681349/>)<br>`http://movie.douban.com/subject/3681349/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:96 |
| [《赫伯和多乐茜》](<http://movie.douban.com/subject/3744753/>)<br>`http://movie.douban.com/subject/3744753/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/rooms/2793793.md:136 |
| [《涼宮ハルヒの消失》](<http://movie.douban.com/subject/4074292/>)<br>`http://movie.douban.com/subject/4074292/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:74 |
| [《けいおん！！》](<http://movie.douban.com/subject/4223466/>)<br>`http://movie.douban.com/subject/4223466/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:96 |
| [《日常》](<http://movie.douban.com/subject/4848701/>)<br>`http://movie.douban.com/subject/4848701/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:75 |
| [《映画 けいおん！》](<http://movie.douban.com/subject/5403927/>)<br>`http://movie.douban.com/subject/5403927/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/525677843.md:97 |
| [《轻音！》系列](<http://movie.douban.com/subject_search?search_text=%E8%BD%BB%E9%9F%B3%E5%B0%91%E5%A5%B3&cat=1002>)<br>`http://movie.douban.com/subject_search?search_text=%E8%BD%BB%E9%9F%B3%E5%B0%91%E5%A5%B3&cat=1002` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:14<br>docs/rooms/2793793.md:132 |
| [《赫伯和多乐茜》](<http://movie.douban.com/trailer/131206/>)<br>`http://movie.douban.com/trailer/131206/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/541065079.md:19 |
| [Pao](<https://movie.douban.com/photos/photo/2198139096/>)<br>`https://movie.douban.com/photos/photo/2198139096/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/578163214.md:19<br>docs/notes/604396376.md:20 |
| [《乒乓》](<https://movie.douban.com/subject/25813424/>)<br>`https://movie.douban.com/subject/25813424/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/575910736.md:32 |
| [《Sing Street》](<https://movie.douban.com/subject/25855071/>)<br>`https://movie.douban.com/subject/25855071/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:18<br>docs/notes/617677191.md:14<br>docs/rooms/2793793.md:136 |
| [《问题餐厅》](<https://movie.douban.com/subject/26266666/>)<br>`https://movie.douban.com/subject/26266666/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/about.md:20<br>docs/notes/569110361.md:33<br>docs/notes/583976644.md:23<br>docs/notes/624442255.md:20<br>docs/rooms/2793793.md:138 |

### music.163.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [“寻觅到爱的地方”](<http://music.163.com/>)<br>`http://music.163.com/` | 音乐平台 / 可点击 | docs/notes/501830142.md:110<br>docs/notes/536415117.md:17<br>docs/notes/581837681.md:86<br>docs/notes/582498318.md:58 |

### music.baidu.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [例](<http://music.baidu.com/song/s/030710ecfdb0854ce4b65>)<br>`http://music.baidu.com/song/s/030710ecfdb0854ce4b65` | 音乐平台 / 可点击 | docs/notes/496259160.md:36 |

### music.douban.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [原声集](<http://music.douban.com/subject/25906747/>)<br>`http://music.douban.com/subject/25906747/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/410095370.md:20 |
| [Compilation CD](<http://music.douban.com/subject/25959783/>)<br>`http://music.douban.com/subject/25959783/` | 豆瓣作品 / 人物 / 搜索 / 可点击 | docs/notes/410095370.md:20 |

### my.tv.sohu.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://my.tv.sohu.com/us/63319385/60600665.shtml](<http://my.tv.sohu.com/us/63319385/60600665.shtml>)<br>`http://my.tv.sohu.com/us/63319385/60600665.shtml` | 视频平台 / 纯文本 | docs/broadcast/page/81.md:32 |

### natalie.mu

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [映画「聲の形」大今良時が入野自由の声を聞き「将也を主人公にしてくれた」 http://natalie.mu/comic/news/196038 （左から）山田尚子監督、入野自由、早見沙織、大今良時。](<http://natalie.mu/comic/news/196038>)<br>`http://natalie.mu/comic/news/196038` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:150 |
| [完成披露舞台挨拶 http://natalie.mu/comic/news/199347](<http://natalie.mu/comic/news/199347>)<br>`http://natalie.mu/comic/news/199347` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:125 |
| [http://natalie.mu/comic/news/202294](<http://natalie.mu/comic/news/202294>)<br>`http://natalie.mu/comic/news/202294` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:53<br>docs/albums/190597061.md:54 |
| [Comic Natalie](<http://natalie.mu/comic/pp/koenokatachi>)<br>`http://natalie.mu/comic/pp/koenokatachi` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/581837681.md:13 |
| [完成披露上映会 http://natalie.mu/eiga/news/199355](<http://natalie.mu/eiga/news/199355>)<br>`http://natalie.mu/eiga/news/199355` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:123<br>docs/albums/190597061.md:124 |

### nazism.cocolog-nifty.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [たまこまーけっと各話感想](<http://nazism.cocolog-nifty.com/blog/2013/01/post-f272.html>)<br>`http://nazism.cocolog-nifty.com/blog/2013/01/post-f272.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/274238773.md:13<br>docs/rooms/2794121.md:22 |

### news.mynavi.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [mynavi news](<http://news.mynavi.jp/articles/2016/09/21/koe/>)<br>`http://news.mynavi.jp/articles/2016/09/21/koe/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/624442255.md:12 |

### news.qq.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [第九大行星](<http://news.qq.com/a/20160122/007534.htm>)<br>`http://news.qq.com/a/20160122/007534.htm` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/536415117.md:41 |

### news.walkerplus.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://news.walkerplus.com/article/87023/](<http://news.walkerplus.com/article/87023/>)<br>`http://news.walkerplus.com/article/87023/` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:83<br>docs/albums/190597061.md:84 |

### nuruwota.blog4.fc2.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [「けいおん」の山田尚子監督のダンサー三部作を君は見たか](<http://nuruwota.blog4.fc2.com/blog-entry-1443.html>)<br>`http://nuruwota.blog4.fc2.com/blog-entry-1443.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794117.md:54 |
| [http://nuruwota.blog4.fc2.com/blog-entry-3004.html](<http://nuruwota.blog4.fc2.com/blog-entry-3004.html>)<br>`http://nuruwota.blog4.fc2.com/blog-entry-3004.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/433476997.md:39 |

### p.twipple.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://p.twipple.jp/5afqZ 「星とピエロ」のお店「喫茶華波／BAR華波様楽」さんの最新の交流ノートの1ページ目です♪ #たまこまーけっと #聖地巡礼 #出町桝形商店街 #華波](<http://p.twipple.jp/5afqZ>)<br>`http://p.twipple.jp/5afqZ` | 图片 / 全景资料链接 / 纯文本 | docs/albums/13433748.md:188 |
| [http://p.twipple.jp/OD08P](<http://p.twipple.jp/OD08P>)<br>`http://p.twipple.jp/OD08P` | 图片 / 全景资料链接 / 纯文本 | docs/albums/13433748.md:85 |

### priority1.blog51.fc2.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [TV第二期感想](<http://priority1.blog51.fc2.com/blog-category-3.html>)<br>`http://priority1.blog51.fc2.com/blog-category-3.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:26 |
| [【映画感想・読解・考察】 過去の関連記事のインデックス](<http://priority1.blog51.fc2.com/blog-entry-1498.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1498.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:29 |
| [【イベントレポ】 グラスゴー＆ロンドン遠征レポ （１）準備編](<http://priority1.blog51.fc2.com/blog-entry-1600.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1600.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:51 |
| [【イベントレポ】 グラスゴー＆ロンドン遠征レポ （２）初日](<http://priority1.blog51.fc2.com/blog-entry-1601.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1601.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:52 |
| [【イベントレポ】 グラスゴー＆ロンドン遠征レポ （３）２日目](<http://priority1.blog51.fc2.com/blog-entry-1602.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1602.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:53 |
| [【イベントレポ】グラスゴー＆ロンドン遠征レポ（４）３日目](<http://priority1.blog51.fc2.com/blog-entry-1603.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1603.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/577308827.md:12<br>docs/rooms/2794136.md:54 |
| [【イベントレポ】 グラスゴー＆ロンドン遠征レポ （５）最終日](<http://priority1.blog51.fc2.com/blog-entry-1604.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1604.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:55 |
| [【学園祭】鶴岡陽太音響監督講演会レポート！](<http://priority1.blog51.fc2.com/blog-entry-1620.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1620.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:56 |
| [第17回アニメーション神戸授賞式簡易レポ＆お花企画ギリギリ仔細ｗ](<http://priority1.blog51.fc2.com/blog-entry-1641.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1641.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:58 |
| [【映画考察】映画「さらば青春の光」を通してのＥＤ解釈](<http://priority1.blog51.fc2.com/blog-entry-1674.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1674.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/429716807.md:11<br>docs/rooms/2794136.md:31 |
| [【映画考察】映画「エコール」を通してのＥＤ解釈](<http://priority1.blog51.fc2.com/blog-entry-1677.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1677.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/521041733.md:13<br>docs/rooms/2794136.md:32 |
| [自己当时的感想](<http://priority1.blog51.fc2.com/blog-entry-1715.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1715.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/332912954.md:20 |
| [たまこまーけっと もちもちトーク＆ライブイベント 簡易レポ!!](<http://priority1.blog51.fc2.com/blog-entry-1729.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1729.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:62 |
| [山田尚子監督からキャスト５人へのお手紙書き起こし](<http://priority1.blog51.fc2.com/blog-entry-1740.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1740.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:59 |
| [过去的日志](<http://priority1.blog51.fc2.com/blog-entry-1744.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1744.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/338329832.md:106<br>docs/rooms/2794117.md:56 |
| [映画けいおん！時系列順作品解説（2013ver.）](<http://priority1.blog51.fc2.com/blog-entry-1758.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1758.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/319279183.md:13<br>docs/rooms/2794136.md:30 |
| [【映画読解】 空の向こう、星の彼方](<http://priority1.blog51.fc2.com/blog-entry-1759.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1759.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/326223685.md:10<br>docs/rooms/2794136.md:33 |
| [【考察】 続・空の向こう、星の彼方](<http://priority1.blog51.fc2.com/blog-entry-1760.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1760.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/326223685.md:11<br>docs/rooms/2794136.md:34 |
| [【考察】「けいおん！」のその先を描く物語としての「たまこラブストーリー」](<http://priority1.blog51.fc2.com/blog-entry-1766.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1766.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/332912954.md:10<br>docs/rooms/2794121.md:26 |
| [之前所写](<http://priority1.blog51.fc2.com/blog-entry-1768.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1768.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/338329832.md:110 |
| [【たまこラ】 PV第一弾解禁！ここまでの作品考察、推察のまとめ](<http://priority1.blog51.fc2.com/blog-entry-1769.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1769.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/338329832.md:11<br>docs/rooms/2794121.md:27 |
| [【4.19】「たまこまーけっと」おさらい上映会＆スタッフトークショーレポ【京都文博】](<http://priority1.blog51.fc2.com/blog-entry-1772.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1772.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/347460778.md:11<br>docs/rooms/2794121.md:66 |
| [【たまこラブストーリー】 読解メモ 01](<http://priority1.blog51.fc2.com/blog-entry-1776.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1776.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/433188862.md:11<br>docs/rooms/2794121.md:31 |
| [【たまこラブストーリー】 初見感想 『まずは総論みたいなのｗ』 【感想】](<http://priority1.blog51.fc2.com/blog-entry-1777.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1777.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/433039361.md:12<br>docs/rooms/2794121.md:30 |
| [【たまこラブストーリー】 読解メモ 01 追補](<http://priority1.blog51.fc2.com/blog-entry-1778.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1778.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/433207087.md:11<br>docs/rooms/2794121.md:32 |
| [http://priority1.blog51.fc2.com/blog-entry-1779.html](<http://priority1.blog51.fc2.com/blog-entry-1779.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1779.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/433476997.md:37<br>docs/notes/433804876.md:10<br>docs/rooms/2794121.md:33 |
| [【たまこラブストーリー】読解メモ 02追補](<http://priority1.blog51.fc2.com/blog-entry-1780.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1780.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:34 |
| [【たまこラブストーリー】読解メモ 03](<http://priority1.blog51.fc2.com/blog-entry-1781.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1781.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:35 |
| [03 追補](<http://priority1.blog51.fc2.com/blog-entry-1782.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1782.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/433207087.md:11<br>docs/notes/433237635.md:10<br>docs/rooms/2794121.md:36 |
| [【たまこラブストーリー】読解メモ 04追補](<http://priority1.blog51.fc2.com/blog-entry-1784.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1784.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:37 |
| [【たまこラブストーリー】 読解メモ 05](<http://priority1.blog51.fc2.com/blog-entry-1785.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1785.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/433821101.md:11<br>docs/rooms/2794121.md:38 |
| [「たまこラブストーリー」総論：「橋」の物語としてのたまラブ](<http://priority1.blog51.fc2.com/blog-entry-1786.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1786.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/434075254.md:11<br>docs/rooms/2794121.md:39 |
| [【たまこラブストーリー】 読解メモ 06](<http://priority1.blog51.fc2.com/blog-entry-1787.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1787.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/464638733.md:11<br>docs/rooms/2794121.md:40 |
| [【たまこラブストーリー】読解メモ 07](<http://priority1.blog51.fc2.com/blog-entry-1788.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1788.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:41 |
| [【たまこラブストーリー】 読解メモ 08](<http://priority1.blog51.fc2.com/blog-entry-1789.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1789.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/434258171.md:11<br>docs/rooms/2794121.md:42 |
| [【たまこラブストーリー】 読解メモ 09](<http://priority1.blog51.fc2.com/blog-entry-1790.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1790.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/434498947.md:11<br>docs/rooms/2794121.md:43 |
| [【山田尚子作品考】「映画けいおん！」「たまこラブストーリー」そして…](<http://priority1.blog51.fc2.com/blog-entry-1791.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1791.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:44 |
| [【たまこラブストーリー】感想その２ 『本作の作劇はいかにして携帯を克服したかｗ』](<http://priority1.blog51.fc2.com/blog-entry-1795.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1795.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:45 |
| [【たまこラブストーリー】 読解メモ 10](<http://priority1.blog51.fc2.com/blog-entry-1796.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1796.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/434874102.md:11<br>docs/rooms/2794121.md:46 |
| [「Free!ES」第12話！絵コンテ・演出／山田尚子を堪能する!! その２](<http://priority1.blog51.fc2.com/blog-entry-1807.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1807.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/425866593.md:10<br>docs/rooms/2794117.md:58 |
| [「たまラブ」のフィルム演出の意図について～「映画けいおん！」の写真を踏まえて～](<http://priority1.blog51.fc2.com/blog-entry-1841.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1841.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:47 |
| [【たまラブ】 「タンポポ」を補助線にした読解について…とその他(笑)](<http://priority1.blog51.fc2.com/blog-entry-1844.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-1844.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:48 |
| [作品への簡単な総括と、最終回へのいくつかの私見](<http://priority1.blog51.fc2.com/blog-entry-444.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-444.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:27 |
| [＜構造解析＞将来・進路決定の物語](<http://priority1.blog51.fc2.com/blog-entry-450.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-450.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/519006182.md:11<br>docs/rooms/2794136.md:28 |
| [アニメーション神戸授賞式に山田監督ご登壇！](<http://priority1.blog51.fc2.com/blog-entry-560.html>)<br>`http://priority1.blog51.fc2.com/blog-entry-560.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:50 |

### qrion.net

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [Qrion](<http://qrion.net/>)<br>`http://qrion.net/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/about.md:26<br>docs/notes/525677843.md:358<br>docs/rooms/2793793.md:144 |

### rdm.ne.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [マニュエラだから作れた『たまこまーけっと』の音楽](<http://rdm.ne.jp/sound/column/tamacomanu>)<br>`http://rdm.ne.jp/sound/column/tamacomanu` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:59 |

### realsound.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [Real Sound](<http://realsound.jp/movie/2016/09/post-2807.html>)<br>`http://realsound.jp/movie/2016/09/post-2807.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/583425563.md:12 |
| [Real Sound](<http://realsound.jp/movie/2016/09/post-2808.html>)<br>`http://realsound.jp/movie/2016/09/post-2808.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/586870147.md:12 |
| [山田尚子監督＆早見沙織、映画『聲の形』舞台挨拶で日本アカデミー賞受賞を語る http://realsound.jp/movie/2017/02/post-3949.html](<http://realsound.jp/movie/2017/02/post-3949.html>)<br>`http://realsound.jp/movie/2017/02/post-3949.html` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:14 |

### rubeusu-trend.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [紫陽花](<http://rubeusu-trend.com/4605/>)<br>`http://rubeusu-trend.com/4605/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/501830142.md:15 |

### sensesapporo.bandcamp.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [《sink》](<http://sensesapporo.bandcamp.com/album/sink>)<br>`http://sensesapporo.bandcamp.com/album/sink` | 音乐平台 / 可点击 | docs/notes/525677843.md:358 |

### shimirubon.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [放課後という生（ライブ）ティータイムのための世界](<https://shimirubon.jp/series/3>)<br>`https://shimirubon.jp/series/3` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:39 |

### shine.web.wox.cc

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [山田尚子とソフィア・コッポラ](<http://shine.web.wox.cc/blog/entry14.html>)<br>`http://shine.web.wox.cc/blog/entry14.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794117.md:59 |

### t.cn

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [山田：我很喜欢松冈出演的电视剧《问题餐厅》，每周都会收看，从第一集开始就对松冈很在意。《聲之形》最先想到的就是想请松冈配音。发邀请时完全是抱着试试看的心态，她愿意出演让我感到很幸运。 http://t.cn/RcfasXQ](<http://t.cn/RcfasXQ>)<br>`http://t.cn/RcfasXQ` | 短链接，待解析 / 纯文本 | docs/albums/190597061.md:89<br>docs/albums/190597061.md:90<br>docs/albums/190597061.md:91 |

### tamakolovestory.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://tamakolovestory.com/ main visual 2](<http://tamakolovestory.com/>)<br>`http://tamakolovestory.com/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/albums/13432051.md:23<br>docs/albums/13432051.md:24<br>docs/rooms/2794121.md:18 |
| [Story](<http://tamakolovestory.com/images/introduction/story.png>)<br>`http://tamakolovestory.com/images/introduction/story.png` | 图片 / 全景资料链接 / 可点击 | docs/notes/325869921.md:25 |
| [Introduction](<http://tamakolovestory.com/introduction/>)<br>`http://tamakolovestory.com/introduction/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/325869921.md:12 |
| [京都动画作品上映会](<http://tamakolovestory.com/news/?id=54>)<br>`http://tamakolovestory.com/news/?id=54` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/578163214.md:17 |
| [http://tamakolovestory.com/special/ ——一开始想在这部电影中描写什么？ 我想把玉子这个角色当作一名女孩子来描写。想在电影中深入玉子的内心，描绘在飘溢青春芳香的美好空间中步入17岁的玉子。 ——为描写玉子的内心而选了这个题...](<http://tamakolovestory.com/special/>)<br>`http://tamakolovestory.com/special/` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/broadcast/page/66.md:30 |
| [http://tamakolovestory.com/special/comment/](<http://tamakolovestory.com/special/comment/>)<br>`http://tamakolovestory.com/special/comment/` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13432051.md:23<br>docs/albums/13432051.md:24<br>docs/albums/13432051.md:25<br>docs/albums/13432051.md:26<br>docs/albums/13432051.md:27<br>docs/albums/13432051.md:28 |
| [http://tamakolovestory.com/special/interview/ 前篇 ——请说一下各主要角色的看点。 ・玉子 我想以不损害迄今为止的玉子为前提，去描写不只是对周围的人们，对自己也能珍惜重视的玉子。此前不曾知晓恋爱的玉子面前增添一个新世界...](<http://tamakolovestory.com/special/interview/>)<br>`http://tamakolovestory.com/special/interview/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/broadcast/page/64.md:16<br>docs/notes/348784334.md:11<br>docs/notes/350255703.md:11 |
| [『たまこラブストーリー』本予告 - YouTube『たまこラブストーリー』の公式サイトのインタビューで山田尚子監督はこう語っている。http://tamakolovestory.com/special/interview/今回は「映画」ということをだいぶ意識...](<http://tamakolovestory.com/special/interview/今回は「映画」ということをだいぶ意識>)<br>`http://tamakolovestory.com/special/interview/今回は「映画」ということをだいぶ意識` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/broadcast/page/67.md:30 |

### tamakomarket.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [官网](<http://tamakomarket.com/>)<br>`http://tamakomarket.com/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:17 |

### tehepero-tini.hatenablog.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [【たまこラブストーリー『星とピエロ』に登場する実在レコードの紹介】〜邦夫さんの言葉にしないメッセージ〜](<http://tehepero-tini.hatenablog.jp/entry/2014/12/07/220120>)<br>`http://tehepero-tini.hatenablog.jp/entry/2014/12/07/220120` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:55 |
| [【山田尚子監督からのデラちゃん直筆年賀状】](<http://tehepero-tini.hatenablog.jp/entry/2015/01/01/232746>)<br>`http://tehepero-tini.hatenablog.jp/entry/2015/01/01/232746` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794121.md:56 |

### theta360.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [360°全景照](<https://theta360.com/s/myykG2lvld68JWnyipGqO8NqG>)<br>`https://theta360.com/s/myykG2lvld68JWnyipGqO8NqG` | 图片 / 全景资料链接 / 可点击 | docs/notes/581837681.md:153 |

### tokyo-anime-news.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [「見てくれた方々の勇気の一つに」 映画『たまこラブストーリー』初日舞台挨拶レポート http://tokyo-anime-news.jp/?p=23500](<http://tokyo-anime-news.jp/?p=23500>)<br>`http://tokyo-anime-news.jp/?p=23500` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:148<br>docs/albums/13433748.md:149 |

### trackback.blogsys.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://trackback.blogsys.jp/livedoor/geek/51456007](<http://trackback.blogsys.jp/livedoor/geek/51456007>)<br>`http://trackback.blogsys.jp/livedoor/geek/51456007` | 回链服务端点 / 纯文本 | docs/broadcast/page/48.md:14 |

### twitter.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [桝形商店街に見に行ったら洲崎さんの記入ありました。 https://twitter.com/Pan0831/status/749802976244408320](<https://twitter.com/Pan0831/status/749802976244408320>)<br>`https://twitter.com/Pan0831/status/749802976244408320` | 社交帖子 / 个人主页 / 纯文本 | docs/albums/13431474.md:34 |
| [②](<https://twitter.com/ShindyMonkey/status/779674792848793600>)<br>`https://twitter.com/ShindyMonkey/status/779674792848793600` | 社交帖子 / 个人主页 / 可点击 | docs/notes/584217092.md:12 |
| [@SuperMnemonic](<https://twitter.com/SuperMnemonic>)<br>`https://twitter.com/SuperMnemonic` | 社交帖子 / 个人主页 / 可点击 | docs/notes/347460778.md:11 |
| [天竺](<https://twitter.com/Tenjiq/status/665476046293086209>)<br>`https://twitter.com/Tenjiq/status/665476046293086209` | 社交帖子 / 个人主页 / 可点击 | docs/notes/525677843.md:358 |
| [介绍](<https://twitter.com/Tenjiq/status/665479544049020928>)<br>`https://twitter.com/Tenjiq/status/665479544049020928` | 社交帖子 / 个人主页 / 可点击 | docs/notes/525677843.md:358 |
| [AnimeJapan2015「響け！ユーフォニアム」 https://twitter.com/anime_eupho/status/579253985208479744](<https://twitter.com/anime_eupho/status/579253985208479744>)<br>`https://twitter.com/anime_eupho/status/579253985208479744` | 社交帖子 / 个人主页 / 纯文本 | docs/albums/13431950.md:118<br>docs/albums/13431950.md:119 |
| [5月15日は高坂麗奈の誕生日なのです！！おめでとう麗奈！ということで、石原監督が現場で即興で描いてくださいました！！久美子の後ろ姿ww https://twitter.com/anime_eupho/status/598867212028379137](<https://twitter.com/anime_eupho/status/598867212028379137>)<br>`https://twitter.com/anime_eupho/status/598867212028379137` | 社交帖子 / 个人主页 / 纯文本 | docs/albums/13431950.md:97 |
| [https://twitter.com/cmykpaste/status/887596020468637698](<https://twitter.com/cmykpaste/status/887596020468637698>)<br>`https://twitter.com/cmykpaste/status/887596020468637698` | 社交帖子 / 个人主页 / 可点击 | docs/albums/190597061.md:11<br>docs/notes/621342820.md:76 |
| [新宿ピカデリー前のアニメイトで山田尚子監督（？）らしき書き込みを発見。 https://twitter.com/goriko7188/status/472317677810102272](<https://twitter.com/goriko7188/status/472317677810102272>)<br>`https://twitter.com/goriko7188/status/472317677810102272` | 社交帖子 / 个人主页 / 纯文本 | docs/albums/13433748.md:64 |
| [https://twitter.com/goriko7188/status/633593141539397633 山田的签名，亮点是悠风君与德拉](<https://twitter.com/goriko7188/status/633593141539397633>)<br>`https://twitter.com/goriko7188/status/633593141539397633` | 社交帖子 / 个人主页 / 纯文本 | docs/albums/13431950.md:69 |
| [推友](<https://twitter.com/honekawap/status/660315448056025088>)<br>`https://twitter.com/honekawap/status/660315448056025088` | 社交帖子 / 个人主页 / 可点击 | docs/notes/525677843.md:57 |
| [https://twitter.com/kanekosandes/status/519712759752060929](<https://twitter.com/kanekosandes/status/519712759752060929>)<br>`https://twitter.com/kanekosandes/status/519712759752060929` | 社交帖子 / 个人主页 / 纯文本 | docs/albums/13433748.md:49 |
| [【P&#x27;s Live! 02 ～LOVE＆P&#x27;s～ 2015年3月8日】 https://twitter.com/kanekosanndesu/status/574930949995020288](<https://twitter.com/kanekosanndesu/status/574930949995020288>)<br>`https://twitter.com/kanekosanndesu/status/574930949995020288` | 社交帖子 / 个人主页 / 纯文本 | docs/albums/13433748.md:34<br>docs/albums/13433748.md:35 |
| [@los_endos_](<https://twitter.com/los_endos_>)<br>`https://twitter.com/los_endos_` | 社交帖子 / 个人主页 / 可点击 | docs/notes/347460778.md:10 |
| [https://twitter.com/los_endos_/status/464770324601401344](<https://twitter.com/los_endos_/status/464770324601401344>)<br>`https://twitter.com/los_endos_/status/464770324601401344` | 社交帖子 / 个人主页 / 可点击 | docs/notes/433476997.md:38 |
| [森胁清隆](<https://twitter.com/mk_pai>)<br>`https://twitter.com/mk_pai` | 社交帖子 / 个人主页 / 可点击 | docs/notes/347460778.md:31 |
| [②](<https://twitter.com/omg0monica/status/780938399880400896>)<br>`https://twitter.com/omg0monica/status/780938399880400896` | 社交帖子 / 个人主页 / 可点击 | docs/notes/585518914.md:12 |
| [中嶋元美](<https://twitter.com/pinklovemoto>)<br>`https://twitter.com/pinklovemoto` | 社交帖子 / 个人主页 / 可点击 | docs/notes/584217092.md:27 |
| [①](<https://twitter.com/tobyr2ta9/status/781155152057159681>)<br>`https://twitter.com/tobyr2ta9/status/781155152057159681` | 社交帖子 / 个人主页 / 可点击 | docs/notes/585518914.md:12 |
| [片冈知子](<https://twitter.com/tomo_kat/status/456601037705457664>)<br>`https://twitter.com/tomo_kat/status/456601037705457664` | 社交帖子 / 个人主页 / 可点击 | docs/notes/347460778.md:17 |
| [山口优](<https://twitter.com/yama_g/status/456528754676752384>)<br>`https://twitter.com/yama_g/status/456528754676752384` | 社交帖子 / 个人主页 / 可点击 | docs/notes/347460778.md:17 |
| [⑥](<https://twitter.com/yu_hqA/status/777517387184615426>)<br>`https://twitter.com/yu_hqA/status/777517387184615426` | 社交帖子 / 个人主页 / 可点击 | docs/notes/583976644.md:12 |

### v.youku.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://v.youku.com/v_show/id_XMTUyNzc5OTkwNA==.html?from=s1.8-1-1.2](<http://v.youku.com/v_show/id_XMTUyNzc5OTkwNA==.html?from=s1.8-1-1.2>)<br>`http://v.youku.com/v_show/id_XMTUyNzc5OTkwNA==.html?from=s1.8-1-1.2` | 视频平台 / 纯文本 | docs/broadcast/page/25.md:14 |
| [http://v.youku.com/v_show/id_XMTYzNTkwMDU0OA==.html](<http://v.youku.com/v_show/id_XMTYzNTkwMDU0OA==.html>)<br>`http://v.youku.com/v_show/id_XMTYzNTkwMDU0OA==.html` | 视频平台 / 纯文本 | docs/broadcast/page/22.md:14 |
| [http://v.youku.com/v_show/id_XMTc0MTExODA1Ng==.html](<http://v.youku.com/v_show/id_XMTc0MTExODA1Ng==.html>)<br>`http://v.youku.com/v_show/id_XMTc0MTExODA1Ng==.html` | 视频平台 / 纯文本 | docs/broadcast/page/10.md:24 |
| [《聲之形》ZIP!特集（20161027）](<http://v.youku.com/v_show/id_XMTc3NjcwOTA0MA==.html>)<br>`http://v.youku.com/v_show/id_XMTc3NjcwOTA0MA==.html` | 视频平台 / 可点击 | docs/albums/index.md:24<br>docs/broadcast/page/8.md:14<br>docs/rooms/3598399.md:79 |
| [http://v.youku.com/v_show/id_XMTcxMDk1MDY5Ng==.html?beta&amp;](<http://v.youku.com/v_show/id_XMTcxMDk1MDY5Ng==.html?beta&>)<br>`http://v.youku.com/v_show/id_XMTcxMDk1MDY5Ng==.html?beta&` | 视频平台 / 纯文本 | docs/broadcast/page/17.md:24 |
| [http://v.youku.com/v_show/id_XMTcxOTA0MTk5Ng==.html](<http://v.youku.com/v_show/id_XMTcxOTA0MTk5Ng==.html>)<br>`http://v.youku.com/v_show/id_XMTcxOTA0MTk5Ng==.html` | 视频平台 / 纯文本 | docs/broadcast/page/16.md:22 |
| [http://v.youku.com/v_show/id_XMTcxOTA0MjU4MA==.html](<http://v.youku.com/v_show/id_XMTcxOTA0MjU4MA==.html>)<br>`http://v.youku.com/v_show/id_XMTcxOTA0MjU4MA==.html` | 视频平台 / 纯文本 | docs/broadcast/page/16.md:20 |
| [http://v.youku.com/v_show/id_XMTcyMDM1Mzc1Mg==.html](<http://v.youku.com/v_show/id_XMTcyMDM1Mzc1Mg==.html>)<br>`http://v.youku.com/v_show/id_XMTcyMDM1Mzc1Mg==.html` | 视频平台 / 纯文本 | docs/broadcast/page/16.md:16 |
| [《吹响悠风号2》PV第2弹](<http://v.youku.com/v_show/id_XMTcyMDYyODA3Ng==.html>)<br>`http://v.youku.com/v_show/id_XMTcyMDYyODA3Ng==.html` | 视频平台 / 可点击 | docs/albums/index.md:32<br>docs/broadcast/page/15.md:32<br>docs/rooms/2794117.md:107 |
| [http://v.youku.com/v_show/id_XMTcyMzg1NzU2OA==.html](<http://v.youku.com/v_show/id_XMTcyMzg1NzU2OA==.html>)<br>`http://v.youku.com/v_show/id_XMTcyMzg1NzU2OA==.html` | 视频平台 / 纯文本 | docs/broadcast/page/15.md:16 |
| [http://v.youku.com/v_show/id_XMTcyMzkzMTc4OA==.html](<http://v.youku.com/v_show/id_XMTcyMzkzMTc4OA==.html>)<br>`http://v.youku.com/v_show/id_XMTcyMzkzMTc4OA==.html` | 视频平台 / 纯文本 | docs/broadcast/page/14.md:32 |
| [http://v.youku.com/v_show/id_XMTcyNjgyNDM0OA==.html](<http://v.youku.com/v_show/id_XMTcyNjgyNDM0OA==.html>)<br>`http://v.youku.com/v_show/id_XMTcyNjgyNDM0OA==.html` | 视频平台 / 纯文本 | docs/broadcast/page/14.md:18 |
| [http://v.youku.com/v_show/id_XMTcyNzg1NzMxMg==.html](<http://v.youku.com/v_show/id_XMTcyNzg1NzMxMg==.html>)<br>`http://v.youku.com/v_show/id_XMTcyNzg1NzMxMg==.html` | 视频平台 / 纯文本 | docs/broadcast/page/13.md:24 |
| [http://v.youku.com/v_show/id_XMTczMTI0MTQ2MA==.html](<http://v.youku.com/v_show/id_XMTczMTI0MTQ2MA==.html>)<br>`http://v.youku.com/v_show/id_XMTczMTI0MTQ2MA==.html` | 视频平台 / 纯文本 | docs/broadcast/page/12.md:16 |
| [http://v.youku.com/v_show/id_XMTczMTYwNDYxMg==.html](<http://v.youku.com/v_show/id_XMTczMTYwNDYxMg==.html>)<br>`http://v.youku.com/v_show/id_XMTczMTYwNDYxMg==.html` | 视频平台 / 纯文本 | docs/broadcast/page/11.md:30 |
| [http://v.youku.com/v_show/id_XMTczNDA4MDI4MA==.html](<http://v.youku.com/v_show/id_XMTczNDA4MDI4MA==.html>)<br>`http://v.youku.com/v_show/id_XMTczNDA4MDI4MA==.html` | 视频平台 / 纯文本 | docs/broadcast/page/11.md:24 |
| [http://v.youku.com/v_show/id_XMTczOTgxMDc0OA==.html](<http://v.youku.com/v_show/id_XMTczOTgxMDc0OA==.html>)<br>`http://v.youku.com/v_show/id_XMTczOTgxMDc0OA==.html` | 视频平台 / 纯文本 | docs/broadcast/page/10.md:30 |
| [瑞穗金融集团 CM 电影《聲之形》篇 30秒](<http://v.youku.com/v_show/id_XMTgwODE3Mjg5Ng==.html>)<br>`http://v.youku.com/v_show/id_XMTgwODE3Mjg5Ng==.html` | 视频平台 / 可点击 | docs/albums/index.md:23<br>docs/broadcast/page/7.md:26<br>docs/rooms/3598399.md:77 |
| [《怪兽的歌谣》](<http://v.youku.com/v_show/id_XMjc3NzY3OTMwNA==.html?spm=a2h3j.8428770.3416059.1>)<br>`http://v.youku.com/v_show/id_XMjc3NzY3OTMwNA==.html?spm=a2h3j.8428770.3416059.1` | 视频平台 / 可点击 | docs/notes/621342820.md:16 |
| [http://v.youku.com/v_show/id_XNTQ3OTE0MjE2.html](<http://v.youku.com/v_show/id_XNTQ3OTE0MjE2.html>)<br>`http://v.youku.com/v_show/id_XNTQ3OTE0MjE2.html` | 视频平台 / 纯文本 | docs/broadcast/page/89.md:14 |
| [http://v.youku.com/v_show/id_XNTU5ODg5MDU2.html](<http://v.youku.com/v_show/id_XNTU5ODg5MDU2.html>)<br>`http://v.youku.com/v_show/id_XNTU5ODg5MDU2.html` | 视频平台 / 可点击 | docs/broadcast/page/87.md:28<br>docs/notes/291753270.md:11 |
| [http://v.youku.com/v_show/id_XNTU5ODkwNDcy.html](<http://v.youku.com/v_show/id_XNTU5ODkwNDcy.html>)<br>`http://v.youku.com/v_show/id_XNTU5ODkwNDcy.html` | 视频平台 / 纯文本 | docs/broadcast/page/87.md:26 |
| [http://v.youku.com/v_show/id_XNTU5ODkwOTY0.html](<http://v.youku.com/v_show/id_XNTU5ODkwOTY0.html>)<br>`http://v.youku.com/v_show/id_XNTU5ODkwOTY0.html` | 视频平台 / 纯文本 | docs/broadcast/page/87.md:24 |
| [【けいおん!!】けいおん学講義 第６回～輝く未来へ～](<http://v.youku.com/v_show/id_XNTU5ODkxMTg0.html>)<br>`http://v.youku.com/v_show/id_XNTU5ODkxMTg0.html` | 视频平台 / 可点击 | docs/albums/index.md:31<br>docs/broadcast/page/87.md:22<br>docs/rooms/2794136.md:105 |
| [http://v.youku.com/v_show/id_XNTUwODQ4MjIw.html](<http://v.youku.com/v_show/id_XNTUwODQ4MjIw.html>)<br>`http://v.youku.com/v_show/id_XNTUwODQ4MjIw.html` | 视频平台 / 可点击 | docs/broadcast/page/88.md:22<br>docs/notes/274371246.md:10 |
| [http://v.youku.com/v_show/id_XNTUwODQ4NjIw.html](<http://v.youku.com/v_show/id_XNTUwODQ4NjIw.html>)<br>`http://v.youku.com/v_show/id_XNTUwODQ4NjIw.html` | 视频平台 / 可点击 | docs/broadcast/page/88.md:20<br>docs/notes/274768174.md:10 |
| [ボルヴィックCM『飲む自然』篇](<http://v.youku.com/v_show/id_XNTY4NzUwNjU2.html>)<br>`http://v.youku.com/v_show/id_XNTY4NzUwNjU2.html` | 视频平台 / 可点击 | docs/albums/index.md:33<br>docs/broadcast/page/34.md:18<br>docs/rooms/2794117.md:109 |
| [http://v.youku.com/v_show/id_XNjUwMzYwNjk2.html](<http://v.youku.com/v_show/id_XNjUwMzYwNjk2.html>)<br>`http://v.youku.com/v_show/id_XNjUwMzYwNjk2.html` | 视频平台 / 纯文本 | docs/broadcast/page/83.md:32 |
| [http://v.youku.com/v_show/id_XNjcwNTI5Mzky.html](<http://v.youku.com/v_show/id_XNjcwNTI5Mzky.html>)<br>`http://v.youku.com/v_show/id_XNjcwNTI5Mzky.html` | 视频平台 / 纯文本 | docs/broadcast/page/79.md:22 |
| [【けいおん!!】けいおん学講義 第５回～広がる世界と変わらぬ心](<http://v.youku.com/v_show/id_XNjcwNTM1MjI4.html>)<br>`http://v.youku.com/v_show/id_XNjcwNTM1MjI4.html` | 视频平台 / 可点击 | docs/albums/index.md:30<br>docs/rooms/2794136.md:103 |
| [http://v.youku.com/v_show/id_XNjcwNTMzMTMy.html](<http://v.youku.com/v_show/id_XNjcwNTMzMTMy.html>)<br>`http://v.youku.com/v_show/id_XNjcwNTMzMTMy.html` | 视频平台 / 纯文本 | docs/broadcast/page/79.md:20 |
| [http://v.youku.com/v_show/id_XNjcwNTMzMzI0.html](<http://v.youku.com/v_show/id_XNjcwNTMzMzI0.html>)<br>`http://v.youku.com/v_show/id_XNjcwNTMzMzI0.html` | 视频平台 / 纯文本 | docs/broadcast/page/79.md:18 |
| [http://v.youku.com/v_show/id_XNjg4NjkzMzcy.html](<http://v.youku.com/v_show/id_XNjg4NjkzMzcy.html>)<br>`http://v.youku.com/v_show/id_XNjg4NjkzMzcy.html` | 视频平台 / 纯文本 | docs/broadcast/page/76.md:32 |
| [http://v.youku.com/v_show/id_XNjg4NjkzNTEy.html](<http://v.youku.com/v_show/id_XNjg4NjkzNTEy.html>)<br>`http://v.youku.com/v_show/id_XNjg4NjkzNTEy.html` | 视频平台 / 纯文本 | docs/broadcast/page/76.md:30 |
| [http://v.youku.com/v_show/id_XNjg4NzcyNjE2.html](<http://v.youku.com/v_show/id_XNjg4NzcyNjE2.html>)<br>`http://v.youku.com/v_show/id_XNjg4NzcyNjE2.html` | 视频平台 / 纯文本 | docs/broadcast/page/76.md:24 |
| [http://v.youku.com/v_show/id_XNjkxNzUwMTM2.html](<http://v.youku.com/v_show/id_XNjkxNzUwMTM2.html>)<br>`http://v.youku.com/v_show/id_XNjkxNzUwMTM2.html` | 视频平台 / 纯文本 | docs/broadcast/page/76.md:22 |
| [http://v.youku.com/v_show/id_XNzA0OTE3OTY0.html](<http://v.youku.com/v_show/id_XNzA0OTE3OTY0.html>)<br>`http://v.youku.com/v_show/id_XNzA0OTE3OTY0.html` | 视频平台 / 纯文本 | docs/broadcast/page/68.md:24 |
| [http://v.youku.com/v_show/id_XNzA0OTE4MDI0.html](<http://v.youku.com/v_show/id_XNzA0OTE4MDI0.html>)<br>`http://v.youku.com/v_show/id_XNzA0OTE4MDI0.html` | 视频平台 / 纯文本 | docs/broadcast/page/68.md:22 |
| [http://v.youku.com/v_show/id_XNzA1ODUyNzQw.html](<http://v.youku.com/v_show/id_XNzA1ODUyNzQw.html>)<br>`http://v.youku.com/v_show/id_XNzA1ODUyNzQw.html` | 视频平台 / 纯文本 | docs/broadcast/page/68.md:20 |
| [http://v.youku.com/v_show/id_XNzAxMDc4NDg0.html](<http://v.youku.com/v_show/id_XNzAxMDc4NDg0.html>)<br>`http://v.youku.com/v_show/id_XNzAxMDc4NDg0.html` | 视频平台 / 纯文本 | docs/broadcast/page/73.md:28 |
| [http://v.youku.com/v_show/id_XNzEwMTA2Njc2.html](<http://v.youku.com/v_show/id_XNzEwMTA2Njc2.html>)<br>`http://v.youku.com/v_show/id_XNzEwMTA2Njc2.html` | 视频平台 / 纯文本 | docs/broadcast/page/64.md:20 |
| [http://v.youku.com/v_show/id_XNzEyMDMwNDgw.html](<http://v.youku.com/v_show/id_XNzEyMDMwNDgw.html>)<br>`http://v.youku.com/v_show/id_XNzEyMDMwNDgw.html` | 视频平台 / 纯文本 | docs/broadcast/page/62.md:16 |
| [http://v.youku.com/v_show/id_XNzEyMDQ1MzM2.html](<http://v.youku.com/v_show/id_XNzEyMDQ1MzM2.html>)<br>`http://v.youku.com/v_show/id_XNzEyMDQ1MzM2.html` | 视频平台 / 纯文本 | docs/broadcast/page/62.md:14 |
| [http://v.youku.com/v_show/id_XNzEyMDQ2MDQ4.html](<http://v.youku.com/v_show/id_XNzEyMDQ2MDQ4.html>)<br>`http://v.youku.com/v_show/id_XNzEyMDQ2MDQ4.html` | 视频平台 / 纯文本 | docs/broadcast/page/61.md:32 |
| [http://v.youku.com/v_show/id_XNzM1MTA5NzUy.html](<http://v.youku.com/v_show/id_XNzM1MTA5NzUy.html>)<br>`http://v.youku.com/v_show/id_XNzM1MTA5NzUy.html` | 视频平台 / 纯文本 | docs/broadcast/page/58.md:18 |
| [http://v.youku.com/v_show/id_XNzM4NjUxNDc2.html](<http://v.youku.com/v_show/id_XNzM4NjUxNDc2.html>)<br>`http://v.youku.com/v_show/id_XNzM4NjUxNDc2.html` | 视频平台 / 纯文本 | docs/broadcast/page/57.md:28 |
| [【画像90枚】けいおん！ラッピング電車 HO-KAGO TEA TIME TRAIN](<http://v.youku.com/v_show/id_XNzk4NzI0NTc2.html>)<br>`http://v.youku.com/v_show/id_XNzk4NzI0NTc2.html` | 视频平台 / 可点击 | docs/albums/index.md:29<br>docs/broadcast/page/51.md:30<br>docs/rooms/2794136.md:101 |
| [【たまこラブストーリー】出町桝形商店街“標語”再現メイキング映像](<http://v.youku.com/v_show/id_XODAwMjc5MTEy.html>)<br>`http://v.youku.com/v_show/id_XODAwMjc5MTEy.html` | 视频平台 / 可点击 | docs/albums/index.md:28<br>docs/broadcast/page/51.md:20<br>docs/rooms/2794121.md:133 |
| [TAMAKO MEMORY&#x27;S NOTE PV](<http://v.youku.com/v_show/id_XODQ2NTM5OTQw.html>)<br>`http://v.youku.com/v_show/id_XODQ2NTM5OTQw.html` | 视频平台 / 可点击 | docs/albums/index.md:27<br>docs/broadcast/page/41.md:28<br>docs/rooms/2794121.md:131 |
| [TVアニメ『たまこまーけっと』Blu-ray Box PV](<http://v.youku.com/v_show/id_XODU0MTY1OTI0.html>)<br>`http://v.youku.com/v_show/id_XODU0MTY1OTI0.html` | 视频平台 / 可点击 | docs/albums/index.md:26<br>docs/broadcast/page/41.md:24<br>docs/rooms/2794121.md:129 |
| [http://v.youku.com/v_show/id_XODU4NTAxNzgw.html](<http://v.youku.com/v_show/id_XODU4NTAxNzgw.html>)<br>`http://v.youku.com/v_show/id_XODU4NTAxNzgw.html` | 视频平台 / 纯文本 | docs/broadcast/page/40.md:32 |
| [TVアニメ『響け！ユーフォニアム』PV第2弾](<http://v.youku.com/v_show/id_XOTE4MDMzODE2.html>)<br>`http://v.youku.com/v_show/id_XOTE4MDMzODE2.html` | 视频平台 / 可点击 | docs/albums/index.md:34<br>docs/broadcast/page/38.md:26<br>docs/rooms/2794117.md:111 |

### we-love-brass.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [日程表](<http://we-love-brass.jp/concours/2015/contents003672.html>)<br>`http://we-love-brass.jp/concours/2015/contents003672.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/505913072.md:90 |

### weibo.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [“养老天命反转地”](<http://weibo.com/5783798079/Eu62TpLZd?ref=collection&type=comment>)<br>`http://weibo.com/5783798079/Eu62TpLZd?ref=collection&type=comment` | 社交帖子 / 个人主页 / 可点击 | docs/notes/623421008.md:35 |
| [养老天命反转地](<http://weibo.com/5783798079/Eu62TpLZd?type=comment>)<br>`http://weibo.com/5783798079/Eu62TpLZd?type=comment` | 社交帖子 / 个人主页 / 可点击 | docs/notes/623264433.md:38 |

### ww3.sinaimg.cn

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [上手／下手](<http://ww3.sinaimg.cn/mw690/eb96d04egw1elay2auxtvj208c05ut8s.jpg>)<br>`http://ww3.sinaimg.cn/mw690/eb96d04egw1elay2auxtvj208c05ut8s.jpg` | 图片 / 全景资料链接 / 可点击 | docs/notes/433821101.md:12 |

### www.agraph.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://www.agraph.jp/](<http://www.agraph.jp/>)<br>`http://www.agraph.jp/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/575910736.md:29 |

### www.amazon.co.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [《今天与你共呼吸》](<http://www.amazon.co.jp/dp/4800210119>)<br>`http://www.amazon.co.jp/dp/4800210119` | 商品 / 商店 / 可点击 | docs/notes/519468055.md:30 |
| [《电影 轻音！官方Guidebook~樱高轻音部 Travel Diary~》](<http://www.amazon.co.jp/dp/4832242466>)<br>`http://www.amazon.co.jp/dp/4832242466` | 商品 / 商店 / 可点击 | docs/notes/429473097.md:37<br>docs/notes/429716807.md:24 |
| [唱片助君](<http://www.amazon.co.jp/dp/494395927X/>)<br>`http://www.amazon.co.jp/dp/494395927X/` | 商品 / 商店 / 可点击 | docs/notes/525677843.md:294 |
| [CA-53W-1ZD](<http://www.amazon.co.jp/dp/B000GB1R7S>)<br>`http://www.amazon.co.jp/dp/B000GB1R7S` | 商品 / 商店 / 可点击 | docs/notes/525677843.md:127 |
| [AKG K404](<http://www.amazon.co.jp/dp/B003A5OGW0>)<br>`http://www.amazon.co.jp/dp/B003A5OGW0` | 商品 / 商店 / 可点击 | docs/notes/525677843.md:279 |
| [炸虾型的……](<http://www.amazon.co.jp/dp/B008XTND40>)<br>`http://www.amazon.co.jp/dp/B008XTND40` | 商品 / 商店 / 可点击 | docs/notes/525677843.md:284 |
| [SONY RX1](<http://www.amazon.co.jp/dp/B009O06WY0/>)<br>`http://www.amazon.co.jp/dp/B009O06WY0/` | 商品 / 商店 / 可点击 | docs/notes/525677843.md:272 |
| [精选歌集](<http://www.amazon.co.jp/dp/B00QJZZVM2/>)<br>`http://www.amazon.co.jp/dp/B00QJZZVM2/` | 商品 / 商店 / 可点击 | docs/notes/490420693.md:15 |
| [《玉子市场》的BOX](<http://www.amazon.co.jp/dp/B00QK17D9E/>)<br>`http://www.amazon.co.jp/dp/B00QK17D9E/` | 商品 / 商店 / 可点击 | docs/notes/485196288.md:18 |
| [解释](<http://www.amazon.co.jp/review/R23DM57RGHWY43/>)<br>`http://www.amazon.co.jp/review/R23DM57RGHWY43/` | 商品 / 商店 / 可点击 | docs/notes/550509861.md:14 |
| [《聲之形 官方FANBOOK》](<https://www.amazon.co.jp/dp/4063930688/>)<br>`https://www.amazon.co.jp/dp/4063930688/` | 商品 / 商店 / 可点击 | docs/notes/623421008.md:11<br>docs/notes/623887272.md:13<br>docs/notes/624120737.md:30 |
| [《Quick Japan》Vol.127](<https://www.amazon.co.jp/dp/4778315405/>)<br>`https://www.amazon.co.jp/dp/4778315405/` | 商品 / 商店 / 可点击 | docs/notes/581099972.md:12 |
| [《Animestyle 010》](<https://www.amazon.co.jp/dp/4802151381/>)<br>`https://www.amazon.co.jp/dp/4802151381/` | 商品 / 商店 / 可点击 | docs/notes/620299921.md:12 |
| [《Newtype》2014年7月号](<https://www.amazon.co.jp/dp/B0093DSLK6/>)<br>`https://www.amazon.co.jp/dp/B0093DSLK6/` | 商品 / 商店 / 可点击 | docs/notes/575910736.md:32 |
| [《the shader》](<https://www.amazon.co.jp/dp/B017VXAAU8/>)<br>`https://www.amazon.co.jp/dp/B017VXAAU8/` | 商品 / 商店 / 可点击 | docs/notes/620796838.md:40 |
| [《Animage》2016年9月号](<https://www.amazon.co.jp/dp/B01HIP2K0C/>)<br>`https://www.amazon.co.jp/dp/B01HIP2K0C/` | 商品 / 商店 / 可点击 | docs/notes/576189949.md:12 |
| [《Animedia》2016年9月号](<https://www.amazon.co.jp/dp/B01HIP2K34>)<br>`https://www.amazon.co.jp/dp/B01HIP2K34` | 商品 / 商店 / 可点击 | docs/notes/575615184.md:12 |
| [《Newtype》2016年9月号](<https://www.amazon.co.jp/dp/B01IVC9OH8/>)<br>`https://www.amazon.co.jp/dp/B01IVC9OH8/` | 商品 / 商店 / 可点击 | docs/notes/575811208.md:12 |
| [《周刊少年Magazine》2016年42号](<https://www.amazon.co.jp/dp/B01LVXKPUF>)<br>`https://www.amazon.co.jp/dp/B01LVXKPUF` | 商品 / 商店 / 可点击 | docs/notes/581617831.md:12 |

### www.amazon.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [《Blackstar》](<http://www.amazon.com/dp/B017VORJK6>)<br>`http://www.amazon.com/dp/B017VORJK6` | 商品 / 商店 / 可点击 | docs/notes/536415117.md:42 |

### www.animate.tv

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [【山田尚子、小川太一、瀬波里梨】大ヒット御礼！ 山田尚子監督を始めとする制作陣が登壇した『たまこラブストーリー』スタッフ舞台挨拶をレポート！ http://www.animate.tv/news/details.php?id=1401535119&amp;p=1](<http://www.animate.tv/news/details.php?id=1401535119&p=1>)<br>`http://www.animate.tv/news/details.php?id=1401535119&p=1` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:60 |

### www.animatetimes.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://www.animatetimes.com/news/details.php?id=1472042096](<http://www.animatetimes.com/news/details.php?id=1472042096>)<br>`http://www.animatetimes.com/news/details.php?id=1472042096` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:119 |
| [完成披露上映会 http://www.animatetimes.com/news/details.php?id=1472049160](<http://www.animatetimes.com/news/details.php?id=1472049160>)<br>`http://www.animatetimes.com/news/details.php?id=1472049160` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:120<br>docs/albums/190597061.md:121 |

### www.anime-recorder.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://www.anime-recorder.com/ArticleDetail.aspx?seq_no=9559](<http://www.anime-recorder.com/ArticleDetail.aspx?seq_no=9559>)<br>`http://www.anime-recorder.com/ArticleDetail.aspx?seq_no=9559` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/190597061.md:41<br>docs/albums/190597061.md:42 |

### www.artsbj.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [荒川修作的《养老天命反转地》](<http://www.artsbj.com/show-19-501928-1.html>)<br>`http://www.artsbj.com/show-19-501928-1.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/581837681.md:153 |

### www.asahi.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [《朝日新闻》2016年9月10日晚报](<http://www.asahi.com/articles/DA3S12553913.html>)<br>`http://www.asahi.com/articles/DA3S12553913.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/581373515.md:12 |

### www.bilibili.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [【声优广播】洲崎绫和林原惠美的童话故事【微笑背后的辛酸】](<http://www.bilibili.com/video/av1603077/>)<br>`http://www.bilibili.com/video/av1603077/` | 视频平台 / 可点击 | docs/rooms/2794121.md:73 |
| [http://www.bilibili.com/video/av5406226/index_4.html](<http://www.bilibili.com/video/av5406226/index_4.html>)<br>`http://www.bilibili.com/video/av5406226/index_4.html` | 视频平台 / 纯文本 | docs/broadcast/page/18.md:28 |
| [http://www.bilibili.com/video/av5990134/](<http://www.bilibili.com/video/av5990134/>)<br>`http://www.bilibili.com/video/av5990134/` | 视频平台 / 可点击 | docs/broadcast/page/18.md:30<br>docs/notes/578163214.md:12 |
| [电影《聲之形》热映答谢见面会（2016.10.01）](<http://www.bilibili.com/video/av6489116/>)<br>`http://www.bilibili.com/video/av6489116/` | 视频平台 / 可点击 | docs/albums/index.md:25<br>docs/broadcast/page/9.md:30<br>docs/rooms/3598399.md:81 |

### www.chatterbox.tips

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://www.chatterbox.tips/# !【レポート】京アニ＆Doイベント「私たちは、いま！！」。監督対談！！/c1lhw/567bc47a0cf203da56ea29bd](<http://www.chatterbox.tips/>)<br>`http://www.chatterbox.tips/` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:17 |

### www.cinematoday.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://www.cinematoday.jp/image/N0062531_l 《玉子爱情故事》首映见面会现场照。“这部作品中塞满了各种各样的勇气，在制作中也总是鼓励着我。希望这部作品能成为大家迈出一步的勇气。”（山田导演）](<http://www.cinematoday.jp/image/N0062531_l>)<br>`http://www.cinematoday.jp/image/N0062531_l` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:150 |

### www.douban.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [豆瓣豆列](<http://www.douban.com/doulist/13935160/>)<br>`http://www.douban.com/doulist/13935160/` | 豆列 / 可点击 | docs/curated/index.md:83<br>docs/rooms/2793793.md:72 |
| [豆瓣豆列](<http://www.douban.com/doulist/39014187/>)<br>`http://www.douban.com/doulist/39014187/` | 豆列 / 可点击 | docs/curated/index.md:115<br>docs/rooms/2793793.md:96 |
| [豆瓣豆列](<http://www.douban.com/doulist/43094828/>)<br>`http://www.douban.com/doulist/43094828/` | 豆列 / 可点击 | docs/curated/index.md:66<br>docs/rooms/2793793.md:61 |
| [豆列](<http://www.douban.com/doulist/43094984/>)<br>`http://www.douban.com/doulist/43094984/` | 豆列 / 可点击 | docs/about.md:17<br>docs/rooms/2793793.md:135 |
| [豆列](<http://www.douban.com/doulist/43095035/>)<br>`http://www.douban.com/doulist/43095035/` | 豆列 / 可点击 | docs/about.md:15<br>docs/rooms/2793793.md:133 |
| [感想笔记](<http://www.douban.com/note/261864994/>)<br>`http://www.douban.com/note/261864994/` | 豆瓣日记 / 话题 / 可点击 | docs/notes/274238773.md:13<br>docs/rooms/2794121.md:22 |
| [豆瓣豆列](<https://www.douban.com/doulist/44247823/>)<br>`https://www.douban.com/doulist/44247823/` | 豆列 / 可点击 | docs/curated/index.md:22<br>docs/rooms/2793793.md:19 |
| [phil](<https://www.douban.com/people/phil/>)<br>`https://www.douban.com/people/phil/` | 豆瓣其他页面 / 可点击 | docs/notes/501830142.md:207 |
| [原站页面](<https://www.douban.com/topic/499780453/>)<br>`https://www.douban.com/topic/499780453/` | 豆瓣日记 / 话题 / 可点击 | docs/external/topic-499780453.md:122 |

### www.e-switch.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [龙落子的传说](<http://www.e-switch.jp/sz-deaf/symbol.html>)<br>`http://www.e-switch.jp/sz-deaf/symbol.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/550509861.md:14 |

### www.excite.co.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [excite](<http://www.excite.co.jp/News/bit/E1475063249559.html>)<br>`http://www.excite.co.jp/News/bit/E1475063249559.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/621091894.md:13 |
| [excite](<http://www.excite.co.jp/News/bit/E1475237612490.html>)<br>`http://www.excite.co.jp/News/bit/E1475237612490.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/621946123.md:13 |
| [http://www.excite.co.jp/News/reviewbook/20140617/E1402938201318.html （文中涉及剧透，请斟酌阅读。） ——故事前半是饼藏关注玉子，告白后则是玉子开始关注饼藏。不过饼藏在告白后就再也没付诸过任何行动了呢。 山田：这](<http://www.excite.co.jp/News/reviewbook/20140617/E1402938201318.html>)<br>`http://www.excite.co.jp/News/reviewbook/20140617/E1402938201318.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/broadcast/page/56.md:16<br>docs/notes/409767702.md:10 |
| [http://www.excite.co.jp/News/reviewmov/20140616/E1402850805404.html ——上映后周围反响如何？ 山田：周围的制作人员很多在公映首日就去看了，第二天对我说“非常好！”。这种事还是头一次经历，觉得很欣喜。 ——制作人员](<http://www.excite.co.jp/News/reviewmov/20140616/E1402850805404.html>)<br>`http://www.excite.co.jp/News/reviewmov/20140616/E1402850805404.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/broadcast/page/56.md:24<br>docs/notes/400308340.md:11 |
| [excite](<http://www.excite.co.jp/News/reviewmov/20160916/E1473959561942.html>)<br>`http://www.excite.co.jp/News/reviewmov/20160916/E1473959561942.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/581998436.md:12 |
| [excite](<http://www.excite.co.jp/News/reviewmov/20160918/E1474130571077.html>)<br>`http://www.excite.co.jp/News/reviewmov/20160918/E1474130571077.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/582222645.md:12 |

### www.hanakotoba.name

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [【花言葉事典】](<http://www.hanakotoba.name/>)<br>`http://www.hanakotoba.name/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/curated/index.md:153<br>docs/rooms/2793793.md:109 |
| [“真心的爱”、“装模作样”、“爱的天启”、“离别”](<http://www.hanakotoba.name/archives/2005/09/post_139.html>)<br>`http://www.hanakotoba.name/archives/2005/09/post_139.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/338329832.md:50<br>docs/notes/435337731.md:150 |
| [玛格丽特花](<http://www.hanakotoba.name/archives/2005/09/post_208.html>)<br>`http://www.hanakotoba.name/archives/2005/09/post_208.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/435337731.md:23 |

### www.hatago.co.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://www.hatago.co.jp/cherry/cherry-blossoms2015.htm](<http://www.hatago.co.jp/cherry/cherry-blossoms2015.htm>)<br>`http://www.hatago.co.jp/cherry/cherry-blossoms2015.htm` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/494796780.md:54 |

### www.hisaz.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [“かざり屋”与“一和”](<http://www.hisaz.com/sweet/kyoto/11.html>)<br>`http://www.hisaz.com/sweet/kyoto/11.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/347460778.md:89 |

### www.hobbystock.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://www.hobbystock.jp/sp/tamakomarket/](<http://www.hobbystock.jp/sp/tamakomarket/>)<br>`http://www.hobbystock.jp/sp/tamakomarket/` | 商品 / 商店 / 纯文本 | docs/albums/13433748.md:36<br>docs/albums/13433748.md:37<br>docs/albums/13433748.md:38 |

### www.jfd.or.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [全日本聋哑联盟](<http://www.jfd.or.jp/about/jfdlogo>)<br>`http://www.jfd.or.jp/about/jfdlogo` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/550509861.md:14 |

### www.korg.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [アニメ『けいおん！』5周年アニバーサリーを記念して、コルグ「RK-100S けいおん！スペシャル」の誕生です。 - See more http://www.korg.com/jp/products/synthesizers/rk_100s/k_on.php](<http://www.korg.com/jp/products/synthesizers/rk_100s/k_on.php>)<br>`http://www.korg.com/jp/products/synthesizers/rk_100s/k_on.php` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13431373.md:19 |

### www.kyotoanimation.co.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [【京アニHP】](<http://www.kyotoanimation.co.jp/>)<br>`http://www.kyotoanimation.co.jp/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/curated/index.md:151<br>docs/rooms/2793793.md:109 |
| [http://www.kyotoanimation.co.jp/books/tamako/ mainVisual](<http://www.kyotoanimation.co.jp/books/tamako/>)<br>`http://www.kyotoanimation.co.jp/books/tamako/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/albums/13432051.md:29<br>docs/notes/347460778.md:173 |
| [「京アニ&amp;Do C・T・F・K 2013」，石原立也、武本康弘、堀口悠紀子、山田尚子。 http://www.kyotoanimation.co.jp/ctfk2013/report/](<http://www.kyotoanimation.co.jp/ctfk2013/report/>)<br>`http://www.kyotoanimation.co.jp/ctfk2013/report/` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:187 |
| [去字 http://www.kyotoanimation.co.jp/information/?id=794 http://www.kyotoanimation.co.jp/img/newyear/topNewYear2014.jpg](<http://www.kyotoanimation.co.jp/img/newyear/topNewYear2014.jpg>)<br>`http://www.kyotoanimation.co.jp/img/newyear/topNewYear2014.jpg` | 图片 / 全景资料链接 / 纯文本 | docs/albums/13432051.md:31<br>docs/albums/13432051.md:33 |
| [去字 http://www.kyotoanimation.co.jp/information/?id=794 http://www.kyotoanimation.co.jp/img/newyear/topNewYear2014.jpg](<http://www.kyotoanimation.co.jp/information/?id=794>)<br>`http://www.kyotoanimation.co.jp/information/?id=794` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13432051.md:31<br>docs/albums/13432051.md:32 |
| [THE☆アニメバカ一代](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?author=18>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?author=18` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/about.md:7<br>docs/rooms/2793793.md:125 |
| [http://www.kyotoanimation.co.jp/staff/anibaka/blog/?m=20170725](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?m=20170725>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?m=20170725` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/630626923.md:31 |
| [2015年7月6日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1042>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1042` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/507086258.md:10 |
| [2015年8月10日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1100>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1100` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/512288929.md:11 |
| [2015年9月7日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1145>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1145` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/515999854.md:10 |
| [2015年10月13日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1193>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1193` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/520501904.md:11 |
| [2015年11月13日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1248>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1248` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/524707046.md:10 |
| [2015年12月15日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1286>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1286` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/529201220.md:10 |
| [2016年1月21日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1322>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1322` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/536415117.md:11 |
| [2016年2月22日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1368>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1368` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/541065079.md:10 |
| [2016年3月24日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1414>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1414` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/547187777.md:10 |
| [2016年5月26日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1493>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1493` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/560290293.md:10 |
| [2016年7月22日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1567>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1567` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/572029004.md:10 |
| [2016年8月25日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1595>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1595` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/578163214.md:10 |
| [2016年9月26日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1650>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1650` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/583640613.md:10 |
| [2016年10月27日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1686>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1686` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/589189219.md:10 |
| [2016年11月28日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1725>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1725` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/594375309.md:11 |
| [2016年12月27日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1756>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1756` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/599081646.md:10 |
| [2017年1月31日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1790>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1790` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/604396376.md:10 |
| [2017年3月1日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1830>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1830` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/608843975.md:11 |
| [&lt;a href=&quot;http://2017年3月31日&quot;&gt;http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1865&lt;/a&gt; 大家好！ 春天的气息已经相当浓郁了呢。 各位近来可好？ 我不知是感冒还是怎么了，嗓子变得怪怪的，现](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1865>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1865` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/broadcast/page/5.md:26<br>docs/notes/614170395.md:10 |
| [2017年4月26日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1892>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1892` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/617677191.md:10 |
| [2017年5月30日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1945>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1945` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/622694100.md:10 |
| [2017年6月27日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1987>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1987` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/626780778.md:10 |
| [2017年7月25日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2050>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2050` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/630626923.md:11 |
| [2017年8月23日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2094>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2094` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/634384397.md:10 |
| [2017年9月20日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2133>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2133` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/638128887.md:10 |
| [2017年10月19日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2172>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2172` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/641740675.md:10 |
| [2017年11月16日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2223>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2223` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/645545220.md:11 |
| [2017年12月15日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2261>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2261` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/649190492.md:11 |
| [2018年1月18日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2313>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2313` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/653967636.md:11 |
| [2018年2月16日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2361>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2361` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/657510394.md:11 |
| [2018年3月15日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2395>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2395` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/661229588.md:11 |
| [2018年4月16日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2495>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2495` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/666011890.md:10 |
| [2018年5月17日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2541>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2541` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/669962541.md:10 |
| [2018年6月14日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2598>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=2598` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/673585518.md:11 |
| [2014年5月28日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=363>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=363` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/410073605.md:10 |
| [2014年7月18日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=404>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=404` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/410095370.md:10 |
| [2014年08月25日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=475>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=475` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/410464332.md:10 |
| [2014年9月29日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=552>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=552` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/430242140.md:10 |
| [2014年10月30日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=654>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=654` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/441842568.md:11 |
| [2014年12月5日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=711>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=711` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/467449573.md:10 |
| [2015年1月15日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=762>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=762` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/480506533.md:10 |
| [2015年2月18日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=811>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=811` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/485196288.md:10 |
| [2015年3月23日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=860>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=860` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/490420693.md:10 |
| [2015年4月27日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=909>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=909` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/496648491.md:10 |
| [2015年6月2日](<http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=968>)<br>`http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=968` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/502324234.md:11 |

### www.lmaga.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [Lmaga.jp](<http://www.lmaga.jp/news/2016/10/15946/>)<br>`http://www.lmaga.jp/news/2016/10/15946/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/586749537.md:12 |

### www.nao.ac.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [【天文情報】](<http://www.nao.ac.jp/astro/>)<br>`http://www.nao.ac.jp/astro/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/curated/index.md:154<br>docs/rooms/2793793.md:109 |

### www.nicovideo.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [けいおん学](<http://www.nicovideo.jp/mylist/21479054>)<br>`http://www.nicovideo.jp/mylist/21479054` | 视频平台 / 可点击 | docs/rooms/2794136.md:40 |
| [もぶおん学](<http://www.nicovideo.jp/mylist/24488341>)<br>`http://www.nicovideo.jp/mylist/24488341` | 视频平台 / 可点击 | docs/rooms/2794136.md:41 |
| [けいおん学講義 第1回～けいおんのテーマとは～](<http://www.nicovideo.jp/watch/sm12191489>)<br>`http://www.nicovideo.jp/watch/sm12191489` | 视频平台 / 可点击 | docs/notes/274371246.md:10 |
| [けいおん学講義 第2回～けいおんと暗喩～](<http://www.nicovideo.jp/watch/sm12207106>)<br>`http://www.nicovideo.jp/watch/sm12207106` | 视频平台 / 可点击 | docs/notes/274768174.md:10 |
| [けいおん学講義 第3回～キャラクターとキーアイテム(前)～](<http://www.nicovideo.jp/watch/sm12248330>)<br>`http://www.nicovideo.jp/watch/sm12248330` | 视频平台 / 可点击 | docs/notes/291753270.md:11 |
| [【けいおん学番外編】Listen!!レビュー](<http://www.nicovideo.jp/watch/sm12900652>)<br>`http://www.nicovideo.jp/watch/sm12900652` | 视频平台 / 可点击 | docs/notes/519165447.md:69 |
| [【けいおん学１３】けいおんキャラクターレビュー第６回～鈴木純～](<https://www.nicovideo.jp/watch/sm13556149>)<br>`https://www.nicovideo.jp/watch/sm13556149` | 视频平台 / 可点击 | docs/notes/820543319.md:32 |

### www.okuru-hana.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [诞生花](<http://www.okuru-hana.com/40/post_21.html>)<br>`http://www.okuru-hana.com/40/post_21.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/493628625.md:26 |

### www.recosuke.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [本秀康](<http://www.recosuke.com/>)<br>`http://www.recosuke.com/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/about.md:22<br>docs/notes/525677843.md:293<br>docs/rooms/2793793.md:140 |

### www.shuwa-island.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [手语岛](<http://www.shuwa-island.jp/>)<br>`http://www.shuwa-island.jp/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/584217092.md:23 |

### www.tbs.co.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [官网](<http://www.tbs.co.jp/anime/k-on/k-on_tv/index-j.html>)<br>`http://www.tbs.co.jp/anime/k-on/k-on_tv/index-j.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:17 |

### www.tudou.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://www.tudou.com/programs/view/-uye3_2pTeA/](<http://www.tudou.com/programs/view/-uye3_2pTeA/>)<br>`http://www.tudou.com/programs/view/-uye3_2pTeA/` | 视频平台 / 纯文本 | docs/broadcast/page/40.md:26 |
| [http://www.tudou.com/programs/view/NWwQE5NJoKA/](<http://www.tudou.com/programs/view/NWwQE5NJoKA/>)<br>`http://www.tudou.com/programs/view/NWwQE5NJoKA/` | 视频平台 / 纯文本 | docs/broadcast/page/39.md:22 |

### www.uji-genji.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [源氏物语博物馆](<http://www.uji-genji.jp/ch/genji/>)<br>`http://www.uji-genji.jp/ch/genji/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/501830142.md:65 |

### www.watch-watcher.xyz

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [CA-50](<http://www.watch-watcher.xyz/article/418614927.html>)<br>`http://www.watch-watcher.xyz/article/418614927.html` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/notes/525677843.md:127 |

### www42.atwiki.jp

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [まとめwiki](<http://www42.atwiki.jp/keionbu/>)<br>`http://www42.atwiki.jp/keionbu/` | 其他网页（文章 / 官网 / 博客，需细分） / 可点击 | docs/rooms/2794136.md:17 |

### wx4.sinaimg.cn

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [http://wx4.sinaimg.cn/large/615f9184ly1fobsx8jys4j20vv0hx4qp.jpg](<http://wx4.sinaimg.cn/large/615f9184ly1fobsx8jys4j20vv0hx4qp.jpg>)<br>`http://wx4.sinaimg.cn/large/615f9184ly1fobsx8jys4j20vv0hx4qp.jpg` | 图片 / 全景资料链接 / 可点击 | docs/notes/653967636.md:48 |

### zh.wikipedia.org

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [可可·香奈儿](<http://zh.wikipedia.org/wiki/%E5%8F%AF%E5%8F%AF%C2%B7%E9%A6%99%E5%A5%88%E5%B0%94>)<br>`http://zh.wikipedia.org/wiki/%E5%8F%AF%E5%8F%AF%C2%B7%E9%A6%99%E5%A5%88%E5%B0%94` | 百科资料 / 可点击 | docs/notes/347460778.md:125 |
| [奥黛丽·赫本](<http://zh.wikipedia.org/wiki/%E5%A5%A5%E9%BB%9B%E4%B8%BD%C2%B7%E8%B5%AB%E6%9C%AC>)<br>`http://zh.wikipedia.org/wiki/%E5%A5%A5%E9%BB%9B%E4%B8%BD%C2%B7%E8%B5%AB%E6%9C%AC` | 百科资料 / 可点击 | docs/notes/347460778.md:125 |
| [定格动画（Stop-motion animation）](<http://zh.wikipedia.org/wiki/%E5%AE%9A%E6%A0%BC%E5%8A%A8%E7%94%BB>)<br>`http://zh.wikipedia.org/wiki/%E5%AE%9A%E6%A0%BC%E5%8A%A8%E7%94%BB` | 百科资料 / 可点击 | docs/notes/435337731.md:33 |
| [小津安二郎](<http://zh.wikipedia.org/wiki/%E5%B0%8F%E6%B4%A5%E5%AE%89%E4%BA%8C%E9%83%8E>)<br>`http://zh.wikipedia.org/wiki/%E5%B0%8F%E6%B4%A5%E5%AE%89%E4%BA%8C%E9%83%8E` | 百科资料 / 可点击 | docs/notes/347460778.md:126 |
| [麦金托什](<http://zh.wikipedia.org/wiki/%E6%9F%A5%E7%88%BE%E6%96%AF%C2%B7%E9%9B%B7%E5%B0%BC%C2%B7%E9%BA%A5%E9%87%91%E6%89%98%E4%BB%80>)<br>`http://zh.wikipedia.org/wiki/%E6%9F%A5%E7%88%BE%E6%96%AF%C2%B7%E9%9B%B7%E5%B0%BC%C2%B7%E9%BA%A5%E9%87%91%E6%89%98%E4%BB%80` | 百科资料 / 可点击 | docs/notes/347460778.md:125 |
| [笠智众](<http://zh.wikipedia.org/wiki/%E7%AC%A0%E6%99%BA%E7%9C%BE>)<br>`http://zh.wikipedia.org/wiki/%E7%AC%A0%E6%99%BA%E7%9C%BE` | 百科资料 / 可点击 | docs/notes/347460778.md:125 |
| [“8球”](<http://zh.wikipedia.org/wiki/8%E8%99%9F%E7%90%83>)<br>`http://zh.wikipedia.org/wiki/8%E8%99%9F%E7%90%83` | 百科资料 / 可点击 | docs/notes/425866593.md:108 |
| [完形崩溃](<http://zh.wikipedia.org/zh-sg/%E5%AE%8C%E5%BD%A2%E5%B4%A9%E5%A3%9E>)<br>`http://zh.wikipedia.org/zh-sg/%E5%AE%8C%E5%BD%A2%E5%B4%A9%E5%A3%9E` | 百科资料 / 可点击 | docs/notes/347460778.md:138 |
| [石原（立也）](<http://zh.wikipedia.org/zh/%E7%9F%B3%E5%8E%9F%E7%AB%8B%E4%B9%9F>)<br>`http://zh.wikipedia.org/zh/%E7%9F%B3%E5%8E%9F%E7%AB%8B%E4%B9%9F` | 百科资料 / 可点击 | docs/notes/347460778.md:82 |
| [大卫·鲍伊](<https://zh.wikipedia.org/wiki/%E5%A4%A7%E5%8D%AB%C2%B7%E9%B2%8D%E4%BC%8A>)<br>`https://zh.wikipedia.org/wiki/%E5%A4%A7%E5%8D%AB%C2%B7%E9%B2%8D%E4%BC%8A` | 百科资料 / 可点击 | docs/about.md:26<br>docs/rooms/2793793.md:144 |
| [《暴れん坊将軍》](<https://zh.wikipedia.org/zh-cn/%E6%9A%B4%E5%9D%8A%E5%B0%87%E8%BB%8D>)<br>`https://zh.wikipedia.org/zh-cn/%E6%9A%B4%E5%9D%8A%E5%B0%87%E8%BB%8D` | 百科资料 / 可点击 | docs/notes/511505892.md:74 |

### zyunko.kyoto-yoroken.com

| 目标与标签 | 类型 / 形式 | 来源页面 |
| --- | --- | --- |
| [制作组在京都老字号糕点店“养老轩”取材时拍摄的纪念照（2012年3月） http://zyunko.kyoto-yoroken.com/?eid=319](<http://zyunko.kyoto-yoroken.com/?eid=319>)<br>`http://zyunko.kyoto-yoroken.com/?eid=319` | 其他网页（文章 / 官网 / 博客，需细分） / 纯文本 | docs/albums/13433748.md:189 |

## 附属 URL

原站链接：169 个目标；见 JSON 的 `originalSiteLinks`。
正文远程图片：0 个目标；见 `remoteImages`。
frontmatter URL：151 次；见 `frontmatterUrls`。

重新统计：`uv run python reviews/2026-09-30/external-links/capture_inventory.py`。
