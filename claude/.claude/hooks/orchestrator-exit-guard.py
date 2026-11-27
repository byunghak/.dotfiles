#!/usr/bin/env python3
"""PreToolUse(Bash) hook: tmux 로 세션을 닫는 명령(`kill-pane`, send-keys 로 보내는 `/exit`)은 worker pane 에만 허용한다.

orchestrator·design·다른 묶음 세션을 실수로 닫지 않게 대상 pane 제목을 확인한다.
kill-pane 은 진행 중인 턴을 끊으므로 @claude_state 가 busy·waiting 이면 막는다.
worker 가 만든 worktree(@claude_worktrees, worker-worktree-record.py 가 적음)가 남아 있으면 막는다 — 지우지는 않는다.
"""

import json
import os
import re
import shlex
import subprocess
import sys

RUNNING_STATES = ("busy", "waiting")
SHELL_PREFIXES = (
    "",
    "do",
    "then",
    "else",
    "elif",
    "!",
    "time",
    "command",
    "exec",
    "sudo",
    "env",
    "xargs",
)


def main() -> None:
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    if "kill-pane" not in command and not (
        "send-keys" in command and "/exit" in command
    ):
        return
    for action, target in close_targets(command):
        title, state = pane_info(target)
        if "-worker-" not in title:
            block(f"{action} target pane {target} is not a worker (title: {title!r})")
        if action == "kill-pane" and state in RUNNING_STATES:
            block(
                f"kill-pane target pane {target} is {state} — wait until it is idle (title: {title!r})"
            )
        leftover = leftover_worktrees(target)
        if leftover:
            block(
                f"{action} target pane {target} still has worktrees it created: {', '.join(leftover)} "
                f"(title: {title!r}). Have the worker remove them, or record kept paths in "
                f"@claude_worktrees_keep with a reason (session-worker skill)"
            )


def close_targets(command: str) -> list[tuple[str, str]]:
    targets = []
    for segment in re.split(r"&&|\|\||;|\n", command):
        tokens = split_tokens(segment)
        # 명령 자리가 tmux 인 조각만 본다 (글 본문에 나온 "tmux kill-pane" 은 건너뜀)
        if not runs_tmux(tokens):
            continue
        if "kill-pane" in tokens:
            action = "kill-pane"
        elif "send-keys" in tokens and "/exit" in segment:
            action = "/exit"
        else:
            continue
        if "-t" not in tokens:
            block(f"{action} without explicit -t target: {segment.strip()!r}")
        targets.append((action, tokens[tokens.index("-t") + 1]))
    return targets


def runs_tmux(tokens: list[str]) -> bool:
    # 앞의 변수 대입·셸 키워드(for 의 do 등)·괄호는 건너뛰고 첫 명령 이름을 본다
    command_words = [
        token
        for token in tokens
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token)
        and token.lstrip("({") not in SHELL_PREFIXES
    ]
    return bool(command_words) and command_words[0].rsplit("/", 1)[-1] == "tmux"


def split_tokens(segment: str) -> list[str]:
    # heredoc 본문처럼 따옴표 짝이 안 맞는 조각은 shlex 가 못 푸니 공백으로 나눈다
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def pane_info(target: str) -> tuple[str, str]:
    output = subprocess.run(
        ["tmux", "display", "-p", "-t", target, "#{pane_title}\t#{@claude_state}"],
        capture_output=True,
        text=True,
    ).stdout.rstrip("\n")
    title, _, state = output.partition("\t")
    title = title.split(" ", 1)[-1] if " " in title else title
    return title, state


def leftover_worktrees(target: str) -> list[str]:
    """worker-worktree-record 가 적은 경로 중 아직 있고 보존 목록에 없는 것."""
    output = subprocess.run(
        [
            "tmux",
            "display",
            "-p",
            "-t",
            target,
            "#{@claude_worktrees}\t#{@claude_worktrees_keep}",
        ],
        capture_output=True,
        text=True,
    ).stdout.rstrip("\n")
    recorded, _, kept = output.partition("\t")
    kept_paths = {os.path.realpath(path) for path in kept.split("|") if path}
    return [
        path
        for path in recorded.split("|")
        if path and os.path.isdir(path) and os.path.realpath(path) not in kept_paths
    ]


def block(reason: str) -> None:
    print(f"BLOCKED: orchestrator-exit-guard — {reason}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
