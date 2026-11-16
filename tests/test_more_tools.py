import json

import pytest

import simplutils
from simplutils.cli import main
from simplutils.registry import ToolError
from simplutils.tools.pii import detect, iban_ok, luhn_ok, verhoeff_check_digit, verhoeff_ok


# ---------------- regex ----------------
def test_regex_test():
    out = simplutils.regex_test("a1 b22 c333", r"([a-z])(\d+)")
    assert "3 matches" in out and "group 1: 'b'" in out and "group 2: '22'" in out
    assert simplutils.regex_test("abc", r"\d") == "No matches."
    assert "'ABC'" in simplutils.regex_test("ABC", "abc", ignore_case=True)


def test_regex_named_groups_and_errors():
    assert "<year>: '2026'" in simplutils.regex_test("2026-01", r"(?P<year>\d{4})-\d\d")
    with pytest.raises(ToolError):
        simplutils.regex_test("x", "(")
    with pytest.raises(ToolError):
        simplutils.regex_replace("x", "x", r"\9")  # invalid group reference


def test_regex_replace():
    assert simplutils.regex_replace("john smith", r"(\w+) (\w+)", r"\2, \1") == "smith, john"


# ---------------- diff ----------------
def test_text_diff():
    out = simplutils.text_diff([b"a\nb\nc\n", b"a\nB\nc\n"])
    assert "-b" in out and "+B" in out
    assert simplutils.text_diff([b"x", b"x"]) == "No differences."
    assert simplutils.text_diff([b"a  b", b"a b"], ignore_whitespace=True) == "No differences."


def test_diff_needs_exactly_two():
    for files in ([b"x"], [b"x", b"y", b"z"]):
        with pytest.raises(ToolError):
            simplutils.text_diff(files)


def test_json_diff():
    a = json.dumps({"name": "x", "n": 1, "tags": ["a", "b"], "gone": True, "o": {"k": 1}}).encode()
    b = json.dumps({"name": "x", "n": 2, "tags": ["a", "c", "d"], "new": 5, "o": {"k": 1}}).encode()
    out = simplutils.json_diff([a, b])
    assert "~ n: 1 -> 2" in out
    assert "~ tags[1]: \"b\" -> \"c\"" in out and "+ tags[2]: \"d\"" in out
    assert "- gone: true" in out and "+ new: 5" in out
    assert "name" not in out and "o.k" not in out
    assert simplutils.json_diff([a, a]) == "No differences."
    assert "~ x: 1 -> 1.0" in simplutils.json_diff([b'{"x": 1}', b'{"x": 1.0}'])  # type change is a change
    with pytest.raises(ToolError):
        simplutils.json_diff([b"{bad", b"{}"])


# ---------------- convert ----------------
def test_yaml_roundtrip():
    y = simplutils.json_to_yaml('{"b": 1, "a": {"c": [1, 2]}}')
    assert y.splitlines()[0] == "b: 1"  # key order preserved
    assert json.loads(simplutils.yaml_to_json(y)) == {"b": 1, "a": {"c": [1, 2]}}
    assert json.loads(simplutils.yaml_to_json("a: 1\n---\nb: 2")) == [{"a": 1}, {"b": 2}]
    with pytest.raises(ToolError):
        simplutils.yaml_to_json("a: [unclosed")


def test_json_to_csv_flattens():
    out = simplutils.json_to_csv('[{"id":1,"u":{"n":"A"},"t":[1,2]},{"id":2,"extra":"x"}]')
    lines = out.splitlines()
    assert lines[0] == "id,u.n,t,extra"
    assert lines[1] == '1,A,"[1, 2]",'
    assert lines[2] == "2,,,x"
    with pytest.raises(ToolError):
        simplutils.json_to_csv("[]")


def test_csv_to_json():
    assert json.loads(simplutils.csv_to_json("a,b\n1,x\n2,y")) == [{"a": "1", "b": "x"}, {"a": "2", "b": "y"}]
    typed = json.loads(simplutils.csv_to_json("a;b;c\n1;true;\n2.5;no;z", infer_types=True))
    assert typed == [{"a": 1, "b": True, "c": None}, {"a": 2.5, "b": "no", "c": "z"}]  # delimiter auto-detected
    with pytest.raises(ToolError):
        simplutils.csv_to_json("only,a,header")


# ---------------- qr ----------------
def test_qr_generate():
    png = simplutils.qr_generate("https://example.com")
    assert png.data.startswith(b"\x89PNG") and png.filename == "qr.png"
    svg = simplutils.qr_generate("hi", kind="svg")
    assert b"<svg" in svg.data and svg.mime == "image/svg+xml"
    with pytest.raises(ToolError):
        simplutils.qr_generate("x" * 10000)  # too much data
    with pytest.raises(ToolError):
        simplutils.qr_generate("x", scale=0)
    assert len(simplutils.qr_text("hello").splitlines()) > 5


# ---------------- pii: checksums (independent known vectors) ----------------
def test_checksums():
    assert verhoeff_ok("2363") and not verhoeff_ok("2364")  # Wikipedia's Verhoeff example
    assert verhoeff_check_digit("236") == "3"
    assert luhn_ok("4111 1111 1111 1111") and not luhn_ok("4111 1111 1111 1112")
    assert not luhn_ok("0000 0000 0000 0000")
    assert iban_ok("GB82 WEST 1234 5698 7654 32") and not iban_ok("GB82 WEST 1234 5698 7654 33")


