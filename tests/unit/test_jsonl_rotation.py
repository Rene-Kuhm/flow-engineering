from __future__ import annotations

import os
import time as _time
from datetime import datetime
from pathlib import Path

import pytest

from flow_engineering._jsonl_rotation import (
    _resolve_jsonl_max_age_days,
    _resolve_jsonl_rotation_threshold_bytes,
    _rotate_jsonl_if_needed,
    _stamp_now,
)

DRIFT_BYTES = "FLOW_DRIFT_EVENT_LOG_MAX_BYTES"
DRIFT_AGE = "FLOW_DRIFT_EVENT_LOG_MAX_AGE_DAYS"
METRICS_BYTES = "FLOW_METRICS_LOG_MAX_BYTES"
METRICS_AGE = "FLOW_METRICS_LOG_MAX_AGE_DAYS"
DEFAULTS = {"default_max_bytes": 10 * 1024 * 1024, "default_max_age_days": 30}


def test_stamp_iso_format() -> None:
    stamp = _stamp_now()
    assert len(stamp) == 16
    assert stamp[8] == "T"
    assert stamp.endswith("Z")
    assert datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").tzinfo is None


@pytest.mark.parametrize(
    ("raw", "default", "expected"),
    [
        (None, 42, 42), ("", 42, 42), ("garbage", 42, 42),
        ("-1", 42, 0), ("0", 42, 0), ("1024", 42, 1024),
    ],
)
def test_resolve_threshold_bytes(
    monkeypatch: pytest.MonkeyPatch, raw: str | None, default: int, expected: int
) -> None:
    if raw is None:
        monkeypatch.delenv(DRIFT_BYTES, raising=False)
    else:
        monkeypatch.setenv(DRIFT_BYTES, raw)
    assert _resolve_jsonl_rotation_threshold_bytes(env=DRIFT_BYTES, default=default) == expected


@pytest.mark.parametrize(
    ("raw", "default", "expected"),
    [
        (None, 30, 30), ("", 30, 30), ("garbage", 30, 30),
        ("-7", 30, 0), ("0", 30, 0), ("7", 30, 7),
    ],
)
def test_resolve_max_age_days(
    monkeypatch: pytest.MonkeyPatch, raw: str | None, default: int, expected: int
) -> None:
    if raw is None:
        monkeypatch.delenv(DRIFT_AGE, raising=False)
    else:
        monkeypatch.setenv(DRIFT_AGE, raw)
    assert _resolve_jsonl_max_age_days(env=DRIFT_AGE, default=default) == expected


@pytest.mark.parametrize(
    ("scheme", "bytes_env", "age_env", "threshold", "content_size", "should_rotate"),
    [
        ("drift_events", DRIFT_BYTES, DRIFT_AGE, "1024", 2048, True),
        ("metrics", METRICS_BYTES, METRICS_AGE, "1", 2, True),
        ("metrics", METRICS_BYTES, METRICS_AGE, str(10 * 1024 * 1024), 10, False),
    ],
)
def test_size_threshold_rotation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scheme: str,
    bytes_env: str,
    age_env: str,
    threshold: str,
    content_size: int,
    should_rotate: bool,
) -> None:
    monkeypatch.setenv(bytes_env, threshold)
    monkeypatch.setenv(age_env, "30")
    path = tmp_path / f"{scheme}.jsonl"
    path.write_bytes(b"x" * content_size)
    _rotate_jsonl_if_needed(
        path, glob_prefix=scheme, max_bytes_env=bytes_env, max_age_days_env=age_env, **DEFAULTS
    )
    rotated = sorted(tmp_path.glob(f"{scheme}.*.jsonl"))
    if should_rotate:
        assert len(rotated) == 1
        assert not path.exists()
        stamp = rotated[0].name[len(scheme) + 1 : -6]
        assert len(stamp) == 16
        assert stamp[8] == "T"
        assert stamp.endswith("Z")
    else:
        assert path.exists()
        assert rotated == []


def test_missing_active_file_is_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "drift_events.jsonl"
    monkeypatch.setenv(DRIFT_BYTES, "1")
    monkeypatch.setenv(DRIFT_AGE, "30")
    assert _rotate_jsonl_if_needed(
        path, glob_prefix="drift_events", max_bytes_env=DRIFT_BYTES, max_age_days_env=DRIFT_AGE, **DEFAULTS
    ) is None
    assert not path.exists()
    assert sorted(tmp_path.glob("drift_events.*.jsonl")) == []


