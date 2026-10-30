#!/usr/bin/env python3
"""Stop hook: orchestrator 가 끝난 worker 세션을 닫지 않고 턴을 끝내지 못하게 한다.

worker 의 표준 보고 `#N 닫음 · 남은 일 없음`(이슈 없이 PR 정리만 하면 `#N 정리 끝 · 남은 일 없음`) 을 transcript 에서 직접 찾는다.
상태 파일에 orchestrator 가 손으로 적게 하면 그 기록 자체를 잊을 수 있어서다 (10-27: 닫기 규칙이 skill 에 있었지만 지켜지지 않음).
"""

import json
import os
import re
import subprocess
import sys

DONE_REPORT = re.compile(
    r'<cross-session-message[^>]*from-name="([^"]+-worker-[^"]+)"[^>]*>\s*#\d+ (?:닫음|정리 끝) · 남은 일 없음'
)


def main() -> None:
    hook_input = json.load(sys.stdin)
    # 같은 턴에 한 번만 막는다 — /exit 이 실패해도 무한 반복하지 않게
    if hook_input.get("stop_hook_active"):
        return
    pane = os.environ.get("TMUX_PANE")
    if not pane or not pane_title(pane).endswith("-orchestrator"):
        return
    open_workers = sorted(reported_done_workers(hook_input["transcript_path"]) & live_pane_titles())
    if not open_workers:
        return
    reason = (
        "작업이 끝났다고 보고한 worker 세션이 아직 열려 있다: "
        + ", ".join(open_workers)
        + ". multi-session skill 대로 pane 이 idle·입력 칸이 빈 것을 확인하고 `/exit` 을 보낸 뒤 상태 파일에 적을 것. "
        "busy 면 이유를 사용자에게 말하고 턴을 끝내도 된다."
    )
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


def reported_done_workers(transcript_path: str) -> set[str]:
    names: set[str] = set()
    with open(transcript_path, encoding="utf-8") as transcript:
        for line in transcript:
            # unicode escape 된 줄이라 cross-session 표식으로 먼저 거른다
            if "cross-session-message" not in line:
                continue
            entry = json.loads(line)
            if entry.get("type") != "user":
                continue
            names.update(DONE_REPORT.findall(message_text(entry.get("message", {}))))
    return names


def message_text(message: dict) -> str:
    # content 는 문자열이거나 text 블록 목록이다
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    return "\n".join(block.get("text", "") for block in content if isinstance(block, dict))


def live_pane_titles() -> set[str]:
    listing = subprocess.run(
        ["tmux", "list-panes", "-a", "-F", "#{pane_title}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {strip_status_glyph(title) for title in listing.splitlines()}


def pane_title(pane: str) -> str:
    title = subprocess.run(
        ["tmux", "display", "-p", "-t", pane, "#{pane_title}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return strip_status_glyph(title.strip())


def strip_status_glyph(title: str) -> str:
    # Claude 가 pane 제목 앞에 붙이는 상태 기호(✳ 등) 제거
    return title.split(" ", 1)[-1] if " " in title else title


if __name__ == "__main__":
    main()
