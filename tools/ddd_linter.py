#!/usr/bin/env python3
"""Check project-specific DDD and Onion Architecture conventions."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "backend" / "app"
TEST_ROOT = ROOT / "backend" / "tests"

FORBIDDEN_DOMAIN_IMPORT_PREFIXES = (
    "app.usecase",
    "app.infrastructure",
    "app.presentation",
    "fastapi",
    "pydantic",
    "sqlalchemy",
    "sqlmodel",
    "arq",
    "redis",
)
FORBIDDEN_USECASE_IMPORT_PREFIXES = (
    "app.infrastructure",
    "app.presentation",
    "fastapi",
    "sqlalchemy",
    "sqlmodel",
    "arq",
)
ARCH_DIRS = {"entities", "value_objects", "repositories", "exceptions"}


@dataclass(frozen=True)
class Violation:
    """Represent one DDD convention violation."""

    code: str
    path: Path
    message: str

    def format(self) -> str:
        """Return a human-readable violation line."""
        return f"{self.code}: {self.path.relative_to(ROOT)}: {self.message}"


@dataclass(frozen=True)
class ClassInfo:
    """Represent a parsed class declaration."""

    name: str
    lineno: int
    bases: tuple[str, ...]
    decorators: tuple[str, ...]

    @property
    def is_dataclass(self) -> bool:
        """Return whether the class has a dataclass decorator."""
        return any(decorator.endswith("dataclass") for decorator in self.decorators)

    @property
    def is_exception(self) -> bool:
        """Return whether the class appears to define an exception."""
        if self.name.endswith(("Error", "Exception")):
            return True
        return any(base.endswith(("Error", "Exception")) for base in self.bases)

    @property
    def is_repository(self) -> bool:
        """Return whether the class appears to define a repository."""
        return self.name.endswith("Repository")


@dataclass(frozen=True)
class ModuleInfo:
    """Represent parsed Python module metadata."""

    path: Path
    imports: tuple[str, ...]
    classes: tuple[ClassInfo, ...]
    all_exports: tuple[str, ...]


def main() -> int:
    """Run the DDD linter."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        choices=("all", "imports", "dataclasses", "exceptions", "repositories", "tests"),
        default="all",
    )
    args = parser.parse_args()

    modules = [parse_module(path) for path in python_files(APP_ROOT)]
    checks = {
        "imports": check_imports,
        "dataclasses": check_dataclasses,
        "exceptions": check_exceptions,
        "repositories": check_repositories,
        "tests": check_tests,
    }
    selected = checks.values() if args.check == "all" else (checks[args.check],)

    violations: list[Violation] = []
    for check in selected:
        violations.extend(check(modules))

    if violations:
        for violation in sorted(violations, key=lambda item: (item.path, item.code)):
            print(violation.format())
        print(f"\n{len(violations)} DDD violation(s) found.")
        return 1

    print("DDD linter passed.")
    return 0


def python_files(root: Path) -> Iterable[Path]:
    """Yield Python source files under root."""
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def parse_module(path: Path) -> ModuleInfo:
    """Parse imports, classes, and __all__ from a module."""
    tree = ast.parse(path.read_text(), filename=str(path))
    imports: list[str] = []
    classes: list[ClassInfo] = []
    all_exports: tuple[str, ...] = ()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
        elif isinstance(node, ast.ClassDef):
            classes.append(
                ClassInfo(
                    name=node.name,
                    lineno=node.lineno,
                    bases=tuple(expr_name(base) for base in node.bases),
                    decorators=tuple(expr_name(decorator) for decorator in node.decorator_list),
                )
            )
        elif isinstance(node, ast.Assign):
            if any(is_name(target, "__all__") for target in node.targets):
                all_exports = literal_string_tuple(node.value)

    return ModuleInfo(
        path=path,
        imports=tuple(imports),
        classes=tuple(classes),
        all_exports=all_exports,
    )


