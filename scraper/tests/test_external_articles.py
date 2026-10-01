from __future__ import annotations

from scraper.external_articles import parse_capture


def _capture(tmp_path, html: str):
    raw = tmp_path / "page.html"
    raw.write_text(html, encoding="utf-8")
    return {
        "fetchStatus": "fetched",
        "rawResponse": str(raw),
        "finalUrl": "https://cycle-junrei.hatenablog.jp/entry/1",
        "contentType": "text/html; charset=utf-8",
    }


def test_hatenablog_extracts_entry_body_without_sidebar(tmp_path) -> None:
    html = """<html><body><div id="content">
      <article class="entry hentry"><header class="entry-header">标题日期</header>
        <div class="entry-content hatenablog-entry"><p>这是文章正文内容，包含足够长度来验证 Hatena Blog 正文适配规则有效。</p>
          <p>文章第二段。</p></div><footer class="entry-footer">作者与相关文章</footer>
      </article>
      <div class="hatena-module hatena-module-profile">プロフィール 作者简介</div>
      <div class="hatena-module hatena-module-recent-entries">最新記事 另一篇文章的内容</div>
    </div></body></html>"""
    article = parse_capture("https://cycle-junrei.hatenablog.jp/entry/1", _capture(tmp_path, html), tmp_path)

    assert article is not None
    assert article.adapter == "hatenablog.jp"
    assert "文章正文内容" in article.content_html
    assert "プロフィール" not in article.content_html
    assert "最新記事" not in article.content_html
    assert "作者与相关文章" not in article.content_html


def test_hatenablog_does_not_fall_back_to_site_shell_when_entry_is_missing(tmp_path) -> None:
    html = """<html><body><div id="content">
      <article class="entry no-entry sleeping-ads"><div class="entry-content">この広告は、90日以上更新していないブログに表示しています。</div></article>
      <div class="hatena-module hatena-module-profile">プロフィール とても長いプロフィール説明文。記事本文ではない情報です。</div>
      <div class="hatena-module hatena-module-recent-entries">最新記事 とても長い関連記事一覧。記事本文ではない情報です。</div>
    </div></body></html>"""

    assert parse_capture(
        "https://cycle-junrei.hatenablog.jp/entry/1", _capture(tmp_path, html), tmp_path
    ) is None


def test_tbs_selects_exact_news_fragment_and_never_month_index(tmp_path):
    html = '<div class="news_box" id="other"><h3>Wrong</h3>' + '无关' * 100 + '</div><a id="201401171800"></a><div class="news_title"><h3>原新闻</h3><div class="news_body">' + '原文' * 100 + '</div></div>'
    capture = _capture(tmp_path, html)
    url = 'https://www.tbs.co.jp/anime/k-on/k-on_tv/news/news1401.html#201401171800'
    capture['finalUrl'] = url
    result = parse_capture(url, capture, tmp_path)
    assert result.title == '原新闻'
    assert 'Wrong' not in result.content_html
    capture['finalUrl'] = url.split('#')[0]
    assert parse_capture(url, capture, tmp_path) is None


def test_widgets_filtered_before_local_rewrite_and_from_download_queue(tmp_path):
    from scraper.external_articles import extract_image_sources
    html = '<article>' + '正文' * 100 + '''
      <img src="photo.jpg" width="16" height="16" alt="小幅插画">
      <img src="emoji.gif" class="emoji" width="16" height="16" alt="笑">
      <div class="fc2button-clap"><img src="//static.fc2.com/image/clap/number/green/0.gif"></div>
      <img src="https://b.hatena.ne.jp/entry/image/http://example.com/article.html">
      <img src="https://media.fc2.com/counter_img.php?id=595">
      <img src="pixel.php" width="1" height="1">
      <img src="data:image/gif;base64,placeholder" data-src="1x1.png" alt="">
      <span class="thumbnail_link"><img class="thumbnail" src="main.jpg"><img class="thumbnail_exp" src="expansion.jpg"></span>
      <div class="main_share"><img src="share.png"></div>
      <blockquote class="twitter-tweet"><span class="avatar"><img src="avatar.jpg"></span><p>引用文字</p><img src="tweet-photo.jpg"></blockquote>
    </article>'''
    capture = _capture(tmp_path, html)
    url = 'https://example.com/article.html'
    capture['finalUrl'] = url
    capture['archivedImages'] = {'https://b.hatena.ne.jp/entry/image/http://example.com/article.html': '/media/external-articles/example/counter.gif'}
    sources = extract_image_sources(url, capture, tmp_path)
    assert sources == [f'https://example.com/{name}' for name in ('photo.jpg', 'emoji.gif', 'main.jpg', 'tweet-photo.jpg')]
    article = parse_capture(url, capture, tmp_path)
    assert article is not None
    assert 'counter.gif' not in article.content_html
    assert '引用文字' in article.content_html
    assert 'emoji.gif' in article.content_html


def test_short_cocolog_article_uses_same_image_threshold(tmp_path):
    from scraper.external_articles import extract_image_sources
    capture = _capture(tmp_path, '<div class="entry-content">' + '正文' * 12 + '<img src="photo.jpg"></div>')
    url = 'https://example.cocolog-nifty.com/post.html'
    capture['finalUrl'] = url
    assert parse_capture(url, capture, tmp_path) is not None
    assert extract_image_sources(url, capture, tmp_path) == ['https://example.cocolog-nifty.com/photo.jpg']
