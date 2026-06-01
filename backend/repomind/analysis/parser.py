from __future__ import annotations

import ast
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

ENV_RE = re.compile(
    r"(?:os\.getenv\(\s*['\"]([A-Z0-9_]{3,})['\"]|"
    r"os\.environ(?:\.get)?\(\s*['\"]([A-Z0-9_]{3,})['\"]|"
    r"os\.environ\[['\"]([A-Z0-9_]{3,})['\"]\]|"
    r"process\.env\.([A-Z0-9_]{3,}))"
)
TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b[:\s-]*(.*)", re.IGNORECASE)
PY_ROUTE_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}
JS_ROUTE_METHODS = PY_ROUTE_METHODS | {"use", "all"}
DB_MODEL_BASES = {"Base", "Model", "SQLModel", "DeclarativeBase", "Document"}
JAVA_ROUTE_ANNOTATION_RE = re.compile(
    r"@(?P<method>GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping|RequestMapping)"
    r"(?:\((?P<args>[^)]*)\))?"
)
JAVA_METHOD_RE = re.compile(
    r"(?m)^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:final\s+)?"
    r"[\w<>\[\], ?]+\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
)
GO_IMPORT_RE = re.compile(r'(?m)^\s*import\s+(?:[._\w]+\s+)?["`]([^"`]+)["`]')
GO_IMPORT_BLOCK_RE = re.compile(r"import\s*\((?P<body>.*?)\)", re.DOTALL)
GO_FUNC_RE = re.compile(
    r"(?m)^func\s+(?:\((?P<receiver>[^)]*)\)\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\("
)
GO_ROUTE_RE = re.compile(
    r"\.(?P<method>GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD|Handle|HandleFunc)\s*"
    r"\(\s*[`\"](?P<path>/[^`\"]*)[`\"]"
)
RUST_USE_RE = re.compile(r"(?m)^\s*use\s+([^;]+);")
RUST_ITEM_RE = re.compile(
    r"(?m)^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?P<kind>fn|struct|enum|trait|mod)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
)
RUST_ROUTE_RE = re.compile(
    r"#\[(?P<method>get|post|put|patch|delete|route)\s*\(\s*\"(?P<path>/[^\"]*)\""
)


def parse_file(path: Path, relative_path: str, language: str) -> dict[str, Any]:
    text = path.read_text(errors="ignore")
    result: dict[str, Any] = {
        "relative_path": relative_path,
        "imports": [],
        "exports": [],
        "classes": [],
        "functions": [],
        "methods": [],
        "routes": [],
        "database_models": [],
        "env_vars": [],
        "todos": [],
        "metadata": {},
        "parser": None,
    }
    if language == "Python":
        result.update(_parse_python(text))
    elif language in {"JavaScript", "TypeScript"}:
        result.update(
            _parse_js_ts(text, _tree_sitter_language(relative_path, language), relative_path)
        )
    elif language == "Java":
        result.update(_parse_java(text))
    elif language == "Go":
        result.update(_parse_go(text))
    elif language == "Rust":
        result.update(_parse_rust(text))
    elif language == "JSON":
        result["metadata"] = _parse_json_metadata(text)
    elif language == "YAML":
        result["metadata"] = _parse_yaml_metadata(text)

    result["env_vars"] = sorted(
        {value for match in ENV_RE.finditer(text) for value in match.groups() if value}
    )
    result["todos"] = [
        {
            "tag": m.group(1).upper(),
            "text": m.group(2).strip(),
            "line": _line_for_offset(text, m.start()),
        }
        for m in TODO_RE.finditer(text)
    ]
    return result


def _parse_java(text: str) -> dict[str, Any]:
    imports = re.findall(r"(?m)^\s*import\s+([\w.*]+)\s*;", text)
    classes = [
        {"name": match.group("name"), "line": _line_for_offset(text, match.start())}
        for match in re.finditer(
            r"(?m)^\s*(?:public\s+)?(?:abstract\s+|final\s+)?"
            r"(?P<kind>class|interface|enum)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)",
            text,
        )
    ]
    functions = [
        {"name": match.group("name"), "line": _line_for_offset(text, match.start()), "async": False}
        for match in JAVA_METHOD_RE.finditer(text)
        if match.group("name") not in {"if", "for", "while", "switch", "catch"}
    ]
    routes: list[dict[str, Any]] = []
    for match in JAVA_ROUTE_ANNOTATION_RE.finditer(text):
        method = match.group("method").replace("Mapping", "").upper() or "ROUTE"
        if method == "REQUEST":
            method = "ROUTE"
        route_path = _quoted_route_path(match.group("args") or "") or "/"
        routes.append(
            {
                "method": method,
                "path": route_path,
                "handler": _next_java_method_name(text, match.end()),
                "line": _line_for_offset(text, match.start()),
            }
        )
    database_models = [
        item | {"orm": "JPA/Hibernate"}
        for item in classes
        if _has_java_annotation_near(text, item["line"], {"@Entity", "@Table", "@Document"})
    ]
    return {
        "imports": sorted(set(imports)),
        "exports": [],
        "classes": classes,
        "functions": functions,
        "methods": [],
        "routes": _unique_routes(routes),
        "database_models": database_models,
        "parser": "regex-java",
    }


