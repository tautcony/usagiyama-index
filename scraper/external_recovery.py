"""Recover external articles through canonical URLs, HTTP and public snapshots.

Keep the fetched URL separate from the original article URL. Never accept a
password form, site index or unrelated new article as a successful recovery.
"""
from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup

from .config import Config
from .external_articles import _select_body, _strip_site_extras, article_minimum_text, detect_capture_access_failure
from .http_client import CachedResponse, Fetcher, decode_html
from .link_policy import classify_external_link


def cached_short_destinations(cfg: Config) -> dict[str, dict[str, str]]:
    """Recover explicit expanded hrefs retained in the original source HTML.

    Douban renders a short URL in the title while preserving its destination
    in href. Reject conflicting evidence rather than guessing from post text.
    """
    evidence: dict[str, dict[str, dict[str, str]]] = {}
    for path in (cfg.cache_dir / 'site.douban.com').glob('*.body'):
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if b'douc.cc/' not in raw and b'dou.bz/' not in raw:
            continue
        soup = BeautifulSoup(decode_html(raw, ''), 'lxml')
        for anchor in soup.find_all('a', href=True, title=True):
            match = re.fullmatch(r'https?://(?:douc\.cc|dou\.bz)/([a-zA-Z0-9]+)', str(anchor['title']))
            target = str(anchor['href'])
            parsed = urlparse(target)
            if not match or parsed.scheme not in {'http', 'https'} or not parsed.hostname:
                continue
            if parsed.hostname in {'douc.cc', 'dou.bz', 't.cn', 'www.douban.com', 'douban.com'}:
                continue
            evidence.setdefault(match.group(1), {})[target] = {
                'url': target, 'evidencePath': str(path.relative_to(cfg.data_dir.parent)),
            }
    return {code: next(iter(targets.values())) for code, targets in evidence.items() if len(targets) == 1}


def recovery_urls(url: str) -> list[str]:
    """Deterministic publisher migrations that retain the article identifier."""
    p = urlparse(url)
    host = (p.hostname or '').lower()
    candidates: list[str] = []
    query = [(key, value) for key, value in parse_qsl(p.query, keep_blank_values=True)
             if not key.lower().startswith('utm_') and key.lower() not in {'afid', 'kid'}]
    if len(query) != len(parse_qsl(p.query, keep_blank_values=True)):
        candidates.append(urlunparse(p._replace(scheme='https', query=urlencode(query))))
    fc2 = re.fullmatch(r'(.+)\.blog\d+\.fc2\.com', host)
    if fc2:
        candidates.append(urlunparse(p._replace(scheme='https', netloc=fc2.group(1) + '.blog.fc2.com')))
    # The full Los Endos URL appears elsewhere in this archive; the album
    # caption truncated the timestamp. These are exact corrections, not a
    # general license to guess missing article IDs.
    if url == 'http://d.hatena.ne.jp/los_endos/20131201/13859':
        candidates.append('http://d.hatena.ne.jp/los_endos/20131201/1385905981')
    if host == 'tamakolovestory.com' and p.path.startswith('/special/interview/今回は「映画」'):
        candidates.append('https://tamakolovestory.com/special/interview/')
    if host == 'dou.bz' and '，' in p.path:
        code = p.path.split('，', 1)[0]
        if re.fullmatch(r'/[a-zA-Z0-9]+', code):
            candidates.append('https://douc.cc' + code)
    if host == 'mantan-web.jp' and re.fullmatch(r'/\d{4}/\d{2}/\d{2}/[^/]+\.html', p.path):
        candidates.append('https://mantan-web.jp/article/' + p.path.rsplit('/', 1)[1])
    if host in {'www.animate.tv', 'animate.tv', 'www.animatetv.jp', 'animatetv.jp'}:
        candidates.append(urlunparse(p._replace(scheme='https', netloc='www.animatetimes.com')))
    if host == 'www.tbs.co.jp' and p.path.endswith('/news/news.html') and re.fullmatch(r'\d{12}', p.fragment):
        month = p.fragment[2:6]
        candidates.append(urlunparse(p._replace(scheme='https', path=p.path[:-9] + f'news{month}.html')))
    if host == 'news.walkerplus.com':
        candidates.append(urlunparse(p._replace(scheme='https', netloc='www.walkerplus.com')))
    if host.endswith('.blogspot.jp'):
        candidates.append(urlunparse(p._replace(scheme='https', netloc=host[:-3] + '.com')))
    if host == 'dou.bz' and re.fullmatch(r'/[a-zA-Z0-9]+', p.path):
        candidates.append('https://douc.cc' + p.path)
    if host.endswith('excite.co.jp'):
        match = re.search(r'/(?:News|news)/(\w+)/(\d{8}/)?E(\d+)\.html', p.path)
        if match:
            category, date, article_id = match.groups()
            if date:
                candidates.append(f'https://www.excite.co.jp/news/article/{category.capitalize()}_{date.rstrip("/")}_{article_id}/')
            candidates.append(f'https://www.excite.co.jp/news/article/E{article_id}/')
    if p.scheme == 'http':
        candidates.append(urlunparse(p._replace(scheme='https')))
    candidates.append(url)
    return list(dict.fromkeys(candidates))


