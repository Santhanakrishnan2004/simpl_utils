"""Command line interface, generated from the tool registry."""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from typing import List, Optional

from . import __version__
from .logs import log_path, setup_logging, tail
from .registry import FileResult, Tool, ToolError, groups, load_all
from .textio import decode_text, read_text_file

TIP = "Tip: run 'simplutils' with no arguments for a step-by-step menu."


class _Parser(argparse.ArgumentParser):
    """Friendlier errors: suggest the closest command/choice instead of dumping a huge list."""

    def error(self, message: str):
        m = re.search(r"invalid choice: '?(.*?)'? \(choose from (.*)\)", message)
        if m:
            bad = m.group(1)
            choices = [c.strip().strip("'") for c in m.group(2).split(",")]
            close = difflib.get_close_matches(bad, choices, n=3, cutoff=0.5)
            msg = f"unknown choice '{bad}'."
            if close:
                msg += " Did you mean: " + ", ".join(close) + "?"
            elif len(choices) <= 8:
                msg += " Choose from: " + ", ".join(choices) + "."
            if self.prog == "simplutils":
                msg += " See all tools with: simplutils list"
            self.exit(2, f"{self.prog}: error: {msg}\n")
        super().error(message)


def _add_tool(sub, t: Tool) -> None:
    sp = sub.add_parser(t.name, help=t.description, description=t.description)
    if t.input_kind == "text":
        sp.add_argument("text", nargs="?", help="input text (omit to read stdin)")
        sp.add_argument("-f", "--file", help="read input text from a file")
    elif t.input_kind == "file":
        sp.add_argument("path", help="input file path ('-' reads binary stdin)")
    elif t.input_kind == "files":
        sp.add_argument("paths", nargs="+", metavar="path", help="input file paths, in order")
    sp.add_argument("-o", "--output", help="save the result to this file instead of printing it")
    for p in t.params:
        flag = "--" + p.name.replace("_", "-")
        if p.type is bool:
            sp.add_argument(flag, action="store_true", dest=p.name)
        else:
            sp.add_argument(
                flag, dest=p.name, type=p.type, choices=p.choices,
                required=p.required, default=None if p.required else p.default,
                help=None if p.required else f"(default: {p.default})",
            )


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="simplutils", description="All-in-one developer utilities.", epilog=TIP)
    parser.add_argument("--version", action="version", version=f"simplutils {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="also print log messages to the screen")
    sub = parser.add_subparsers(dest="command", metavar="<tool>")
    sub.add_parser("menu", help="step-by-step interactive menu (same as running with no arguments)")
    lst = sub.add_parser("list", help="list all tools (optionally filter by a word)")
    lst.add_argument("query", nargs="?", help="e.g. pdf, base64, image")
    lg = sub.add_parser("logs", help="show the most recent log lines")
    lg.add_argument("-n", type=int, default=20, help="how many lines (default 20)")
    lg.add_argument("--path", action="store_true", help="only print the log file location")
    ui = sub.add_parser("ui", help="launch the local web UI (needs simplutils[ui])")
    ui.add_argument("--port", type=int, default=8080)
    ui.add_argument("--no-browser", action="store_true")
    for t in load_all().values():
        _add_tool(sub, t)
    return parser


def _read_input(t: Tool, args: argparse.Namespace):
    try:
        if t.input_kind == "file":
            if args.path == "-":
                return sys.stdin.buffer.read()
            with open(args.path, "rb") as fh:
                return fh.read()
        if t.input_kind == "files":
            out = []
            for p in args.paths:
                with open(p, "rb") as fh:
                    out.append(fh.read())
            return out
        if args.text is not None:
            return args.text
        if args.file:
            return read_text_file(args.file)
    except OSError as e:
        raise ToolError(f"cannot read input: {e}")
    if not sys.stdin.isatty():
        buffer = getattr(sys.stdin, "buffer", None)
        text = decode_text(buffer.read()) if buffer is not None else sys.stdin.read()
        return text.rstrip("\r\n")
    raise ToolError("no input: pass text, --file, or pipe via stdin")


def _emit(result, output: Optional[str]) -> None:
    try:
        if isinstance(result, FileResult):
            path = output or result.filename
            with open(path, "wb") as fh:
                fh.write(result.data)
            print(f"saved {len(result.data)} bytes to {path}")
        elif output:
            with open(output, "w", encoding="utf-8") as fh:
                fh.write(result)
            print(f"saved {len(result)} characters to {output}")
        else:
            print(result)
    except OSError as e:
        raise ToolError(f"cannot write output: {e}")


def _print_list(query: Optional[str]) -> None:
    q = (query or "").lower()
    found = False
    for group, tools in groups().items():
        rows = [t for t in tools if not q or q in t.name or q in t.title.lower() or q in t.description.lower()]
        if rows:
            found = True
            print(f"\n{group}")
            for t in rows:
                print(f"  {t.name:<15} {t.description}")
    if not found:
        print(f"No tools match '{query}'. Run 'simplutils list' to see everything.")
    print(f"\n{TIP}\nDetails for any tool: simplutils <tool> -h")


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr, sys.stdin):  # Windows consoles default to cp1252
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(verbose=args.verbose)

    if args.command is None:
        if argv is None and sys.stdin.isatty() and sys.stdout.isatty():
            from .interactive import start
            return start()
        parser.print_help()
        return 0
    if args.command == "menu":
        from .interactive import start
        return start()
    if args.command == "list":
        _print_list(args.query)
        return 0
    if args.command == "logs":
        if args.path:
            print(log_path())
            return 0
        lines = tail(args.n)
        print("\n".join(lines) if lines else f"(no log entries yet; log file: {log_path()})")
        return 0
    if args.command == "ui":
        try:
            from .ui import run
        except ImportError:
            print("The UI needs extra dependencies: pip install simplutils[ui]", file=sys.stderr)
            return 1
        run(port=args.port, show=not args.no_browser)
        return 0

    t = load_all()[args.command]
    try:
        options = {p.name: getattr(args, p.name) for p in t.params}
        result = t.run(_read_input(t, args) if t.needs_input else None, **options)
        _emit(result, args.output)
    except ToolError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except Exception as e:  # tool bug: the traceback is in the log, keep the screen readable
        print(f"error: unexpected failure ({type(e).__name__}: {e}). Details: {log_path()}", file=sys.stderr)
        return 1
    return 0
