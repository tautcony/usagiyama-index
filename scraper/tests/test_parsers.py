"""HTML 解析测试。

用例中的 HTML 片段按目标站点的真实结构裁剪而来，
选择器一旦失效，这里会第一时间报错。
"""

from __future__ import annotations

from scraper.parsers import (
    clean_title,
    parse_bulletin,
    parse_comment_count,
    parse_date,
    parse_discussion,
    parse_miniblog,
    parse_note,
    parse_note_list,
    parse_page_step,
    parse_photo_detail,
    parse_photo_list,
    parse_room_nav,
    parse_site_meta,
    parse_total_pages,
    parse_video_list,
    parse_widgets,
)

ROOM_HTML = """
<html><head><title>兔子山的小站 (豆瓣)</title></head><body>
<div class="nav-items"><ul>
  <li id='current-room' class="on" data-url-for-json='https://site.douban.com/j/211330//room/2793793/'>
    <a href="https://site.douban.com/211330/room/2793793/"><span>宇宙的入口</span></a></li>
  <li><a href="https://site.douban.com/211330/room/3598399/"><span>☆ 聲之形</span></a></li>
</ul></div>
<div id="content"><div class="main">
  <div class="mod" id="bulletin-190597046">
    <div class="hd"><h2><span>公告栏</span></h2></div>
    <div class="bd"><div class="bulletin-content" id="link-report" data-id="190597046">《聲之形》（Movie 2016）<a href="http://koenokatachi-movie.com/">官网</a></div></div>
  </div>
  <div class="mod" id="notes-190597056">
    <div class="hd"><h2><span>日记</span></h2></div><div class="bd"></div>
  </div>
  <div class="mod" id="photos-190597061">
    <div class="hd"><h2><span>相册</span></h2></div><div class="bd"></div>
  </div>
  <div class="mod" id="sp-user">
    <div class="bd">
      <div class="user-pic"><img width="192" height="192" alt="兔子山" src="https://img3.doubanio.com/img/site/large/6b3d50076fa7103" /></div>
      <div class="desc">《轻音！》系列、《玉子市场》<br /><br />世界中闪耀的光辉☆<br />山田尚子作品专题站</div>
    </div>
  </div>
</div></div></body></html>
"""

NOTE_LIST_HTML = """
<html><body><div class="item-entry">
  <div class="title"><a title="起用的理由与意外的发现——松冈茉优×山田尚子导演《聲之形》对谈（mynavi）"
     href="https://site.douban.com/211330/widget/notes/190597056/note/624442255/">起用的理由与意外的发现——松冈茉优…</a></div>
  <div class="datetime">2017-06-12 21:17:43</div>
  <div class="summary" id="note_624442255_short"><div class="ll"><a href="https://www.douban.com/note/624442255/">
    <img src="https://img3.doubanio.com/view/note/small/public/p43282417.jpg" alt=""/></a></div>
    译自mynavi news（记者=公文哲）……</div>
  <div class="actions"><a href="https://site.douban.com/211330/widget/notes/190597056/note/624442255/#comments">(3回应)</a></div>
</div>
<div class="paginator"><span class="thispage" data-total-page="4">1</span></div>
</body></html>
"""

# 正文容器 ``#link-report`` 尾部跟着豆瓣的"投诉"举报按钮（真实页面就是这么写的），
# 它不是正文 —— 只取容器内部 HTML 会把它一并带上。
NOTE_DETAIL_HTML = """
<html><head><title>电影《聲之形》导演山田尚子创作感言（《Animedia》2016年9月号） (兔子山的小站)</title></head><body>
<h1>电影《聲之形》导演山田尚子创作感言（《Animedia》2016年9月号）</h1>
<div class="note-header"><span class="datetime">2016-08-11 21:06:31</span></div>
<div id="note_575615184_full" class="note-content">
  <div id="link-report"><div class="cc"><table><tr><td><img src="https://img9.doubanio.com/view/note/large/public/p36410176.jpg" alt=""/></td></tr></table></div><br>译自<a rel="nofollow" href="https://www.douban.com/link2/?url=https%3A%2F%2Fwww.amazon.co.jp%2Fdp%2FB01HIP2K34">《Animedia》2016年9月号</a><br>西宫硝子有着生动和固执的一面。<div class="clear"></div>
  <span class="btn-report">投诉</span></div>
</div>
</body></html>
"""

