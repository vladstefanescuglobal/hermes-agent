"""The installer stage and later desktop product build are separate processes."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.platforms("windows")
def test_packaged_desktop_build_restores_pm_git_for_stamp_and_pack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pm
    from hermes_cli import main_desktop

    desktop = tmp_path / "apps" / "desktop"
    desktop.mkdir(parents=True)
    original = {"PATH": "C:\\without-git", "HERMES_HOME": str(tmp_path)}
    calls: list[tuple[list[str], dict[str, str]]] = []

    def installed_git(*names: str, base_env: dict[str, str]) -> dict[str, str]:
        assert names == ("git",)
        assert base_env == original
        return {**base_env, "PATH": "C:\\pm-pinned-git\\cmd;" + base_env["PATH"]}

    def run(command: list[str], *, env: dict[str, str], **_kwargs: object) -> None:
        calls.append((command, env))

    monkeypatch.setattr(pm, "ensure", lambda *names, base_env, **_: SimpleNamespace(env=installed_git(*names, base_env=base_env)))
    monkeypatch.setattr(main_desktop.subprocess, "run", run)
    monkeypatch.setattr(main_desktop, "_promote_staged_desktop_app", lambda *_args: desktop / "Hermes.exe")
    main_desktop.build_prepared_desktop(desktop, source_mode=False, npm="C:\\node\\npm.cmd", env=original)

    assert [command[2] for command, _ in calls] == ["build", "builder"]
    assert all(env["PATH"].startswith("C:\\pm-pinned-git\\cmd;") for _, env in calls)
    assert original["PATH"] == "C:\\without-git"


@pytest.mark.platforms("windows")
def test_packaged_desktop_build_keeps_system_git_without_pm_provisioning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pm
    from hermes_cli import main_desktop

    desktop = tmp_path / "apps" / "desktop"
    desktop.mkdir(parents=True)
    original = {"PATH": "C:\\system-git\\cmd;C:\\Windows\\System32", "HERMES_HOME": str(tmp_path)}
    calls: list[tuple[list[str], dict[str, str]]] = []

    monkeypatch.setattr("shutil.which", lambda name, path=None: "C:\\system-git\\cmd\\git.exe"
                        if name == "git" and path == original["PATH"] else None)
    monkeypatch.setattr(pm, "ensure", lambda *_args, **_kwargs: pytest.fail("PM should not provision Git"))
    monkeypatch.setattr(main_desktop.subprocess, "run",
                        lambda command, *, env, **_kwargs: calls.append((command, env)))
    monkeypatch.setattr(main_desktop, "_promote_staged_desktop_app", lambda *_args: desktop / "Hermes.exe")

    main_desktop.build_prepared_desktop(desktop, source_mode=False, npm="C:\\node\\npm.cmd", env=original)

    assert [command[2] for command, _ in calls] == ["build", "builder"]
    assert all(env["PATH"] == original["PATH"] for _, env in calls)
