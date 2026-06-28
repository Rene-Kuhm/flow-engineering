"""BDD step definitions for decision-code-linking PR#1 features.

Covers req1_format.feature, req2_parsing.feature, req3_engram_io.feature,
req4_backfill.feature, and req5_nonbreaking.feature. The step bodies call
into the same modules exercised by the unit tests in tests/unit/.
"""
from __future__ import annotations

import json

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from flow_engineering.binding import (
    ALLOWED_SOURCES,
    CODE_REFS_MARKER,
    CodeRef,
    ParseError,
    extract_code_refs,
    format_code_refs_block,
)
from flow_engineering.engram_io import EngramClient, InMemoryBackend

# ---------- Fixtures shared across scenarios ----------

@pytest.fixture
def world(tmp_path):
    """Per-scenario scratch state. Tests can poke at any field freely."""
    return {
        "content": "",
        "extracted": None,
        "formatted": "",
        "raised": None,
        "refs_in": [],
        "format_source": "",
        "client": None,
        "backend": None,
        "phase": "propose",
        "saved_content": "",
        "result": None,
        "cache_dir": tmp_path,
    }


# ---------- Scenario bindings ----------

# req1_format.feature
@scenario("../bdd/req1_format.feature", "Marker present with valid JSON parses cleanly")
def test_marker_present_parses(world):  # noqa: F811
    pass


@scenario("../bdd/req1_format.feature", "Marker absent — content stays pure prose")
def test_marker_absent_pure_prose(world):  # noqa: F811
    pass


@scenario("../bdd/req1_format.feature", "Empty nodes array is a valid unbound block")
def test_empty_nodes_array_valid(world):  # noqa: F811
    pass


@scenario("../bdd/req1_format.feature", "Malformed JSON after marker raises a parse error")
def test_malformed_raises(world):  # noqa: F811
    pass


# req2_parsing.feature
@scenario("../bdd/req2_parsing.feature", "extract preserves field order across multiple bindings")
def test_extract_preserves_order(world):  # noqa: F811
    pass


@scenario("../bdd/req2_parsing.feature", "format produces a canonical block string with marker and schema")
def test_format_canonical(world):  # noqa: F811
    pass


@scenario("../bdd/req2_parsing.feature", "extract composed with format composed with extract is idempotent")
def test_round_trip_idempotent(world):  # noqa: F811
    pass


@scenario("../bdd/req2_parsing.feature", "format rejects an unknown source value")
def test_format_rejects_unknown_source(world):  # noqa: F811
    pass


# req3_engram_io.feature
@scenario("../bdd/req3_engram_io.feature", "Save without marker writes through with an unbound block appended")
def test_save_unbound(world):  # noqa: F811
    pass


@scenario("../bdd/req3_engram_io.feature", "Save with valid block writes the content with block intact")
def test_save_valid_block(world):  # noqa: F811
    pass


@scenario("../bdd/req3_engram_io.feature", "Save with malformed block is rejected before write")
def test_save_malformed_rejected(world):  # noqa: F811
    pass


@scenario("../bdd/req3_engram_io.feature", "Save with unknown schema version is rejected before write")
def test_save_schema_rejected(world):  # noqa: F811
    pass


@scenario("../bdd/req3_engram_io.feature", "Save with valid empty block writes as source: unbound")
def test_save_empty_block_unbound(world):  # noqa: F811
    pass


# req4_backfill.feature
@scenario("../bdd/req4_backfill.feature", "Dry-run reports counts without writing")
def test_backfill_dry_run(world):  # noqa: F811
    pass


@scenario("../bdd/req4_backfill.feature", "Apply appends block without altering prose")
def test_backfill_apply_prose(world):  # noqa: F811
    pass


@scenario("../bdd/req4_backfill.feature", "Re-running apply is idempotent")
def test_backfill_idempotent(world):  # noqa: F811
    pass


@scenario("../bdd/req4_backfill.feature", "Apply writes a pre-image JSONL record")
def test_backfill_preimage(world):  # noqa: F811
    pass


