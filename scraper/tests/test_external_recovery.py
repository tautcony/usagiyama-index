from __future__ import annotations

import dataclasses
import json

from scraper.external_recovery import ExternalRecovery, cached_short_destinations, recovery_urls
from scraper.http_client import CachedResponse, FetchStats


class FakeFetcher:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.stats = FetchStats()

    def fetch(self, url, **kw):
        self.calls.append((url, kw))
        result = self.responses[url]
        if isinstance(result, Exception):
            raise result
        return result


def article(url, text='本文' * 100):
    return CachedResponse(url, 200, f'<article>{text}</article>'.encode(),
                          'text/html; charset=utf-8', final_url=url)


def test_migrations_retain_identifier_and_never_map_reused_kyoto_ids():
    assert recovery_urls('http://mantan-web.jp/2015/05/30/20150529dog00m200066000c.html')[0] == 'https://mantan-web.jp/article/20150529dog00m200066000c.html'
    assert recovery_urls('http://www.animate.tv/news/details.php?id=1401535119&p=1')[0] == 'https://www.animatetimes.com/news/details.php?id=1401535119&p=1'
    assert all('/diary/' not in u for u in recovery_urls('http://www.kyotoanimation.co.jp/staff/anibaka/blog/?p=1790'))


def test_navigation_failure_falls_back_to_http(cfg):
    url = 'https://example.org/article/1'
    browser = FakeFetcher({url: RuntimeError('navigation failed')})
    http = FakeFetcher({url: article(url)})
    result = ExternalRecovery(cfg, browser, http=http).fetch(url)
    assert result.method == 'http'
    assert result.response.content == article(url).content
    assert len(result.attempts) == 2


def test_error_page_200_is_not_success(cfg):
    url = 'https://example.org/article/1'
    browser = FakeFetcher({url: CachedResponse(url, 200, b'<main>Not found</main>', 'text/html')})
    result = ExternalRecovery(cfg, browser, http=FakeFetcher({})).fetch(url)
    assert result.method == 'exhausted'
    assert result.attempts[0]['accepted'] is False


def test_public_snapshot_keeps_original_base_and_separate_cache_url(cfg):
    from urllib.parse import urlencode
    cfg = dataclasses.replace(cfg, archive_enabled=True)
    url = 'https://ameblo.jp/test/entry-1.html'
    replay = 'https://web.archive.org/web/20180120125832/' + url
    raw = replay.replace('20180120125832/', '20180120125832id_/')
    endpoint = 'https://archive.org/wayback/available?' + urlencode({'url': url})
    primary = FakeFetcher({url: CachedResponse(url, 404, b'gone', 'text/html')})
    http = FakeFetcher({
        endpoint: CachedResponse(endpoint, 200, json.dumps({'archived_snapshots': {'closest': {
            'available': True, 'status': '200', 'url': replay, 'timestamp': '20180120125832'
        }}}).encode(), 'application/json'),
        raw: CachedResponse(raw, 200, ('<div id="entryBody">' + '原文' * 100 + '</div>').encode(), 'text/html', final_url=raw),
    })
    result = ExternalRecovery(cfg, primary, http=http).fetch(url)
    assert result.method == 'wayback'
    assert result.response.url == raw
    assert result.response.final_url == url
    assert result.snapshot['date'] == '2018-01-20'


def test_offline_does_not_query_archive_or_http(cfg):
    cfg = dataclasses.replace(cfg, offline=True, archive_enabled=True)
    url = 'https://example.org/article/1'
    primary = FakeFetcher({url: CachedResponse(url, 404, b'gone')})
    http = FakeFetcher({})
    result = ExternalRecovery(cfg, primary, http=http).fetch(url, force=True)
    assert result.method == 'exhausted'
    assert not http.calls


def test_metadata_redirect_404_still_resolves_short_link(cfg):
    url = 'https://douc.cc/abc'
    final = 'https://site.douban.com/211330/widget/photos/1/photo/2/'
    primary = FakeFetcher({url: CachedResponse(url, 404, b'gone', final_url=final)})
    result = ExternalRecovery(cfg, primary, http=FakeFetcher({})).fetch(url, action='resolve')
    assert result.method == 'primary'
    assert result.response.final_url == final