# 列表页里两条都没有评论数链接：第一条摘要以数字收尾、第二条没有评论区。
# 第一条末尾跟着一段内嵌评论，评论尾部的"回应"回复按钮就在正文后面 ——
# 这正是"整条文本搜 数字+回应"会读出假数量的形状（→ 20180517）。
NOTE_LIST_NO_COUNT_HTML = """
<html><body>
<div class="item-entry">
  <div class="title"><a href="https://site.douban.com/211330/widget/notes/17565710/note/669962541/">丽兹亦青鸟☆Papico</a></div>
  <div class="datetime">2018-05-17 21:36:55</div>
  <div class="summary">真的很开心，谢谢大家20180517</div>
  <div class="comment-item"><span><a href="?cid=47263983#add_comment" class="lnk-reply hidden_lnk">回应</a></span></div>
  <div class="actions"><a href="#" class="fav-add j a_show_login">喜欢</a></div>
</div>
<div class="item-entry">
  <div class="title"><a href="https://site.douban.com/211330/widget/notes/17565710/note/485196288/">烤肉☆Papico</a></div>
  <div class="datetime">2015-02-18 21:30:57</div>
  <div class="summary">好想吃烤肉。</div>
</div>
</body></html>
"""

# 详情页：两条评论的正文都以数字收尾，后面紧跟各自的"回应"回复按钮
# （真实 href 是 ``?cid=…#add_comment``）。旧实现整页搜"数字+回应"，
# 于是把评论正文结尾当成了评论数（208 → 20170725 / 23333）。
NOTE_DETAIL_WITH_COMMENTS_HTML = """
<html><head><title>标题 (兔子山的小站)</title></head><body>
<h1>标题</h1>
<div class="note-header"><span class="datetime">2017-07-25 21:00:00</span></div>
<div id="note_594375309_full" class="note-content"><div id="link-report"><div class="cc">正文内容。</div></div></div>
<div id="comments">
  <ul class="comment-list">
    <li class="comment-item">
      <div class="comment-content"><p>参考 http://www.kyotoanimation.co.jp/staff/anibaka/blog/?m=20170725</p></div>
      <span><a href="?cid=47263983#add_comment" class="lnk-reply hidden_lnk">回应</a></span>
    </li>
    <li class="comment-item">
      <div class="comment-content"><p>这就是山田不拍她们穿大学校服的理由么23333</p></div>
      <span><a href="?cid=47263984#add_comment" class="lnk-reply hidden_lnk">回应</a></span>
    </li>
  </ul>
</div>
</body></html>
"""

PHOTO_LIST_HTML = """
<html><head><title>海报墙 (豆瓣)</title></head><body><h1>海报墙</h1>
<div class="event-photo-list"><ul class="list-s"><li><div class="photo-item">
  <a href="https://site.douban.com/211330/widget/photos/13432051/photo/2770778841/"
     title="诸行无常，唯有祈福方能克服世间苦难。" alt="诸行无常，唯有祈福方能克服世间苦难。"
     class="album_photo" id="p2770778841"><img src="https://img2.doubanio.com/view/photo/thumb/public/p2770778841.jpg" /></a>
  <div class="desc"><p>诸行无常，唯有...</p></div>
</div></li></ul></div></body></html>
"""

# 照片详情页的真实骨架（按缓存页面裁剪）：
# #link-report 里除了照片本身，还套着每张照片都一样的相册导航与按钮。
PHOTO_DETAIL_HTML = """
<html><head><title>幕后&周边</title></head><body>
<div class="photo-wrapper"><div id="link-report">
  <div class="photitle">&gt; 返回相册 第156张 / 共179张 <a id="pre_photo">上一张</a> / <a id="next_photo">下一张</a></div>
  <div class="phoview"><a class="mainphoto"><img src="https://img2.doubanio.com/view/photo/large/public/p2180208471.jpg" /></a></div>
  <div class="phodesc">
    <p>【4/19 たまこまーけっと おさらい上映会＆スタッフトークショー】（左起）瀬波里梨、山田尚子</p>
    <p><span id="original"><a href="https://img2.doubanio.com/view/photo/raw/public/p2180208471.jpg" title="查看原图">查看原图</a></span></p>
  </div>
  <span class="btn-report">投诉</span>
</div></div>
</body></html>
"""

# 一篇没有描述的照片：.phodesc 只剩"查看原图"
PHOTO_DETAIL_NO_DESC_HTML = """
<html><head><title>幕后&周边</title></head><body>
<div id="link-report">
  <div class="photitle">&gt; 返回相册 第1张 / 共22张 上一张 / 下一张</div>
  <div class="phodesc">
    <p><span id="original"><a href="https://img9.doubanio.com/view/photo/raw/public/p1958678825.jpg" title="查看原图">查看原图</a></span></p>
  </div>
  <span class="btn-report">投诉</span>
</div>
</body></html>
"""

