"""Git checks that run before `f1 sync` touches the data files.

Sync rewrites the same files the data-sync workflow commits to main, so running
it on a half-merged or out-of-date checkout is how local data ends up in
conflict. Where these checks can't run (a tarball deploy, no git, no upstream,
no network) they report nothing and sync carries on.
"""
from __future__ import annotations

import contextlib
import os
import subprocess
from pathlib import Path

_FETCH_STALL_SECONDS = 10
_FETCH_TIMEOUT_SECONDS = 15

_UNFINISHED_MARKERS = {
    "MERGE_HEAD": "merge",
    "rebase-merge": "rebase",
    "rebase-apply": "rebase",
    "CHERRY_PICK_HEAD": "cherry-pick",
    "REVERT_HEAD": "revert",
}


def _environment() -> dict[str, str]:
    return {**os.environ, "GIT_TERMINAL_PROMPT": "0"}


def _git(repo: Path, *args: str) -> str | None:
    """A git command's output, or None if it couldn't run or failed."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            env=_environment(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _fetch(repo: Path) -> None:
    """Refresh the remote-tracking refs, giving up quietly on a stalled remote.

    Don't capture this command's output. On Windows a helper process outlives the
    timeout and holds the pipes open, so reading them would wait forever.
    """
    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
        subprocess.run(
            [
                "git", "-C", str(repo),
                "-c", "http.lowSpeedLimit=1",
                "-c", f"http.lowSpeedTime={_FETCH_STALL_SECONDS}",
                "fetch", "--quiet",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=_FETCH_TIMEOUT_SECONDS,
            env=_environment(),
        )


def unfinished_operation(repo: Path) -> str | None:
    """The git operation left in progress in `repo`, if there is one."""
    git_dir = _git(repo, "rev-parse", "--absolute-git-dir")
    if git_dir is None:
        return None
    for marker, operation in _UNFINISHED_MARKERS.items():
        if (Path(git_dir) / marker).exists():
            return operation
    return None


def commits_behind(repo: Path) -> int:
    """How many commits the upstream has that `repo` doesn't. 0 when unknown."""
    _fetch(repo)
    count = _git(repo, "rev-list", "--count", "HEAD..@{upstream}")
    return int(count) if count else 0
