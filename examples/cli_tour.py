"""Runs a series of real `simplutils` commands against examples/sample_data and prints them.

Run it from the project folder:   python examples/cli_tour.py
Each "$ simplutils ..." line is what you would type in a terminal.
"""
import subprocess
import tempfile
from pathlib import Path

from simplutils.cli import main

DATA = Path(__file__).parent / "sample_data"
OUT = Path(tempfile.mkdtemp(prefix="simplutils_cli_"))


def run(*args: str) -> None:
    """Show the command, then run it. Arguments are passed as a list, so paths with
    backslashes or spaces are safe on every OS."""
    print(f"\n$ simplutils {subprocess.list2cmdline(args)}")
    try:
        code = main(list(args))
    except SystemExit as e:  # argparse exits on usage errors, exactly like a real terminal run
        code = e.code
    if code:
        print(f"(exit code {code})")


def d(name: str) -> str:
    return str(DATA / name)


def o(name: str) -> str:
    return str(OUT / name)


run("b64-encode", "hello world")
run("hash", "hello", "--algo", "md5")
run("list", "pdf")
run("case-convert", "user profile page", "--style", "camel")
run("regex-test", "order 123, order 4567", "--pattern", r"order (\d+)")
run("csv-to-json", "-f", d("people.csv"), "--infer-types")
run("json-diff", d("config_v1.json"), d("config_v2.json"))
run("diff", d("notes_v1.txt"), d("notes_v2.txt"))
run("pii-scan", "-f", d("server.log"))
run("pii-redact", "-f", d("server.log"), "-o", o("server_clean.log"))
run("pii-redact", "-f", d("server.log"), "--only", "email,phone", "--mode", "mask")
run("qr-text", "https://example.com")
run("b64-encode", "oops", "--nope")          # a mistake in the options -> usage error
run("b64encode", "typo in the command")      # a typo -> suggests the right command
run("logs", "-n", "3")

print(f"\nOutput files are in: {OUT}")
