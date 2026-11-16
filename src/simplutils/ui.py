"""Local web UI (NiceGUI), generated from the tool registry. Runs entirely on localhost."""
from __future__ import annotations

import base64
import inspect
import json

from nicegui import ui

from .logs import setup_logging
from .registry import FileResult, Tool, groups, load_all
from .tools.files import detect_image


def _data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _tool_panel(t: Tool) -> None:
    values = {p.name: (None if p.required else p.default) for p in t.params}
    refs = {}
    state = {"bytes": None, "result": None, "files": [], "names": []}

    def show_preview(data: bytes, mime: str) -> None:
        refs["preview"].clear()
        if mime.startswith("image/"):
            with refs["preview"]:
                ui.image(_data_uri(data, mime)).classes("max-w-md border rounded")

    def run(*_) -> None:
        state["result"] = None
        refs["download"].set_visibility(False)
        try:
            if t.input_kind == "file":
                data = state["bytes"]
                if data is None:
                    refs["output"].value = "Upload a file to begin."
                    return
            elif t.input_kind == "files":
                data = state["files"]
                if not data:
                    refs["output"].value = "Upload one or more files to begin (they are used in upload order)."
                    return
            elif t.input_kind == "text":
                data = refs["input"].value
                if not data:
                    refs["output"].value = ""
                    return
            else:
                data = None
            result = t.run(data, **values)
        except Exception as e:  # ToolError or anything unexpected
            refs["output"].value = f"Error: {e}"
            return
        if isinstance(result, FileResult):
            state["result"] = result
            refs["output"].value = f"Ready: {result.filename} ({len(result.data):,} bytes) - use Download"
            refs["download"].set_visibility(True)
            show_preview(result.data, result.mime)
        else:
            refs["output"].value = result

    async def on_upload(e) -> None:
        data = e.file.read()
        if inspect.isawaitable(data):
            data = await data
        if t.input_kind == "files":
            state["files"].append(data)
            state["names"].append(e.file.name)
            refs["filename"].text = "Files (in order): " + ", ".join(state["names"])
            run()
            return
        state["bytes"] = data
        refs["filename"].text = f"{e.file.name} ({len(data):,} bytes)"
        kind = detect_image(data)
        refs["preview"].clear()
        if kind:
            show_preview(data, kind[0])
        run()

    def clear_files() -> None:
        state["files"].clear()
        state["names"].clear()
        refs["upload"].reset()
        refs["filename"].text = ""
        run()

    ui.label(t.title).classes("text-2xl font-bold")
    ui.label(t.description).classes("text-gray-500")

    if t.input_kind == "text":
        refs["input"] = ui.textarea("Input", on_change=run).props("outlined autogrow").classes("w-full")
    elif t.input_kind in ("file", "files"):
        multi = t.input_kind == "files"
        refs["upload"] = ui.upload(
            label="Drop files here or click +" if multi else "Drop a file here or click +",
            multiple=multi, auto_upload=True, on_upload=on_upload,
        ).classes("w-full")
        refs["filename"] = ui.label("").classes("text-sm text-gray-500")
        if multi:
            ui.button("Clear files", on_click=clear_files, icon="delete").props("flat dense")
    refs["preview"] = ui.column()

    if t.params:
        with ui.row().classes("items-center gap-4"):
            for p in t.params:
                def setter(name):
                    def _set(e):
                        values[name] = e.value
                        run()
                    return _set
                label = p.name.replace("_", " ")
                if p.choices:
                    ui.select(list(p.choices), value=p.default, label=label, on_change=setter(p.name))
                elif p.type is bool:
                    ui.switch(label, value=False, on_change=setter(p.name))
                elif p.type is int:
                    ui.number(label, value=None if p.required else p.default, precision=0,
                              on_change=lambda e, n=p.name: (values.__setitem__(n, int(e.value) if e.value is not None else None), run()))
                else:
                    ui.input(label, value="" if p.required else p.default, on_change=setter(p.name))

    refs["output"] = ui.textarea("Output").props("outlined readonly autogrow").classes("w-full")

    def copy() -> None:
        ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(refs['output'].value)})")
        ui.notify("Copied", type="positive")

    def download() -> None:
        r = state["result"]
        if r is not None:
            ui.download(r.data, r.filename, r.mime)

    with ui.row():
        ui.button("Run", on_click=run, icon="play_arrow")
        ui.button("Copy output", on_click=copy, icon="content_copy").props("outline")
        refs["download"] = ui.button("Download file", on_click=download, icon="download").props("color=positive")
    refs["download"].set_visibility(False)
    run()


def run(port: int = 8080, show: bool = True) -> None:
    setup_logging()
    all_tools = load_all()
    state = {"tool": next(iter(all_tools)), "query": ""}

    @ui.page("/")
    def index() -> None:
        dark = ui.dark_mode()

        @ui.refreshable
        def nav() -> None:
            q = state["query"].lower()
            for group, tools in groups().items():
                matches = [t for t in tools if q in t.title.lower() or q in t.name or q in t.description.lower()]
                if not matches:
                    continue
                ui.label(group).classes("text-xs uppercase text-gray-500 mt-3")
                for t in matches:
                    ui.button(t.title, on_click=lambda t=t: select(t.name)).props(
                        "flat no-caps align=left" + ("" if t.name != state["tool"] else " color=primary")
                    ).classes("w-full")

        @ui.refreshable
        def panel() -> None:
            _tool_panel(all_tools[state["tool"]])

        def select(name: str) -> None:
            state["tool"] = name
            nav.refresh()
            panel.refresh()

        def search(e) -> None:
            state["query"] = e.value or ""
            nav.refresh()

        with ui.header().classes("items-center justify-between"):
            ui.label("simplutils").classes("text-xl font-bold")
            ui.button(icon="dark_mode", on_click=dark.toggle).props("flat round color=white")
        with ui.left_drawer(fixed=True).props("width=260"):
            ui.input(placeholder="Search tools...", on_change=search).props("outlined dense clearable").classes("w-full")
            nav()
        with ui.column().classes("w-full max-w-4xl mx-auto p-4"):
            panel()

    ui.run(title="simplutils", port=port, show=show, reload=False, favicon="🧰")