def external_image_variants(url: str, *, timestamp: str = '', archive_enabled: bool = False) -> list[str]:
    parsed = urlparse(url)
    canonical = url
    if (parsed.scheme, parsed.port) in {('http', 80), ('https', 443)}:
        canonical = urlunparse(parsed._replace(netloc=parsed.hostname or parsed.netloc))
    originals = list(dict.fromkeys([url, canonical]))
    if parsed.query and set(key for key, _ in parse_qsl(parsed.query)) <= {'d'}:
        originals.append(urlunparse(urlparse(canonical)._replace(query='')))
    direct = []
    for original in originals:
        p = urlparse(original)
        if p.scheme == 'http' and p.port in {None, 80}:
            direct.append(urlunparse(p._replace(scheme='https', netloc=p.hostname or p.netloc)))
        direct.append(original)
    replay = [f'https://web.archive.org/web/{timestamp or "20180101000000"}im_/{original}'
              for original in originals] if timestamp or archive_enabled else []
    return list(dict.fromkeys([*replay, *direct] if timestamp else [*direct, *replay]))


def usable_article(response: CachedResponse) -> bool:
    if not response.ok or not response.content or response.size > 5 * 1024 * 1024:
        return False
    if response.content_type and 'html' not in response.content_type.lower():
        return False
    p = urlparse(response.final_url or response.url)
    host = (p.hostname or '').lower()
    if detect_capture_access_failure(response.content, response.content_type, host):
        return False
    soup = BeautifulSoup(decode_html(response.content, response.content_type), 'lxml')
    body, adapter = _select_body(soup, host, p.path, p.fragment)
    if body is None:
        return False
    _strip_site_extras(body, host)
    text = body.get_text(' ', strip=True)
    minimum = article_minimum_text(adapter)
    return len(text) >= minimum and not re.search(r'(?i)domain (?:has )?expired|404 not found|page not found', text[:500])


@dataclass
class RecoveryResult:
    response: CachedResponse | None = None
    method: str = ''
    attempts: list[dict] = field(default_factory=list)
    snapshot: dict | None = None
    republication: dict | None = None

    def metadata(self) -> dict:
        result = {'recoveryMethod': self.method, 'recoveryAttempts': self.attempts}
        if self.response:
            result['captureUrl'] = self.response.url
        if self.snapshot:
            result['snapshot'] = self.snapshot
        if self.republication:
            result['republication'] = self.republication
        return result


