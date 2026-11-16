"""simplutils - all-in-one developer utilities.

Use as a library:   from simplutils import b64_encode; b64_encode("hi")
Use as a CLI:       simplutils b64-encode "hi"
Use as a local UI:  simplutils ui   (pip install simplutils[ui])
"""
from .registry import TOOLS, FileResult, Tool, ToolError, groups, load_all

load_all()

from .tools.encoding import (  # noqa: E402
    b64_decode, b64_encode, hex_decode, hex_encode,
    html_escape, html_unescape, url_decode, url_encode,
)
from .tools.files import b64_to_image, b64_to_pdf, image_to_b64, pdf_to_b64  # noqa: E402
from .tools.convert import csv_to_json, json_to_csv, json_to_yaml, yaml_to_json  # noqa: E402
from .tools.diff import json_diff, text_diff  # noqa: E402
from .tools.pii import pii_redact, pii_scan, pii_types  # noqa: E402
from .tools.qr import qr_generate, qr_text  # noqa: E402
from .tools.regex import regex_replace, regex_test  # noqa: E402
from .tools.generators import password, random_text, uuid_gen  # noqa: E402
from .tools.mapsearch import map_search  # noqa: E402
from .tools.hashing import hash_text, hmac_text  # noqa: E402
from .tools.images import (  # noqa: E402
    image_compress, image_convert, image_info, image_resize, image_to_pdf,
)
from .tools.pdfs import pdf_extract, pdf_info, pdf_merge, pdf_split, pdf_text  # noqa: E402
from .tools.jsontools import json_format, json_minify  # noqa: E402
from .tools.jwt import jwt_decode  # noqa: E402
from .tools.text import case_convert, count, slugify  # noqa: E402
from .tools.timetools import date_to_ts, now, ts_to_date  # noqa: E402

__version__ = "0.1.0"