def test_cached_expanded_short_link_has_evidence_and_needs_no_network(cfg):
    source = cfg.cache_dir / 'site.douban.com' / 'source.body'
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text('<a title="https://douc.cc/abc" href="https://www.youtube.com/watch?v=real">abc</a>')
    evidence = cached_short_destinations(cfg)
    primary = FakeFetcher({})
    result = ExternalRecovery(cfg, primary, short_destinations=evidence).fetch('https://dou.bz/abc', action='resolve')
    assert result.method == 'cached_source_link'
    assert result.response.final_url == 'https://www.youtube.com/watch?v=real'
    assert result.attempts[0]['evidencePath'].endswith('source.body')
    assert not primary.calls
    source.write_text('<a title="https://douc.cc/abc" href="https://twitter.com/other">abc</a>')
    (source.parent / 'conflict.body').write_text('<a title="https://dou.bz/abc" href="https://youtube.com/another">abc</a>')
    assert 'abc' not in cached_short_destinations(cfg)


def test_exact_truncated_link_corrections_do_not_guess_other_ids():
    assert recovery_urls('http://d.hatena.ne.jp/los_endos/20131201/13859')[0].endswith('/1385905981')
    assert recovery_urls('http://d.hatena.ne.jp/los_endos/20131201/13858')[0].endswith('/13858')
    assert recovery_urls('http://tamakolovestory.com/special/interview/今回は「映画」ということをだいぶ意識')[0] == 'https://tamakolovestory.com/special/interview/'


def test_publisher_chrome_is_not_accepted_as_body(cfg):
    url = 'https://ameblo.jp/test/entry-1.html'
    response = CachedResponse(url, 200, ('<div id="entryBody"><nav>' + '导航' * 100 + '</nav></div>').encode(), 'text/html', final_url=url)
    primary = FakeFetcher({url: response})
    result = ExternalRecovery(cfg, primary, http=FakeFetcher({})).fetch(url)
    assert result.method == 'exhausted'


def test_stage_persists_actual_recovery_cache_path(cfg, monkeypatch):
    import hashlib
    from scraper import cli
    from scraper.http_client import cache_paths
    from scraper.util import atomic_write_bytes
    url = 'https://example.org/article/1'
    raw_url = 'https://web.archive.org/web/20180120125832id_/' + url
    response = dataclasses.replace(article(raw_url), final_url=url)
    fake = FakeFetcher({url: response})
    body, _ = cache_paths(cfg, raw_url)
    atomic_write_bytes(body, response.content)
    monkeypatch.setattr(cli, 'scan_external_links', lambda _: {
        url: {'action': 'fetch_article', 'references': [], 'domain': 'example.org'}
    })
    monkeypatch.setattr(cli, 'ExternalRecovery', lambda config, primary, **kw: ExternalRecovery(config, fake, http=fake, **kw))
    ctx = cli.SyncContext(cfg)
    try:
        cli.stage_external(ctx, show_progress=False, pages_only=True)
        capture = ctx.external_captures[url]
        assert capture['fetchStatus'] == 'fetched'
        assert (cfg.data_dir.parent / capture['rawResponse']) == body
        assert capture['captureUrl'] == raw_url
        key = 'external:' + hashlib.sha256(url.encode()).hexdigest()[:20]
        assert ctx.progress.is_done(key)
    finally:
        ctx.close()


def test_stage_does_not_complete_http_200_error_page(cfg, monkeypatch):
    from scraper import cli
    url = 'https://example.org/article/1'
    fake = FakeFetcher({url: CachedResponse(url, 200, b'<main>error</main>', 'text/html')})
    monkeypatch.setattr(cli, 'scan_external_links', lambda _: {
        url: {'action': 'fetch_article', 'references': [], 'domain': 'example.org'}
    })
    monkeypatch.setattr(cli, 'ExternalRecovery', lambda config, primary, **kw: ExternalRecovery(config, fake, http=fake, **kw))
    ctx = cli.SyncContext(cfg)
    try:
        cli.stage_external(ctx, show_progress=False, pages_only=True)
        assert ctx.external_captures[url]['fetchStatus'] == 'unparsed'
        assert ctx.progress.unavailable()
    finally:
        ctx.close()


