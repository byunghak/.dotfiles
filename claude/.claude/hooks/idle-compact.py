#!/usr/bin/env python3
"""Stop hook: 1시간 캐시가 만료되기 전에 idle 세션을 /compact 한다.

캐시가 만료된 뒤 깨어나면 컨텍스트 전체를 cache write(read 의 약 12배 단가)로 다시 쓴다.
만료 전에 요약해 두면 깨어날 때 요약만 다시 쓴다 (10-22~30: 1시간+ 쉬고 재개한 호출 394회, cache write $436).

orchestrator pane(제목이 *-orchestrator)은 compact 대신 상태 파일 갱신을 요청하고, 갱신이 확인되면 /clear 한 뒤
상태 파일과 직전 transcript 로 이어가게 한다. compact 요약은 상태 파일보다 커서(orchestrator 실측: compact 직후 104K, 새 시작 48K) 다시 빨리 찬다.
갱신이 확인되지 않으면 compact 한다.

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
# orchestrator 가 flush 턴에서 자기 상태 파일 절대 경로를 적는 pane 옵션
_STATUS_FILE = "@claude_status_file"
# flush 턴이 이 안에 끝나지 않으면(사용자가 끼어듦 등) clear·compact 모두 하지 않는다
_FLUSH_TIMEOUT_SECONDS = 600
_CLEAR_SCRIPT = Path.home() / ".dotfiles/tmux/clear-claude-pane.sh"


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
            if _pane_title(pane).endswith("-orchestrator"):
                _flush_then_clear(pane)
            else:
                _send_line(pane, "/compact")
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


def _flush_then_clear(pane: str) -> None:
    flush_sent_at = time.time()
    since_before_flush = _get_option(pane, _SINCE)
    _send_line(pane, _flush_prompt(pane))
    flush_end_since = _wait_turn_end(pane, since_before_flush)
    if flush_end_since is None:
        return
    status_file = _get_option(pane, _STATUS_FILE)
    if not _modified_after(status_file, flush_sent_at):
        _send_line(pane, "/compact")
        return
    # flush 턴 뒤 다른 턴(worker 메시지 처리)이 돌았으면 그 내용은 상태 파일에 없다. 다음 idle 에 다시 flush 한다
    if _get_option(pane, _SINCE) != flush_end_since:
        return
    subprocess.run(
        [str(_CLEAR_SCRIPT), pane, _resume_prompt(pane, status_file)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _flush_prompt(pane: str) -> str:
    # send-keys 로 한 줄에 넣으므로 줄바꿈 없이 쓴다 (줄바꿈은 제출로 처리된다)
    return (
        "[idle-clear] 캐시 만료 전에 이 세션을 /clear 한다. 상태 파일을 지금 상태로 갱신하고"
        "(진행 중 질문·기다리는 worker·다음 확인할 것, 바뀐 것이 없으면 touch), "
        f"`tmux set -p -t {pane} {_STATUS_FILE} <상태 파일 절대 경로>` 를 실행한 뒤 다른 일 없이 턴을 끝낼 것."
    )


def _resume_prompt(pane: str, status_file: str) -> str:
    status_written_at = time.strftime(
        "%H:%M:%S", time.localtime(Path(status_file).stat().st_mtime)
    )
    return (
        f"{status_file} 를 먼저 읽고 이어서 orchestrator 를 맡는다. "
        f"직전 대화 transcript: {_get_option(pane, _TRANSCRIPT)} — "
        f"상태 파일 갱신({status_written_at}) 뒤 도착한 cross-session-message 가 그 transcript 에 있으면 그것부터 처리한다."
    )


def _wait_turn_end(pane: str, since_before: str) -> str | None:
    # Stop hook 이 _SINCE 를 새로 적고 pane 이 idle 이 되면 턴이 끝난 것이다
    deadline = time.time() + _FLUSH_TIMEOUT_SECONDS
    while time.time() < deadline:
        time.sleep(2)
        since = _get_option(pane, _SINCE)
        if since != since_before and _get_option(pane, "@claude_state") == "idle":
            return since
    return None


def _modified_after(path: str, timestamp: float) -> bool:
    status_path = Path(path)
    return (
        bool(path)
        and status_path.is_file()
        and status_path.stat().st_mtime >= timestamp
    )


def _send_line(pane: str, text: str) -> None:
    subprocess.run(["tmux", "send-keys", "-t", pane, "-l", text], check=True)
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


def _pane_title(pane: str) -> str:
    title = subprocess.run(
        ["tmux", "display", "-p", "-t", pane, "#{pane_title}"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    # Claude 가 pane 제목 앞에 붙이는 상태 기호(✳ 등) 제거
    return title.split(" ", 1)[-1] if " " in title else title


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