# 长链接里插了嵌套的 <wbr> 断行提示（真实页面就是这么写的）
PHOTO_DETAIL_WBR_HTML = """
<html><head><title>幕后&周边</title></head><body>
<div id="link-report">
  <div class="phodesc"><p>KORG 联名款 - See more <a rel="nofollow" href="http://x/"> http://www.korg.com/ <wbr> jp/products/synthesi <wbr> zers/rk_100s/k_on.ph <wbr> p </wbr></wbr></wbr></a></p>
  <p><span id="original">查看原图</span></p></div>
</div>
</body></html>
"""

# 页面 <img> 只到 photo 尺寸、且是 .webp 的后端渲染（实测形态）。
# 原图只藏在"查看原图"链接里 —— 这正是此前被漏掉的那份文件。
PHOTO_DETAIL_ORIGINAL_HTML = """
<html><head><title>第八集 山顶场景 分镜</title></head><body>
<div class="photo-wrapper"><div id="link-report">
  <div class="photitle">&gt; 返回相册 第1张 / 共11张 上一张 / 下一张</div>
  <div class="phoview"><a class="mainphoto"><img src="https://img1.doubanio.com/view/photo/photo/public/p2325379542.webp" /></a></div>
  <div class="phodesc"><p>第八集山顶场景的分镜（by 山田尚子）</p>
    <p><span id="original"><a href="https://img1.doubanio.com/view/photo/raw/public/p2325379542.jpg" title="查看原图">查看原图</a></span></p>
  </div>
</div></div>
</body></html>
"""

# 结构变形：没有 #original 包裹，只有一个普通链接指向 raw 尺寸
PHOTO_DETAIL_ORIGINAL_LOOSE_HTML = """
<html><head><title>幕后&周边</title></head><body>
<div id="link-report">
  <div class="phoview"><img src="https://img2.doubanio.com/view/photo/large/public/p2180208471.jpg" /></div>
  <div class="phodesc"><p>看原图：<a href="https://img2.doubanio.com/view/photo/raw/public/p2180208471.jpg">这里</a></p></div>
</div>
</body></html>
"""

# 源站抖动：后端把地址渲染成字面量 "None"（实测形态）
PHOTO_DETAIL_SRC_NONE_HTML = """
<html><head><title>幕后&周边</title></head><body>
<div class="photo-wrapper"><div id="link-report">
  <div class="phoview"><a class="mainphoto"><img src="None" /></a></div>
  <div class="phodesc"><p>某张照片的描述</p></div>
</div></div>
</body></html>
"""

DISCUSSION_HTML = """
<html><head><title>【小站论坛开放，欢迎讨论】</title></head><body>
<h1>【小站论坛开放，欢迎讨论】</h1>
<div class="post"><div class="post-content">
  <div class="post-info"><span class="datetime">2014-08-21 13:56:32</span>
    <span class="from">来自: <a href="https://www.douban.com/people/2097286/">羽音</a></span></div>
  <p id="link-report">如题ｗ</p>
</div></div>
<div class="post-comments"><div id="comments">
  <div class="comment-item" data-cid="15592964">
    <div class="pic"><a href="https://www.douban.com/people/47486856/"><img src="https://img9.doubanio.com/icon/u47486856-24.jpg" alt="不花刺"/></a></div>
    <div class="content report-comment"><div class="author"><span>2014-10-12 16:14:13</span>
      <a href="https://www.douban.com/people/47486856/">不花刺</a> (So cool ,So sad)</div>
      <p>我的友邻好厉害啊系列。。。QAQ</p></div>
  </div>
</div></div></body></html>
"""

VIDEO_LIST_HTML = """
<html><body><div class="video-list"><ul class="list-s"><li><div class="item-video">
  <div class="pic"><a href="https://site.douban.com/211330/widget/videos/191513700/video/783649/">
    <img src="https://vthumb.ykimg.com/05420408581EFA5E6A0A4C0468D66385" alt=""
         name="http://v.youku.com/v_show/id_XMTgwODE3Mjg5Ng==.html" width="130" height="97"></a></div>
  <div class="info"><a href="https://site.douban.com/211330/widget/videos/191513700/video/783649/">
    瑞穗金融集团 CM 电影《聲之形》篇 30秒</a><br>2016-11-06上传<br><a href="#">0回应</a><br></div>
</div></li></ul></div></body></html>
"""

