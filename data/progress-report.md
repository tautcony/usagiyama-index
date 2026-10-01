# 归档进度报告

- 站点：https://site.douban.com/211330/
- 生成时间：2026-10-01T15:17:00+08:00

## 整体累计进度

累计成功数按唯一 key 记录；完成过的项目不会因重试失败或解析器升级而扣回。

- 累计成功归档：**3420** 个对象

| 阶段 | 累计成功归档 |
| --- | ---: |
| albums | 6 |
| bulletins | 7 |
| external | 584 |
| external-images | 2054 |
| forum | 1 |
| main | 81 |
| miniblog | 1 |
| notes | 144 |
| photos | 523 |
| rooms | 7 |
| videos | 12 |

## 当前状态快照

当前进度库记录 3460 个对象；此处状态用于续跑和排错，可能随重试变化。

## 状态汇总

| 状态 | 数量 |
| --- | ---: |
| 已完成 | 3419 |
| 不可访问（已标记） | 8 |
| 失败（下次重试） | 33 |
| 已跳过 | 0 |

## 分阶段

| 阶段 | 完成 | 不可访问 | 失败 | 跳过 |
| --- | ---: | ---: | ---: | ---: |
| albums | 6 | 0 | 0 | 0 |
| bulletins | 7 | 0 | 0 | 0 |
| external | 583 | 7 | 0 | 0 |
| external-images | 2054 | 0 | 32 | 0 |
| forum | 1 | 0 | 0 | 0 |
| main | 81 | 1 | 1 | 0 |
| miniblog | 1 | 0 | 0 | 0 |
| notes | 144 | 0 | 0 | 0 |
| photos | 523 | 0 | 0 | 0 |
| rooms | 7 | 0 | 0 | 0 |
| videos | 12 | 0 | 0 | 0 |

## 待重试项

