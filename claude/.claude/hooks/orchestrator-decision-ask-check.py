#!/usr/bin/env python3
"""Stop hook: orchestrator 가 "남은 결정 N건" 을 글로 끝내지 못하게 한다.

orchestrator skill 은 남은 결정을 그 턴에 AskUserQuestion 으로 띄우라고 하지만 글로 나열하고 끝내는 일이 반복돼서,
이번 턴 마지막 글에 대기 결정 목록이 있는데 AskUserQuestion 호출이 없으면 막는다.
"""

import json
import os
import re
import subprocess
import sys

# 줄 머리의 "남은 결정 N건" · "결정 N건 대기" · "결정 필요" 만 본다 — worker 보고를 인용한 `>` 줄은 제외
PENDING_DECISION_LINE = re.compile(
    r"^[ \t\-*#]*(?:남은 결정\s*\d+\s*건|결정\s*\d+\s*건\s*대기|결정 필요)",
    re.MULTILINE,
)
# 마지막 글의 끝부분만 본다 — 본문 중간의 설명은 대기 목록이 아니다
TAIL_CHARS = 800
# transcript 끝에서 이만큼만 읽는다
TAIL_BYTES = 512 * 1024


def main() -> None:
    hook_input = json.load(sys.stdin)
    # 같은 턴에 한 번만 막는다 — 무한 반복 방지
    if hook_input.get("stop_hook_active"):
        return
    # transcript 에는 최종 답이 늦게 기록될 수 있어 Stop 입력의 최종 답을 읽는다
    final_text = hook_input["last_assistant_message"]
    if not PENDING_DECISION_LINE.search(final_text[-TAIL_CHARS:]):
        return
    if asked_user_question(current_turn_entries(hook_input["transcript_path"])):
        return
    pane = os.environ.get("TMUX_PANE")
    if not pane or not pane_title(pane).endswith("-orchestrator"):
        return
    reason = (
        "마지막 글에 대기 중인 결정 목록이 있는데 이번 턴에 AskUserQuestion 을 부르지 않았다. "
        'orchestrator skill 규칙대로 "남은 결정 N건" 으로 끝내지 말고, 가장 급한 결정 하나를 지금 AskUserQuestion 으로 물을 것.'
    )
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


def current_turn_entries(transcript_path: str) -> list[dict]:
    """마지막 실제 user 메시지 이후의 entry. 꼬리 안에서 경계를 못 찾으면 빈 목록(허용)."""
    entries = tail_entries(transcript_path)
    for index in range(len(entries) - 1, -1, -1):
        if is_real_user_message(entries[index]):
            return entries[index + 1 :]
    return []


def tail_entries(transcript_path: str) -> list[dict]:
    with open(transcript_path, "rb") as transcript:
        transcript.seek(0, os.SEEK_END)
        start = max(0, transcript.tell() - TAIL_BYTES)
        transcript.seek(start)
        raw_lines = transcript.read().decode("utf-8", errors="replace").splitlines()
    # 꼬리 첫 줄은 중간에서 잘렸을 수 있다
    if start > 0:
        raw_lines = raw_lines[1:]
    return [json.loads(line) for line in raw_lines if line.strip()]


def is_real_user_message(entry: dict) -> bool:
    # tool_result 만 담은 user entry 는 사용자 입력이 아니다
    if entry.get("type") != "user":
        return False
    content = entry.get("message", {}).get("content", "")
    if isinstance(content, str):
        return True
    return any(
        isinstance(block, dict) and block.get("type") != "tool_result"
        for block in content
    )


def asked_user_question(entries: list[dict]) -> bool:
    for entry in entries:
        if entry.get("type") != "assistant":
            continue
        content = entry.get("message", {}).get("content", [])
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == "AskUserQuestion"
            ):
                return True
    return False


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