MINIBLOG_HTML = """
<html><body><div class="miniblog-content"><div class="stream-items">
  <div class="status-item" data-sid="3666848632" data-action="1" data-object-id="820543319">
    <div class="mod" data-status-id="3666848632">
      <div class="hd"><a href="https://www.douban.com/people/900109449/status/3666848632/" class="calendar">十一月<em>26</em></a></div>
      <div class="bd layout-1">
        <a href="https://site.douban.com/211330/widget/notes/15416684/note/820543319/" class="media">
          <img src="https://img3.doubanio.com/view/status/small/public/3iMHcq.jpg"/></a>
        <p class="text">写了新日记</p>
        <h5><a href="https://site.douban.com/211330/widget/notes/15416684/note/820543319/">《轻音》小彩蛋：漫画卷数与纯和忧加入轻音部的暗示</a></h5>
        <div class="description">《轻音！！》（第2期）第5集中……</div>
      </div>
    </div>
  </div>
</div></div></body></html>
"""


class TestHelpers:
    def test_clean_title_strips_site_suffix(self) -> None:
        assert clean_title("日记标题 (兔子山的小站)") == "日记标题"

    def test_clean_title_strips_douban_suffix(self) -> None:
        assert clean_title("海报墙 (豆瓣)") == "海报墙"

    def test_clean_title_keeps_inner_parens(self) -> None:
        title = "电影《聲之形》导演山田尚子创作感言（《Animedia》2016年9月号）"
        assert clean_title(f"{title} (兔子山的小站)") == title

    def test_parse_date(self) -> None:
        assert parse_date("2016-08-11 21:06:31") == "2016-08-11 21:06:31"

    def test_parse_date_short(self) -> None:
        assert parse_date("2014-08-21") == "2014-08-21"

    def test_parse_date_missing(self) -> None:
        assert parse_date("没有日期") == ""

    def test_parse_comment_count(self) -> None:
        assert parse_comment_count("(3回应)") == 3
        assert parse_comment_count("(12 回应)") == 12
        assert parse_comment_count("无") == 0

    def test_parse_total_pages(self) -> None:
        assert parse_total_pages('<span data-total-page="5">1</span>') == 5

    def test_parse_total_pages_accepts_single_and_unquoted_attributes(self) -> None:
        assert parse_total_pages("<span data-total-page='6'>1</span>") == 6
        assert parse_total_pages("<span data-total-page = 7>1</span>") == 7

    def test_parse_total_pages_default(self) -> None:
        # 没有 data-total-page 时返回 None（"无法确定"），由调用方告警/重试，
        # 而不是静默当成单页截断多页列表。
        assert parse_total_pages("<div></div>") is None

    def test_parse_page_step_from_paginator(self) -> None:
        html = """<div class="paginator">
            <a href="/x/widget/photos/1/?start=0">1</a>
            <a href="/x/widget/photos/1/?start=30">2</a>
            <a href="/x/widget/photos/1/?start=60">3</a>
        </div>"""
        assert parse_page_step(html) == 30

    def test_parse_page_step_ignores_page_jumps(self) -> None:
        """分页器混着「首页」这类跨页跳转时，取最小间距才是每页条数。"""
        html = """<div class="paginator">
            <a href="/x/widget/notes/1/?start=0">首页</a>
            <a href="/x/widget/notes/1/?start=40">4</a>
            <a href="/x/widget/notes/1/?start=50">5</a>
        </div>"""
        assert parse_page_step(html) == 10

    def test_parse_page_step_falls_back_without_paginator(self) -> None:
        assert parse_page_step("<div></div>", fallback=30) == 30
        # 单页列表只有一个页码链接，推不出间距
        single = '<div class="paginator"><a href="/x/?start=0">1</a></div>'
        assert parse_page_step(single, fallback=30) == 30

    def test_parse_page_step_rejects_degenerate_step(self) -> None:
        """间距为 1 必然是误读，照做会把列表逐条翻一遍。"""
        html = """<div class="paginator">
            <a href="/x/?start=0">1</a>
            <a href="/x/?start=1">2</a>
        </div>"""
        assert parse_page_step(html, fallback=30) == 30


class TestSiteStructure:
    def test_room_nav(self) -> None:
        rooms = parse_room_nav(ROOM_HTML)
        assert len(rooms) == 2
        assert rooms[0][0] == "2793793"
        assert rooms[0][1] == "宇宙的入口"
        assert rooms[1][1] == "☆ 聲之形"

    def test_widgets(self) -> None:
        widgets = parse_widgets(ROOM_HTML, "3598399")
        kinds = {(w.kind, w.widget_id) for w in widgets}
        assert ("bulletin", "190597046") in kinds
        assert ("notes", "190597056") in kinds
        assert ("photos", "190597061") in kinds
        # sp-user 不是有效模块，应被忽略
        assert not any(w.widget_id == "sp-user" for w in widgets)

    def test_site_meta(self) -> None:
        meta = parse_site_meta(ROOM_HTML)
        assert meta["name"] == "兔子山的小站"
        assert "山田尚子作品专题站" in meta["description"]
        assert meta["avatar"].endswith("6b3d50076fa7103")