def check_imports(modules: list[ModuleInfo]) -> list[Violation]:
    """Check forbidden inward dependency violations."""
    violations: list[Violation] = []
    for module in modules:
        if is_under(module.path, APP_ROOT / "domain"):
            forbidden = FORBIDDEN_DOMAIN_IMPORT_PREFIXES
        elif is_under(module.path, APP_ROOT / "usecase"):
            forbidden = FORBIDDEN_USECASE_IMPORT_PREFIXES
        else:
            continue

        for imported in module.imports:
            if imported.startswith(forbidden):
                violations.append(
                    Violation(
                        code="DDD001",
                        path=module.path,
                        message=f"forbidden layer import `{imported}`",
                    )
                )
    return violations


def check_dataclasses(modules: list[ModuleInfo]) -> list[Violation]:
    """Check dataclass ownership and one-domain-class-per-file rules."""
    violations: list[Violation] = []
    for module in modules:
        dataclasses = [class_ for class_ in module.classes if class_.is_dataclass]
        if not dataclasses:
            continue

        if not dataclass_allowed_path(module.path):
            names = ", ".join(class_.name for class_ in dataclasses)
            violations.append(
                Violation(
                    code="DDD101",
                    path=module.path,
                    message=f"dataclass outside domain entity/value_object/event/contract ownership: {names}",
                )
            )

        if is_domain_entity_or_value_object_file(module.path) and len(dataclasses) > 1:
            names = ", ".join(class_.name for class_ in dataclasses)
            violations.append(
                Violation(
                    code="DDD102",
                    path=module.path,
                    message=f"multiple dataclasses in one domain file: {names}",
                )
            )

        if is_domain_entity_or_value_object_file(module.path):
            expected = snake_case(dataclasses[0].name)
            if module.path.stem != expected:
                violations.append(
                    Violation(
                        code="DDD103",
                        path=module.path,
                        message=f"file name should be `{expected}.py` for `{dataclasses[0].name}`",
                    )
                )
    return violations


def check_exceptions(modules: list[ModuleInfo]) -> list[Violation]:
    """Check exception placement and exports."""
    violations: list[Violation] = []
    exception_modules: dict[Path, list[str]] = {}

    for module in modules:
        exceptions = [class_ for class_ in module.classes if class_.is_exception]
        if not exceptions:
            continue

        if "exceptions" not in module.path.parts:
            names = ", ".join(class_.name for class_ in exceptions)
            violations.append(
                Violation(
                    code="DDD201",
                    path=module.path,
                    message=f"exception classes must live in a domain exceptions package: {names}",
                )
            )
            continue

        if len(exceptions) > 1:
            names = ", ".join(class_.name for class_ in exceptions)
            violations.append(
                Violation(
                    code="DDD202",
                    path=module.path,
                    message=f"one exception class per file required: {names}",
                )
            )

        exception = exceptions[0]
        expected = snake_case(exception.name)
        if module.path.stem != expected:
            violations.append(
                Violation(
                    code="DDD203",
                    path=module.path,
                    message=f"file name should be `{expected}.py` for `{exception.name}`",
                )
            )
        exception_modules[module.path] = [class_.name for class_ in exceptions]

    init_exports = {
        module.path.parent: set(module.all_exports)
        for module in modules
        if module.path.name == "__init__.py" and module.path.parent.name == "exceptions"
    }
    for path, names in exception_modules.items():
        exports = init_exports.get(path.parent, set())
        for name in names:
            if name not in exports:
                violations.append(
                    Violation(
                        code="DDD204",
                        path=path.parent / "__init__.py",
                        message=f"`{name}` is not exported from exceptions package",
                    )
                )
    return violations