class ExternalRecovery:
    """One isolated transport session per target; share the request rate limiter."""
    def __init__(self, cfg: Config, primary, *, http=None, short_destinations=None):
        self.cfg = cfg
        self.primary = primary
        self.http = http
        self.owns_http = http is None
        self.source = http
        self.short_destinations = short_destinations or {}

    def _http(self):
        if self.http is None:
            self.http = Fetcher(dataclasses.replace(self.cfg, max_retries=min(1, self.cfg.max_retries)),
                                limiter=getattr(self.primary, '_limiter', None))
        return self.http

    def _source(self):
        if self.source is None:
            self.source = Fetcher(dataclasses.replace(self.cfg, max_retries=min(1, self.cfg.max_retries)),
                                  limiter=getattr(self.primary, '_limiter', None))
        return self.source

    def fetch(self, url: str, *, action: str = 'fetch_article', force: bool = False, references=None) -> RecoveryResult:
        result = RecoveryResult()
        last_response = None
        candidates = recovery_urls(url)
        parsed_url = urlparse(url)
        # This moving ranking index was cited for Tamako's second consecutive
        # first place (May 3–4, 2014). The publisher retains that exact weekly
        # page. Do not apply it to references to other weeks or newer rankings.
        if parsed_url.hostname == 'www.kogyotsushin.com' and parsed_url.path == '/archives/minitheater/' and any(
            ref.get('label') == '『たまこラブストーリー』ミニシアターランキングで２週連続１位！' for ref in references or []
        ):
            weekly = 'https://www.kogyotsushin.com/archives/minitheater/201405/04000000.php'
            candidates.insert(0, weekly)
            result.attempts.append({'url': weekly, 'transport': 'reference_context',
                                    'evidence': '原引用：玉子爱情故事连续两周第一；出版方 2014-05-03～04 周榜', 'accepted': True})
        evidence = self.short_destinations.get(parsed_url.path.strip('/')) if parsed_url.hostname in {'douc.cc', 'dou.bz'} else None
        if action == 'resolve' and evidence and not self.cfg.offline:
            destination = evidence['url']
            result.attempts.append({'transport': 'cached_source_link', **evidence, 'accepted': True})
            if classify_external_link(destination)['action'] not in {'fetch_article', 'resolve'}:
                result.response = CachedResponse(url, 200, b'', final_url=destination, from_cache=True)
                result.method = 'cached_source_link'
                return result
            candidates.insert(0, destination)
        # Offline reads never create new recovery state or query an archive.
        for candidate in candidates:
            source = self._source() if isinstance(self.primary, Fetcher) and not self.cfg.offline else self.primary
            transports = [('primary', source)]
            if not self.cfg.offline and not isinstance(self.primary, Fetcher):
                transports.append(('http', None))
            for name, transport in transports:
                try:
                    transport = transport or self._source()
                    response = transport.fetch(candidate, force=force)
                    last_response = response
                    final = response.final_url or candidate
                    resolved = action == 'resolve' and final != candidate and (urlparse(final).hostname or '') not in {'douc.cc', 'dou.bz', 't.cn'}
                    valid = resolved or usable_article(response)
                    result.attempts.append({'url': candidate, 'transport': name,
                                            'httpStatus': response.status, 'accepted': valid})
                    if valid:
                        result.response = response
                        result.method = 'canonical_url' if candidate != url else name
                        return result
                except AssertionError:
                    raise
                except Exception as exc:
                    result.attempts.append({'url': candidate, 'transport': name,
                                            'error': f'{type(exc).__name__}: {exc}'})
        if not self.cfg.offline and parsed_url.hostname == 'tower.jp' and parsed_url.path == '/store/news/2014/04/140404nanl_tamako':
            # The film's official announcement republishes all four campaign
            # details and explicitly cites this exact dead Tower Records URL.
            mirror = 'https://tamakolovestory.com/news/?id=14'
            try:
                response = self._source().fetch(mirror)
                source = BeautifulSoup(response.text, 'lxml')
                cited = any(urlparse(str(a.get('href', ''))).hostname == 'tower.jp' and
                            urlparse(str(a.get('href', ''))).path == parsed_url.path
                            for a in source.find_all('a', href=True))
                valid = cited and usable_article(response)
                result.attempts.append({'url': mirror, 'transport': 'official_republication', 'accepted': valid})
                if valid:
                    result.response = response
                    result.method = 'official_republication'
                    result.republication = {'url': mirror, 'label': '玉子爱情故事电影官网',
                                             'evidence': '官方转载包含四项活动详情，并明确引用原 Tower Records 地址'}
                    return result
            except Exception as exc:
                result.attempts.append({'url': mirror, 'transport': 'official_republication', 'error': str(exc)})
        if self.cfg.archive_enabled and not self.cfg.offline:
            archive_candidates = list(dict.fromkeys([url, *candidates]))
            if last_response and last_response.final_url and last_response.final_url not in archive_candidates:
                final = urlparse(last_response.final_url)
                if final.path and 'login' not in final.path and final.hostname not in {'douban.com', 'www.douban.com'}:
                    archive_candidates.append(last_response.final_url)
            parsed = urlparse(url)
            if parsed.hostname in {'douc.cc', 'dou.bz'}:
                code = parsed.path.split('，', 1)[0]
                if re.fullmatch(r'/[a-zA-Z0-9]+', code):
                    archive_candidates.extend(['http://dou.bz' + code, 'http://douc.cc' + code])
            for candidate in dict.fromkeys(archive_candidates):
                try:
                    endpoint = 'https://archive.org/wayback/available?' + urlencode({'url': candidate})
                    availability = self._http().fetch(endpoint, force=force)
                    if not availability.ok:
                        result.attempts.append({'url': endpoint, 'httpStatus': availability.status})
                        continue
                    closest = json.loads(availability.text).get('archived_snapshots', {}).get('closest', {})
                    if not closest.get('available') or str(closest.get('status')) not in ({'200', '301', '302', '307', '308'} if action == 'resolve' else {'200'}):
                        result.attempts.append({'url': endpoint, 'result': 'no_snapshot'})
                        continue
                    timestamp = str(closest['timestamp'])
                    replay = str(closest['url'])
                    m = re.fullmatch(r'https?://web\.archive\.org/web/(\d{14})/(https?://.+)', replay)
                    if not m or not re.fullmatch(r'\d{14}', timestamp):
                        continue
                    original = m.group(2)
                    raw_url = f'https://web.archive.org/web/{timestamp}id_/{original}'
                    if self._replay(result, raw_url, candidate, action):
                        return result
                except AssertionError:
                    raise
                except Exception as exc:
                    result.attempts.append({'url': candidate, 'transport': 'wayback',
                                            'error': f'{type(exc).__name__}: {exc}'})
            # The availability index can report no snapshot while the replay
            # service still finds one (observed for Kyoto IDs 1042/1100 and
            # DDnavi 193933). Ask for a nearest capture once and require the
            # returned real timestamp plus a valid article body.
            replay_candidates = list(dict.fromkeys([url, candidates[0]]))
            if parsed.hostname in {'douc.cc', 'dou.bz'}:
                replay_candidates = [c for c in archive_candidates if c.startswith('http://dou.bz/')]
            date = re.search(r'/(20\d{2})/?(\d{2})/?(\d{2})(?:[/_]|\d)', parsed.path)
            seed = ''.join(date.groups()) + '000000' if date else '20180101000000'
            # A later snapshot may be a parked domain. Also try the earliest
            # available capture, still requiring the publisher's article body.
            for timestamp in dict.fromkeys([seed, '20000101000000']):
                for candidate in replay_candidates:
                    raw_url = f'https://web.archive.org/web/{timestamp}id_/' + candidate
                    try:
                        if self._replay(result, raw_url, candidate, action):
                            return result
                    except AssertionError:
                        raise
                    except Exception as exc:
                        result.attempts.append({'url': raw_url, 'transport': 'wayback_replay',
                                                'error': f'{type(exc).__name__}: {exc}'})
        result.response = last_response
        result.method = 'exhausted'
        return result

    def _replay(self, result: RecoveryResult, raw_url: str, candidate: str, action: str) -> bool:
        raw = self._http().fetch(raw_url)
        replay_match = re.fullmatch(
            r'https?://web\.archive\.org/web/(\d{14})[a-z_]*?/(https?://.+)',
            raw.final_url or raw_url,
        )
        if not replay_match:
            result.attempts.append({'url': raw_url, 'httpStatus': raw.status, 'accepted': False})
            return False
        timestamp, original = replay_match.groups()
        replay = f'https://web.archive.org/web/{timestamp}/{original}'
        if urlparse(candidate).fragment and not urlparse(original).fragment:
            original = urlunparse(urlparse(original)._replace(fragment=urlparse(candidate).fragment))
        response = dataclasses.replace(raw, final_url=original)
        resolved = action == 'resolve' and original != candidate and (urlparse(original).hostname or '') not in {'douc.cc', 'dou.bz', 't.cn'}
        valid = resolved or usable_article(response)
        result.attempts.append({'url': raw_url, 'httpStatus': raw.status, 'accepted': valid})
        if valid:
            result.response = response
            result.method = 'wayback'
            result.snapshot = {'timestamp': timestamp, 'url': original, 'waybackUrl': replay,
                               'date': f'{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}'}
        return valid

    def close(self):
        if self.owns_http:
            for transport in (self.source, self.http):
                if transport is not None:
                    self.primary.stats.merge(transport.finalize())
                    transport.close()