class TestBulletin:
    def test_content_extracted(self) -> None:
        bulletin = parse_bulletin(ROOM_HTML, "190597046", "https://example.com/")
        assert bulletin.title == "公告栏"
        assert "《聲之形》" in bulletin.content_html
        assert "koenokatachi-movie.com" in bulletin.content_html


class TestNoteList:
    def test_entry_parsed(self) -> None:
        entries = parse_note_list(NOTE_LIST_HTML, "190597056")
        assert len(entries) == 1
        entry = entries[0]
        assert entry.note_id == "624442255"
        assert entry.widget_id == "190597056"
        assert entry.date == "2017-06-12 21:17:43"
        assert entry.comment_count == 3
        assert "起用的理由" in entry.title

    def test_no_duplicate_entries(self) -> None:
        doubled = NOTE_LIST_HTML + NOTE_LIST_HTML
        assert len(parse_note_list(doubled, "190597056")) == 1

    def test_count_only_from_comments_anchor(self) -> None:
        """没有指向 ``#comments`` 的链接时评论数必须是 0。

        摘要以数字收尾（"…20180517"）也不能被当成评论数——那样的
        结果会一路写进 manifest 与原站标注统计里。
        """
        entries = parse_note_list(NOTE_LIST_NO_COUNT_HTML, "17565710")
        assert [entry.comment_count for entry in entries] == [0, 0]


class TestNote:
    def test_note_parsed(self) -> None:
        note = parse_note(NOTE_DETAIL_HTML, "190597056", "575615184", "https://example.com/")
        assert note.title == "电影《聲之形》导演山田尚子创作感言（《Animedia》2016年9月号）"
        assert note.date == "2016-08-11 21:06:31"
        assert "西宫硝子" in note.content_html
        assert note.status.availability == "ok"

    def test_table_wrapper_preserved_in_raw_html(self) -> None:
        """解析阶段保留原始结构，由 html2md 负责拆解。"""
        note = parse_note(NOTE_DETAIL_HTML, "190597056", "575615184", "https://example.com/")
        assert "<table>" in note.content_html
        assert "p36410176.jpg" in note.content_html

    def test_comment_count_not_taken_from_comment_bodies(self) -> None:
        """详情页不解析评论数。

        页面上每条评论都有个"回应"回复按钮，整页文本里搜"数字+回应"命中
        的是上一条评论正文的结尾（"…?m=20170725 回应" → 20170725）。
        权威数量在列表页条目的 ``(N回应)`` 上，由 ``stage_notes`` 填进来，
        这里一律留 0。
        """
        note = parse_note(NOTE_DETAIL_WITH_COMMENTS_HTML, "17565710", "594375309", "https://example.com/")
        assert note.comment_count == 0
        # 评论区不混进正文（评论另有归档流程）
        assert "23333" not in note.content_html

    def test_report_button_stripped(self) -> None:
        """``#link-report`` 尾部的"投诉"举报按钮是界面文字，不是正文。

        照搬容器内部 HTML 会让归档的每篇日记都以一行"投诉"收尾。
        """
        note = parse_note(NOTE_DETAIL_HTML, "190597056", "575615184", "https://example.com/")
        assert "投诉" not in note.content_html
        assert "西宫硝子" in note.content_html

    def test_empty_body_marks_unavailable(self) -> None:
        html = '<html><head><title>空 (豆瓣)</title></head><body><h1>空</h1></body></html>'
        note = parse_note(html, "1", "2", "https://example.com/")
        assert note.status.availability == "unavailable"


