import json

import pytest

import simplutils
from simplutils import ToolError, map_search, random_text

DATA = json.dumps({
    "users": [
        {"name": "Asha", "city": "Chennai", "email": "a@x.com", "age": 31},
        {"name": "Ravi", "city": "Pune", "email": "r@x.com", "age": 28},
        {"name": "Meena", "city": "Chennai", "email": "m@y.org", "age": 31},
    ],
    "meta": {"city": "Chennai", "a.b": 1, "active": True},
})


def run(**kw):
    return simplutils.TOOLS["map-search"].run(DATA, **kw)


# ---- random-text ------------------------------------------------------------
@pytest.mark.parametrize("charset", ["alnum", "letters", "lower", "upper", "digits", "hex", "words"])
@pytest.mark.parametrize("length", [1, 7, 64, 1000])
def test_random_text_exact_length(charset, length):
    out = random_text(length=length, charset=charset)
    assert len(out) == length
    if charset == "words":
        assert not out.endswith(" ")


def test_random_text_charsets_and_custom():
    assert random_text(50, "digits").isdigit()
    assert set(random_text(50, "hex")) <= set("0123456789abcdef")
    assert set(random_text(200, custom="ab1")) <= {"a", "b", "1"}
    assert len(random_text(10, count=5).splitlines()) == 5


def test_random_text_is_random_and_validates():
    assert random_text(32) != random_text(32)
    for bad in (dict(length=0), dict(length=1_000_001), dict(count=0), dict(length=10_000, count=1000)):
        with pytest.raises(ToolError):
            random_text(**bad)


# ---- map-search ------------------------------------------------------------
def test_find_key_anywhere():
    out = run(query="city")
    assert out.startswith("4 matching keys")
    assert "users[1].city: \"Pune\"" in out and "meta.city" in out


def test_find_and_count_values():
    assert run(action="count", by="value", query="Chennai") == "3"
    assert run(action="count", by="value", query="31") == "2"  # numbers match as text
    assert run(action="count", by="value", query="true") == "1"
    assert run(by="value", query="nobody") == "No matches."


def test_match_modes_and_ignore_case():
    assert run(action="count", by="value", query="@x.com", match="contains") == "2"
    assert run(action="count", by="value", query="^c", match="regex", ignore_case=True) == "3"
    assert run(action="count", by="value", query="chennai") == "0"
    assert run(action="count", by="value", query="chennai", ignore_case=True) == "3"
    assert run(action="count", by="key", query="^(name|city)$", match="regex") == "7"


def test_get_by_path():
    assert json.loads(run(action="get", query="users[0].name")) == "Asha"
    assert json.loads(run(action="get", query="users[*].name")) == ["Asha", "Ravi", "Meena"]
    assert json.loads(run(action="get", query='meta["a.b"]')) == 1
    assert json.loads(run(action="get", query="users[-1].city")) == "Chennai"
    with pytest.raises(ToolError, match="nothing found"):
        run(action="get", query="users[9].name")


def test_find_output_paths_can_be_fed_back_to_get():
    out = run(by="value", query="Ravi")
    path = out.splitlines()[1].split(":")[0]
    assert json.loads(run(action="get", query=path)) == "Ravi"
    quoted = run(by="key", query="a.b").splitlines()[1].split(":")[0]
    assert quoted == 'meta["a.b"]'


def test_tally():
    out = run(action="tally", query="city")
    assert '"Chennai"  3' in out and '"Pune"     1' in out
    assert out.splitlines()[0].startswith("4 match")
    with pytest.raises(ToolError):
        run(action="tally", by="value", query="x")


def test_limit_and_errors():
    out = run(query="city", limit=2)
    assert "... and 2 more" in out
    with pytest.raises(ToolError):
        run(query="")
    with pytest.raises(ToolError, match="invalid regex"):
        run(query="(", match="regex")
    with pytest.raises(ToolError):
        simplutils.TOOLS["map-search"].run("just words", query="x")
    with pytest.raises(ToolError):
        simplutils.TOOLS["map-search"].run("42", query="x")


def test_top_level_list_and_deep_nesting():
    out = simplutils.TOOLS["map-search"].run('[{"id": 1}, {"id": 2}]', query="id", action="count")
    assert out == "2"
    deep = "[" * 3000 + "]" * 3000  # must not crash with a traceback
    try:
        simplutils.TOOLS["map-search"].run(deep, query="x", action="count")
    except ToolError:
        pass


def test_accepts_python_dict_and_list_directly():
    d = json.loads(DATA)
    assert map_search(d, action="count", by="value", query="Chennai") == "3"
    assert json.loads(map_search(d, action="get", query="users[*].name")) == ["Asha", "Ravi", "Meena"]
    assert map_search(d["users"], action="count", query="name") == "3"
    assert simplutils.TOOLS["map-search"].run(d, query="city", action="count") == "4"
