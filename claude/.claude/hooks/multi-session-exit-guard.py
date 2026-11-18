#!/usr/bin/env python3
"""PreToolUse(Bash) hook: tmux 로 세션을 닫는 명령(`kill-pane`, send-keys 로 보내는 `/exit`)은 worker pane 에만 허용한다.

orchestrator·design·다른 묶음 세션을 실수로 닫지 않게 대상 pane 제목을 확인한다.
kill-pane 은 진행 중인 턴을 끊으므로 @claude_state 가 busy·waiting 이면 막는다.
"""

import json
import re
import shlex
import subprocess
import sys

RUNNING_STATES = ("busy", "waiting")


def main() -> None:
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    if "kill-pane" not in command and not ("send-keys" in command and "/exit" in command):
        return
    for action, target in close_targets(command):
        title, state = pane_info(target)
        if "-worker-" not in title:
            block(f"{action} target pane {target} is not a worker (title: {title!r})")
        if action == "kill-pane" and state in RUNNING_STATES:
            block(f"kill-pane target pane {target} is {state} — wait until it is idle (title: {title!r})")


def close_targets(command: str) -> list[tuple[str, str]]:
    targets = []
    for segment in re.split(r"&&|\|\||;|\n", command):
        tokens = shlex.split(segment)
        if "tmux" in tokens and "kill-pane" in tokens:
            action = "kill-pane"
        elif "send-keys" in tokens and "/exit" in segment:
            action = "/exit"
        else:
            continue
        if "-t" not in tokens:
            block(f"{action} without explicit -t target: {segment.strip()!r}")
        targets.append((action, tokens[tokens.index("-t") + 1]))
    return targets


def pane_info(target: str) -> tuple[str, str]:
    output = subprocess.run(
        ["tmux", "display", "-p", "-t", target, "#{pane_title}\t#{@claude_state}"],
        capture_output=True,
        text=True,
    ).stdout.rstrip("\n")
    title, _, state = output.partition("\t")
    title = title.split(" ", 1)[-1] if " " in title else title
    return title, state


def block(reason: str) -> None:
    print(f"BLOCKED: multi-session-exit-guard — {reason}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
