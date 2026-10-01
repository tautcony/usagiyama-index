from __future__ import annotations

import json
from types import SimpleNamespace

from scraper.links import (
    record_resolved_destinations, resolved_destination, resolved_link_targets,
    scan_external_links,
)


def test_scan_deduplicates_one_source_line_and_ignores_fake_url(tmp_path, monkeypatch) -> None:
    source = tmp_path / "notes" / "1.md"
    source.parent.mkdir()
    source.write_text(
        "[source](http://ameblo.jp/example/entry-123.html) "
        "http://ameblo.jp/example/entry-123.html http://2017年3月31日\n",
        encoding="utf-8",
    )
    rendered = [{
        "path": str(source),
        "source": source.read_text(encoding="utf-8"),
        "html": (
            '<a href="http://ameblo.jp/example/entry-123.html">source</a> '
            '<a href="http://ameblo.jp/example/entry-123.html">source</a> '
            'http://ameblo.jp/example/entry-123.html http://2017年3月31日'
        ),
    }]
    monkeypatch.setattr(
        "scraper.links.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps(rendered)),
    )

    targets = scan_external_links(tmp_path)

    assert "http://2017年3月31日" not in targets
    assert len(targets["http://ameblo.jp/example/entry-123.html"]["references"]) == 1


def test_short_link_to_commerce_is_recorded_but_excluded_from_inventory() -> None:
    short = "https://douc.cc/35YXYm"
    wrapper = "https://www.douban.com/link2/?url=http%3A%2F%2Fwww.amazon.co.jp%2Fdp%2FB00K817716"
    actual = "http://www.amazon.co.jp/dp/B00K817716"
    reference = {"file": "broadcast/page/64.md", "line": 24, "label": short}
    targets = {short: {"action": "resolve", "references": [reference]}}

    assert resolved_destination(wrapper) == actual
    captures = {short: {
        "action": "resolve", "finalUrl": wrapper,
        "fetchStatus": "resolved_non_article",
    }}
    record_resolved_destinations(captures)
    result = resolved_link_targets(targets, captures)

    assert captures[short]["resolvedUrl"] == actual
    assert captures[short]["finalAction"] == "skip"
    assert short not in result
    assert actual not in result


def test_short_link_to_article_uses_target_domain_and_keeps_provenance() -> None:
    short = "https://douc.cc/article"
    wrapper = "https://www.douban.com/link2/?url=http%3A%2F%2Fameblo.jp%2Fexample%2Fentry-123.html"
    actual = "http://ameblo.jp/example/entry-123.html"
    reference = {"file": "notes/1.md", "line": 11, "label": short}
    captures = {short: {"action": "resolve", "finalUrl": wrapper}}
    record_resolved_destinations(captures)

    result = resolved_link_targets(
        {short: {"action": "resolve", "references": [reference]}}, captures
    )

    assert result[actual]["domain"] == "ameblo.jp"
    assert result[actual]["action"] == "fetch_article"
    assert result[actual]["resolvedFrom"] == [{"url": short, "references": [reference]}]


def test_failed_original_keeps_explicit_translation_alternative(cfg, monkeypatch):
    from scraper.links import emit_links_index
    url = 'https://example.com/article/lost'
    captures = {url: {'fetchStatus': 'http_error', 'localAlternatives': [
        {'kind': '已归档译文', 'title': '本地译文', 'route': '/notes/1'}
    ]}}
    monkeypatch.setattr('scraper.links.scan_external_links', lambda _: {
        url: {'requestedUrl': url, 'domain': 'example.com', 'action': 'fetch_article', 'category': '文章', 'references': []}
    })
    emit_links_index(cfg, captures=captures)
    text = (cfg.docs_dir / 'links/index.md').read_text()
    assert '原链接尚不可恢复' in text
    assert '[本地译文](/notes/1)' in text
    assert captures[url]['fetchStatus'] == 'http_error'