class TestPhoto:
    def test_photo_list(self) -> None:
        photos = parse_photo_list(PHOTO_LIST_HTML, "13432051")
        assert len(photos) == 1
        assert photos[0].photo_id == "2770778841"
        assert photos[0].caption.startswith("诸行无常")
        assert "thumb" in photos[0].thumb_url

    def test_photo_detail_prefers_large(self) -> None:
        photo = parse_photo_detail(PHOTO_DETAIL_HTML, "13431373", "2180208471", "https://example.com/")
        assert "/large/" in photo.large_url
        assert photo.status.availability == "ok"

    def test_caption_excludes_album_chrome(self) -> None:
        """描述只取照片自己的文字。

        ``#link-report`` 里除了照片还有一条每张都一样的相册导航
        （"返回相册 第N张 / 共M张 上一张 / 下一张"）与"查看原图 投诉"按钮，
        旧代码用的 ``.photo-desc`` 选择器匹配不上真实类名 ``.phodesc``，
        于是一路退到 ``#link-report``，把整页界面文字当成了描述。
        """
        photo = parse_photo_detail(PHOTO_DETAIL_HTML, "13431373", "2180208471", "https://example.com/")
        assert photo.caption.startswith("【4/19")
        for chrome in ("返回相册", "上一张", "下一张", "查看原图", "投诉", "第156张"):
            assert chrome not in photo.caption

    def test_empty_description_stays_empty(self) -> None:
        """没有描述的照片不能拿相册名顶上——那是另一回事的噪音。"""
        photo = parse_photo_detail(PHOTO_DETAIL_NO_DESC_HTML, "13431373", "1958678825", "https://example.com/")
        assert photo.caption == ""

    def test_wbr_rejoined_into_full_url(self) -> None:
        """长链接里的 ``<wbr>`` 断行提示要拼回去，而不是留一串空格。"""
        photo = parse_photo_detail(PHOTO_DETAIL_WBR_HTML, "13431373", "2212412958", "https://example.com/")
        assert "http://www.korg.com/jp/products/synthesizers/rk_100s/k_on.php" in photo.caption
        assert "korg.com/ jp" not in photo.caption

    def test_photo_detail_missing(self) -> None:
        html = "<html><body><img src='https://img2.doubanio.com/view/photo/large/public/p999.jpg'/></body></html>"
        photo = parse_photo_detail(html, "1", "123", "https://example.com/")
        assert photo.status.availability == "unavailable"

    def test_original_link_extracted(self) -> None:
        """详情页的"查看原图"链接指向 ``raw`` 尺寸，那才是上传时的原图。

        页面 ``<img>`` 里的 ``large`` 是豆瓣的处理版（长边 1600，小图还会被放大），
        此前完全没处理过这个链接，归档下来的是处理版甚至 ``<img>`` 的 webp 转码。
        """
        photo = parse_photo_detail(
            PHOTO_DETAIL_ORIGINAL_HTML, "13431950", "2325379542", "https://example.com/"
        )
        assert photo.original_url == "https://img1.doubanio.com/view/photo/raw/public/p2325379542.jpg"
        # 页面那张（photo 尺寸的 webp）仍然留着，供原图取不到时兜底
        assert photo.large_url.endswith("/photo/public/p2325379542.webp")
        assert photo.status.availability == "ok"

    def test_large_also_recorded_when_original_present(self) -> None:
        photo = parse_photo_detail(
            PHOTO_DETAIL_HTML, "13431373", "2180208471", "https://example.com/"
        )
        assert photo.original_url == "https://img2.doubanio.com/view/photo/raw/public/p2180208471.jpg"
        assert "/large/" in photo.large_url

    def test_original_link_without_special_markup(self) -> None:
        """页面结构变了也要认得出原图链接（退化为全页扫 ``raw`` 尺寸）。"""
        photo = parse_photo_detail(
            PHOTO_DETAIL_ORIGINAL_LOOSE_HTML, "13431373", "2180208471", "https://example.com/"
        )
        assert photo.original_url == "https://img2.doubanio.com/view/photo/raw/public/p2180208471.jpg"

    def test_original_link_for_other_photo_ignored(self) -> None:
        """页面若被重定向到别的照片，不能把那张的原图安在这张头上。"""
        html = """
        <html><body><div id="link-report">
          <div class="phodesc"><p>x</p>
            <p><span id="original"><a href="https://img1.doubanio.com/view/photo/raw/public/p111.jpg" title="查看原图">查看原图</a></span></p>
          </div>
        </div></body></html>
        """
        photo = parse_photo_detail(html, "1", "222", "https://example.com/")
        assert photo.original_url == ""

    def test_none_src_is_retryable(self) -> None:
        """源站抖动渲染出 ``src="None"``：不是"这张照片没图"，而是没渲染好。

        这类失败必须标成可重试，否则下次同步不会再看它一眼，照片就永久缺了。
        """
        photo = parse_photo_detail(
            PHOTO_DETAIL_SRC_NONE_HTML, "13431950", "2325379527", "https://example.com/"
        )
        assert photo.large_url == ""
        assert photo.original_url == ""
        assert photo.status.availability == "unavailable"
        assert photo.status.retryable is True

    def test_genuinely_missing_page_is_not_retryable(self) -> None:
        """对照：拿到的根本不是照片页（没有页面骨架）时，照旧是确定性结论。"""
        html = "<html><body><p>呃...你想访问的页面不存在</p></body></html>"
        photo = parse_photo_detail(html, "1", "123", "https://example.com/")
        assert photo.status.availability == "unavailable"
        assert photo.status.retryable is False


