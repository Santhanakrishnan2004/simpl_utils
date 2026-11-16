"""Tool registry: one decorated function = one tool, usable from Python, CLI and UI.

Conventions for a tool function:
  * The first parameter decides the input: ``text`` = free-form text,
    ``data`` = one file (``bytes``), ``files`` = several files (``List[bytes]``);
    no such parameter = no input. Return a ``FileResult`` to produce a
    downloadable/savable file.
  * Every other parameter is an *option*. Supported types: str, int, bool
    (bool options must default to False) and ``Literal[...]`` (a choice list).
  * Return a string (or anything printable).
"""
from __future__ import annotations

import inspect
import logging
import time
import typing
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

REQUIRED = inspect.Parameter.empty
log = logging.getLogger("simplutils")
log.addHandler(logging.NullHandler())  # library default: stay silent unless the app configures logging
_INPUT_KINDS = {"text": "text", "data": "file", "files": "files"}


class ToolError(Exception):
    """Raised by a tool for bad user input (shown without a traceback)."""


@dataclass
class Param:
    name: str
    type: type
    default: Any
    choices: Optional[Tuple[Any, ...]] = None

    @property
    def required(self) -> bool:
        return self.default is REQUIRED


@dataclass
class FileResult:
    """Returned by tools that produce a binary file (the CLI saves it, the UI offers a download)."""
    data: bytes
    filename: str
    mime: str = "application/octet-stream"


@dataclass
class Tool:
    name: str
    title: str
    group: str
    description: str
    func: Callable[..., Any]
    params: List[Param]
    input_kind: str  # "none" | "text" | "file" | "files"

    @property
    def needs_input(self) -> bool:
        return self.input_kind != "none"

    def _describe_input(self, data: Any) -> str:
        if self.input_kind == "text":
            return f"{len(data)} chars"
        if self.input_kind == "file":
            return f"{len(data)} bytes"
        if self.input_kind == "files":
            return f"{len(data)} files/{sum(len(d) for d in data)} bytes"
        return "none"

    def _describe_options(self, kwargs: Dict[str, Any]) -> str:
        # Free-text option values (keys, passwords, ...) are never logged.
        shown = {
            k: (v if _loggable(self, k) else "<hidden>") for k, v in kwargs.items()
        }
        return str(shown)

    def run(self, data: Any = None, **options: Any) -> Any:
        """Run the tool. Returns a str, or a FileResult for file-producing tools."""
        started = time.perf_counter()
        try:
            kwargs = {}
            for p in self.params:
                if p.name in options and options[p.name] is not None:
                    kwargs[p.name] = options[p.name]
                elif p.required:
                    raise ToolError(f"missing required option: {p.name}")
            if self.needs_input:
                if data is None or (self.input_kind == "files" and not data):
                    what = {"text": "text", "file": "file", "files": "files"}[self.input_kind]
                    raise ToolError(f"this tool needs input {what}")
                result = self.func(data, **kwargs)
            else:
                result = self.func(**kwargs)
            result = result if isinstance(result, FileResult) else str(result)
        except ToolError as e:
            log.warning("tool=%s failed: %s", self.name, e)
            raise
        except Exception:
            log.exception("tool=%s crashed", self.name)
            raise
        ms = (time.perf_counter() - started) * 1000
        out = f"file {result.filename} {len(result.data)} bytes" if isinstance(result, FileResult) else f"{len(result)} chars"
        log.info("tool=%s ok in=%s options=%s out=%s time=%.0fms", self.name,
                 self._describe_input(data) if self.needs_input else "none",
                 self._describe_options(kwargs), out, ms)
        return result

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


def _loggable(t: "Tool", name: str) -> bool:
    p = next((p for p in t.params if p.name == name), None)
    return p is not None and (p.type is not str or p.choices is not None)


TOOLS: Dict[str, Tool] = {}


def tool(name: str, title: str, group: str) -> Callable[[Callable[..., Any]], Tool]:
    def decorator(func: Callable[..., Any]) -> Tool:
        hints = typing.get_type_hints(func)
        sig = inspect.signature(func)
        params: List[Param] = []
        input_kind = "none"
        for i, (pname, p) in enumerate(sig.parameters.items()):
            if i == 0 and pname in _INPUT_KINDS:
                input_kind = _INPUT_KINDS[pname]
                continue
            hint = hints.get(pname, str)
            choices = None
            if typing.get_origin(hint) is typing.Literal:
                choices = typing.get_args(hint)
                hint = type(choices[0])
            params.append(Param(pname, hint, p.default, choices))
        doc = (inspect.getdoc(func) or "").strip().splitlines()
        t = Tool(name, title, group, doc[0] if doc else title, func, params, input_kind)
        if name in TOOLS:
            raise ValueError(f"duplicate tool name: {name}")
        TOOLS[name] = t
        return t

    return decorator


def load_all() -> Dict[str, Tool]:
    """Import every tool module so they register themselves."""
    from . import tools  # noqa: F401

    return TOOLS


def groups() -> Dict[str, List[Tool]]:
    out: Dict[str, List[Tool]] = {}
    for t in load_all().values():
        out.setdefault(t.group, []).append(t)
    return out