def check_repositories(modules: list[ModuleInfo]) -> list[Violation]:
    """Check repository port and implementation placement."""
    violations: list[Violation] = []
    for module in modules:
        repositories = [class_ for class_ in module.classes if class_.is_repository]
        if not repositories:
            continue

        in_domain = is_under(module.path, APP_ROOT / "domain")
        in_repositories_dir = "repositories" in module.path.parts
        in_infrastructure = is_under(module.path, APP_ROOT / "infrastructure")

        for repository in repositories:
            if in_domain and not in_repositories_dir:
                violations.append(
                    Violation(
                        code="DDD301",
                        path=module.path,
                        message=f"repository port `{repository.name}` must be under `repositories/`",
                    )
                )
            if in_domain and repository.name.endswith("Impl"):
                violations.append(
                    Violation(
                        code="DDD302",
                        path=module.path,
                        message=f"repository implementation `{repository.name}` cannot live in domain",
                    )
                )
            if not in_domain and not in_infrastructure and repository.name.endswith("Repository"):
                violations.append(
                    Violation(
                        code="DDD303",
                        path=module.path,
                        message=f"repository `{repository.name}` belongs in domain port or infrastructure implementation",
                    )
                )
    return violations


def check_tests(modules: list[ModuleInfo]) -> list[Violation]:
    """Check that source files have mirrored test paths."""
    violations: list[Violation] = []
    for module in modules:
        if module.path.name == "__init__.py":
            continue
        if "__pycache__" in module.path.parts:
            continue
        if should_skip_test_mirror(module.path):
            continue

        expected = expected_test_path(module.path)
        if not expected.exists():
            violations.append(
                Violation(
                    code="DDD401",
                    path=module.path,
                    message=f"missing mirrored test `{expected.relative_to(ROOT)}`",
                )
            )
    return violations


def dataclass_allowed_path(path: Path) -> bool:
    """Return whether dataclass definitions are allowed in a path."""
    parts = path.parts
    if is_under(path, TEST_ROOT):
        return True
    if not is_under(path, APP_ROOT / "domain"):
        return False
    return any(part in parts for part in ("entities", "value_objects"))


def is_domain_entity_or_value_object_file(path: Path) -> bool:
    """Return whether path is a domain entity/value object source file."""
    if not is_under(path, APP_ROOT / "domain"):
        return False
    return "entities" in path.parts or "value_objects" in path.parts


def should_skip_test_mirror(path: Path) -> bool:
    """Return whether a file is exempt from mirror-test enforcement."""
    if path.name in {"config.py", "main.py"}:
        return True
    if path.suffix != ".py":
        return True
    if path.name.endswith("_dto.py"):
        return False
    return False


def expected_test_path(path: Path) -> Path:
    """Return the expected mirrored test path for an app source file."""
    relative = path.relative_to(APP_ROOT)
    return TEST_ROOT / relative.parent / f"test_{path.name}"


def is_under(path: Path, parent: Path) -> bool:
    """Return whether path is under parent."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def expr_name(node: ast.AST) -> str:
    """Return a dotted expression name for an AST node."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = expr_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return expr_name(node.func)
    return ""


def is_name(node: ast.AST, name: str) -> bool:
    """Return whether an AST node is a Name with the given value."""
    return isinstance(node, ast.Name) and node.id == name


def literal_string_tuple(node: ast.AST) -> tuple[str, ...]:
    """Return literal string values from a tuple/list assignment."""
    if not isinstance(node, ast.Tuple | ast.List):
        return ()
    values: list[str] = []
    for element in node.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            values.append(element.value)
    return tuple(values)


def snake_case(name: str) -> str:
    """Convert CamelCase to snake_case."""
    chars: list[str] = []
    for index, char in enumerate(name):
        if char.isupper() and index > 0:
            previous = name[index - 1]
            next_char = name[index + 1] if index + 1 < len(name) else ""
            if previous.islower() or (next_char and next_char.islower()):
                chars.append("_")
        chars.append(char.lower())
    return "".join(chars)


if __name__ == "__main__":
    raise SystemExit(main())
