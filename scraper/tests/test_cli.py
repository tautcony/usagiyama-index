"""``--speed`` 限速档位：档位表本身，以及「命令行参数 → 配置」的映射。

纯离线：只解析参数与替换 dataclass 字段，不构造任何传输对象。
"""

from __future__ import annotations

import pytest

from scraper import cli
from scraper.config import (
    CONFIG,
    DEFAULT_SPEED,
    ROBOTS_CRAWL_DELAY,
    SPEED_TIERS,
    Config,
    describe_delay,
    speed_tier,
    speed_tier_name,
)
from scraper.cli import _status_from_dict


def _config_for(monkeypatch: pytest.MonkeyPatch, *argv: str) -> Config:
    """按命令行参数生成配置；``ensure_dirs`` 换成空操作，测试不落盘。"""
    monkeypatch.setattr(cli, "ensure_dirs", lambda cfg: None)
    args = cli.build_parser().parse_args(list(argv))
    return cli._config_from_args(args)


class TestSpeedTiers:
    def test_three_tiers_match_the_documented_ranges(self) -> None:
        # 这三组秒数是给使用者看的承诺，改它们等于改预期。
        assert SPEED_TIERS == {
            "cautious": (5.0, 7.0),
            "normal": (2.0, 3.0),
            "fast": (1.0, 2.0),
        }

    def test_default_tier_is_not_faster_than_crawl_delay(self) -> None:
        # 不传参数时守住 robots.txt 的 Crawl-delay —— 快档是**主动选择**，
        # 不能是默认值。
        assert SPEED_TIERS[DEFAULT_SPEED][0] == ROBOTS_CRAWL_DELAY

    def test_lookup(self) -> None:
        assert speed_tier("normal") == (2.0, 3.0)

    def test_unknown_tier_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            speed_tier("ludicrous")

    @pytest.mark.parametrize("name", list(SPEED_TIERS))
    def test_describe_delay_names_the_tier(self, name: str) -> None:
        low, high = SPEED_TIERS[name]
        assert name in describe_delay(low, high)

    def test_describe_delay_labels_custom_intervals(self) -> None:
        # --delay 0.5 这类自定义间隔不属于任何一档，不能硬套名字。
        assert speed_tier_name(0.5, 2.5) is None
        assert "自定义" in describe_delay(0.5, 2.5)


class TestSpeedArg:
    @pytest.mark.parametrize("name", list(SPEED_TIERS))
    def test_each_tier_is_accepted(self, name: str) -> None:
        args = cli.build_parser().parse_args(["sync", "--speed", name])
        assert args.speed == name

    def test_unknown_tier_is_rejected_by_argparse(self) -> None:
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(["sync", "--speed", "ludicrous"])

    def test_speed_and_delay_are_mutually_exclusive(self) -> None:
        # 同时给出时该听谁的？不给猜的机会，argparse 直接报错。
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(["sync", "--speed", "fast", "--delay", "1"])

    def test_help_lists_every_tier(self) -> None:
        help_text = cli.build_parser().format_help()
        for name in SPEED_TIERS:
            assert name in help_text


class TestConfigFromArgs:
    def test_source_status_round_trip_includes_wayback_status(self) -> None:
        status = _status_from_dict({"availability": "archived", "waybackStatus": 200})
        assert status.wayback_status == 200

    def test_default_keeps_config_delays(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg = _config_for(monkeypatch, "sync")
        assert (cfg.delay_min, cfg.delay_max) == (CONFIG.delay_min, CONFIG.delay_max)

    @pytest.mark.parametrize("name", list(SPEED_TIERS))
    def test_speed_sets_both_bounds(self, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
        cfg = _config_for(monkeypatch, "sync", "--speed", name)
        assert (cfg.delay_min, cfg.delay_max) == SPEED_TIERS[name]

    def test_delay_wins_when_both_survive_argparse(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 参数分别写在子命令两侧时，主解析器与子解析器各管一段，
        # argparse 的互斥拦不住；那种写法下更具体的 --delay 生效。
        cfg = _config_for(monkeypatch, "--speed", "fast", "sync", "--delay", "0.5")
        assert (cfg.delay_min, cfg.delay_max) == (0.5, 2.5)

    def test_environment_transport_defaults_are_preserved(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import dataclasses
        configured = dataclasses.replace(CONFIG, archive_enabled=True, browser_enabled=False)
        monkeypatch.setattr(cli, "CONFIG", configured)
        monkeypatch.setattr(cli, "ensure_dirs", lambda cfg: None)
        cfg = cli._config_from_args(cli.build_parser().parse_args(["sync"]))
        assert cfg.archive_enabled is True
        assert cfg.browser_enabled is False

    def test_explicit_transport_flags_override_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import dataclasses
        configured = dataclasses.replace(CONFIG, archive_enabled=True, browser_enabled=False)
        monkeypatch.setattr(cli, "CONFIG", configured)
        monkeypatch.setattr(cli, "ensure_dirs", lambda cfg: None)
        cfg = cli._config_from_args(cli.build_parser().parse_args(
            ["sync", "--no-archive", "--browser"]
        ))
        assert cfg.archive_enabled is False
        assert cfg.browser_enabled is True

    @pytest.mark.parametrize("args", [["sync", "--limit", "-1"], ["sync", "--delay", "0"],
                                       ["sync", "--impersonate", "bogus"]])
    def test_invalid_common_values_rejected(self, args: list[str]) -> None:
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(args)


class TestRateWarning:
    def test_default_tier_needs_no_warning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg = _config_for(monkeypatch, "sync")
        assert cli.crawl_delay_warning(cfg) == ""
        assert "快于" not in cli.robots_notice(cfg)

    @pytest.mark.parametrize("name", ["normal", "fast"])
    def test_faster_tiers_are_called_out(
        self, monkeypatch: pytest.MonkeyPatch, name: str
    ) -> None:
        # 快档照跑，但不该无声地跑：提示里必须点出它快于 Crawl-delay。
        cfg = _config_for(monkeypatch, "sync", "--speed", name)
        warning = cli.crawl_delay_warning(cfg)
        assert "Crawl-delay" in warning
        assert name in warning
        assert warning in cli.robots_notice(cfg)
