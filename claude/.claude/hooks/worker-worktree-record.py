#!/usr/bin/env python3
"""PostToolUse(Bash) hook: worker 가 `git worktree add` 로 만든 경로를 자기 pane 옵션 `@claude_worktrees` 에 적는다.

`orchestrator-exit-guard.py` 가 kill-pane 전에 이 목록 중 아직 남은 worktree 를 찾아 닫기를 거부한다.
경로는 `|` 로 잇고, 명령이 실패해 디렉터리가 없으면 적지 않는다.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys

WORKTREES_OPTION = "@claude_worktrees"
PATH_SEPARATOR = "|"
# 값을 하나 더 받는 `git worktree add` 옵션 (경로 위치 인자를 찾을 때 건너뛴다)
OPTIONS_WITH_VALUE = {"-b", "-B", "--orphan", "--reason"}
GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree"}


def main() -> None:
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return
    event = json.load(sys.stdin)
    command = event.get("tool_input", {}).get("command", "")
    if "worktree" not in command or "add" not in command:
        return
    if "-worker-" not in pane_title(pane):
        return
    cwd = event.get("cwd") or os.getcwd()
    added = [path for path in added_worktree_paths(command, cwd) if os.path.isdir(path)]
    if not added:
        return
    recorded = read_paths(pane)
    merged = recorded + [path for path in added if path not in recorded]
    subprocess.run(
        [
            "tmux",
            "set",
            "-p",
            "-t",
            pane,
            WORKTREES_OPTION,
            PATH_SEPARATOR.join(merged),
        ],
        check=True,
    )


def added_worktree_paths(command: str, cwd: str) -> list[str]:
    """명령 안의 `git [-C dir] worktree add [옵션] <경로>` 마다 절대 경로를 돌려준다."""
    paths = []
    for segment in re.split(r"&&|\|\||;|\n", command):
        tokens = split_tokens(segment)
        # 같은 명령 안의 `cd <dir>` 는 뒤 조각의 상대 경로 기준을 바꾼다
        if len(tokens) >= 2 and tokens[0] == "cd":
            cwd = os.path.join(cwd, os.path.expanduser(tokens[1]))
            continue
        path = worktree_add_path(tokens, cwd)
        if path:
            paths.append(path)
    return paths


def worktree_add_path(tokens: list[str], cwd: str) -> str | None:
    # 명령 자리(앞 변수 대입 뒤 첫 단어)가 git 인 조각만 본다 — echo 본문 속 글은 건너뜀
    git_index = 0
    while git_index < len(tokens) and re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[git_index]
    ):
        git_index += 1
    if git_index >= len(tokens) or tokens[git_index].rsplit("/", 1)[-1] != "git":
        return None
    base_dir = cwd
    index = git_index + 1
    # git 전역 옵션(-C 등)을 읽으며 worktree 하위 명령까지 간다
    while index < len(tokens) and tokens[index].startswith("-"):
        if tokens[index] == "-C" and index + 1 < len(tokens):
            base_dir = os.path.join(cwd, os.path.expanduser(tokens[index + 1]))
        index += 2 if tokens[index] in GIT_OPTIONS_WITH_VALUE else 1
    if tokens[index : index + 2] != ["worktree", "add"]:
        return None
    index += 2
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            index += 1
            break
        if not token.startswith("-"):
            break
        index += 2 if token in OPTIONS_WITH_VALUE else 1
    if index >= len(tokens):
        return None
    return os.path.realpath(os.path.join(base_dir, os.path.expanduser(tokens[index])))


def split_tokens(segment: str) -> list[str]:
    # 따옴표 짝이 안 맞는 조각(heredoc 본문 등)은 shlex 가 못 푸니 공백으로 나눈다
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def read_paths(pane: str) -> list[str]:
    value = subprocess.run(
        ["tmux", "display", "-p", "-t", pane, f"#{{{WORKTREES_OPTION}}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return [path for path in value.split(PATH_SEPARATOR) if path]


def pane_title(pane: str) -> str:
    title = subprocess.run(
        ["tmux", "display", "-p", "-t", pane, "#{pane_title}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return title.split(" ", 1)[-1] if " " in title else title


if __name__ == "__main__":
    main()
