from __future__ import annotations

from pathlib import Path

import pytest

from core.path_guard import PathGuard, PathGuardError
from core.workspace_service import WorkspaceService


def test_path_guard_allows_only_paths_inside_workspace(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    guard = PathGuard(root)

    assert guard.resolve_safe_path("Projects/demo.txt") == root / "Projects" / "demo.txt"
    with pytest.raises(PathGuardError):
        guard.resolve_safe_path("../outside.txt")
    with pytest.raises(PathGuardError):
        guard.resolve_safe_path(str(tmp_path / "outside.txt"))
    with pytest.raises(PathGuardError):
        guard.resolve_safe_path("Documents/file.txt:secret")


def test_workspace_copies_external_input_and_creates_safe_artifacts(tmp_path: Path):
    source = tmp_path / "original.txt"
    source.write_text("original", encoding="utf-8")
    workspace = WorkspaceService(tmp_path / "Roman2050 Workspace")
    workspace.ensure()

    imported = workspace.copy_input_to_workspace(source)
    artifact = workspace.create_artifact_path("Documents", "answer.md")
    artifact.write_text("new copy", encoding="utf-8")

    assert imported.parent == workspace.root / "Imports"
    assert imported.read_text(encoding="utf-8") == "original"
    assert source.read_text(encoding="utf-8") == "original"
    assert artifact.is_relative_to(workspace.root)
    with pytest.raises(PathGuardError):
        workspace.create_artifact_path("Documents", "../outside.md")
