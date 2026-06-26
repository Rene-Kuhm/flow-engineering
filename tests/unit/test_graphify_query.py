"""Unit tests for graphify_query.py — CLI wrapper + Jaccard fallback.

REQ-3 (PR#1): mocked subprocess tests for query_nodes (cache hit/miss,
Jaccard fallback, fail-open on missing binary/JSON/timeout).

These tests are written BEFORE the implementation per strict TDD. They MUST
fail until the GREEN commit implements graphify_query.py.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from flow_engineering.graphify_query import (
    DEFAULT_CACHE_DIR,
    DEFAULT_CACHE_FILE,
    DEFAULT_MAX_RESULTS,
    DEFAULT_THRESHOLD,
    DEFAULT_TIMEOUT_SECONDS,
    jaccard_fallback,
    query_nodes,
)

# ---------- Fixtures ----------

def _make_graph_json(tmp_path: Path, nodes: list[dict]) -> Path:
    """Write a minimal graph.json with the given nodes."""
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps({"nodes": nodes, "links": []}), encoding="utf-8")
    return graph_path


NODES_5 = [
    {"id": "src_auth_jwt_tokenmgr", "label": "TokenManager", "file_type": "code",
     "source_file": "src/auth/jwt.py", "source_location": "L42", "community_name": "Token Service"},
    {"id": "src_auth_oauth_oauthhandler", "label": "OAuthHandler", "file_type": "code",
     "source_file": "src/auth/oauth.py", "source_location": "L10", "community_name": "Auth Providers"},
    {"id": "src_db_sqlite_connector", "label": "SqliteConnector", "file_type": "code",
     "source_file": "src/db/sqlite.py", "source_location": "L1", "community_name": "Database"},
    {"id": "src_models_user", "label": "User", "file_type": "code",
     "source_file": "src/models/user.py", "source_location": "L5", "community_name": "Models"},
    {"id": "src_views_user_view", "label": "UserView", "file_type": "code",
     "source_file": "src/views/user_view.py", "source_location": "L1", "community_name": "Views"},
]


# ---------- query_nodes tests ----------

class TestQueryNodesFailOpen:
    """query_nodes MUST return [] on every error path — never raise."""

    def test_returns_empty_when_cli_missing(self, tmp_path):
        with patch(
            "flow_engineering.graphify_query._run_graphify_cli",
            side_effect=FileNotFoundError("graphify not on PATH"),
        ):
            result = query_nodes("jwt auth", cache_dir=tmp_path)
        assert result == []

    def test_returns_empty_when_cli_returns_non_zero(self, tmp_path):
        with patch(
            "flow_engineering.graphify_query._run_graphify_cli",
            return_value=(1, "", "non-fatal error"),
        ):
            result = query_nodes("jwt auth", cache_dir=tmp_path)
        assert result == []

    def test_returns_empty_when_cli_times_out(self, tmp_path):
        with patch(
            "flow_engineering.graphify_query._run_graphify_cli",
            side_effect=subprocess.TimeoutExpired(cmd="graphify", timeout=5),
        ):
            result = query_nodes("jwt auth", cache_dir=tmp_path)
        assert result == []


class TestQueryNodesCache:
    """query_nodes caches by sha1(text + graph.json mtime)."""

    def test_cache_hit_avoids_subprocess(self, tmp_path):
        # Pre-seed the cache file with a known payload.
        cache_file = tmp_path / DEFAULT_CACHE_FILE
        cache_file.write_text(json.dumps({
            "key_abc": {
                "refs": [
                    {"project": "insyd", "id": "src_auth_jwt_tokenmgr",
                     "label": "TokenManager", "file": "src/auth/jwt.py",
                     "line": 42, "confidence": 0.8, "source": "auto_suggest"}
                ],
                "mtime": 0,
            }
        }), encoding="utf-8")

        # Pretend the cache key derivation returns 'key_abc' for this input.
        with patch(
            "flow_engineering.graphify_query._cache_key",
            return_value="key_abc",
        ):
            result = query_nodes("jwt auth", cache_dir=tmp_path)
        assert len(result) == 1
        assert result[0].id == "src_auth_jwt_tokenmgr"

    def test_cache_miss_calls_subprocess(self, tmp_path):
        # Empty cache; subprocess returns a successful payload.
        cli_payload = json.dumps({
            "nodes": [
                {"project": "insyd", "id": "x", "label": "X", "file": "x.py",
                 "line": 1, "confidence": 0.5, "source": "auto_suggest"}
            ]
        })
        with patch(
            "flow_engineering.graphify_query._run_graphify_cli",
            return_value=(0, cli_payload, ""),
        ), patch(
            "flow_engineering.graphify_query._graph_json_mtime",
            return_value=12345,
        ):
            result = query_nodes("jwt auth", cache_dir=tmp_path)
        assert len(result) == 1
        assert result[0].id == "x"


# ---------- jaccard_fallback tests ----------

class TestJaccardFallback:
    """jaccard_fallback scores nodes by token overlap with the query text."""

    def test_returns_top_k_ranked_by_score(self, tmp_path):
        graph_path = _make_graph_json(tmp_path, NODES_5)
        # "jwt auth token" should rank jwt + oauth nodes highest.
        results = jaccard_fallback("jwt auth token", graph_path, top_k=3)
        assert 1 <= len(results) <= 3
        # The first result should mention jwt or auth.
        first_label = results[0].label.lower()
        assert "jwt" in first_label or "token" in first_label or "auth" in first_label

    def test_returns_empty_for_empty_query(self, tmp_path):
        graph_path = _make_graph_json(tmp_path, NODES_5)
        results = jaccard_fallback("", graph_path, top_k=3)
        assert results == []

    def test_returns_empty_for_missing_graph(self, tmp_path):
        missing = tmp_path / "no_such_graph.json"
        results = jaccard_fallback("jwt auth", missing, top_k=3)
        assert results == []


# ---------- Default constants ----------

class TestDefaults:
    def test_default_threshold_is_0_3(self):
        assert DEFAULT_THRESHOLD == 0.3

    def test_default_max_results_is_5(self):
        assert DEFAULT_MAX_RESULTS == 5

    def test_default_timeout_is_5_seconds(self):
        assert DEFAULT_TIMEOUT_SECONDS == 5.0

    def test_default_cache_dir_is_home_dot_flow_engineering(self):
        assert Path.home() / ".flow-engineering" == DEFAULT_CACHE_DIR
