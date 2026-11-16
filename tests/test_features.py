import io
import zipfile

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

import simplutils
from simplutils import interactive
from simplutils.cli import main
from simplutils.logs import log_path, setup_logging
from simplutils.registry import ToolError


def make_png(w=100, h=50, mode="RGBA", color=(255, 0, 0, 128)) -> bytes:
    buf = io.BytesIO()
    Image.new(mode, (w, h), color).save(buf, "PNG")
    return buf.getvalue()


def make_pdf(pages=3) -> bytes:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=200, height=300)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def size(data: bytes):
    return Image.open(io.BytesIO(data)).size


# ---------------- images ----------------
def test_image_convert_flattens_alpha_for_jpg():
    r = simplutils.image_convert(make_png(), to="jpg")
    assert r.filename == "converted.jpg" and r.mime == "image/jpeg"
    assert Image.open(io.BytesIO(r.data)).format == "JPEG"


def test_image_resize_modes():
    png = make_png(100, 50)
    assert size(simplutils.image_resize(png, width=50).data) == (50, 25)
    assert size(simplutils.image_resize(png, height=100).data) == (200, 100)
    assert size(simplutils.image_resize(png, scale=200).data) == (200, 100)
    assert size(simplutils.image_resize(png, width=40, height=40).data) == (40, 20)  # fits the box
    assert size(simplutils.image_resize(png, width=40, height=40, exact=True).data) == (40, 40)


@pytest.mark.parametrize("kwargs", [{}, {"scale": 50, "width": 10}, {"width": -1}, {"width": 99999}])
def test_image_resize_bad_args(kwargs):
    with pytest.raises(ToolError):
        simplutils.image_resize(make_png(), **kwargs)


def test_image_compress_never_grows_and_caps_width():
    big = io.BytesIO()
    Image.effect_noise((400, 300), 60).convert("RGB").save(big, "JPEG", quality=100)
    out = simplutils.image_compress(big.getvalue(), quality=30)
    assert len(out.data) < len(big.getvalue())
    assert size(simplutils.image_compress(make_png(100, 50), max_width=20).data)[0] == 20


def test_image_info_and_bad_input():
    assert "100 x 50" in simplutils.image_info(make_png())
    with pytest.raises(ToolError):
        simplutils.image_info(b"not an image")
    with pytest.raises(ToolError):
        simplutils.image_convert(b"not an image")


def test_images_to_pdf():
    r = simplutils.image_to_pdf([make_png(), make_png(60, 60)])
    assert r.data.startswith(b"%PDF") and len(PdfReader(io.BytesIO(r.data)).pages) == 2


# ---------------- pdf ----------------
def test_pdf_merge_extract_split_info():
    a, b = make_pdf(3), make_pdf(2)
    merged = simplutils.pdf_merge([a, b])
    assert len(PdfReader(io.BytesIO(merged.data)).pages) == 5
    assert len(PdfReader(io.BytesIO(simplutils.pdf_extract(a, "3,1-2").data)).pages) == 3
    assert len(PdfReader(io.BytesIO(simplutils.pdf_extract(a, "2-").data)).pages) == 2
    z = zipfile.ZipFile(io.BytesIO(simplutils.pdf_split(a).data))
    assert z.namelist() == ["page_01.pdf", "page_02.pdf", "page_03.pdf"]
    assert "pages: 3" in simplutils.pdf_info(a)


@pytest.mark.parametrize("spec", ["0", "4", "3-1", "x", ""])
def test_pdf_extract_bad_pages(spec):
    with pytest.raises(ToolError):
        simplutils.pdf_extract(make_pdf(3), spec)


def test_pdf_errors():
    with pytest.raises(ToolError):
        simplutils.pdf_merge([make_pdf(1)])  # needs two
    with pytest.raises(ToolError):
        simplutils.pdf_info(b"hello")
    assert "no text found" in simplutils.pdf_text(make_pdf(1))


def test_cli_multi_file_tools(tmp_path):
    a, b, out = tmp_path / "a.pdf", tmp_path / "b.pdf", tmp_path / "m.pdf"
    a.write_bytes(make_pdf(1))
    b.write_bytes(make_pdf(2))
    assert main(["pdf-merge", str(a), str(b), "-o", str(out)]) == 0
    assert len(PdfReader(str(out)).pages) == 3
    assert main(["pdf-merge", str(a)]) == 1  # only one file -> friendly error


# ---------------- logging ----------------
def test_logging_records_runs_without_content():
    setup_logging()
    simplutils.TOOLS["hmac"].run("super-secret-message", key="top-secret-key")
    simplutils.TOOLS["hash"].run("another-secret", algo="md5")
    text = log_path().read_text(encoding="utf-8")
    assert "tool=hmac ok" in text and "tool=hash ok" in text
    assert "algo': 'md5'" in text  # choices are fine to log
    for secret in ("super-secret-message", "top-secret-key", "another-secret"):
        assert secret not in text
    assert "<hidden>" in text


