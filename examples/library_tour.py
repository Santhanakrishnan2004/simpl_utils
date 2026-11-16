"""A tour of simplutils used as a Python library.

Run it from the project folder:   python examples/library_tour.py
(Needs the extras for the image / PDF / YAML / QR sections:  pip install "simplutils[all]")
"""
import io
import tempfile
from pathlib import Path

import simplutils as eu
from PIL import Image
from pypdf import PdfReader, PdfWriter

DATA = Path(__file__).parent / "sample_data"


def title(text: str) -> None:
    print(f"\n=== {text} ===")


# ------------------------------------------------------------------ encoding & hashing
title("Encoding and hashing")
print(eu.b64_encode("hello world"))                       # aGVsbG8gd29ybGQ=
print(eu.b64_decode("aGVsbG8gd29ybGQ="))                  # hello world
print(eu.url_encode("name=Asha & co/önemli"))             # name%3DAsha%20%26%20co%2F%C3%B6nemli
print(eu.hash_text("hello", algo="sha256"))
print(eu.hmac_text("message", key="secret"))

# ------------------------------------------------------------------ JSON, YAML, CSV
title("JSON / YAML / CSV")
config = (DATA / "config_v1.json").read_text()
print(eu.json_to_yaml(config))
print(eu.csv_to_json((DATA / "people.csv").read_text(), infer_types=True)[:120], "...")
print(eu.json_to_csv('[{"id":1,"user":{"name":"Asha"}},{"id":2,"user":{"name":"Ravi"}}]'))

# ------------------------------------------------------------------ comparing
title("Diff")
print(eu.json_diff([(DATA / "config_v1.json").read_bytes(), (DATA / "config_v2.json").read_bytes()]))
print(eu.text_diff([(DATA / "notes_v1.txt").read_bytes(), (DATA / "notes_v2.txt").read_bytes()]))

# ------------------------------------------------------------------ privacy
title("PII scan and redact")
log_text = (DATA / "server.log").read_text()
print(eu.pii_scan(log_text).split("Details")[0])           # summary only
print(eu.pii_redact(log_text).splitlines()[1])             # one redacted line
print(eu.pii_redact("mail a@x.com, again a@x.com, and b@x.com", mode="hash"))

# ------------------------------------------------------------------ time, JWT, generators
title("Time, JWT, generators")
print(eu.ts_to_date("1700000000"))
print(eu.jwt_decode("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMiLCJleHAiOjF9.sig")[:80], "...")
print(eu.uuid_gen(2))
print(eu.password(20))

# ------------------------------------------------------------------ files: images and PDFs
# Tools that return files give you a FileResult with .data (bytes), .filename and .mime
title("Images and PDFs (files in, files out)")
work = Path(tempfile.mkdtemp(prefix="simplutils_demo_"))

png = io.BytesIO()
Image.new("RGB", (400, 200), (30, 120, 200)).save(png, "PNG")
png_bytes = png.getvalue()
print(eu.image_info(png_bytes))

small = eu.image_resize(png_bytes, width=100)               # keeps aspect ratio -> 100x50
(work / small.filename).write_bytes(small.data)
print("resized ->", small.filename, Image.open(io.BytesIO(small.data)).size)

webp = eu.image_convert(png_bytes, to="webp", quality=80)
print("converted ->", webp.filename, webp.mime)

pdf = eu.image_to_pdf([png_bytes, small.data])              # one image per page
print("images -> pdf pages:", len(PdfReader(io.BytesIO(pdf.data)).pages))

w = PdfWriter()
for _ in range(5):
    w.add_blank_page(width=200, height=300)
buf = io.BytesIO()
w.write(buf)
five_pages = buf.getvalue()
print(eu.pdf_info(five_pages))
part = eu.pdf_extract(five_pages, pages="2-3,5")
print("extract 2-3,5 -> pages:", len(PdfReader(io.BytesIO(part.data)).pages))
merged = eu.pdf_merge([five_pages, part.data])
print("merged pages:", len(PdfReader(io.BytesIO(merged.data)).pages))

b64 = eu.pdf_to_b64(five_pages)                             # PDF -> Base64 text ...
back = eu.b64_to_pdf(b64)                                   # ... and back to a PDF file
print("pdf <-> base64 roundtrip identical:", back.data == five_pages)

qr = eu.qr_generate("https://example.com", kind="png", scale=6)
(work / qr.filename).write_bytes(qr.data)
print("QR saved:", work / qr.filename)

# ------------------------------------------------------------------ errors are friendly
title("Errors")
try:
    eu.b64_decode("this is not base64!!!")
except eu.ToolError as e:                                  # bad user input -> ToolError, never a crash
    print("ToolError:", e)

print(f"\nFiles written to: {work}")