| Key | 阶段 | 次数 | 说明 |
| --- | --- | ---: | --- |
| `external-image:025045178d95623bb7d2` | external-images | 1 | http://pbs.twimg.com/profile_images/635373462333198337/T39fIGIv_normal.jpg → HTTP 404 · image/jpeg · 0B · 本次网络请求，源站无此尺寸 |
| `external-image:0c9b5a5020321f1cfdbb` | external-images | 1 | http://blog-imgs-58.fc2.com/p/r/i/priority1/05_20130519020956s.jpg → HTTP 404 · application/xml · 137B · 本次网络请求，源站无此尺寸 |
| `external-image:0fe7913fff639c5de956` | external-images | 2 | https://web.archive.org/web/20160319155837im_/http://watch-watcher.up.n.seesaa.net/watch-watcher/image/ca53-thumbnail2.jpg?d=a0 → HTTP 404 · text/html · 4710B · 来自缓存（2026-10-01T13:31:02+08:00），源站无此尺寸… |
| `external-image:158b75707c6eebb1e673` | external-images | 2 | https://web.archive.org/web/20161009180204im_/http://www.anime-recorder.com/system/doc/AT004_Article/9559/2.jpg → HTTP 404 · text/html · 4700B · 来自缓存（2026-10-01T13:29:47+08:00），源站无此尺寸；https://www.ani… |
| `external-image:1c3807217b4b167ef63d` | external-images | 2 | https://web.archive.org/web/20160319155837im_/http://watch-watcher.up.n.seesaa.net/watch-watcher/image/bttfpg-thumbnail2.jpg?d=a1 → HTTP 404 · text/html · 4712B · 来自缓存（2026-10-01T13:31:05+08:00），源站无此… |
| `external-image:21d54292e541e85f2607` | external-images | 1 | https://blogroll.livedoor.net/img/blog_favicon.ico?t=20230912 → HTTP 200 · image/x-icon · 16958B · 本次网络请求，疑似错误页 |
| `external-image:24459b0eea339a1da615` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!010.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:27+08:00），源站无此尺寸；https://w… |
| `external-image:26011e7e76746558d71c` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!009.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:21+08:00），源站无此尺寸；https://w… |
| `external-image:2c5887024d5f475ded82` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!901.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:53+08:00），源站无此尺寸；https://w… |
| `external-image:2ddb6e38bcd970b70e8f` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!012.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:37+08:00），源站无此尺寸；https://w… |
| `external-image:324a37808937e356df5d` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!007.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:17+08:00），源站无此尺寸；https://w… |
| `external-image:3a9d828256bcdf3e12b1` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!006.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:06+08:00），源站无此尺寸；https://w… |
| `external-image:3ac91c3bd1000acb8b5c` | external-images | 2 | https://web.archive.org/web/20140821115823im_/http://twi-ani.com/anitter/report/images/05171.jpg → HTTP 404 · text/html · 4647B · 来自缓存（2026-10-01T13:16:16+08:00），源站无此尺寸；https://twi-ani.com/anitter/re… |
| `external-image:47fb73dad7c391350c08` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!011.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:40+08:00），源站无此尺寸；https://w… |
| `external-image:498751ced94758b2e78c` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!013.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:38+08:00），源站无此尺寸；https://w… |
| `external-image:71d7b573f3d481d07ae9` | external-images | 2 | https://web.archive.org/web/20160618145242im_/http://columii.jp:80/movie/images/article/eigaka.jpg → HTTP 404 · text/html · 4642B · 来自缓存（2026-10-01T13:15:22+08:00），源站无此尺寸；https://web.archive.org/web/… |
| `external-image:79fd788f1ccc61f44e55` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!001.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:16:46+08:00），源站无此尺寸；https://w… |
| `external-image:7f93b05e8db20bead71f` | external-images | 1 | https://img.animeanime.jp/imgs/zoom/52845.jpg → HTTP 403 · 源站拒绝访问 |
| `external-image:87deb10986f2a2b3d133` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!003.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:16:56+08:00），源站无此尺寸；https://w… |
| `external-image:a0c4dfd38ad506957102` | external-images | 2 | https://web.archive.org/web/20161009180204im_/http://www.anime-recorder.com/system/doc/AT004_Article/9559/1.jpg → HTTP 404 · text/html · 4700B · 来自缓存（2026-10-01T13:29:40+08:00），源站无此尺寸；https://www.ani… |
| `external-image:af20ff7f8446b9fd6f11` | external-images | 2 | https://web.archive.org/web/20160319155837im_/http://watch-watcher.up.n.seesaa.net/watch-watcher/image/bttf2-thumbnail2.jpg?d=a0 → HTTP 404 · text/html · 4711B · 来自缓存（2026-10-01T13:30:55+08:00），源站无此尺… |
| `external-image:b106087c6fbfb17a8836` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!005.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:07+08:00），源站无此尺寸；https://w… |
| `external-image:b12c33a7c5e80848c8d1` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!004.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:05+08:00），源站无此尺寸；https://w… |
| `external-image:b60f27ab7c355654f3c7` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!014.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:48+08:00），源站无此尺寸；https://w… |
| `external-image:c341c5e0a84cd153df20` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!008.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:18+08:00），源站无此尺寸；https://w… |
| `external-image:d38786d37646232003e2` | external-images | 1 | https://img.animeanime.jp/imgs/zoom/96736.jpg → HTTP 403 · 源站拒绝访问 |
| `external-image:d3d9d6d751a88cfc0b44` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!002.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:16:52+08:00），源站无此尺寸；https://w… |
| `external-image:de57fbf78dd62807bcb8` | external-images | 2 | https://web.archive.org/web/20160618145242im_/http://columii.jp:80/movie/images/article/dbook.jpg → HTTP 404 · text/html · 4641B · 来自缓存（2026-10-01T13:15:29+08:00），源站无此尺寸；https://web.archive.org/web/2… |
| `external-image:eb4d471293152371fcf0` | external-images | 2 | https://web.archive.org/web/20161009180204im_/http://www.anime-recorder.com/system/doc/AT004_Article/9559/3.jpg → HTTP 404 · text/html · 4700B · 来自缓存（2026-10-01T13:29:43+08:00），源站无此尺寸；https://www.ani… |
| `external-image:ecbed63dcd247123ae55` | external-images | 2 | https://web.archive.org/web/20180407081111im_/http://moca-news.net:80/article/20160902/2016090216000a_/image/!015.jpg → HTTP 404 · text/html · 4705B · 来自缓存（2026-10-01T13:17:54+08:00），源站无此尺寸；https://w… |
| `external-image:ef3356f459d7b6a3239a` | external-images | 2 | https://web.archive.org/web/20160319155837im_/http://watch-watcher.up.n.seesaa.net/watch-watcher/image/bttf4-thumbnail2.jpg?d=a1 → HTTP 404 · text/html · 4711B · 来自缓存（2026-10-01T13:31:16+08:00），源站无此尺… |
| `external-image:f0a4edf3fce5a7b5ee89` | external-images | 2 | https://web.archive.org/web/20161009180204im_/http://www.anime-recorder.com/system/doc/AT004_Article/9559/4.jpg → HTTP 404 · text/html · 4700B · 来自缓存（2026-10-01T13:29:59+08:00），源站无此尺寸；https://www.ani… |
| `main:view-photo` | main | 1 | Page.goto: net::ERR_HTTP_RESPONSE_CODE_FAILURE at http://img3.douban.com/view/photo/raw/public/p2173264901.jpg Call log: - navigating to "http://img3.douban.com/view/photo/raw/public/p2173264901.jpg"… |

## 不可访问项

| Key | 阶段 | 说明 |
| --- | --- | --- |
| `external:26e7ea127ec1058ae70a` | external | 未取得有效文章正文；详见 recoveryAttempts |
| `external:659312bae9f75e2a34f6` | external | 未取得有效文章正文；详见 recoveryAttempts |
| `external:666f5eadc5e93ab3513e` | external | 未取得有效文章正文；详见 recoveryAttempts |
| `external:7f948b7a27ed59c95b43` | external | 未取得有效文章正文；详见 recoveryAttempts |
| `external:9e3e5c01ca595a62d2a3` | external | 未取得有效文章正文；详见 recoveryAttempts |
| `external:b351073233fe2a039f4c` | external | 未取得有效文章正文；详见 recoveryAttempts |
| `external:c9865a002b3c1a2aec4b` | external | 未取得有效文章正文；详见 recoveryAttempts |
| `main:people-phil` | main | 源站返回 HTTP 404 |