def test_decode_legacy_japanese_meta_charset_and_browser_header():
    from scraper.http_client import decode_html
    html = '<meta http-equiv="Content-Type" content="text/html; charset=iso-2022-jp"><p>けいおん</p>'
    assert 'けいおん' in decode_html(html.encode('iso-2022-jp'), 'text/html')
    assert 'けいおん' in decode_html(html.encode(), 'text/html; charset=utf-8')
    sjis = '<meta charset="Shift_JIS"><p>山田尚子</p>'
    assert '山田尚子' in decode_html(sjis.encode('shift_jis'), 'text/html')


def test_missing_availability_index_uses_actual_replay_timestamp(cfg):
    from urllib.parse import urlencode
    cfg = dataclasses.replace(cfg, archive_enabled=True)
    url = 'https://example.org/article/1'
    seed = 'https://web.archive.org/web/20180101000000id_/' + url
    actual = 'https://web.archive.org/web/20190720000142id_/' + url
    endpoint = 'https://archive.org/wayback/available?' + urlencode({'url': url})
    primary = FakeFetcher({url: CachedResponse(url, 404, b'gone')})
    http = FakeFetcher({endpoint: CachedResponse(endpoint, 200, b'{"archived_snapshots": {}}'),
                        seed: dataclasses.replace(article(seed), final_url=actual)})
    result = ExternalRecovery(cfg, primary, http=http).fetch(url)
    assert result.method == 'wayback'
    assert result.snapshot['timestamp'] == '20190720000142'
    assert result.snapshot['date'] == '2019-07-20'
    assert result.response.url == seed
    assert result.response.final_url == url


def test_official_republication_requires_explicit_original_citation(cfg):
    url = 'https://tower.jp/store/news/2014/04/140404nanl_tamako'
    mirror = 'https://tamakolovestory.com/news/?id=14'
    primary = FakeFetcher({url: CachedResponse(url, 404, b'gone')})
    body = '<div id="newsIndexData">' + '活动说明' * 100 + '<a href="http://tower.jp/store/news/2014/04/140404nanl_tamako">详情</a></div>'
    http = FakeFetcher({mirror: CachedResponse(mirror, 200, body.encode(), 'text/html; charset=utf-8', final_url=mirror)})
    result = ExternalRecovery(cfg, primary, http=http).fetch(url)
    assert result.method == 'official_republication'
    assert result.republication['url'] == mirror
    http.responses[mirror] = dataclasses.replace(http.responses[mirror], content=body.replace('140404nanl_tamako','unrelated').encode())
    assert ExternalRecovery(cfg, primary, http=http).fetch(url).method == 'exhausted'


def test_image_variants_normalize_default_port_and_keep_snapshot_first():
    from scraper.external_recovery import external_image_variants
    url = 'http://images.example.org:80/image.jpg?d=a1'
    variants = external_image_variants(url, timestamp='20160905051313')
    assert variants[0] == 'https://web.archive.org/web/20160905051313im_/' + url
    assert 'https://images.example.org/image.jpg?d=a1' in variants
    assert 'https://web.archive.org/web/20160905051313im_/http://images.example.org/image.jpg' in variants
    assert not any(v.startswith('https://images.example.org:80/') for v in variants)


def test_moving_ranking_is_recovered_only_for_verified_reference_week(cfg):
    url = 'https://www.kogyotsushin.com/archives/minitheater/'
    weekly = 'https://www.kogyotsushin.com/archives/minitheater/201405/04000000.php'
    primary = FakeFetcher({weekly: CachedResponse(weekly, 200, ('<div id="main">' + 'たまこラブストーリー ' * 20 + '</div>').encode(), 'text/html; charset=utf-8', final_url=weekly)})
    result = ExternalRecovery(cfg, primary, http=FakeFetcher({})).fetch(url, references=[{'label':'『たまこラブストーリー』ミニシアターランキングで２週連続１位！'}])
    assert result.response.final_url == weekly
    assert result.attempts[0]['transport'] == 'reference_context'
    primary.calls.clear()
    ExternalRecovery(cfg, primary, http=FakeFetcher({})).fetch(url, references=[{'label':'新作の週間ランキング'}])
    assert weekly not in [u for u, _ in primary.calls]
