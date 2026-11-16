"""Interactive menu: run `simplutils` with no arguments. Pick a tool, answer the prompts. No flags to remember."""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

from .registry import FileResult, Param, Tool, ToolError, groups, load_all
from .textio import read_text_file

HELP = (
    "Type a number to pick a tool, or a word to search (e.g. 'pdf', 'base64').\n"
    "  q = quit, ? = show this help"
)


def _clean_path(raw: str) -> str:
    return raw.strip().strip('"').strip("'")  # drag & drop adds quotes


class Menu:
    def __init__(self, ask: Optional[Callable[[str], str]] = None, say: Optional[Callable[..., None]] = None):
        # Resolve input/print at call time (not import time) so they can be swapped out.
        self.ask = ask or (lambda prompt="": input(prompt))
        self.say = say or (lambda *a, **k: print(*a, **k))
        self.numbered: List[Tool] = []
        for tools in groups().values():
            self.numbered.extend(tools)

    # ---- screens -------------------------------------------------------
    def show_tools(self, only: Optional[List[Tool]] = None) -> None:
        shown = only if only is not None else self.numbered
        current = None
        for t in shown:
            if t.group != current:
                current = t.group
                self.say(f"\n  {current}")
            self.say(f"    {self.numbered.index(t) + 1:>2}. {t.title:<22} {t.description}")
        self.say("")

    def pick_tool(self) -> Optional[Tool]:
        self.show_tools()
        self.say(HELP)
        while True:
            choice = self.ask("\nTool> ").strip()
            if not choice:
                continue
            low = choice.lower()
            if low in ("q", "quit", "exit"):
                return None
            if low == "?":
                self.show_tools()
                self.say(HELP)
                continue
            if choice.isdigit():
                n = int(choice)
                if 1 <= n <= len(self.numbered):
                    return self.numbered[n - 1]
                self.say(f"  Please pick 1-{len(self.numbered)}.")
                continue
            matches = [t for t in self.numbered
                       if low in t.name or low in t.title.lower() or low in t.description.lower()]
            if not matches:
                self.say(f"  Nothing matches '{choice}'. Type ? to see everything.")
            elif len(matches) == 1:
                return matches[0]
            else:
                self.say(f"  {len(matches)} matches - type the number:")
                self.show_tools(matches)

    # ---- prompts -------------------------------------------------------
    def _read_text(self) -> str:
        self.say("Enter the text. Type @path to load it from a file, or << for multi-line input.")
        first = self.ask("Text> ")
        if first.strip().startswith("@"):
            return self._read_file_text(_clean_path(first.strip()[1:]))
        if first.strip() == "<<":
            self.say("(paste your text, then finish with an empty line)")
            lines: List[str] = []
            while True:
                line = self.ask("")
                if line == "":
                    break
                lines.append(line)
            return "\n".join(lines)
        return first

    def _read_file_text(self, path: str) -> str:
        return read_text_file(path)

    def _read_file_bytes(self, path: str) -> bytes:
        path = _clean_path(path)
        try:
            with open(path, "rb") as fh:
                return fh.read()
        except OSError as e:
            raise ToolError(f"cannot read '{path}': {e}")

    def _read_input(self, t: Tool) -> Any:
        if t.input_kind == "text":
            return self._read_text()
        if t.input_kind == "file":
            return self._read_file_bytes(self.ask("File path (you can drag the file into this window)> "))
        if t.input_kind == "files":
            self.say("Enter file paths one per line, in order. Press Enter on an empty line when done.")
            out: List[bytes] = []
            while True:
                p = self.ask(f"File {len(out) + 1}> ").strip()
                if not p:
                    break
                out.append(self._read_file_bytes(p))
            return out
        return None

    def _ask_option(self, p: Param) -> Any:
        label = p.name.replace("_", " ")
        if p.choices:
            opts = ", ".join(str(c) for c in p.choices)
            while True:
                ans = self.ask(f"{label} [{opts}] (Enter = {p.default}): ").strip()
                if not ans:
                    return None if p.required else p.default
                if ans in [str(c) for c in p.choices]:
                    return type(p.choices[0])(ans)
                self.say(f"  Choose one of: {opts}")
        if p.type is bool:
            return self.ask(f"{label}? [y/N]: ").strip().lower() in ("y", "yes")
        suffix = "" if p.required else f" (Enter = {p.default!r})"
        while True:
            ans = self.ask(f"{label}{suffix}: ").strip()
            if not ans:
                if p.required:
                    self.say("  This one is required.")
                    continue
                return p.default
            if p.type is int:
                try:
                    return int(ans)
                except ValueError:
                    self.say("  Please enter a whole number.")
                    continue
            return ans

    # ---- main flow -----------------------------------------------------
    def run_tool(self, t: Tool) -> None:
        self.say(f"\n== {t.title} ==\n{t.description}\n")
        data = self._read_input(t)
        options: Dict[str, Any] = {}
        if t.params:
            self.say("\nOptions (just press Enter to accept the default):")
            for p in t.params:
                options[p.name] = self._ask_option(p)
        result = t.run(data, **options)
        self._deliver(result)

    def _deliver(self, result: Any) -> None:
        if isinstance(result, FileResult):
            default = result.filename
            path = _clean_path(self.ask(f"\nSave as (Enter = {default}): ")) or default
            try:
                with open(path, "wb") as fh:
                    fh.write(result.data)
            except OSError as e:
                raise ToolError(f"cannot write '{path}': {e}")
            self.say(f"Saved {len(result.data):,} bytes to {os.path.abspath(path)}")
            return
        self.say("\n" + result + "\n")
        path = _clean_path(self.ask("Save the result to a file? Type a path, or Enter to skip: "))
        if path:
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(result)
            except OSError as e:
                raise ToolError(f"cannot write '{path}': {e}")
            self.say(f"Saved to {os.path.abspath(path)}")

    def loop(self) -> int:
        self.say("simplutils - pick what you want to do. (Ctrl+C anytime to quit)")
        try:
            while True:
                t = self.pick_tool()
                if t is None:
                    return 0
                try:
                    self.run_tool(t)
                except ToolError as e:
                    self.say(f"\n  Problem: {e}")
                self.ask("\nPress Enter to go back to the menu...")
        except (EOFError, KeyboardInterrupt):
            self.say("\nBye!")
            return 0


def start(ask: Optional[Callable[[str], str]] = None, say: Optional[Callable[..., None]] = None) -> int:
    load_all()
    return Menu(ask, say).loop()