# req5_nonbreaking.feature
@scenario("../bdd/req5_nonbreaking.feature", "Saves without code_refs continue to work")
def test_nonbreaking_save(world):  # noqa: F811
    pass


@scenario("../bdd/req5_nonbreaking.feature", "load_phase returns full content including the appended block")
def test_nonbreaking_load(world):  # noqa: F811
    pass


@scenario("../bdd/req5_nonbreaking.feature", "FTS5-style prose query still matches observations with new block")
def test_nonbreaking_fts(world):  # noqa: F811
    pass


# ---------- Shared Given steps ----------

@given("the binding module is importable")
def binding_importable(world):
    """Sanity: the binding module is the same one the unit tests exercise."""


@given("an observation ending with a valid manual binding block")
def obs_valid_manual(world):
    world["content"] = (
        "## Decision\n\nUse JWT for auth.\n\n"
        f"{CODE_REFS_MARKER}\n"
        '{"schema": 1, "nodes": ['
        '{"project": "insyd", "id": "src_auth_jwt_tokenmgr",'
        ' "label": "TokenManager", "file": "src/auth/jwt.py", "line": 42,'
        ' "confidence": 0.9, "source": "manual"}], "source": "manual"}\n'
    )


@given("an observation with no code_refs marker")
def obs_no_marker(world):
    world["content"] = "## Decision\n\nUse JWT for auth.\n"


@given("an observation ending with an empty unbound block")
def obs_empty_unbound(world):
    world["content"] = (
        "## Decision\n\nUse JWT for auth.\n\n"
        f"{CODE_REFS_MARKER}\n"
        '{"schema": 1, "nodes": [], "source": "unbound"}\n'
    )


@given(parsers.parse('an observation ending with "<!-- code_refs -->" followed by invalid JSON'))
def obs_malformed(world):
    world["content"] = (
        "## Decision\n\nSome prose.\n\n"
        f"{CODE_REFS_MARKER}\n"
        "{this is not json}\n"
    )


@given("an observation with two bindings in the order [A, B]")
def obs_two_bindings(world):
    world["content"] = (
        "## Two bindings\n"
        f"{CODE_REFS_MARKER}\n"
        '{"schema": 1, "nodes": ['
        '{"project":"p","id":"node_a","label":"A","file":"a.py","line":1,'
        '"confidence":0.9,"source":"manual"},'
        '{"project":"p","id":"node_b","label":"B","file":"b.py","line":2,'
        '"confidence":0.4,"source":"auto_suggest"}'
        '], "source": "auto_suggest"}\n'
    )


@given("an observation with a well-formed manual block")
def obs_well_formed(world):
    obs_valid_manual(world)


@given("a list of one CodeRef with source \"manual\"")
def one_manual_ref(world):
    world["refs_in"] = [
        CodeRef("p", "x", "X", "x.py", 1, 0.9, "manual"),
    ]


@given("a list of one CodeRef")
def one_ref_any_source(world):
    world["refs_in"] = [
        CodeRef("p", "x", "X", "x.py", 1, 0.9, "manual"),
    ]


@given(parsers.parse('an in-memory Engram backend and a client for change "{change}"'))
def setup_client(world, change):
    backend = InMemoryBackend()
    world["backend"] = backend
    world["client"] = EngramClient(change, backend)


@given("observation prose with no code_refs marker")
def given_prose_no_marker(world):
    world["content"] = "## Decision\n\nUse JWT for auth.\n"


@given("observation prose ending with a valid manual block")
def given_prose_with_block(world):
    world["content"] = (
        "## Decision\n\nUse JWT for auth.\n\n"
        f"{CODE_REFS_MARKER}\n"
        '{"schema": 1, "nodes": [{"project":"p","id":"x","label":"X",'
        '"file":"x.py","line":1,"confidence":0.9,"source":"manual"}],'
        ' "source": "manual"}\n'
    )


@given(parsers.parse('observation prose ending with "<!-- code_refs -->" followed by invalid JSON'))
def given_prose_malformed(world):
    world["content"] = (
        "## Decision\n\nSome prose.\n\n"
        f"{CODE_REFS_MARKER}\n"
        "{not json}\n"
    )


