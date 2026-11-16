"""JSON <-> YAML / CSV (YAML needs PyYAML: pip install simplutils[extras])."""
import csv
import io
import json
from typing import Any, Dict, List, Literal

from ..registry import ToolError, tool

G = "Convert"


def _yaml():
    try:
        import yaml
    except ImportError:
        raise ToolError("this tool needs PyYAML: pip install simplutils[extras]")
    return yaml


def _load_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ToolError(f"invalid JSON: {e}")


@tool("json-to-yaml", "JSON → YAML", G)
def json_to_yaml(text: str) -> str:
    """Convert JSON to YAML."""
    yaml = _yaml()
    return yaml.safe_dump(_load_json(text), sort_keys=False, allow_unicode=True, default_flow_style=False).rstrip()


@tool("yaml-to-json", "YAML → JSON", G)
def yaml_to_json(text: str, indent: int = 2) -> str:
    """Convert YAML to JSON (dates become strings)."""
    yaml = _yaml()
    try:
        docs = list(yaml.safe_load_all(text))
    except yaml.YAMLError as e:
        raise ToolError(f"invalid YAML: {e}")
    if not docs:
        raise ToolError("empty YAML")
    data = docs[0] if len(docs) == 1 else docs  # several '---' documents -> a list
    return json.dumps(data, indent=indent, ensure_ascii=False, default=str)


def _flatten(value: Any, prefix: str, out: Dict[str, Any]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(v, f"{prefix}.{k}" if prefix else str(k), out)
    else:
        out[prefix or "value"] = json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value


@tool("json-to-csv", "JSON → CSV", G)
def json_to_csv(text: str) -> str:
    """Convert a JSON array of objects to CSV. Nested objects become dotted columns (a.b); lists stay as JSON."""
    data = _load_json(text)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not data:
        raise ToolError("expected a non-empty JSON array of objects")
    rows = []
    for item in data:
        row: Dict[str, Any] = {}
        _flatten(item, "", row)
        rows.append(row)
    columns: List[str] = []
    for r in rows:
        for k in r:
            if k not in columns:
                columns.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if v is None else v) for k, v in r.items()})
    return buf.getvalue().rstrip("\n")


def _infer(v: str) -> Any:
    s = v.strip()
    if s == "":
        return None
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return v


@tool("csv-to-json", "CSV → JSON", G)
def csv_to_json(text: str, delimiter: Literal["auto", "comma", "semicolon", "tab", "pipe"] = "auto",
                infer_types: bool = False) -> str:
    """Convert CSV (first row = headers) to a JSON array. Use infer_types for numbers/booleans/empty->null."""
    seps = {"comma": ",", "semicolon": ";", "tab": "\t", "pipe": "|"}
    if delimiter == "auto":
        try:
            sep = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            sep = ","
    else:
        sep = seps[delimiter]
    try:
        rows = list(csv.DictReader(io.StringIO(text), delimiter=sep))
    except csv.Error as e:
        raise ToolError(f"invalid CSV: {e}")
    if not rows:
        raise ToolError("no data rows found (is the first line a header?)")
    if infer_types:
        rows = [{k: (_infer(v) if isinstance(v, str) else v) for k, v in r.items()} for r in rows]
    return json.dumps(rows, indent=2, ensure_ascii=False)
