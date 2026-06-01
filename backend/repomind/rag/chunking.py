from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from repomind.core.config import get_settings

SYMBOL_RE = re.compile(
    r"^(?P<indent>\s*)(?:async\s+def|def|class)\s+(?P<python>[A-Za-z_][A-Za-z0-9_]*)|"
    r"^(?:export\s+)?(?:async\s+)?(?:function|class)\s+(?P<js>[A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
TREE_SITTER_NODE_TYPES = {
    "javascript": {
        "class_declaration",
        "function_declaration",
        "generator_function_declaration",
        "lexical_declaration",
        "export_statement",
    },
    "typescript": {
        "class_declaration",
        "abstract_class_declaration",
        "function_declaration",
        "generator_function_declaration",
        "lexical_declaration",
        "export_statement",
    },
    "tsx": {
        "class_declaration",
        "abstract_class_declaration",
        "function_declaration",
        "generator_function_declaration",
        "lexical_declaration",
        "export_statement",
    },
    "java": {
        "class_declaration",
        "interface_declaration",
        "enum_declaration",
        "method_declaration",
        "constructor_declaration",
    },
    "go": {
        "function_declaration",
        "method_declaration",
        "type_declaration",
    },
    "rust": {
        "function_item",
        "impl_item",
        "struct_item",
        "enum_item",
        "trait_item",
        "mod_item",
    },
}


def chunk_text(
    text: str,
    path: str,
    kind: str = "text",
    symbol: str | None = None,
    parser: str | None = None,
) -> list[dict]:
    settings = get_settings()
    chunks = []
    start = 0
    index = 0
    while start < len(text):
        end = min(len(text), start + settings.chunk_size)
        body = text[start:end]
        line_start = text.count("\n", 0, start) + 1
        line_end = text.count("\n", 0, end) + 1
        chunks.append(
            {
                "id": f"{path}:{index}",
                "path": path,
                "text": body,
                "line_start": line_start,
                "line_end": line_end,
                "kind": kind,
                "symbol": symbol,
                "parser": parser,
            }
        )
        if end == len(text):
            break
        start = max(end - settings.chunk_overlap, start + 1)
        index += 1
    return chunks


def chunk_file(path: Path, relative_path: str) -> list[dict]:
    text = path.read_text(errors="ignore")
    ast_chunks = _ast_chunks(text, relative_path)
    if ast_chunks:
        return ast_chunks
    symbol_chunks = _symbol_chunks(text, relative_path)
    return symbol_chunks or chunk_text(text, relative_path)


def _ast_chunks(text: str, path: str) -> list[dict]:
    suffix = Path(path).suffix.lower()
    if suffix == ".py":
        return _python_ast_chunks(text, path)
    if suffix in {".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs"}:
        return _tree_sitter_chunks(text, path, _tree_sitter_language(path))
    return []


def _python_ast_chunks(text: str, path: str) -> list[dict]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    chunks = []
    for index, node in enumerate(_python_chunk_nodes(tree)):
        line_start = getattr(node, "lineno", 1)
        line_end = getattr(node, "end_lineno", line_start)
        body = "\n".join(text.splitlines()[line_start - 1 : line_end])
        if not body.strip():
            continue
        symbol = getattr(node, "name", None)
        chunks.extend(
            _bounded_node_chunks(
                body,
                path,
                index,
                line_start,
                line_end,
                "ast_node",
                symbol,
                "python-ast",
                type(node).__name__,
            )
        )
    return chunks


def _python_chunk_nodes(tree: ast.Module) -> list[ast.AST]:
    nodes: list[ast.AST] = []
    for item in tree.body:
        if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            nodes.append(item)
    return nodes


def _tree_sitter_chunks(text: str, path: str, language: str) -> list[dict]:
    try:
        from tree_sitter_language_pack import get_parser

        tree = get_parser(language).parse(text)
    except Exception:
        return []
    root = tree.root_node() if callable(tree.root_node) else tree.root_node
    chunks = []
    seen: set[tuple[int, int]] = set()
    node_types = TREE_SITTER_NODE_TYPES.get(language, set())
    for index, node in enumerate(_walk(root)):
        kind = _kind(node)
        if kind not in node_types:
            continue
        if kind == "export_statement":
            child = _first_named_child(node, node_types - {"export_statement"})
            if child is not None:
                node = child
                kind = _kind(node)
        start = _byte(node, "start_byte")
        end = _byte(node, "end_byte")
        if not end or (start, end) in seen:
            continue
        seen.add((start, end))
        body = text.encode(errors="ignore")[start:end].decode(errors="ignore").strip("\n")
        if not body:
            continue
        line_start = _line_for_offset(text, start)
        line_end = _line_for_offset(text, end)
        symbol = _node_name(text, node)
        chunks.extend(
            _bounded_node_chunks(
                body,
                path,
                index,
                line_start,
                line_end,
                "ast_node",
                symbol,
                f"tree-sitter-{language}",
                kind,
            )
        )
    return chunks


def _bounded_node_chunks(
    body: str,
    path: str,
    index: int,
    line_start: int,
    line_end: int,
    kind: str,
    symbol: str | None,
    parser: str,
    ast_type: str,
) -> list[dict]:
    settings = get_settings()
    if len(body) <= settings.chunk_size:
        return [
            {
                "id": f"{path}:ast:{index}",
                "path": path,
                "text": body,
                "line_start": line_start,
                "line_end": line_end,
                "kind": kind,
                "symbol": symbol,
                "parser": parser,
                "ast_type": ast_type,
            }
        ]
    chunks = chunk_text(body, path, kind=kind, symbol=symbol, parser=parser)
    for offset, chunk in enumerate(chunks):
        chunk["id"] = f"{path}:ast:{index}:{offset}"
        chunk["line_start"] = line_start + chunk["line_start"] - 1
        chunk["line_end"] = min(line_end, line_start + chunk["line_end"] - 1)
        chunk["ast_type"] = ast_type
    return chunks


def _symbol_chunks(text: str, path: str) -> list[dict]:
    matches = list(SYMBOL_RE.finditer(text))
    if not matches:
        return []
    chunks = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip("\n")
        if not body:
            continue
        symbol = match.group("python") or match.group("js")
        line_start = text.count("\n", 0, start) + 1
        line_end = text.count("\n", 0, end) + 1
        chunks.append(
            {
                "id": f"{path}:symbol:{index}",
                "path": path,
                "text": body,
                "line_start": line_start,
                "line_end": line_end,
                "kind": "symbol",
                "symbol": symbol,
                "parser": "regex-symbol",
            }
        )
    return chunks


def _tree_sitter_language(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix in {".tsx", ".jsx"}:
        return "tsx"
    if suffix == ".ts":
        return "typescript"
    if suffix == ".java":
        return "java"
    if suffix == ".go":
        return "go"
    if suffix == ".rs":
        return "rust"
    return "javascript"


def _walk(node: Any):
    yield node
    for index in range(_node_count(node, "child_count")):
        yield from _walk(node.child(index))


def _kind(node: Any) -> str:
    value = getattr(node, "type", getattr(node, "kind", ""))
    return value() if callable(value) else value


def _byte(node: Any, attr: str) -> int:
    value = getattr(node, attr, 0)
    return value() if callable(value) else value


def _line_for_offset(text: str, offset: int) -> int:
    return text.encode(errors="ignore")[:offset].decode(errors="ignore").count("\n") + 1


def _first_named_child(node: Any, kinds: set[str]) -> Any | None:
    for index in range(_node_count(node, "named_child_count")):
        child = node.named_child(index)
        if _kind(child) in kinds:
            return child
    return None


def _node_count(node: Any, attr: str) -> int:
    value = getattr(node, attr, 0)
    return int(value() if callable(value) else value)


def _node_name(text: str, node: Any) -> str | None:
    getter = getattr(node, "child_by_field_name", None)
    if callable(getter):
        child = getter("name")
        if child is not None:
            return _node_text(text, child).strip("'\"`")
    for child_kind in ("identifier", "type_identifier", "property_identifier"):
        child = _first_named_child(node, {child_kind})
        if child is not None:
            return _node_text(text, child).strip("'\"`")
    return None


def _node_text(text: str, node: Any) -> str:
    start = _byte(node, "start_byte")
    end = _byte(node, "end_byte")
    return text.encode(errors="ignore")[start:end].decode(errors="ignore")
