#!/usr/bin/env python3
"""Stop hook: 1시간 캐시가 만료되기 전에 idle 세션을 /compact 한다.

캐시가 만료된 뒤 깨어나면 컨텍스트 전체를 cache write(read 의 약 12배 단가)로 다시 쓴다.
만료 전에 요약해 두면 깨어날 때 요약만 다시 쓴다 (10-22~30: 1시간+ 쉬고 재개한 호출 394회, cache write $436).

Stop 마다 pane 의 마지막 활동 시각만 갱신하고, 대기 프로세스는 pane 당 하나만 둔다.
출력이 없으므로 대화 컨텍스트에 아무것도 넣지 않는다.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# 캐시 TTL(1시간) 전에 compact 가 끝나도록 5분 여유를 둔다
_IDLE_SECONDS = int(os.environ.get("IDLE_COMPACT_SECONDS", "3300"))
_CACHE_TTL_SECONDS = int(os.environ.get("IDLE_COMPACT_TTL_SECONDS", "3600"))
# Mac 잠자기 동안 sleep 도 멈추므로 짧게 끊어 벽시계로 다시 잰다
_POLL_SECONDS = 60
# 이보다 작으면 다시 쓰는 비용보다 compact 비용이 커서 하지 않는다. compact 직후 반복도 이것으로 막는다
_MIN_CONTEXT_TOKENS = int(os.environ.get("IDLE_COMPACT_MIN_TOKENS", "60000"))
_TAIL_BYTES = 2_000_000
_SINCE = "@claude_idle_since"
_WAITER = "@claude_idle_waiter"
_TRANSCRIPT = "@claude_idle_transcript"


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--wait":
        _wait_and_compact(sys.argv[2])
        return
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return
    hook_input = json.load(sys.stdin)
    _set_option(pane, _SINCE, str(int(time.time())))
    _set_option(pane, _TRANSCRIPT, hook_input["transcript_path"])
    if _waiter_alive(pane):
        return
    waiter = subprocess.Popen(
        [sys.executable, __file__, "--wait", pane],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _set_option(pane, _WAITER, str(waiter.pid))


def _wait_and_compact(pane: str) -> None:
    while True:
        since = _get_option(pane, _SINCE)
        if not since:
            return
        idle = time.time() - int(since)
        if idle < _IDLE_SECONDS:
            time.sleep(min(_POLL_SECONDS, _IDLE_SECONDS - idle))
            continue
        # 잠자기에서 깨어 이미 TTL 이 지났으면 compact 가 전체를 다시 쓰고도 얻는 게 없다
        if idle < _CACHE_TTL_SECONDS and _ready_to_compact(pane):
            _send_compact(pane)
        # 판정하는 동안 새 Stop 이 왔으면 그 idle 구간을 이어서 기다린다
        if _get_option(pane, _SINCE) == since:
            _unset_option(pane, _WAITER)
            return


def _ready_to_compact(pane: str) -> bool:
    if _get_option(pane, "@claude_state") != "idle":
        return False
    if _get_option(pane, "@claude_agents_running") not in ("", "0"):
        return False
    if not _prompt_empty(pane):
        return False
    return _last_context_tokens(_get_option(pane, _TRANSCRIPT)) > _MIN_CONTEXT_TOKENS


def _prompt_empty(pane: str) -> bool:
    # 입력창 줄은 '❯' 뒤에 NBSP 가 붙는다. NBSP·공백을 지우고 '❯' 만 남으면 비어 있음
    screen = subprocess.run(
        ["tmux", "capture-pane", "-p", "-t", pane], capture_output=True, text=True
    ).stdout
    prompt_lines = [line for line in screen.splitlines() if line.startswith("❯")]
    return (
        bool(prompt_lines) and prompt_lines[-1].replace(" ", "").replace(" ", "") == "❯"
    )


def _last_context_tokens(transcript: str) -> int:
    path = Path(transcript)
    if not transcript or not path.is_file():
        return 0
    with path.open("rb") as transcript_file:
        transcript_file.seek(max(0, path.stat().st_size - _TAIL_BYTES))
        tail = transcript_file.read().decode(errors="ignore").splitlines()
    for line in reversed(tail):
        if '"usage"' not in line:
            continue
        try:
            usage = json.loads(line)["message"]["usage"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        return (
            usage.get("input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
        )
    return 0


def _send_compact(pane: str) -> None:
    subprocess.run(["tmux", "send-keys", "-t", pane, "-l", "/compact"], check=True)
    time.sleep(1)
    subprocess.run(["tmux", "send-keys", "-t", pane, "Enter"], check=True)


def _waiter_alive(pane: str) -> bool:
    pid = _get_option(pane, _WAITER)
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)  # signal 0: 보내지 않고 살아 있는지만 확인
    except (ProcessLookupError, PermissionError, ValueError):
        return False
    return True


def _get_option(pane: str, name: str) -> str:
    return subprocess.run(
        ["tmux", "show-options", "-p", "-v", "-t", pane, name],
        capture_output=True,
        text=True,
    ).stdout.strip()


def _set_option(pane: str, name: str, value: str) -> None:
    subprocess.run(
        ["tmux", "set-option", "-p", "-t", pane, name, value], capture_output=True
    )


def _unset_option(pane: str, name: str) -> None:
    subprocess.run(
        ["tmux", "set-option", "-p", "-u", "-t", pane, name], capture_output=True
    )


if __name__ == "__main__":
    main()
