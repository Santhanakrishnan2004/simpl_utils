import pytest

import simplutils
from simplutils.cli import main
from simplutils.registry import ToolError


def test_base64_roundtrip():
    assert simplutils.b64_encode("hello") == "aGVsbG8="
    assert simplutils.b64_decode("aGVsbG8=") == "hello"
    assert simplutils.b64_decode("aGVsbG8") == "hello"  # missing padding


def test_b64_invalid():
    with pytest.raises(ToolError):
        simplutils.b64_decode("!!!")


def test_hash_and_hmac():
    assert simplutils.hash_text("abc", "md5") == "900150983cd24fb0d6963f7d28e17f72"
    assert len(simplutils.hmac_text("abc", key="k")) == 64


def test_json():
    assert simplutils.json_minify('{ "a": 1 }') == '{"a":1}'
    with pytest.raises(ToolError):
        simplutils.json_format("{bad")


def test_jwt():
    tok = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMiLCJleHAiOjF9.sig"
    out = simplutils.jwt_decode(tok)
    assert '"sub": "123"' in out and '"expired": true' in out


def test_case_and_slug():
    assert simplutils.case_convert("helloWorld_foo bar", "snake") == "hello_world_foo_bar"
    assert simplutils.case_convert("hello world", "camel") == "helloWorld"
    assert simplutils.slugify("Héllo, World!") == "hello-world"


def test_time():
    assert "2021-01-01T00:00:00" in simplutils.ts_to_date("1609459200")
    assert "seconds: 1609459200" in simplutils.date_to_ts("2021-01-01")


def test_generators():
    assert len(simplutils.uuid_gen(3).splitlines()) == 3
    assert len(simplutils.password(20)) == 20


def test_cli(capsys):
    assert main(["b64-encode", "hi"]) == 0
    assert capsys.readouterr().out.strip() == "aGk="
    assert main(["hash", "abc", "--algo", "md5"]) == 0
    assert main(["b64-decode", "!!!"]) == 1
    assert main(["list"]) == 0


# ---- PDF / image <-> Base64 ----
import base64

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"


def test_pdf_roundtrip():
    b64 = simplutils.pdf_to_b64(PDF)
    res = simplutils.b64_to_pdf(b64)
    assert res.data == PDF and res.filename == "output.pdf"
    uri = simplutils.pdf_to_b64(PDF, data_uri=True)
    assert uri.startswith("data:application/pdf;base64,")
    assert simplutils.b64_to_pdf(uri).data == PDF  # data URI accepted


def test_image_roundtrip():
    uri = simplutils.image_to_b64(PNG, data_uri=True)
    assert uri.startswith("data:image/png;base64,")
    res = simplutils.b64_to_image(uri)
    assert res.data == PNG and res.filename == "output.png" and res.mime == "image/png"
    assert simplutils.b64_to_image(base64.b64encode(PNG).decode().rstrip("=")).data == PNG  # no padding


def test_file_tools_reject_wrong_type():
    with pytest.raises(ToolError):
        simplutils.pdf_to_b64(PNG)
    with pytest.raises(ToolError):
        simplutils.image_to_b64(PDF)
    with pytest.raises(ToolError):
        simplutils.b64_to_pdf(base64.b64encode(PNG).decode())
    with pytest.raises(ToolError):
        simplutils.b64_to_image("not base64 !!")


def test_cli_file_roundtrip(tmp_path, capsys):
    pdf, txt, back = tmp_path / "a.pdf", tmp_path / "a.txt", tmp_path / "b.pdf"
    pdf.write_bytes(PDF)
    assert main(["pdf-to-b64", str(pdf), "-o", str(txt)]) == 0
    assert main(["b64-to-pdf", "-f", str(txt), "-o", str(back)]) == 0
    assert back.read_bytes() == PDF
    img, itxt, iback = tmp_path / "a.png", tmp_path / "i.txt", tmp_path / "back.png"
    img.write_bytes(PNG)
    assert main(["image-to-b64", str(img), "--data-uri", "-o", str(itxt)]) == 0
    assert main(["b64-to-image", "-f", str(itxt), "-o", str(iback)]) == 0
    assert iback.read_bytes() == PNG
    assert main(["pdf-to-b64", str(tmp_path / "missing.pdf")]) == 1
