from scraper.external_media import reconcile_external_media
from scraper.media import MediaArchive

GIF = b'GIF89a' + b'\x00' * 40


def test_completed_images_healed_and_widgets_removed_idempotently(cfg):
    cfg.root.mkdir(parents=True, exist_ok=True)
    raw = cfg.root / 'page.html'
    raw.write_text('<article>' + '正文' * 100 + '<img src="image.php"><img src="https://b.hatena.ne.jp/entry/image/article.html"></article>')
    directory = cfg.media_dir / 'external-articles' / 'example' / 'article'
    directory.mkdir(parents=True)
    wrong = directory / 'image.php'
    wrong.write_bytes(GIF)
    counter = directory / 'counter.gif'
    counter.write_bytes(GIF)
    unrelated = directory / 'unrelated.gif'
    unrelated.write_bytes(GIF)
    captures = {'https://example.com/post.html': {
        'fetchStatus': 'fetched', 'rawResponse': str(raw), 'finalUrl': 'https://example.com/post.html',
        'archivedImages': {'https://example.com/image.php': '/media/external-articles/example/article/image.php', 'https://b.hatena.ne.jp/entry/image/article.html': '/media/external-articles/example/article/counter.gif'},
        'imageFailures': {'https://b.hatena.ne.jp/entry/image/failed.html': '404'},
    }}
    media = MediaArchive(None, cfg=cfg)
    assert reconcile_external_media(captures, media, cfg.root) == {'filtered': 2, 'renamed': 1, 'deleted': 1}
    assert not wrong.exists() and wrong.with_suffix('.gif').read_bytes() == GIF
    assert not counter.exists() and unrelated.exists()
    assert captures['https://example.com/post.html']['archivedImages'] == {'https://example.com/image.php': '/media/external-articles/example/article/image.gif'}
    assert reconcile_external_media(captures, media, cfg.root) == {'filtered': 0, 'renamed': 0, 'deleted': 0}


def test_missing_raw_does_not_delete_assets_and_shared_file_is_preserved(cfg):
    raw = cfg.root / 'page.html'
    raw.write_text('<article>' + '正文' * 100 + '</article>')
    directory = cfg.media_dir / 'external-articles' / 'example'
    directory.mkdir(parents=True)
    shared = directory / 'shared.gif'
    shared.write_bytes(GIF)
    local = '/media/external-articles/example/shared.gif'
    captures = {
        'https://example.com/a': {'fetchStatus': 'fetched', 'rawResponse': str(raw), 'archivedImages': {'https://b.hatena.ne.jp/entry/image/a.html': local}},
        'https://example.com/b': {'fetchStatus': 'fetched', 'rawResponse': 'missing', 'archivedImages': {'https://example.com/photo': local}},
    }
    stats = reconcile_external_media(captures, MediaArchive(None, cfg=cfg), cfg.root)
    assert stats['filtered'] == 1 and stats['deleted'] == 0
    assert shared.exists()
    assert captures['https://example.com/b']['archivedImages']