def _parse_go(text: str) -> dict[str, Any]:
    imports = set(GO_IMPORT_RE.findall(text))
    for block in GO_IMPORT_BLOCK_RE.finditer(text):
        imports.update(re.findall(r'["`]([^"`]+)["`]', block.group("body")))
    functions = []
    methods = []
    for match in GO_FUNC_RE.finditer(text):
        item = {
            "name": match.group("name"),
            "line": _line_for_offset(text, match.start()),
            "async": False,
        }
        receiver = match.group("receiver")
        if receiver:
            item["class"] = _go_receiver_type(receiver)
            methods.append(item)
        else:
            functions.append(item)
    classes = [
        {"name": match.group("name"), "line": _line_for_offset(text, match.start())}
        for match in re.finditer(
            r"(?m)^type\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+(?:struct|interface)\b",
            text,
        )
    ]
    routes = [
        {
            "method": "ROUTE"
            if match.group("method") in {"Handle", "HandleFunc"}
            else match.group("method"),
            "path": match.group("path"),
            "handler": "",
            "line": _line_for_offset(text, match.start()),
        }
        for match in GO_ROUTE_RE.finditer(text)
    ]
    database_models = [
        item | {"orm": "Go struct tags"}
        for item in classes
        if _has_go_struct_db_tags(text, item["name"])
    ]
    return {
        "imports": sorted(imports),
        "exports": [],
        "classes": classes,
        "functions": functions,
        "methods": methods,
        "routes": _unique_routes(routes),
        "database_models": database_models,
        "parser": "regex-go",
    }


def _parse_rust(text: str) -> dict[str, Any]:
    imports = sorted({value.strip() for value in RUST_USE_RE.findall(text)})
    functions = []
    classes = []
    for match in RUST_ITEM_RE.finditer(text):
        item = {"name": match.group("name"), "line": _line_for_offset(text, match.start())}
        if match.group("kind") == "fn":
            functions.append(item | {"async": _rust_function_is_async(text, match.start())})
        else:
            classes.append(item | {"kind": match.group("kind")})
    routes = [
        {
            "method": match.group("method").upper(),
            "path": match.group("path"),
            "handler": _next_rust_function_name(text, match.end()),
            "line": _line_for_offset(text, match.start()),
        }
        for match in RUST_ROUTE_RE.finditer(text)
    ]
    database_models = [
        item | {"orm": "Diesel/SQLx"} for item in classes if _has_rust_db_signal(text, item["name"])
    ]
    return {
        "imports": imports,
        "exports": [],
        "classes": classes,
        "functions": functions,
        "methods": [],
        "routes": _unique_routes(routes),
        "database_models": database_models,
        "parser": "regex-rust",
    }


def _parse_python(text: str) -> dict[str, Any]:
    tree = _parse_tree_sitter("python", text)
    try:
        py_tree = ast.parse(text)
    except SyntaxError:
        return _parse_python_tree_sitter(text, tree)

    imports: list[str] = []
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    methods: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    database_models: list[dict[str, Any]] = []
    parent_classes: dict[ast.AST, str] = {}
    for node in ast.walk(py_tree):
        for child in ast.iter_child_nodes(node):
            if isinstance(node, ast.ClassDef):
                parent_classes[child] = node.name
    for node in ast.walk(py_tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.ClassDef):
            base_names = [_name_from_expr(base) for base in node.bases]
            item = {
                "name": node.name,
                "line": node.lineno,
                "bases": [name for name in base_names if name],
            }
            classes.append(item)
            if _looks_like_python_db_model(node, base_names):
                database_models.append(item | {"orm": _python_orm_name(base_names)})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = {
                "name": node.name,
                "line": node.lineno,
                "async": isinstance(node, ast.AsyncFunctionDef),
            }
            parent = parent_classes.get(node)
            if parent:
                methods.append(fn | {"class": parent})
            else:
                functions.append(fn)
            routes.extend(_python_routes(node, parent))
    return {
        "imports": sorted(set(imports)),
        "exports": [],
        "classes": classes,
        "functions": functions,
        "methods": methods,
        "routes": routes,
        "database_models": database_models,
        "parser": "tree-sitter-python+python-ast",
    }