class TestDiscussion:
    def test_post_and_comments(self) -> None:
        d = parse_discussion(DISCUSSION_HTML, "13466509", "58596553", "https://example.com/")
        assert d.title == "【小站论坛开放，欢迎讨论】"
        assert d.author == "羽音"
        assert d.date == "2014-08-21 13:56:32"
        assert "如题" in d.content_html
        assert len(d.comments) == 1
        assert d.comments[0].author == "不花刺"
        assert "我的友邻好厉害" in d.comments[0].content_html


class TestVideo:
    def test_video_parsed(self) -> None:
        videos = parse_video_list(VIDEO_LIST_HTML, "191513700")
        assert len(videos) == 1
        v = videos[0]
        assert v.video_id == "783649"
        assert v.title.startswith("瑞穗金融集团")
        assert v.external_url.startswith("http://v.youku.com")
        assert v.date == "2016-11-06"

    def test_missing_thumbnail_is_not_marked_ok(self) -> None:
        html = ('<div class="item-video"><div class="pic"><a href="'
                'https://site.douban.com/211330/widget/videos/123/video/771903/">'
                '</a></div><div class="info"><a>标题</a></div></div>')
        video = parse_video_list(html, "123")[0]
        assert video.status.availability == "unavailable"
        assert video.status.retryable


def test_source_status_normalizes_string_availability() -> None:
    from scraper.models import Availability, SourceStatus

    status = SourceStatus(availability="ok")
    assert status.availability is Availability.OK
    assert not status.needs_notice


class TestMiniblog:
    def test_status_parsed(self) -> None:
        statuses = parse_miniblog(MINIBLOG_HTML)
        assert len(statuses) == 1
        s = statuses[0]
        assert s.status_id == "3666848632"
        assert s.text == "写了新日记"
        assert "小彩蛋" in s.link_title
        assert s.date == "十一月26"

    def test_plain_status_keeps_quoted_text(self) -> None:
        html = '''<div class="status-item" data-sid="2" data-action="2">
          <p class="text">说：</p><blockquote>今天也很开心</blockquote></div>'''
        status = parse_miniblog(html)[0]
        assert status.text == "说："
        assert status.content == "今天也很开心"

    def test_next_page_url(self) -> None:
        from scraper.parsers import parse_miniblog_next_url

        html = '<div class="paginator"><link rel="next" href="?start=20"></div>'
        assert parse_miniblog_next_url(
            html, "https://site.douban.com/211330/widget/miniblog/13430546/"
        ) == "https://site.douban.com/211330/widget/miniblog/13430546/?start=20"

    def test_root_relative_next_page_preserves_site_id(self) -> None:
        from scraper.parsers import parse_miniblog_next_url

        html = '<div class="paginator"><link rel="next" href="/widget/miniblog/13430546/?start=20"></div>'
        assert parse_miniblog_next_url(
            html, "https://site.douban.com/211330/widget/miniblog/13430546/"
        ) == "https://site.douban.com/211330/widget/miniblog/13430546/?start=20"

    def test_missing_next_page(self) -> None:
        from scraper.parsers import parse_miniblog_next_url

        assert parse_miniblog_next_url("<div class='paginator'></div>", "https://example.test/") == ""

# 独立列表页结构：<div class="note-item" id="note-{id}"> + .note-hd h3 a
STANDALONE_LIST_HTML = """
<html><head><title>日记 (豆瓣)</title></head><body><h1>日记</h1>
<div class="mod"><div class="bd">
  <div class="note-item" id="note-580950328">
    <div class="note-hd">
      <a class="a_unfolder_n lnk-more" href="https://site.douban.com/211330/widget/notes/13431979/note/580950328/" id="naf-580950328">展开</a>
      <h3><a href="https://site.douban.com/211330/widget/notes/13431979/note/580950328/"
             title="《剧场版 吹响悠风号》特别上映（电影《聲之形》公映纪念）见面会报告">《剧场版 吹响悠风号》…</a></h3>
    </div>
    <div class="note-author">
      <a class="name" href="https://www.douban.com/people/2097286/">羽音</a>
      <span class="datetime">2016-09-10 19:27:22</span>
    </div>
    <div class="summary" id="note_580950328_short">
      <div class="ll"><a href="https://www.douban.com/note/580950328/">
        <img src="https://img3.doubanio.com/view/note/small/public/p37187262.webp" alt=""/></a></div>
      译自響け！ユーフォニアム…
      <a href="https://site.douban.com/211330/widget/notes/13431979/note/580950328/#comments">(1回应)</a>
    </div>
    <div class="note-content" id="note_580950328_full" style="display:none"><div id=""><div class="clear"></div></div></div>
  </div>
  <div class="note-item" id="note-111111111">
    <div class="note-hd"><h3><a href="https://site.douban.com/211330/widget/notes/13431979/note/111111111/"
      title="第二篇">第二篇</a></h3></div>
    <div class="note-author"><span class="datetime">2015-01-02 03:04:05</span></div>
    <div class="summary" id="note_111111111_short">无评论的条目</div>
  </div>
  <div class="paginator"><span class="thispage" data-total-page="3">1</span></div>
</div></div></body></html>
"""