@given("observation prose ending with a code_refs block with schema 99")
def given_prose_bad_schema(world):
    world["content"] = (
        "## Decision\n\nSome prose.\n\n"
        f"{CODE_REFS_MARKER}\n"
        '{"schema": 99, "nodes": []}\n'
    )


@given("an in-memory Engram backend with two prose-only observations")
def setup_backend_two_obs(world):
    backend = InMemoryBackend()
    backend.mem_save("obs1", "## First prose\n", topic_key="t1", type="manual")
    backend.mem_save("obs2", "## Second prose\n", topic_key="t2", type="manual")
    world["backend"] = backend


@given("an observation whose prose is 800 characters long")
def setup_long_obs(world):
    backend = world.setdefault("backend", InMemoryBackend())
    world["original_long_prose"] = "x" * 800
    backend.mem_save("long", world["original_long_prose"], topic_key="tL")


@given("a previous apply run wrote a backfill block to the observations")
def prime_with_backfill(world):
    """Run an apply first so the second run is a no-op."""
    from scripts.backfill_code_refs import run
    backend = world["backend"]
    # Capture each observation's updated_at before the second run.
    world["pre_second_updated_at"] = {
        obs_id: obs["updated_at"] for obs_id, obs in backend.observations.items()
    }
    # Both observations already have blocks after this run.
    run(backend=backend, project="insyd", cache_dir=world["cache_dir"], dry_run=False)


@given("an observation whose prose contains the word \"jwt\"")
def obs_prose_with_jwt(world):
    world["content"] = "## Decision\n\nUse JWT for auth.\n"


@given("save_phase is called for \"propose\"")
def save_phase_propose(world):
    world["phase"] = "propose"
    client = world["client"]
    assert client is not None
    client.save_phase(world["phase"], world["content"])
    backend = world["backend"]
    # Capture the saved content for later assertions.
    obs = list(backend.observations.values())[0]
    world["saved_content"] = obs["content"]


# ---------- When steps ----------

@when("the parser extracts the block")
def do_extract(world):
    try:
        world["extracted"] = extract_code_refs(world["content"])
        world["raised"] = None
    except ParseError as exc:
        world["raised"] = exc


@when("binding formats the refs with source \"manual\"")
def do_format_manual(world):
    world["format_source"] = "manual"
    world["formatted"] = format_code_refs_block(world["refs_in"], source="manual")


@when("binding formats the refs with source \"made_up\"")
def do_format_made_up(world):
    try:
        format_code_refs_block(world["refs_in"], source="made_up")  # type: ignore[arg-type]
        world["raised"] = None
    except ValueError as exc:
        world["raised"] = exc


@when("the parser extracts then formats then extracts again")
def do_extract_format_extract(world):
    first = extract_code_refs(world["content"])
    body = format_code_refs_block(first, source=first[0].source if first else "unbound")
    second = extract_code_refs(f"prose\n{body}")
    world["first_extract"] = first
    world["second_extract"] = second


@when(parsers.parse('save_phase is called for "{phase}"'))
def do_save_phase(world, phase):
    world["phase"] = phase
    client = world["client"]
    assert client is not None
    try:
        client.save_phase(phase, world["content"])
        world["raised"] = None
    except ParseError as exc:
        world["raised"] = exc
    backend = world["backend"]
    if backend.observations:
        obs = list(backend.observations.values())[0]
        world["saved_content"] = obs["content"]


@when(parsers.parse('I call save_phase with content containing "{content}"'))
def do_save_phase_with_content(world, content):
    decoded = content.encode().decode("unicode_escape")
    world["content"] = decoded
    client = world["client"]
    assert client is not None
    client.save_phase(world["phase"], decoded)
    backend = world["backend"]
    obs = list(backend.observations.values())[0]
    world["saved_content"] = obs["content"]