def _parse_python_tree_sitter(text: str, tree: Any | None) -> dict[str, Any]:
    imports: list[str] = []
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    if tree is None:
        return {
            "imports": imports,
            "classes": classes,
            "functions": functions,
            "parser": "unavailable",
        }
    for node in _walk(_root_node(tree)):
        kind = _kind(node)
        if kind == "import_statement":
            imports.append(_text(text, node).replace("import", "", 1).strip().split(",")[0].strip())
        elif kind == "import_from_statement":
            imports.append(_text(text, node).split("import", 1)[0].replace("from", "", 1).strip())
        elif kind == "class_definition":
            name = _field_text(text, node, "name")
            if name:
                classes.append({"name": name, "line": _line_for_node(text, node)})
        elif kind == "function_definition":
            name = _field_text(text, node, "name")
            if name:
                functions.append({"name": name, "line": _line_for_node(text, node), "async": False})
    return {
        "imports": sorted(set(filter(None, imports))),
        "classes": classes,
        "functions": functions,
        "methods": [],
        "routes": [],
        "database_models": [],
        "parser": "tree-sitter-python",
    }


def _parse_js_ts(text: str, language: str, relative_path: str) -> dict[str, Any]:
    tree = _parse_tree_sitter(language, text)
    if tree is None:
        raise RuntimeError(
            f"Tree-sitter parser for {language} is unavailable. Install tree-sitter-language-pack."
        )
    imports: list[str] = []
    exports: list[str] = []
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    methods: list[dict[str, Any]] = []
    routes: list[dict[str, Any]] = []
    database_models: list[dict[str, Any]] = []
    class_stack: list[str] = []

    def visit(node: Any) -> None:
        kind = _kind(node)
        if kind == "import_statement":
            source = _first_descendant_text(text, node, {"string_fragment"})
            if source:
                imports.append(source)
        elif kind == "export_statement":
            exports.extend(_exported_names(text, node))
        elif kind in {"class_declaration", "abstract_class_declaration"}:
            name = _field_text(text, node, "name") or _first_named_child_text(
                text, node, {"type_identifier", "identifier"}
            )
            if name:
                classes.append({"name": name, "line": _line_for_node(text, node)})
                if _looks_like_js_db_model(text, node, name):
                    database_models.append(
                        {"name": name, "line": _line_for_node(text, node), "orm": "JS/TS ORM"}
                    )
                class_stack.append(name)
                for child in _children(node):
                    visit(child)
                class_stack.pop()
                return
        elif kind in {"function_declaration", "generator_function_declaration"}:
            name = _field_text(text, node, "name") or _first_named_child_text(
                text, node, {"identifier"}
            )
            if name:
                functions.append(
                    {
                        "name": name,
                        "line": _line_for_node(text, node),
                        "async": "async" in _text(text, node)[:32],
                    }
                )
                if name.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
                    routes.append(
                        {
                            "method": name.upper(),
                            "path": _route_path_from_file(relative_path),
                            "handler": name,
                            "line": _line_for_node(text, node),
                        }
                    )
        elif kind == "variable_declarator":
            name = _field_text(text, node, "name")
            value = _field_node(node, "value")
            if (
                name
                and value is not None
                and _kind(value) in {"arrow_function", "function", "function_expression"}
            ):
                functions.append(
                    {
                        "name": name,
                        "line": _line_for_node(text, node),
                        "async": "async" in _text(text, value)[:32],
                    }
                )
        elif kind == "method_definition":
            name = _field_text(text, node, "name") or _first_named_child_text(
                text, node, {"property_identifier", "identifier"}
            )
            if name:
                methods.append(
                    {
                        "name": name,
                        "class": class_stack[-1] if class_stack else None,
                        "line": _line_for_node(text, node),
                    }
                )
        elif kind == "call_expression":
            route = _js_route(text, node)
            if route:
                routes.append(route)

        for child in _children(node):
            visit(child)

    visit(_root_node(tree))
    return {
        "imports": sorted(set(imports)),
        "exports": sorted(set(exports)),
        "classes": classes,
        "functions": functions,
        "methods": methods,
        "routes": _unique_routes(routes),
        "database_models": database_models,
        "parser": f"tree-sitter-{language}",
    }


