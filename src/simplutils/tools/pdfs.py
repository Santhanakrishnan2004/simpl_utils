"""PDF tools (need pypdf: pip install simplutils[files])."""
import io
import zipfile
from typing import List

from ..registry import FileResult, ToolError, tool

G = "PDF"


def _pypdf():
    try:
        import pypdf
    except ImportError:
        raise ToolError("this tool needs pypdf: pip install simplutils[files]")
    return pypdf


def _reader(data: bytes):
    pypdf = _pypdf()
    if b"%PDF-" not in data[:1024]:
        raise ToolError("this does not look like a PDF file")
    try:
        r = pypdf.PdfReader(io.BytesIO(data))
        if r.is_encrypted and r.decrypt("") == 0:
            raise ToolError("the PDF is password-protected")
        len(r.pages)  # force parsing now so errors surface here
        return r
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"cannot read PDF: {e}")


def parse_pages(spec: str, total: int) -> List[int]:
    """'1-3,5,8-' -> 0-based page indexes (order and repeats kept). 1-based input."""
    out: List[int] = []
    for part in spec.replace(" ", "").split(","):
        if not part:
            continue
        try:
            if "-" in part:
                a, b = part.split("-", 1)
                start, end = int(a) if a else 1, int(b) if b else total
            else:
                start = end = int(part)
        except ValueError:
            raise ToolError(f"bad page range: '{part}' (use e.g. 1-3,5,8-)")
        if start < 1 or end > total or start > end:
            raise ToolError(f"pages must be between 1 and {total} (got '{part}')")
        out.extend(range(start - 1, end))
    if not out:
        raise ToolError("no pages selected")
    return out


def _write(writer) -> bytes:
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@tool("pdf-merge", "PDF Merge", G)
def pdf_merge(files: List[bytes]) -> FileResult:
    """Merge two or more PDFs into one, in the order given."""
    if len(files) < 2:
        raise ToolError("give at least two PDFs to merge")
    writer = _pypdf().PdfWriter()
    for f in files:
        for page in _reader(f).pages:
            writer.add_page(page)
    return FileResult(_write(writer), "merged.pdf", "application/pdf")


@tool("pdf-extract", "PDF Extract Pages", G)
def pdf_extract(data: bytes, pages: str) -> FileResult:
    """Keep only the given pages, e.g. --pages 1-3,5,8- (order and repeats are respected)."""
    r = _reader(data)
    writer = _pypdf().PdfWriter()
    for i in parse_pages(pages, len(r.pages)):
        writer.add_page(r.pages[i])
    return FileResult(_write(writer), "extracted.pdf", "application/pdf")


@tool("pdf-split", "PDF Split", G)
def pdf_split(data: bytes) -> FileResult:
    """Split a PDF into one file per page, delivered as a ZIP."""
    r = _reader(data)
    n = len(r.pages)
    width = max(len(str(n)), 2)
    pypdf = _pypdf()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for i, page in enumerate(r.pages, 1):
            w = pypdf.PdfWriter()
            w.add_page(page)
            z.writestr(f"page_{i:0{width}d}.pdf", _write(w))
    return FileResult(buf.getvalue(), "split.zip", "application/zip")


@tool("pdf-text", "PDF → Text", G)
def pdf_text(data: bytes, pages: str = "") -> str:
    """Extract text from a PDF (all pages, or e.g. --pages 1-3). Scanned PDFs have no text layer."""
    r = _reader(data)
    idx = parse_pages(pages, len(r.pages)) if pages else range(len(r.pages))
    parts = []
    for i in idx:
        try:
            txt = (r.pages[i].extract_text() or "").strip()
        except Exception as e:
            txt = f"(could not extract: {e})"
        parts.append(f"--- page {i + 1} ---\n{txt}")
    out = "\n\n".join(parts)
    if not any(p.split("\n", 1)[1].strip() for p in parts if "\n" in p):
        out += "\n\n(no text found - this may be a scanned PDF)"
    return out


@tool("pdf-info", "PDF Info", G)
def pdf_info(data: bytes) -> str:
    """Show page count, page size, title/author and file size."""
    r = _reader(data)
    meta = r.metadata or {}
    first = r.pages[0].mediabox if len(r.pages) else None
    lines = [f"pages: {len(r.pages)}"]
    if first is not None:
        lines.append(f"page size: {float(first.width):.0f} x {float(first.height):.0f} pt")
    lines.append(f"file size: {len(data):,} bytes")
    lines.append(f"encrypted: {'yes' if r.is_encrypted else 'no'}")
    for key, label in (("/Title", "title"), ("/Author", "author"), ("/Producer", "producer")):
        if meta.get(key):
            lines.append(f"{label}: {meta.get(key)}")
    return "\n".join(lines)