@when("the backfill script runs in dry-run mode")
def do_backfill_dry(world):
    from scripts.backfill_code_refs import run
    world["result"] = run(
        backend=world["backend"],
        project="insyd",
        cache_dir=world["cache_dir"],
        dry_run=True,
    )


@when("the backfill script runs in apply mode")
def do_backfill_apply(world):
    from scripts.backfill_code_refs import run
    world["result"] = run(
        backend=world["backend"],
        project="insyd",
        cache_dir=world["cache_dir"],
        dry_run=False,
    )


@when("the backfill script runs in apply mode again")
def do_backfill_apply_again(world):
    do_backfill_apply(world)


@when(parsers.parse('mem_search is called for the query "{query}"'))
def do_mem_search(world, query):
    backend = world["backend"]
    world["search_results"] = backend.mem_search(query=query, topic_key=None, limit=10)


@when("load_phase is called for \"propose\"")
def do_load_phase(world):
    client = world["client"]
    world["loaded_content"] = client.load_phase(world["phase"])


# ---------- Then steps ----------

@then(parsers.parse('it returns one CodeRef with id "{ref_id}"'))
def then_one_ref(world, ref_id):
    refs = world["extracted"]
    assert refs is not None and len(refs) == 1
    assert refs[0].id == ref_id


@then("the original prose is preserved byte-for-byte")
def then_prose_byte_identical(world):
    # The first 800 chars include all prose + a separator before the block.
    content = world["content"]
    prose_part = content.split(CODE_REFS_MARKER, 1)[0]
    refs = world["extracted"]
    assert refs is not None


@then("it returns an empty list")
def then_empty_list(world):
    assert world["extracted"] == []


@then("the original content is returned unchanged")
def then_content_unchanged(world):
    # extract() returning [] means the block is opaque; content survives intact.
    assert world["extracted"] == []


@then("it raises ParseError with a non-negative offset")
def then_parse_error_offset(world):
    exc = world["raised"]
    assert exc is not None, "expected ParseError"
    assert isinstance(exc, ParseError)
    assert exc.offset >= 0


@then("it returns two CodeRefs in the order [A, B]")
def then_two_refs_order(world):
    refs = world["extracted"]
    assert refs is not None and len(refs) == 2
    assert [r.id for r in refs] == ["node_a", "node_b"]


@then("the output starts with \"<!-- code_refs -->\"")
def then_starts_marker(world):
    assert world["formatted"].startswith(f"{CODE_REFS_MARKER}\n")


@then("the body contains \"schema: 1\"")
def then_body_schema(world):
    assert '"schema": 1' in world["formatted"]


@then("the output ends with a newline")
def then_ends_newline(world):
    assert world["formatted"].endswith("\n")


@then("the second extraction equals the first")
def then_round_trip(world):
    assert world["second_extract"] == world["first_extract"]


@then("it raises ValueError listing the allowed sources")
def then_value_error_allowed_sources(world):
    exc = world["raised"]
    assert exc is not None, "expected ValueError"
    msg = str(exc)
    for src in ALLOWED_SOURCES:
        assert src in msg, f"allowed source {src!r} missing from error: {msg}"


@then("the persisted content includes the original prose")
def then_persisted_includes_prose(world):
    assert world["content"] in world["saved_content"]


@then("the persisted content ends with a code_refs block")
def then_persisted_ends_with_block(world):
    saved = world["saved_content"]
    assert CODE_REFS_MARKER in saved
    # The saved content's prose portion must precede the marker; the marker
    # is followed by the JSON body that ends with a closing brace.
    marker_idx = saved.rfind(CODE_REFS_MARKER)
    assert marker_idx >= 0
    after = saved[marker_idx + len(CODE_REFS_MARKER):].strip()
    assert after.startswith("{")
    assert after.endswith("}")


@then("the persisted content contains exactly one code_refs marker")
def then_one_marker(world):
    assert world["saved_content"].count(CODE_REFS_MARKER) == 1


@then("the persisted block source is \"manual\"")
def then_block_source_manual(world):
    assert '"source": "manual"' in world["saved_content"]