def _tree_sitter_language(relative_path: str, language: str) -> str:
    suffix = Path(relative_path).suffix.lower()
    if suffix in {".tsx", ".jsx"}:
        return "tsx"
    if suffix == ".ts":
        return "typescript"
    if suffix == ".js":
        return "javascript"
    return "typescript" if language == "TypeScript" else "javascript"


def _parse_tree_sitter(language: str, text: str) -> Any | None:
    try:
        from tree_sitter_language_pack import get_parser

        return get_parser(language).parse(text)
    except Exception:
        return None


def _walk(node: Any | None) -> Iterable[Any]:
    if node is None:
        return
    yield node
    for child in _children(node):
        yield from _walk(child)


def _children(node: Any) -> list[Any]:
    count = _call_attr(node, "child_count", 0)
    return [node.child(index) for index in range(count)]


def _root_node(tree: Any) -> Any:
    root = tree.root_node
    return root() if callable(root) else root


def _kind(node: Any) -> str:
    value = getattr(node, "kind", None)
    if callable(value):
        return value()
    return getattr(node, "type", "")


def _field_node(node: Any, field: str) -> Any | None:
    getter = getattr(node, "child_by_field_name", None)
    return getter(field) if callable(getter) else None


def _field_text(text: str, node: Any, field: str) -> str | None:
    child = _field_node(node, field)
    return _text(text, child) if child is not None else None


def _first_descendant_text(text: str, node: Any, kinds: set[str]) -> str | None:
    for item in _walk(node):
        if _kind(item) in kinds:
            return _strip_quotes(_text(text, item))
    return None


def _first_named_child_text(text: str, node: Any, kinds: set[str]) -> str | None:
    for child in _children(node):
        if _kind(child) in kinds:
            return _strip_quotes(_text(text, child))
    return None


def _exported_names(text: str, node: Any) -> list[str]:
    names = []
    for item in _walk(node):
        if _kind(item) in {"function_declaration", "class_declaration", "lexical_declaration"}:
            name = _field_text(text, item, "name")
            if name:
                names.append(name)
        elif _kind(item) in {"identifier", "type_identifier"} and _text(text, item) != "export":
            names.append(_text(text, item))
    return names[:8]


def _text(text: str, node: Any | None) -> str:
    if node is None:
        return ""
    start = _call_attr(node, "start_byte", 0)
    end = _call_attr(node, "end_byte", 0)
    return text.encode(errors="ignore")[start:end].decode(errors="ignore")


def _call_attr(obj: Any, name: str, default: Any) -> Any:
    value = getattr(obj, name, None)
    if callable(value):
        return value()
    return value if value is not None else default


def _line_for_node(text: str, node: Any) -> int:
    return _line_for_offset(text, _call_attr(node, "start_byte", 0))


def _line_for_offset(text: str, offset: int) -> int:
    prefix = text.encode(errors="ignore")[:offset].decode(errors="ignore")
    return prefix.count("\n") + 1


def _strip_quotes(value: str) -> str:
    return value.strip().strip("'\"`")


def _python_routes(
    node: ast.FunctionDef | ast.AsyncFunctionDef, parent: str | None
) -> list[dict[str, Any]]:
    routes = []
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        method = _route_method(decorator.func)
        if method not in PY_ROUTE_METHODS:
            continue
        path = (
            decorator.args[0].value
            if decorator.args and isinstance(decorator.args[0], ast.Constant)
            else None
        )
        routes.append(
            {
                "method": method.upper(),
                "path": path or "<dynamic>",
                "handler": f"{parent}.{node.name}" if parent else node.name,
                "line": node.lineno,
            }
        )
    return routes


def _route_method(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute):
        return node.attr.lower()
    if isinstance(node, ast.Name):
        return node.id.lower()
    return None


