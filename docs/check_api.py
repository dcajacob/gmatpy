"""Check the handwritten Python reference against source, without importing GMAT.

Checks exported names, object kinds, argument kinds/order, and default values.
Scientific descriptions and examples still need review and native execution.
Run directly or through the Sphinx builder-inited hook in conf.py.
"""
import ast
from copy import deepcopy
from pathlib import Path
import re


def _arguments_key(arguments):
    arguments = deepcopy(arguments)
    for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs):
        argument.annotation = None
        argument.type_comment = None
    for argument in (arguments.vararg, arguments.kwarg):
        if argument:
            argument.annotation = None
            argument.type_comment = None
    return ast.dump(arguments, include_attributes=False)


def _class_arguments(node):
    """Dataclasses in the public facade use ordinary init=True fields."""
    fields = [item for item in node.body if isinstance(item, ast.AnnAssign)]
    return ast.arguments(
        posonlyargs=[], args=[ast.arg(arg=item.target.id) for item in fields],
        vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None,
        defaults=[item.value for item in fields if item.value is not None],
    )


def check_api(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    package = root / "python/gmatpy"
    init = ast.parse((package / "__init__.py").read_text(encoding="utf-8"))
    exports = []
    imports = {}
    for node in init.body:
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            imports.update({alias.asname or alias.name: (node.module, alias.name)
                            for alias in node.names})
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in node.targets):
            exports = ast.literal_eval(node.value)
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == "__all__":
            exports.extend(ast.literal_eval(node.value))
    if not exports or len(exports) != len(set(exports)):
        raise ValueError("Public API export list is empty or contains duplicates")

    reference = (root / "docs/api.rst").read_text(encoding="utf-8")
    directives = {}
    pattern = r"^\.\. py:(function|class|exception):: ([A-Za-z_]\w*)(.*)$"
    for kind, name, tail in re.findall(pattern, reference, flags=re.MULTILINE):
        if name in directives:
            raise ValueError(f"Duplicate public API directive: {name}")
        directives[name] = kind, tail.strip()
    if set(directives) != set(exports):
        raise ValueError(f"API coverage differs from __all__: missing={set(exports)-set(directives)}, "
                         f"extra={set(directives)-set(exports)}")

    for name in exports:
        module, original = imports[name]
        tree = ast.parse((package / (module + ".py")).read_text(encoding="utf-8"))
        node = next(item for item in tree.body
                    if isinstance(item, (ast.FunctionDef, ast.ClassDef)) and item.name == original)
        is_exception = isinstance(node, ast.ClassDef) and any(
            isinstance(base, ast.Name) and base.id.endswith("Error") for base in node.bases)
        expected_kind = "function" if isinstance(node, ast.FunctionDef) else "exception" if is_exception else "class"
        kind, tail = directives[name]
        if kind != expected_kind:
            raise ValueError(f"API kind mismatch for {name}: {kind} != {expected_kind}")
        if is_exception:
            continue
        if not tail.startswith("("):
            raise ValueError(f"Missing complete signature for {name}")
        documented = ast.parse(f"def {name}{tail}:\n    pass\n").body[0].args
        actual = node.args if isinstance(node, ast.FunctionDef) else _class_arguments(node)
        if _arguments_key(documented) != _arguments_key(actual):
            raise ValueError(f"API signature/default mismatch for {name}: {tail}")
    return len(exports)


if __name__ == "__main__":
    print(f"PASS: {check_api()} public API names, kinds, signatures, and defaults match source")
