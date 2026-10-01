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