def _name_from_expr(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _name_from_expr(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Subscript):
        return _name_from_expr(node.value)
    return None


def _looks_like_python_db_model(node: ast.ClassDef, bases: list[str | None]) -> bool:
    if any((base or "").split(".")[-1] in DB_MODEL_BASES for base in bases):
        return True
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign) and _name_from_expr(
            stmt.annotation or ast.Name(id="", ctx=ast.Load())
        ) in {"Mapped", "Column"}:
            return True
        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
            callee = _name_from_expr(stmt.value.func) or ""
            if callee.split(".")[-1] in {"Column", "mapped_column", "relationship"}:
                return True
    return False


def _python_orm_name(bases: list[str | None]) -> str:
    joined = " ".join(base or "" for base in bases)
    if "SQLModel" in joined:
        return "SQLModel"
    if "Document" in joined:
        return "Document ORM"
    return "SQLAlchemy/Python ORM"


def _js_route(text: str, node: Any) -> dict[str, Any] | None:
    call_text = _text(text, node)
    if "." not in call_text or "(" not in call_text:
        return None
    prefix = call_text.split("(", 1)[0].strip()
    method = prefix.rsplit(".", 1)[-1].lower()
    if method not in JS_ROUTE_METHODS:
        return None
    first_arg = _first_descendant_text(text, node, {"string_fragment", "template_string"})
    if not first_arg or not first_arg.startswith("/"):
        return None
    return {
        "method": method.upper(),
        "path": first_arg,
        "handler": prefix,
        "line": _line_for_node(text, node),
    }


def _route_path_from_file(relative_path: str) -> str:
    path = relative_path
    for prefix in ("app/", "pages/api/", "src/app/", "src/pages/api/"):
        if path.startswith(prefix):
            path = path[len(prefix) :]
            break
    for suffix in (
        "/route.ts",
        "/route.tsx",
        "/route.js",
        "/route.jsx",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
    ):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    path = path.replace("index", "").replace("[", ":").replace("]", "")
    path = "/" + path.strip("/")
    return path if path != "/" else "/"


def _looks_like_js_db_model(text: str, node: Any, name: str) -> bool:
    body = _text(text, node).lower()
    lower = name.lower()
    return any(
        token in body for token in ("sequelize", "mongoose", "prisma", "typeorm", "@entity")
    ) or lower.endswith(("model", "schema", "entity"))


def _unique_routes(routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, int]] = set()
    unique = []
    for route in routes:
        key = (route["method"], route["path"], route["line"])
        if key not in seen:
            seen.add(key)
            unique.append(route)
    return unique


def _quoted_route_path(value: str) -> str | None:
    match = re.search(r'["\'](?P<path>/[^"\']*)["\']', value)
    return match.group("path") if match else None


def _next_java_method_name(text: str, offset: int) -> str:
    match = JAVA_METHOD_RE.search(text, offset)
    return match.group("name") if match else ""


def _has_java_annotation_near(text: str, line: int, annotations: set[str]) -> bool:
    lines = text.splitlines()
    window = "\n".join(lines[max(0, line - 6) : min(len(lines), line + 2)])
    return any(annotation in window for annotation in annotations)


def _go_receiver_type(receiver: str) -> str:
    parts = receiver.replace("*", " ").split()
    return parts[-1] if parts else "receiver"


def _has_go_struct_db_tags(text: str, name: str) -> bool:
    match = re.search(rf"type\s+{re.escape(name)}\s+struct\s*\{{(?P<body>.*?)\}}", text, re.DOTALL)
    if not match:
        return False
    body = match.group("body").lower()
    return any(token in body for token in ('`db:"', '`gorm:"', '`sql:"', '`json:"id"'))


def _rust_function_is_async(text: str, offset: int) -> bool:
    prefix = text[max(0, offset - 16) : offset]
    return "async" in prefix


def _next_rust_function_name(text: str, offset: int) -> str:
    match = re.search(r"(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)", text[offset:])
    return match.group(1) if match else ""


def _has_rust_db_signal(text: str, name: str) -> bool:
    pattern = re.compile(
        rf"(diesel|sqlx|Queryable|Insertable|FromRow|table_name).*?{re.escape(name)}|"
        rf"{re.escape(name)}.*?(diesel|sqlx|Queryable|Insertable|FromRow)",
        re.DOTALL,
    )
    return bool(pattern.search(text))


def _parse_json_metadata(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict):
        return {
            "name": data.get("name"),
            "dependencies": sorted((data.get("dependencies") or {}).keys()),
            "dev_dependencies": sorted((data.get("devDependencies") or {}).keys()),
            "scripts": sorted((data.get("scripts") or {}).keys()),
        }
    return {}


def _parse_yaml_metadata(text: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}