class TestStandaloneNoteList:
    """独立列表页（widget/notes/{id}/）的结构与房间内嵌列表完全不同。"""

    def test_entries_parsed(self) -> None:
        entries = parse_note_list(STANDALONE_LIST_HTML, "13431979")
        assert len(entries) == 2
        assert entries[0].note_id == "580950328"

    def test_title_from_h3_anchor(self) -> None:
        entries = parse_note_list(STANDALONE_LIST_HTML, "13431979")
        assert entries[0].title.startswith("《剧场版 吹响悠风号》")

    def test_date_parsed(self) -> None:
        entries = parse_note_list(STANDALONE_LIST_HTML, "13431979")
        assert entries[0].date == "2016-09-10 19:27:22"
        assert entries[1].date == "2015-01-02 03:04:05"

    def test_comment_count_from_comments_link(self) -> None:
        entries = parse_note_list(STANDALONE_LIST_HTML, "13431979")
        assert entries[0].comment_count == 1
        assert entries[1].comment_count == 0

    def test_widget_id_from_url(self) -> None:
        entries = parse_note_list(STANDALONE_LIST_HTML, "13431979")
        assert entries[0].widget_id == "13431979"

    def test_both_structures_coexist_without_duplicates(self) -> None:
        """同一页面同时含两种结构时不应重复计数。"""
        combined = NOTE_LIST_HTML + STANDALONE_LIST_HTML
        entries = parse_note_list(combined, "190597056")
        ids = [e.note_id for e in entries]
        assert len(ids) == len(set(ids))
        assert "624442255" in ids   # 内嵌结构
        assert "580950328" in ids   # 独立结构


# 一个房间同时挂多个公告栏（首页就是如此）
MULTI_BULLETIN_HTML = """
<html><head><title>兔子山的小站</title></head><body>
<div id="content"><div class="main">
  <div class="mod" id="bulletin-16095492">
    <div class="hd"><h2><span>索引①</span></h2></div>
    <div class="bd"><div class="bulletin-content" id="link-report" data-id="16095492">聲之形分组内容</div></div>
  </div>
  <div class="mod" id="bulletin-17754656">
    <div class="hd"><h2><span>索引②</span></h2></div>
    <div class="bd"><div class="bulletin-content" id="link-report" data-id="17754656">轻音与玉子分组内容</div></div>
  </div>
  <div class="mod" id="bulletin-13430830">
    <div class="hd"><h2><span>About PPK</span></h2></div>
    <div class="bd"><div class="bulletin-content" id="link-report" data-id="13430830">山田尚子简介</div></div>
  </div>
</div></div></body></html>
"""


class TestMultipleBulletinsInOneRoom:
    """一个房间可能有多个公告栏，必须按 #bulletin-{id} 精确读取。"""

    def test_each_bulletin_reads_its_own_container(self) -> None:
        first = parse_bulletin(MULTI_BULLETIN_HTML, "16095492", "https://x/")
        second = parse_bulletin(MULTI_BULLETIN_HTML, "17754656", "https://x/")
        third = parse_bulletin(MULTI_BULLETIN_HTML, "13430830", "https://x/")
        assert "聲之形分组内容" in first.content_html
        assert "轻音与玉子分组内容" in second.content_html
        assert "山田尚子简介" in third.content_html

    def test_titles_not_cross_contaminated(self) -> None:
        assert parse_bulletin(MULTI_BULLETIN_HTML, "16095492", "https://x/").title == "索引①"
        assert parse_bulletin(MULTI_BULLETIN_HTML, "17754656", "https://x/").title == "索引②"
        assert parse_bulletin(MULTI_BULLETIN_HTML, "13430830", "https://x/").title == "About PPK"

    def test_missing_container_without_other_report_is_unavailable(self) -> None:
        bulletin = parse_bulletin("<html><body><p>没有公告</p></body></html>", "999", "https://x/")
        assert bulletin.status.availability == "unavailable"

    def test_missing_container_does_not_take_sibling_bulletin(self) -> None:
        bulletin = parse_bulletin(MULTI_BULLETIN_HTML, "99999999", "https://x/")
        assert bulletin.content_html == ""
        assert bulletin.status.availability == "unavailable"
        assert bulletin.status.retryable