def test_env_var_isolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    drift_path = tmp_path / "drift_events.jsonl"
    metrics_path = tmp_path / "metrics.jsonl"
    drift_path.write_bytes(b"x" * 100)
    metrics_path.write_bytes(b"y" * 100)
    monkeypatch.setenv(DRIFT_BYTES, "10")
    monkeypatch.delenv(METRICS_BYTES, raising=False)
    monkeypatch.setenv(DRIFT_AGE, "30")
    monkeypatch.delenv(METRICS_AGE, raising=False)
    _rotate_jsonl_if_needed(
        drift_path, glob_prefix="drift_events", max_bytes_env=DRIFT_BYTES, max_age_days_env=DRIFT_AGE, **DEFAULTS
    )
    _rotate_jsonl_if_needed(
        metrics_path, glob_prefix="metrics", max_bytes_env=METRICS_BYTES, max_age_days_env=METRICS_AGE, **DEFAULTS
    )
    assert sorted(tmp_path.glob("drift_events.*.jsonl"))
    assert sorted(tmp_path.glob("metrics.*.jsonl")) == []


def test_rename_oserror_is_swallowed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "drift_events.jsonl"
    monkeypatch.setenv(DRIFT_BYTES, "1")
    monkeypatch.setenv(DRIFT_AGE, "30")
    path.write_bytes(b"xy")
    original_rename = Path.rename

    def boom(self: Path, target: Path) -> None:
        raise OSError("simulated slow FS rename failure")

    monkeypatch.setattr(Path, "rename", boom)
    try:
        result = _rotate_jsonl_if_needed(
            path, glob_prefix="drift_events", max_bytes_env=DRIFT_BYTES, max_age_days_env=DRIFT_AGE, **DEFAULTS
        )
    finally:
        monkeypatch.setattr(Path, "rename", original_rename)
    assert result is None
    assert path.exists()


def test_age_cutoff_prunes_old_keeps_recent_and_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "drift_events.jsonl"
    monkeypatch.setenv(DRIFT_BYTES, "1048576")
    monkeypatch.setenv(DRIFT_AGE, "30")
    path.write_text("active\n", encoding="utf-8")
    old_sibling = tmp_path / "drift_events.20200101T000000Z.jsonl"
    recent_sibling = tmp_path / "drift_events.20260628T000000Z.jsonl"
    old_sibling.write_text("old\n", encoding="utf-8")
    recent_sibling.write_text("recent\n", encoding="utf-8")
    now = _time.time()
    os.utime(old_sibling, (now - 60 * 86400, now - 60 * 86400))
    os.utime(recent_sibling, (now, now))
    _rotate_jsonl_if_needed(
        path, glob_prefix="drift_events", max_bytes_env=DRIFT_BYTES, max_age_days_env=DRIFT_AGE, **DEFAULTS
    )
    assert not old_sibling.exists()
    assert recent_sibling.exists()
    assert path.exists()


@pytest.mark.parametrize("age_env_val", ["0", "-7"])
def test_zero_and_negative_skip_glob(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, age_env_val: str) -> None:
    path = tmp_path / "drift_events.jsonl"
    monkeypatch.setenv(DRIFT_BYTES, "1048576")
    monkeypatch.setenv(DRIFT_AGE, age_env_val)
    path.write_text("active\n", encoding="utf-8")
    very_old = tmp_path / "drift_events.20200101T000000Z.jsonl"
    very_old.write_text("very old\n", encoding="utf-8")
    now = _time.time()
    os.utime(very_old, (now - 5 * 365 * 86400, now - 5 * 365 * 86400))
    _rotate_jsonl_if_needed(
        path, glob_prefix="drift_events", max_bytes_env=DRIFT_BYTES, max_age_days_env=DRIFT_AGE, **DEFAULTS
    )
    assert very_old.exists()
    assert path.exists()


@pytest.mark.parametrize(
    ("active_scheme", "other_scheme", "bytes_env", "age_env"),
    [
        ("metrics", "drift_events", METRICS_BYTES, METRICS_AGE),
        ("drift_events", "metrics", DRIFT_BYTES, DRIFT_AGE),
    ],
)
def test_glob_prefix_scoping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    active_scheme: str,
    other_scheme: str,
    bytes_env: str,
    age_env: str,
) -> None:
    path = tmp_path / f"{active_scheme}.jsonl"
    monkeypatch.setenv(bytes_env, "1048576")
    monkeypatch.setenv(age_env, "30")
    other_sibling = tmp_path / f"{other_scheme}.20200101T000000Z.jsonl"
    other_sibling.write_text("other\n", encoding="utf-8")
    now = _time.time()
    os.utime(other_sibling, (now - 5 * 365 * 86400, now - 5 * 365 * 86400))
    path.write_text("active\n", encoding="utf-8")
    _rotate_jsonl_if_needed(
        path, glob_prefix=active_scheme, max_bytes_env=bytes_env, max_age_days_env=age_env, **DEFAULTS
    )
    assert other_sibling.exists()
    assert path.exists()
