#!/usr/bin/env python3
"""PreToolUse(Bash) hook: tmux send-keys 로 보내는 `/exit` 은 worker pane 에만 허용한다.

orchestrator·design·다른 묶음 세션을 실수로 닫지 않게 대상 pane 제목을 확인한다.
"""

import json
import re
import shlex
import subprocess
import sys


def main() -> None:
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    if "send-keys" not in command or "/exit" not in command:
        return
    for target in exit_targets(command):
        title = pane_title(target)
        if "-worker-" not in title:
            print(
                f"BLOCKED: multi-session-exit-guard — /exit target pane {target} is not a worker (title: {title!r})",
                file=sys.stderr,
            )
            sys.exit(2)


def exit_targets(command: str) -> list[str]:
    targets = []
    for segment in re.split(r"&&|\|\||;|\n", command):
        if "send-keys" not in segment or "/exit" not in segment:
            continue
        tokens = shlex.split(segment)
        if "-t" not in tokens:
            print(
                f"BLOCKED: multi-session-exit-guard — /exit without explicit -t target: {segment.strip()!r}",
                file=sys.stderr,
            )
            sys.exit(2)
        targets.append(tokens[tokens.index("-t") + 1])
    return targets


def pane_title(target: str) -> str:
    title = subprocess.run(
        ["tmux", "display", "-p", "-t", target, "#{pane_title}"], capture_output=True, text=True
    ).stdout.strip()
    return title.split(" ", 1)[-1] if " " in title else title


if __name__ == "__main__":
    main()
