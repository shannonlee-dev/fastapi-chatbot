"""구현체 조립과 HTTP·Service·Repository 의존 경계를 검증한다."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP_DIRECTORY = Path(__file__).resolve().parents[1] / "app"


def _imports(path: Path) -> list[tuple[str, str]]:
    imports: list[tuple[str, str]] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            imports.extend((node.module or "", name.name) for name in node.names)
        elif isinstance(node, ast.Import):
            imports.extend((name.name, "") for name in node.names)
    return imports


@pytest.mark.parametrize(
    "path",
    sorted(APP_DIRECTORY.glob("*/service.py")),
    ids=lambda path: path.parent.name,
)
def test_services_depend_on_contracts_instead_of_runtime_implementations(
    path: Path,
) -> None:
    violations = [
        (module, name)
        for module, name in _imports(path)
        if module.startswith(("fastapi", "starlette", "openai"))
        or module.endswith(
            (".application", ".openai_client", ".router", ".dependencies")
        )
        or name.startswith("SqlAlchemy")
        or (module == "sqlalchemy.orm" and name == "Session")
        or (module == "app.core.config" and name == "settings")
    ]

    assert violations == []


@pytest.mark.parametrize(
    "path",
    sorted(APP_DIRECTORY.glob("*/router.py"))
    + [APP_DIRECTORY / "auth" / "dependencies.py"],
    ids=lambda path: f"{path.parent.name}/{path.name}",
)
def test_http_layers_call_public_entrypoints_instead_of_persistence(path: Path) -> None:
    violations = [
        module
        for module, _name in _imports(path)
        if module.endswith((".repository", ".models", ".service", ".openai_client"))
        or module.startswith("openai")
    ]

    assert violations == []


@pytest.mark.parametrize(
    "path",
    sorted(APP_DIRECTORY.glob("*/repository.py")),
    ids=lambda path: path.parent.name,
)
def test_repositories_do_not_depend_on_use_cases_or_http(path: Path) -> None:
    violations = [
        module
        for module, _name in _imports(path)
        if module.endswith(
            (".application", ".service", ".router", ".dependencies", ".http")
        )
        or module.startswith(("fastapi", "starlette", "openai"))
    ]

    assert violations == []