def kinds(text, **kw):
    return [f.kind for f in detect(text, **kw)]


def test_pii_detects_each_type():
    aad = "23412341234" + verhoeff_check_digit("23412341234")
    cases = {
        "mail me at jo.doe@example.co.uk": "email",
        "card 4111 1111 1111 1111": "credit-card",
        "ssn 123-45-6789": "ssn",
        f"aadhaar {aad}": "aadhaar",
        "PAN ABCDE1234F": "pan",
        "iban GB82 WEST 1234 5698 7654 32": "iban",
        "host 10.0.0.12 up": "ip-address",
        "call +91 98765 43210": "phone",
        "call (415) 555-2671": "phone",
        "key AKIAIOSFODNN7EXAMPLE": "aws-key",
        "tok ghp_" + "a" * 36: "github-token",
        "Authorization: Bearer abcdefghijklmnop1234": "bearer-token",
        "db https://admin:s3cretpw@host/x": "url-password",
        "password=Hunter2!x": "password",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIB\n-----END RSA PRIVATE KEY-----": "private-key",
        "t eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc": "jwt",
    }
    for text, kind in cases.items():
        assert kinds(text) == [kind], text


def test_pii_avoids_false_positives():
    for text in [
        "card 4111 1111 1111 1112",        # fails Luhn
        "order 8123456789012",             # 13 digits, fails Luhn
        "ts 1700000000",                   # unix timestamp
        "version 1.2.3.4.5",               # not an IP
        "ip-ish 999.1.1.1",                # invalid octet
        "date 2026-11-11",
        "Aadhaar-like 234123412345",       # fails Verhoeff (check digit wrong)
        "GB82 WEST 1234 5698 7654 33",     # fails IBAN mod-97
    ]:
        assert kinds(text) == [], text


def test_pii_overlap_prefers_specific_type():
    # a valid card number must not also be reported as a phone number
    assert kinds("4111 1111 1111 1111") == ["credit-card"]


def test_redact_modes_and_never_leaks():
    text = "mail jo@example.com pw password=Hunter2!x card 4111 1111 1111 1111"
    label = simplutils.pii_redact(text)
    assert label == "mail [EMAIL] pw password=[PASSWORD] card [CREDIT-CARD]"
    masked = simplutils.pii_redact(text, mode="mask")
    assert "Hunter2" not in masked and "jo@example.com" not in masked
    assert "**** **** **** 1111" in masked  # last 4 of a card stay visible
    assert "password=********" in masked    # secrets are fully masked, no hints
    h = simplutils.pii_redact("a@x.com b@x.com a@x.com", mode="hash")
    t = h.split()
    assert t[0] == t[2] and t[0] != t[1]    # same value -> same token within one run
    assert simplutils.pii_redact("a@x.com", mode="hash") != simplutils.pii_redact("a@x.com", mode="hash")  # salt differs per run


def test_redact_only_exclude_and_unknown():
    text = "a@x.com 123-45-6789"
    assert simplutils.pii_redact(text, only="email") == "[EMAIL] 123-45-6789"
    assert simplutils.pii_redact(text, exclude="email") == "a@x.com [SSN]"
    with pytest.raises(ToolError):
        simplutils.pii_redact(text, only="emial")


def test_filtered_out_types_still_claim_their_text():
    url = "postgres://admin:s3cretpw@db.internal:5432/app"
    # regression: with only=email, 's3cretpw@db.internal' used to be reported as an email
    assert simplutils.pii_redact(url, only="email") == url
    assert simplutils.pii_redact(url, only="url-password") == "postgres://admin:[URL-PASSWORD]@db.internal:5432/app"
    # excluding credit-card must not re-report the same digits as a phone number
    assert simplutils.pii_redact("card 4111 1111 1111 1111", exclude="credit-card") == "card 4111 1111 1111 1111"


def test_redact_keeps_surrounding_text_exactly():
    text = "line1\n  jo@x.com,\tnext\n"
    assert simplutils.pii_redact(text) == "line1\n  [EMAIL],\tnext\n"


def test_scan_hides_values():
    text = "x\njo.doe@example.com\npassword=Hunter2!x"
    out = simplutils.pii_scan(text)
    assert "line 2" in out and "line 3" in out and "email" in out
    assert "jo.doe@example.com" not in out and "Hunter2" not in out
    assert "Nothing detected" in simplutils.pii_scan("just words")


def test_pii_types_lists_everything():
    assert "email" in simplutils.pii_types() and "aadhaar" in simplutils.pii_types()


def test_pii_cli_and_log_has_no_values(tmp_path, capsys):
    f = tmp_path / "in.txt"
    f.write_text("mail jo@example.com", encoding="utf-8")
    assert main(["pii-redact", "-f", str(f)]) == 0
    assert capsys.readouterr().out.strip() == "mail [EMAIL]"
    assert main(["logs", "-n", "50"]) == 0
    log = capsys.readouterr().out
    assert "pii-redact: 1 finding(s) {'email': 1}" in log and "jo@example.com" not in log


def test_cli_new_file_tools(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text('{"x":1}')
    b.write_text('{"x":2}')
    out = tmp_path / "d.txt"
    assert main(["json-diff", str(a), str(b), "-o", str(out)]) == 0
    assert "~ x: 1 -> 2" in out.read_text()
    qr = tmp_path / "q.png"
    assert main(["qr-generate", "hello", "-o", str(qr)]) == 0
    assert qr.read_bytes().startswith(b"\x89PNG")
