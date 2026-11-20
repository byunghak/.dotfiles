#!/usr/bin/env python3
"""PreToolUse(AskUserQuestion) hook: 세션 묶음 worker pane 에서는 질문 창을 막고 orchestrator 로 보내게 한다.

사용자는 worker pane 에 답하지 않아 질문 창이 뜨면 worker 가 그 자리에서 멈춘다.
같은 묶음의 orchestrator pane 이 없으면 물을 곳이 사용자뿐이라 막지 않는다.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

WORKER_MARK = "-worker-"
TMUX_TIMEOUT_SECONDS = 3


def main() -> None:
    json.load(sys.stdin)
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return
    session_name = _session_name(_tmux("display", "-p", "-t", pane, "#{pane_title}"))
    if WORKER_MARK not in session_name:
        return
    orchestrator_name = session_name.split(WORKER_MARK, 1)[0] + "-orchestrator"
    open_sessions = {
        _session_name(title)
        for title in _tmux("list-panes", "-a", "-F", "#{pane_title}").splitlines()
    }
    if orchestrator_name not in open_sessions:
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"{session_name} 은 worker 라 사용자에게 직접 묻지 않는다. 결정 규칙표로 갈라 worker 칸이면 스스로 정하고, "
                        f"아니면 {orchestrator_name} 에 SendMessage 로 `결정 필요: <질문>` 과 선택지·권장안을 보내고 기다린다"
                    ),
                }
            },
            ensure_ascii=False,
        )
    )


def _session_name(pane_title: str) -> str:
    """pane 제목은 `<상태 아이콘> <세션 이름>` 꼴이라 마지막 단어가 세션 이름이다."""
    words = pane_title.split()
    return words[-1] if words else ""


def _tmux(*args: str) -> str:
    completed = subprocess.run(
        ["tmux", *args],
        capture_output=True,
        text=True,
        timeout=TMUX_TIMEOUT_SECONDS,
        check=True,
    )
    return completed.stdout.strip()


if __name__ == "__main__":
    main()