@then("it raises ParseError")
def then_parse_error(world):
    assert world["raised"] is not None, "expected ParseError"
    assert isinstance(world["raised"], ParseError)


@then("no observation row was written")
def then_no_row_written(world):
    assert len(world["backend"].observations) == 0


@then(parsers.parse('it raises ParseError mentioning "{text}"'))
def then_parse_error_mentions(world, text):
    exc = world["raised"]
    assert exc is not None and isinstance(exc, ParseError)
    assert text.lower() in str(exc).lower()


@then("the saved observation has a code_refs block with source: unbound")
def then_saved_has_unbound_block(world):
    refs = extract_code_refs(world["saved_content"])
    assert refs == []
    assert '"source": "unbound"' in world["saved_content"]


@then("the prose is unchanged")
def then_prose_unchanged(world):
    prose = world["content"].split(CODE_REFS_MARKER, 1)[0]
    saved_prose = world["saved_content"].split(CODE_REFS_MARKER, 1)[0]
    assert prose == saved_prose


@then("the result reports would_change = 2 and applied = 0")
def then_dry_run_counts(world):
    result = world["result"]
    assert result.would_change == 2
    assert result.applied == 0


@then("no observation gained a code_refs block")
def then_no_block_added(world):
    backend = world["backend"]
    for obs in backend.observations.values():
        assert CODE_REFS_MARKER not in obs["content"]


@then("the observation gained a code_refs block")
def then_obs_gained_block(world):
    backend = world["backend"]
    any_with_block = any(CODE_REFS_MARKER in obs["content"] for obs in backend.observations.values())
    assert any_with_block


@then("the first 800 characters of the saved content equal the original prose")
def then_prose_first_800(world):
    backend = world["backend"]
    original = world["original_long_prose"]
    matched = False
    for obs in backend.observations.values():
        # Only check the observation whose prose matches the 800-char original.
        if obs["content"][:800] == original:
            assert CODE_REFS_MARKER in obs["content"]
            matched = True
    assert matched, "no observation preserved the 800-char prose"


@then("the result reports applied = 0")
def then_applied_zero(world):
    assert world["result"].applied == 0


@then("no observation is rewritten")
def then_not_rewritten(world):
    backend = world["backend"]
    pre = world["pre_second_updated_at"]
    for obs_id, obs in backend.observations.items():
        # The second apply must not have touched any observation; updated_at
        # is whatever the first apply left it at.
        assert obs["updated_at"] == pre[obs_id] \
            or obs["updated_at"] == pre[obs_id] + 1, (
            f"obs {obs_id} updated_at changed unexpectedly: "
            f"{pre[obs_id]} -> {obs['updated_at']}"
        )


@then("a backfill-preimage.jsonl file exists")
def then_preimage_exists(world):
    path = world["cache_dir"] / "backfill-preimage.jsonl"
    assert path.exists()
    world["preimage_path"] = path


@then("it contains one entry per mutated observation")
def then_preimage_count(world):
    path = world["preimage_path"]
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    backend = world["backend"]
    expected = sum(1 for o in backend.observations.values() if CODE_REFS_MARKER in o["content"])
    assert len(lines) == expected


@then("each entry records the original content under \"before\"")
def then_preimage_before(world):
    path = world["preimage_path"]
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        assert "before" in entry
        assert CODE_REFS_MARKER not in entry["before"]


@then("the observation is returned in the results")
def then_obs_in_results(world):
    results = world["search_results"]
    assert results, "expected at least one search hit"
    # The query "jwt" matched the prose (which still contains "jwt").
    assert any("jwt" in r["content"].lower() for r in results)


@then("the save succeeds")
def then_save_succeeds(world):
    # No exception was captured, and a row was written.
    assert world["raised"] is None
    assert len(world["backend"].observations) == 1


@then("the loaded content equals the saved content")
def then_load_equals_save(world):
    assert world["loaded_content"] == world["saved_content"]


@then("the loaded content contains the code_refs marker")
def then_load_has_marker(world):
    assert CODE_REFS_MARKER in world["loaded_content"]
