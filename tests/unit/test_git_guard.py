"""git_guard against real repositories, including real conflicts."""
from __future__ import annotations

import socket
import subprocess
import threading
from pathlib import Path

import pytest

from app.services import git_guard


def _git(repo: Path, *args: str, check: bool = True) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        check=check,
        capture_output=True,
    )


def _commit(repo: Path, content: str, name: str = "data.txt") -> None:
    (repo / name).write_text(content, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", content.strip())


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    _git(path, "init", "-b", "main")
    _commit(path, "base\n")
    return path


def _diverge(repo: Path) -> None:
    """Leave `other` and `main` with conflicting versions of the same line."""
    _git(repo, "checkout", "-b", "other")
    _commit(repo, "theirs\n")
    _git(repo, "checkout", "main")
    _commit(repo, "ours\n")


@pytest.fixture
def cloned(tmp_path: Path) -> tuple[Path, Path]:
    """A checkout with an upstream, plus a second clone that can push to it."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(origin, "init", "--bare", "-b", "main")
    local, other = tmp_path / "local", tmp_path / "other"
    local.mkdir()
    _git(local, "init", "-b", "main")
    _commit(local, "base\n")
    _git(local, "remote", "add", "origin", str(origin))
    _git(local, "push", "-u", "origin", "main")
    subprocess.run(["git", "clone", str(origin), str(other)], check=True, capture_output=True)
    return local, other


def test_folder_outside_git_reports_nothing(tmp_path: Path):
    assert git_guard.unfinished_operation(tmp_path) is None
    assert git_guard.commits_behind(tmp_path) == 0


def test_missing_git_reports_nothing(repo: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert git_guard.unfinished_operation(repo) is None
    assert git_guard.commits_behind(repo) == 0


def test_clean_checkout_has_no_unfinished_operation(repo: Path):
    assert git_guard.unfinished_operation(repo) is None


def test_unfinished_merge_is_named(repo: Path):
    _diverge(repo)
    _git(repo, "merge", "other", check=False)
    assert git_guard.unfinished_operation(repo) == "merge"


def test_unfinished_merge_is_found_from_a_subfolder(repo: Path):
    data = repo / "data"
    data.mkdir()
    _commit(data, "kept\n", name="kept.txt")
    _diverge(repo)
    _git(repo, "merge", "other", check=False)
    assert git_guard.unfinished_operation(data) == "merge"


def test_unfinished_rebase_is_named(repo: Path):
    _diverge(repo)
    _git(repo, "rebase", "other", check=False)
    assert git_guard.unfinished_operation(repo) == "rebase"


def test_unfinished_cherry_pick_is_named(repo: Path):
    _diverge(repo)
    _git(repo, "cherry-pick", "other", check=False)
    assert git_guard.unfinished_operation(repo) == "cherry-pick"


def test_finished_merge_is_no_longer_reported(repo: Path):
    _diverge(repo)
    _git(repo, "merge", "other", check=False)
    _commit(repo, "resolved\n")
    assert git_guard.unfinished_operation(repo) is None


@pytest.mark.parametrize("folder", ["S\u00f8ren", "\u00cdris"])
def test_unfinished_merge_is_found_under_a_non_ascii_path(tmp_path: Path, folder: str):
    path = tmp_path / folder
    path.mkdir()
    _git(path, "init", "-b", "main")
    _commit(path, "base\n")
    _diverge(path)
    _git(path, "merge", "other", check=False)
    assert git_guard.unfinished_operation(path) == "merge"


def test_commits_behind_counts_what_upstream_has(cloned: tuple[Path, Path]):
    local, other = cloned
    assert git_guard.commits_behind(local) == 0

    _commit(other, "first\n")
    _commit(other, "second\n")
    _git(other, "push")

    # Nothing fetched yet, so this also proves the check looks at the remote.
    assert git_guard.commits_behind(local) == 2


def test_checkout_without_an_upstream_is_not_behind(repo: Path):
    assert git_guard.commits_behind(repo) == 0


@pytest.fixture
def stalled_remote():
    """A server that accepts connections and then never says anything."""
    server = socket.create_server(("127.0.0.1", 0))
    connections: list[socket.socket] = []

    def accept() -> None:
        while True:
            try:
                connections.append(server.accept()[0])
            except OSError:
                return

    threading.Thread(target=accept, daemon=True).start()
    yield f"http://127.0.0.1:{server.getsockname()[1]}/repo.git"
    server.close()
    for connection in connections:
        connection.close()


def test_stalled_remote_cannot_hang_the_check(repo: Path, stalled_remote: str, monkeypatch):
    monkeypatch.setattr(git_guard, "_FETCH_STALL_SECONDS", 1)
    monkeypatch.setattr(git_guard, "_FETCH_TIMEOUT_SECONDS", 2)
    _git(repo, "remote", "add", "origin", stalled_remote)
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repo, "config", "branch.main.remote", "origin")
    _git(repo, "config", "branch.main.merge", "refs/heads/main")

    answers: list[int] = []
    worker = threading.Thread(
        target=lambda: answers.append(git_guard.commits_behind(repo)), daemon=True
    )
    worker.start()
    worker.join(timeout=10)

    assert answers == [0], "the check was still waiting on the remote"