def test_logging_records_failures():
    setup_logging()
    with pytest.raises(ToolError):
        simplutils.TOOLS["b64-decode"].run("!!!")
    assert "tool=b64-decode failed" in log_path().read_text(encoding="utf-8")


def test_logs_command(capsys):
    assert main(["b64-encode", "x"]) == 0
    capsys.readouterr()
    assert main(["logs"]) == 0
    assert "tool=b64-encode ok" in capsys.readouterr().out
    assert main(["logs", "--path"]) == 0
    assert capsys.readouterr().out.strip().endswith("simplutils.log")


# ---------------- ease of use ----------------
def test_typo_suggestion(capsys):
    with pytest.raises(SystemExit) as e:
        main(["b64encode", "hi"])
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert "Did you mean" in err and "b64-encode" in err


def test_bad_option_choice_suggestion(capsys):
    with pytest.raises(SystemExit):
        main(["hash", "abc", "--algo", "sha25"])
    assert "sha256" in capsys.readouterr().err


def test_list_filter(capsys):
    assert main(["list", "pdf"]) == 0
    out = capsys.readouterr().out
    assert "pdf-merge" in out and "uuid" not in out


def feed(monkeypatch, answers):
    it = iter(answers)

    def fake(prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr("builtins.input", fake)


def test_menu_text_tool(monkeypatch, capsys):
    # search -> text -> option (urlsafe? n) -> skip save -> back to menu -> quit
    feed(monkeypatch, ["b64-encode", "hello", "n", "", "", "q"])
    assert interactive.start() == 0
    assert "aGVsbG8=" in capsys.readouterr().out


def test_menu_by_number_with_choice_option(monkeypatch, capsys):
    # numbering follows group order, so look the number up the way the menu does
    num = interactive.Menu().numbered.index(simplutils.TOOLS["hash"]) + 1
    feed(monkeypatch, [str(num), "abc", "md5", "", "", "q"])
    assert interactive.start() == 0
    assert "900150983cd24fb0d6963f7d28e17f72" in capsys.readouterr().out


def test_menu_file_tool_saves_result(monkeypatch, capsys, tmp_path):
    src, dst = tmp_path / "in.png", tmp_path / "out.jpg"
    src.write_bytes(make_png())
    # quoted path (as pasted by drag & drop), options: to=jpg, quality default; save as dst
    feed(monkeypatch, ["image-convert", f'"{src}"', "jpg", "", str(dst), "", "q"])
    assert interactive.start() == 0
    assert Image.open(dst).format == "JPEG"


def test_menu_reports_problem_and_continues(monkeypatch, capsys):
    feed(monkeypatch, ["b64-decode", "!!!", "", "", "", "q"])
    assert interactive.start() == 0
    assert "Problem:" in capsys.readouterr().out


def test_menu_no_match_then_quit(monkeypatch, capsys):
    feed(monkeypatch, ["zzzzzz", "q"])
    assert interactive.start() == 0
    assert "Nothing matches" in capsys.readouterr().out


# ---------------- Windows-style text files (BOM / UTF-16) and stdin ----------------
import io as _io
import sys as _sys


class _FakeStdin:
    def __init__(self, raw: bytes):
        self.buffer = _io.BytesIO(raw)

    def isatty(self):
        return False


@pytest.mark.parametrize("raw", [
    b'\xef\xbb\xbf{"a": 1}',                 # UTF-8 with BOM (Notepad, PowerShell Set-Content)
    '{"a": 1}'.encode("utf-16"),             # UTF-16 LE with BOM (PowerShell '>' redirect)
    '{"a": 1}'.encode("utf-16-be").join([b"\xfe\xff", b""]),  # UTF-16 BE with BOM
    b'{"a": 1}',                             # plain UTF-8
])
def test_text_files_with_bom_or_utf16(tmp_path, capsys, raw):
    f = tmp_path / "in.json"
    f.write_bytes(raw)
    assert main(["json-minify", "-f", str(f)]) == 0
    assert capsys.readouterr().out.strip() == '{"a":1}'


@pytest.mark.parametrize("raw", [b'\xef\xbb\xbf{"a": 1}\r\n', '{"a": 1}'.encode("utf-16"), b'{"a": 1}\n'])
def test_stdin_with_bom_or_utf16(monkeypatch, capsys, raw):
    monkeypatch.setattr(_sys, "stdin", _FakeStdin(raw))
    assert main(["json-minify"]) == 0
    assert capsys.readouterr().out.strip() == '{"a":1}'


def test_binary_file_as_text_is_a_friendly_error(tmp_path, capsys):
    f = tmp_path / "bin.dat"
    f.write_bytes(b"\x80\x81\x82\xfe\xfd")
    assert main(["json-minify", "-f", str(f)]) == 1
    assert "not valid UTF-8" in capsys.readouterr().err


def test_diff_tolerates_bom():
    out = simplutils.text_diff([b"\xef\xbb\xbfhello\n", b"hello\n"])
    assert out == "No differences."
