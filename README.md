# simplutils

**All-in-one developer utilities in a single package:** Base64, hashing, JSON/YAML/CSV, JWT,
regex, diff, PDF and image tools, QR codes, and PII redaction.
Use it as a **Python library**, a **command-line tool**, a **step-by-step menu** (nothing to
memorize), or a **local web page**.

Everything runs **offline on your own machine**. Nothing you process is uploaded anywhere, which
matters when the text contains tokens, passwords, or customer data.

- 50 tools in 15 groups
- Zero required dependencies (image/PDF/YAML/QR/UI features are optional extras)
- Friendly errors, typo suggestions, and a privacy-respecting log

After the first PyPI release, install it with `python -m pip install simplutils`. See
[PUBLISHING.md](PUBLISHING.md) to publish the source on GitHub and release the package to PyPI.

---

## Contents

1. [Install](#1-install)
2. [Quick start](#2-quick-start)
3. [The interactive menu](#3-the-interactive-menu-nothing-to-memorize)
4. [Command-line guide](#4-command-line-guide)
5. [Tool reference with examples](#5-tool-reference-with-examples)
6. [Recipes (real-world workflows)](#6-recipes-real-world-workflows)
7. [Using it as a Python library](#7-using-it-as-a-python-library)
8. [The web UI](#8-the-web-ui)
9. [Logging and privacy](#9-logging-and-privacy)
10. [PII redaction: what it does and doesn't do](#10-pii-redaction-what-it-does-and-doesnt-do)
11. [Troubleshooting and FAQ](#11-troubleshooting-and-faq)
12. [Extending: add your own tool](#12-extending-add-your-own-tool)
13. [Development and releasing](#13-development-and-releasing)

---

## 1. Install

Requires **Python 3.9 or newer** (developed and tested on Python 3.13).

```bash
python -m pip install simplutils            # core: text tools, no other dependencies
python -m pip install "simplutils[all]"     # everything: images, PDFs, YAML, QR codes, web UI
```

Pick only what you need:

| Command | Adds | Needed for |
|---|---|---|
| `pip install simplutils` | nothing extra | encoding, hashing, JSON, JWT, regex, diff, CSV, time, PII, generators |
| `pip install "simplutils[files]"` | Pillow, pypdf | image tools and PDF tools |
| `pip install "simplutils[extras]"` | PyYAML, segno | JSON ↔ YAML and QR codes |
| `pip install "simplutils[ui]"` | NiceGUI | the local web page (`simplutils ui`) |
| `pip install "simplutils[all]"` | all of the above | everything |

If you run a tool whose extra isn't installed, it tells you exactly what to do, for example:
`error: this tool needs Pillow: pip install simplutils[files]`.

**Tip for command-line use:** `pipx install "simplutils[all]"` installs it in its own isolated
environment and puts `simplutils` on your PATH.

**Install from a wheel or source folder** (before or without publishing to PyPI):

```bash
pip install simplutils-0.1.0-py3-none-any.whl          # a built wheel file
pip install "simplutils-0.1.0-py3-none-any.whl[all]"   # ... with extras
pip install -e ".[all,dev]"                          # editable install from the project folder
```

Check it worked:

```bash
simplutils --version
simplutils list
```

If `simplutils` isn't found (common on Windows), use `python -m simplutils ...` instead. See
[Troubleshooting](#11-troubleshooting-and-faq).

---

## 2. Quick start

There are four ways to use the same tools. Pick whichever you like.

**1. The menu: just type `simplutils`.** No flags to remember.

```text
$ simplutils
```

**2. Direct commands: fast and scriptable.**

```bash
simplutils b64-encode "hello world"        # aGVsbG8gd29ybGQ=
simplutils hash "hello" --algo md5         # 5d41402abc4b2a76b9719d911017c592
echo "a@b.com" | simplutils pii-redact     # [EMAIL]
```

**3. Python code.**

```python
import simplutils as eu
eu.b64_encode("hello world")             # 'aGVsbG8gd29ybGQ='
```

**4. A web page on your own machine.**

```bash
simplutils ui                              # opens http://localhost:8080
```

---

## 3. The interactive menu (nothing to memorize)

Run `simplutils` with no arguments (or `simplutils menu`). You get a numbered list of every tool.

- Type a **number** to pick a tool, or a **word to search** (`pdf`, `base64`, `qr`).
- It asks for the input, then for each option, showing the default. **Press Enter to accept it.**
- For files: **drag the file into the window** to paste its path (quotes are handled for you).
- For text: type `@path\to\file.txt` to load it from a file, or `<<` to paste several lines
  (finish with an empty line).
- At the end it offers to **save the result** to a file. Files such as a merged PDF are saved
  with a sensible default name.
- `?` shows the list again, `q` quits. A mistake gives a friendly message, then back to the menu.

A real session (hashing a word):

```text
Tool> hash

== Hash ==
Compute a hash digest of the text.

Enter the text. Type @path to load it from a file, or << for multi-line input.
Text> hello

Options (just press Enter to accept the default):
algo [sha256, sha512, sha1, md5] (Enter = sha256): md5

5d41402abc4b2a76b9719d911017c592

Save the result to a file? Type a path, or Enter to skip:
Press Enter to go back to the menu...
```

---

## 4. Command-line guide

### The general shape

```text
simplutils <tool> [input] [--options] [-o output-file]
simplutils list [word]       show tools, optionally filtered ("simplutils list pdf")
simplutils <tool> -h         show the options of one tool
simplutils menu              the interactive menu
simplutils ui                the web UI
simplutils logs              recent log lines
simplutils -v <tool> ...     also print log messages on screen (-v goes BEFORE the tool name)
```

### Giving input

| Tool takes | You provide | Example |
|---|---|---|
| **text** | an argument, `-f file`, or piped stdin | `simplutils hash "hello"` · `simplutils hash -f notes.txt` · `type notes.txt \| simplutils hash` |
| **one file** | its path (`-` reads binary stdin) | `simplutils image-info photo.png` |
| **several files** | their paths, in order | `simplutils pdf-merge a.pdf b.pdf c.pdf -o all.pdf` |
| **nothing** | nothing | `simplutils uuid --count 3` |

Text files may be UTF-8 (with or without a BOM) or UTF-16. This covers files saved by Windows
Notepad and PowerShell.

### Getting output

- By default the result is **printed**.
- `-o file` **saves** it instead. For tools that make files (a PDF, an image, a ZIP), `-o` sets the
  file name; without it the tool uses a default such as `merged.pdf` in the current folder.

### Options

- Option names match the tool's parameters with dashes: `--no-symbols`, `--infer-types`.
- Yes/no options are plain flags: `--urlsafe`, `--ignore-case`.
- Choice options list their values in `-h`: `--algo sha256|sha512|sha1|md5`.
- Mistype a command or a choice and it suggests the right one:

```text
$ simplutils b64encode hi
simplutils: error: unknown choice 'b64encode'. Did you mean: b64-encode, b64-decode, url-encode? See all tools with: simplutils list
```

### Exit codes (for scripts and CI)

| Code | Meaning |
|---|---|
| `0` | success |
| `1` | the tool reported a problem (bad input, missing file, wrong file type) |
| `2` | command-line usage error (unknown option or command) |

---

## 5. Tool reference with examples

All examples below were run for real. Every tool can also be called from Python
([section 7](#7-using-it-as-a-python-library)).

### Encoding (8 tools)

| Tool | What it does |
|---|---|
| `b64-encode` / `b64-decode` | Base64. Options: `--urlsafe`. Decode accepts missing `=` padding. |
| `url-encode` / `url-decode` | Percent-encoding. Option: `--plus` (spaces as `+`). |
| `hex-encode` / `hex-decode` | Text ↔ hexadecimal. |
| `html-escape` / `html-unescape` | `&`, `<`, `>` and quotes ↔ HTML entities. |

```text
$ simplutils b64-encode "hello world"
aGVsbG8gd29ybGQ=
$ simplutils b64-decode "aGVsbG8gd29ybGQ="
hello world
$ simplutils url-decode "name%3DAsha%20%26%20co"
name=Asha & co
$ simplutils hex-encode "hi"
6869
$ simplutils html-escape '<a href="x">Tom & Jerry</a>'
&lt;a href=&quot;x&quot;&gt;Tom &amp; Jerry&lt;/a&gt;
```

### Files ↔ Base64 (4 tools)

Turn a PDF or image into Base64 text (for JSON payloads, HTML, emails) and back.

| Tool | What it does |
|---|---|
| `pdf-to-b64` | PDF file → Base64. `--data-uri` gives `data:application/pdf;base64,...` |
| `b64-to-pdf` | Base64 (or a data URI) → PDF file |
| `image-to-b64` | PNG/JPG/GIF/WebP/BMP/ICO/SVG → Base64. `--data-uri` adds the right `data:image/...` prefix |
| `b64-to-image` | Base64 (or data URI) → image file; the format is detected automatically |

```bash
simplutils pdf-to-b64 report.pdf -o report.txt        # long Base64, so save it to a file
simplutils b64-to-pdf -f report.txt -o copy.pdf       # and back
simplutils image-to-b64 logo.png --data-uri           # prints data:image/png;base64,iVBOR...
simplutils b64-to-image -f logo.txt -o logo.png
```

The tools check the content: giving a PNG to `pdf-to-b64` fails with a clear message instead of
producing nonsense. Large Base64 is too long for a command line, so use `-o` / `-f`.

### Images (5 tools): needs `simplutils[files]`

| Tool | What it does |
|---|---|
| `image-info` | Format, size in pixels, colour mode, file size |
| `image-resize` | `--width`, `--height`, or `--scale` (percent). Aspect ratio is kept; width+height fits inside the box, `--exact` forces the size. Max 20000 px per side |
| `image-convert` | `--to png\|jpg\|webp\|bmp\|gif`, `--quality 1-100`. Transparency becomes white for JPG |
| `image-compress` | `--quality` (JPG/WebP), PNG is optimised losslessly, optional `--max-width`. Never returns a bigger file |
| `image-to-pdf` | One or more images → one PDF, one image per page, in the order given |

```bash
simplutils image-info photo.png
simplutils image-resize photo.png --width 800 -o small.png      # height follows automatically
simplutils image-resize photo.png --scale 50 -o half.png        # 50 %
simplutils image-convert photo.png --to webp --quality 80 -o photo.webp
simplutils image-compress photo.jpg --quality 60 --max-width 1600 -o photo_small.jpg
simplutils image-to-pdf page1.png page2.png -o album.pdf
```

```text
$ simplutils image-info small.png
format: PNG
size: 150 x 100 px
mode: RGB
file size: 230 bytes
```

Animated GIF/WebP files keep only their first frame when converted or resized. Photos are
rotated according to their EXIF orientation.

### PDF (5 tools): needs `simplutils[files]`

| Tool | What it does |
|---|---|
| `pdf-info` | Page count, page size, file size, encryption, title/author |
| `pdf-merge` | Join two or more PDFs, in the order given |
| `pdf-extract` | Keep only some pages: `--pages 1-3,5,8-` (1-based; `8-` means "from 8 to the end"; order and repeats are respected) |
| `pdf-split` | One PDF per page, delivered as a ZIP (`page_01.pdf`, `page_02.pdf`, ...) |
| `pdf-text` | Extract text, optionally `--pages 1-3`. Scanned PDFs have no text to extract and are reported as such |

```bash
simplutils pdf-info contract.pdf
simplutils pdf-merge cover.pdf body.pdf appendix.pdf -o full.pdf
simplutils pdf-extract book.pdf --pages 1-3,10 -o excerpt.pdf
simplutils pdf-split book.pdf -o pages.zip
simplutils pdf-text paper.pdf --pages 1-2
```

```text
$ simplutils pdf-info five_pages.pdf
pages: 5
page size: 200 x 300 pt
file size: 911 bytes
encrypted: no
```

Password-protected PDFs are not supported yet (you get a clear "password-protected" message).

### Privacy / PII (3 tools)

See [section 10](#10-pii-redaction-what-it-does-and-doesnt-do) for details and limits.

| Tool | What it does |
|---|---|
| `pii-scan` | Report what sensitive data the text contains and where, **without printing the values** |
| `pii-redact` | Replace it with placeholders. `--mode label\|mask\|hash`, `--only email,phone`, `--exclude phone` |
| `pii-types` | List every type that can be detected |

```text
$ simplutils pii-scan -f server.log
Found 9 potential item(s) of 9 type(s)

Summary
  email           1
  ip-address      1
  phone           1
  pan             1
  credit-card     1
  bearer-token    1
  url-password    1
  aws-key         1
  password        1

Details (values are hidden)
  line 1     email           pr***
  line 2     phone           +9***
  line 3     credit-card     41***
  ...
```

```text
$ echo "Contact priya@corp.in or +91 98765 43210, key AKIAIOSFODNN7EXAMPLE" | simplutils pii-redact
Contact [EMAIL] or [PHONE], key [AWS-KEY]

$ echo "... same text ..." | simplutils pii-redact --mode hash
Contact [EMAIL#201c7155] or [PHONE#407d0cf8], key [AWS-KEY#702f2990]     (tokens differ on every run)
```

### Convert (4 tools)

| Tool | What it does |
|---|---|
| `json-to-yaml` / `yaml-to-json` | JSON ↔ YAML (needs `simplutils[extras]`). Key order is kept. A YAML file with several `---` documents becomes a JSON list |
| `json-to-csv` | JSON array of objects → CSV. Nested objects become dotted columns (`user.name`); lists stay as JSON text |
| `csv-to-json` | CSV (first row = headers) → JSON. `--delimiter auto\|comma\|semicolon\|tab\|pipe`; `--infer-types` turns `31` into a number, `true` into a boolean, empty cells into `null` |

```text
$ simplutils yaml-to-json "name: demo
tags: [a, b]"
{
  "name": "demo",
  "tags": [
    "a",
    "b"
  ]
}

$ simplutils csv-to-json -f people.csv --infer-types
[
  {
    "name": "Asha",
    "age": 31,
    "city": "Chennai",
    "active": true
  },
  ...                                  (one object per row; output shortened here)
]
```

### Compare (2 tools)

Both take **two files: first the "before", then the "after"**.

```text
$ simplutils json-diff config_v1.json config_v2.json
~ database.host: "db1.internal" -> "db2.internal"
+ features[2]: "reports"
- legacy_mode: true
~ replicas: 2 -> 4
+ timeout_seconds: 30
~ version: "1.4.0" -> "1.5.0"

$ simplutils diff notes_v1.txt notes_v2.txt
--- before
+++ after
@@ -1,4 +1,5 @@
 Meeting notes
 - Review the billing release
-- Fix the refund bug
+- Fix the refund bug (done)
 - Plan the Q4 roadmap
+- Book the retro
```

`+` added, `-` removed, `~` changed. `diff` options: `--context N` (lines of context, default 3),
`--ignore-whitespace`.

### QR codes (2 tools): needs `simplutils[extras]`

```bash
simplutils qr-generate "https://example.com" -o qr.png            # PNG image
simplutils qr-generate "https://example.com" --kind svg -o qr.svg # SVG
simplutils qr-text "https://example.com"                          # scannable right in the terminal
```

Options: `--scale 1-50` (pixel size of each square), `--error L|M|Q|H` (error correction: higher
means more damage tolerance but a denser code). Generating only; reading QR codes is not supported.

### Text and JSON (7 tools)

| Tool | What it does |
|---|---|
| `json-format` | Validate and pretty-print. `--indent 2`, `--sort-keys` |
| `json-minify` | Validate and compact onto one line |
| `regex-test` | List every match with position and capture groups. `--pattern` required; `--ignore-case`, `--multiline`, `--dotall` |
| `regex-replace` | Replace matches; use `\1` or `\g<name>` in `--replacement` |
| `case-convert` | `--style snake\|camel\|pascal\|kebab\|constant\|title\|upper\|lower` |
| `slugify` | URL-friendly slug (accents removed) |
| `count` | Characters, words, lines |

```text
$ simplutils json-format '{"b":1,"a":[1,2]}' --sort-keys     # (PowerShell: see the FAQ on quoting)
{
  "a": [
    1,
    2
  ],
  "b": 1
}

$ simplutils regex-test "order 123, order 4567" --pattern "order (\d+)"
2 matches
#1  [0:9]  'order 123'
      group 1: '123'
#2  [11:21]  'order 4567'
      group 1: '4567'

$ simplutils regex-replace "john smith" --pattern "(\w+) (\w+)" --replacement '\2, \1'
smith, john

$ simplutils case-convert "HTTPServerError" --style snake
http_server_error

$ simplutils slugify "Héllo, World! 2026"
hello-world-2026

$ simplutils count "one two three
four five"
characters: 23
words: 5
lines: 2
```

> Regex patterns are run as given. A badly written pattern on very large input can be slow,
> because Python's `re` has no timeout.

### Hashing and security (3 tools)

```text
$ simplutils hash "hello" --algo sha256
2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
$ simplutils hmac "message" --key secret
8b5f48702995c1598c573db1e21866a9b825d4a794d169d7060a03605796360b
$ simplutils jwt-decode "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMiLCJleHAiOjF9.sig"
{
  "header": {
    "alg": "HS256"
  },
  "payload": {
    "sub": "123",
    "exp": 1
  },
  "times": {
    "exp": "1970-01-01T00:00:01+00:00"
  },
  "expired": true
}
```

`hash --algo` accepts `sha256` (default), `sha512`, `sha1`, `md5`. `jwt-decode` shows the header and
payload and whether the token has expired; **it does not verify the signature**.

### Time (3 tools)

```text
$ simplutils ts-to-date 1700000000        # seconds or milliseconds, detected automatically
UTC:   2023-11-14T22:13:20+00:00
Local: 2023-11-15T03:43:20+05:30        # (your own time zone)
$ simplutils date-to-ts "2026-01-31 14:30"   # no zone given = UTC
seconds: 1769869800
milliseconds: 1769869800000
$ simplutils now
```

### Generators (3 tools)

```bash
simplutils uuid --count 5                 # random UUIDs (v4)
simplutils password --length 20           # cryptographically secure; --no-symbols for letters+digits
simplutils random-text --length 40        # random text of exactly 40 characters
simplutils random-text --length 12 --charset hex --count 3    # three 12-character hex strings
simplutils random-text --length 60 --charset words            # lorem-style words, cut to exactly 60 characters
simplutils random-text --length 10 --custom ACGT              # only the characters you give
```

`--charset` is one of `alnum` (default), `letters`, `lower`, `upper`, `digits`, `hex`, `words`.
`--custom` overrides it. Length is 1-1,000,000, count 1-1000. Uses the operating system's random source.
Use `password` for secrets; `random-text` is for test data, IDs and filler.

### Data: search a map without writing a snippet (1 tool)

`map-search` finds, counts and reads values in a JSON object/list (or YAML, with `simplutils[extras]`),
at any nesting depth, in one pass. Sample `users.json`:

```json
{"users": [{"name": "Asha", "city": "Chennai", "age": 31},
           {"name": "Ravi", "city": "Pune", "age": 28},
           {"name": "Meena", "city": "Chennai", "age": 31}],
 "meta": {"city": "Chennai"}}
```

| You want | Command |
|---|---|
| Every key called `city`, with its path | `simplutils map-search -f users.json --query city` |
| How many values equal `Chennai` | `simplutils map-search -f users.json --action count --by value --query Chennai` |
| Where the value `Ravi` is | `simplutils map-search -f users.json --by value --query Ravi` |
| Values containing `a` | `... --by value --query a --match contains` |
| Regex, ignoring case | `... --by value --query "^c" --match regex --ignore-case` |
| How often each city appears | `simplutils map-search -f users.json --action tally --query city` |
| One value by path | `simplutils map-search -f users.json --action get --query "users[0].name"` |
| All names | `simplutils map-search -f users.json --action get --query "users[*].name"` |

```
$ simplutils map-search -f users.json --query city
4 matching keys
users[0].city: "Chennai"
users[1].city: "Pune"
users[2].city: "Chennai"
meta.city: "Chennai"

$ simplutils map-search -f users.json --action tally --query city
4 match(es) across 2 distinct value(s)
"Chennai"  3
"Pune"     1
```

- `--action`: `find` (default, lists paths), `count` (just the number), `get` (read a path), `tally` (count each distinct value of a key).
- `--by`: `key` (default) or `value`. `--match`: `exact` (default), `contains`, `regex`. `--limit`: lines shown for find/tally (default 100).
- Paths use `a.b`, `list[0]`, `list[-1]` (last), `list[*]` (all) and `["key.with.dots"]`. The paths that `find` prints work in `get`.
- Numbers and booleans match as text (`31`, `true`). The input must be an object or list.
- As a library, pass your Python dict or list straight in (or JSON text):
  ```python
  from simplutils import map_search
  users = {"users": [{"name": "Asha", "city": "Chennai"}, {"name": "Ravi", "city": "Pune"}]}
  map_search(users, query="city")                                      # keys named city, with paths
  map_search(users, action="count", by="value", query="Chennai")       # -> "1"
  map_search(users, action="tally", query="city")                      # count of each distinct city
  map_search(users, action="get", query="users[*].name")               # JSON text of ["Asha", "Ravi"]
  ```
  The result is always a string; for `get`, use `json.loads(...)` to turn it back into Python.
- Regex searches have no timeout, so avoid patterns from untrusted sources on large files.

---

## 6. Recipes (real-world workflows)

**Clean a log before pasting it into a chat, ticket, or AI assistant**

```bash
simplutils pii-scan   -f app.log               # what's in there? (values hidden)
simplutils pii-redact -f app.log -o clean.log  # emails, cards, keys, passwords become [LABELS]
```

Review `clean.log` before sharing. Detection is heuristic ([limits](#10-pii-redaction-what-it-does-and-doesnt-do)).

**See what changed between two config files**

```bash
simplutils json-diff old.json new.json         # structural: shows paths like database.host
simplutils diff old.txt new.txt                # line by line
```

**Turn photos into one PDF, then trim it**

```bash
simplutils image-to-pdf scan1.jpg scan2.jpg scan3.jpg -o scans.pdf
simplutils pdf-extract scans.pdf --pages 1,3 -o selected.pdf
```

**Shrink images for a website**

```bash
simplutils image-resize hero.png --width 1600 -o hero_1600.png
simplutils image-convert hero_1600.png --to webp --quality 80 -o hero.webp
```

**Embed a PDF or image in a JSON API request**

```bash
simplutils pdf-to-b64 invoice.pdf -o invoice.b64         # use the file contents as a JSON string value
simplutils image-to-b64 logo.png --data-uri -o logo.uri  # ready for <img src="..."> or CSS url(...)
```

**Debug a login token**

```bash
simplutils jwt-decode "<paste token>"           # who is it for, and has it expired?
simplutils ts-to-date 1700000000                # what time is this timestamp?
```

**Convert a spreadsheet export into an API payload**

```bash
simplutils csv-to-json -f export.csv --infer-types -o payload.json
simplutils json-to-yaml -f payload.json
```

**Make a QR code for a Wi-Fi network** (the text is the standard Wi-Fi format)

```bash
simplutils qr-generate "WIFI:T:WPA;S:MyNetwork;P:MyPassword;;" -o wifi.png
```

**Build a repeatable step into a script**

```bash
simplutils pii-redact -f in.log -o out.log || exit 1    # exit code 0 = success, 1 = problem
```

---

## 7. Using it as a Python library

```python
import simplutils as eu
```

Every tool is a function with the same name as the command, using underscores:

```python
eu.b64_encode("hello world")                  # 'aGVsbG8gd29ybGQ='
eu.hash_text("hello", algo="sha256")          # 2cf24dba...
eu.hmac_text("message", key="secret")
eu.json_diff([before_bytes, after_bytes])     # "~ version: ..."
eu.pii_redact("mail a@x.com", mode="hash")    # e.g. 'mail [EMAIL#83c61eca]' (token differs per run)
```

Function names differ slightly from the command in a few places: `hash` → `hash_text`,
`hmac` → `hmac_text`, `uuid` → `uuid_gen`, `diff` → `text_diff`. See `simplutils.TOOLS`
for the full list.

### Tools that take or return files

- A tool that takes **one file** receives `bytes`; one that takes **several** receives a
  `list` of `bytes`.
- A tool that **makes a file** returns a `FileResult` with `.data` (bytes), `.filename` and `.mime`.

```python
from pathlib import Path
import simplutils as eu

png = Path("photo.png").read_bytes()

small = eu.image_resize(png, width=800)              # FileResult
Path(small.filename).write_bytes(small.data)         # 'resized.png'

merged = eu.pdf_merge([Path("a.pdf").read_bytes(), Path("b.pdf").read_bytes()])
Path("merged.pdf").write_bytes(merged.data)

pages = eu.pdf_extract(Path("book.pdf").read_bytes(), pages="1-3,10")
b64 = eu.pdf_to_b64(Path("book.pdf").read_bytes())   # str
```

### Errors

Bad input raises `simplutils.ToolError` with a readable message (never a cryptic traceback):

```python
try:
    eu.b64_decode("not base64!!!")
except eu.ToolError as e:
    print(e)     # invalid Base64 (try the urlsafe option?): Only base64 data is allowed
```

### Running a tool by name

```python
eu.TOOLS["hash"].run("hello", algo="md5")             # '5d41402a...'   (also logged)
for name, tool in eu.TOOLS.items():
    print(name, "-", tool.description)
```

Calling `eu.hash_text(...)` directly is the plain function; `TOOLS[name].run(...)` additionally
validates options, applies defaults, and writes the log entry.

A runnable tour of the library is in [`examples/library_tour.py`](examples/library_tour.py) and of
the command line in [`examples/cli_tour.py`](examples/cli_tour.py), with sample files in
[`examples/sample_data/`](examples/sample_data/).

---

## 8. The web UI

```bash
pip install "simplutils[ui]"
simplutils ui                     # opens http://localhost:8080
simplutils ui --port 9000         # another port
simplutils ui --no-browser        # don't open a browser window
```

A searchable sidebar lists every tool. Type or paste into the input box and the result updates
live; options appear as drop-downs and switches. File tools have an upload box (with an image
preview), multi-file tools take several uploads in order, and tools that make files show a
**Download file** button. There is a dark-mode toggle.

It runs a small server **on your own machine only**: nothing is hosted, and nothing leaves your
computer. Use the search box at the top of the sidebar to find any tool.

---

## 9. Logging and privacy

Every run is recorded in a rotating log file (1 MB, 3 backups):

| | |
|---|---|
| Default location | `~/.simplutils/simplutils.log` (on Windows: `C:\Users\<you>\.simplutils\simplutils.log`) |
| Change the folder | set the environment variable `simplutils_LOG_DIR` |

```bash
simplutils logs                # last 20 lines
simplutils logs -n 100
simplutils logs --path         # where is the file?
simplutils -v hash abc         # also show log messages on screen
```

```text
2026-11-11 11:32:36,828 INFO    tool=jwt-decode ok in=41 chars options={} out=77 chars time=0ms
2026-11-11 11:40:02,114 WARNING tool=b64-decode failed: invalid Base64 ...
```

**What is logged:** the tool name, the input *size*, non-text options (like `algo`), the output
size, timing, and success or failure.
**What is never logged:** the text or files you process. Free-text options such as an HMAC key
are written as `<hidden>`. The PII tools log only counts per type
(`pii-redact: 3 finding(s) {'email': 2, 'phone': 1}`), never values.

If a tool crashes unexpectedly you see a short message and the full details go to the log.
If the log folder can't be written (read-only profile), the tools still work; logging is skipped.
When you use `simplutils` as a library, nothing is logged unless your own program calls
`simplutils.logs.setup_logging()`.

---

## 10. PII redaction: what it does and doesn't do

**Detects** (run `simplutils pii-types`):

| Type | Notes |
|---|---|
| `email`, `ip-address` | IPv4. Version strings like `1.2.3.4.5` are not flagged |
| `phone` | India mobile, US/Canada, and international `+CC ...` formats |
| `credit-card` | Luhn-checked, so random digit strings are ignored |
| `iban` | mod-97 checked |
| `aadhaar` | Verhoeff-checked (India) |
| `pan` | Indian PAN format `ABCDE1234F` |
| `ssn` | US Social Security Number format |
| `password` | `password=...`, `secret: ...`, `api_key = ...` style assignments |
| `bearer-token`, `jwt`, `url-password` | Authorization headers, JWTs, `https://user:PASS@host` |
| `aws-key`, `github-token`, `slack-token`, `google-api-key`, `private-key` | Common credential formats |

**Modes** for `pii-redact`:

| `--mode` | Result for `jo@example.com` | Notes |
|---|---|---|
| `label` (default) | `[EMAIL]` | Safest and easiest to read |
| `mask` | `**@******e.com` (last 4 letters/digits kept) | IDs and cards keep their last 4 characters; secrets are fully masked |
| `hash` | `[EMAIL#3f9a1c2b]` | The same value gets the same token **within one run**, so you can still follow "the same user" across a log. The salt is random per run, so tokens can't be matched across runs or brute-forced |

`--only email,phone` limits what is replaced; `--exclude phone` skips a type. A type you switch
off still "claims" its text, so it can't be re-reported as something else (excluding
`credit-card` does not turn the same digits into a `phone`).

**Limits. Please read:**

- Detection is **heuristic** (patterns plus checksums). It will **not** find people's names,
  addresses, or free text such as "my password is blue horse". It is a safety net, not a guarantee.
  **Always review before sharing sensitive text.**
- Some 10-digit numbers can look like phone numbers. If that bites, use `--exclude phone`.
- It works on **text**. PDFs and Word files are not supported yet. Extract the text first
  (`simplutils pdf-text`), then redact it.

---

## 11. Troubleshooting and FAQ

**`simplutils` is "not recognized" (Windows).** The Python *Scripts* folder isn't on your PATH.
Either use `python -m simplutils ...`, or install with `pipx install "simplutils[all]"`, which
handles PATH for you.

**"this tool needs Pillow / pypdf / PyYAML / segno: pip install simplutils[...]".** You're using a
tool from an optional group. Install the extra it names, or `pip install "simplutils[all]"`.

**Inline JSON fails in Windows PowerShell** (`invalid JSON: Expecting property name enclosed in
double quotes`). Windows PowerShell 5.1 strips the inner double quotes when it passes arguments to
programs. Any of these work:

```powershell
'{"a":1}' | simplutils json-format             # pipe it (recommended)
simplutils json-format -f data.json            # or read a file
simplutils json-format '{\"a\":1}'             # or escape the quotes with backslashes
```

PowerShell 7 and Command Prompt/Git Bash don't have this problem.

**A file saved by Notepad / PowerShell won't load.** It should: UTF-8 with or without a BOM and
UTF-16 (what PowerShell's `>` writes) are all handled. If you see `not valid UTF-8 text`, the file
is binary or in an older encoding (such as Windows-1252). Re-save it as UTF-8.

**Non-English text through a PowerShell pipe looks garbled.** Windows PowerShell 5.1 pipes text
using an old code page. Pass the text as an argument, or use `-f file`.

**"the PDF is password-protected".** Decrypt it first (not supported yet).

**`pdf-text` returns "no text found".** The PDF is probably a scan (pictures of pages). It has no
text layer to extract; OCR is not included.

**Where did my output file go?** Next to where you ran the command. Tools that make files print
`saved N bytes to <path>`. Use `-o path` to choose.

**Is anything sent over the network?** No. All processing is local. (`pip install` itself
downloads packages, of course; the tools do not.)

**Can I run it from a script or CI?** Yes. Use the exit codes in section 4, or the Python library.

---

## 12. Extending: add your own tool

A tool is **one decorated function**. The command, menu entry, web page and log entries are all
generated from it automatically.

```python
# src/simplutils/tools/mytools.py
from ..registry import tool, ToolError

@tool("reverse", "Reverse Text", "Text")          # command name, display title, group
def reverse(text: str, words: bool = False) -> str:
    """Reverse the text (or just the order of words)."""     # first line = the help text
    if not text:
        raise ToolError("nothing to reverse")
    return " ".join(reversed(text.split())) if words else text[::-1]
```

Then add `mytools` to the import list in `src/simplutils/tools/__init__.py`. Done:
`simplutils reverse "abc"` → `cba`.

Rules:

- The **first parameter** decides the input: `text` (text), `data` (one file as `bytes`),
  `files` (a `List[bytes]`). No such parameter means no input.
- Other parameters are **options**: `str`, `int`, `bool` (must default to `False`), or
  `Literal["a", "b"]` for a choice list. A parameter with no default is required.
- Return a string, or a `FileResult(data, filename, mime)` for a file.
- Raise `ToolError("friendly message")` for bad input.

---

## 13. Development and releasing

```bash
pip install -e ".[all,dev]"        # editable install with everything
python -m pytest                   # run the tests
python examples/library_tour.py    # try the examples
```

Project layout:

```text
src/simplutils/
  registry.py       the @tool decorator and registry
  cli.py            command line (generated from the registry)
  interactive.py    the step-by-step menu
  ui.py             the web UI (generated from the registry)
  logs.py           logging
  textio.py         robust text-file reading (BOM / UTF-16)
  tools/            one module per group of tools
tests/              pytest tests
examples/           runnable tours and sample data
```

To publish the source on GitHub and make `python -m pip install simplutils` available to everyone,
follow **[PUBLISHING.md](PUBLISHING.md)**. The PyPI install command works after the first successful
release; until then, install from the project folder with `python -m pip install -e .`.

## License

MIT. See [LICENSE](LICENSE).
