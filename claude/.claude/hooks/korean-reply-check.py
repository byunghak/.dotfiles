#!/usr/bin/env python3
"""Stop hook: 한국어로 답해야 하는데 영어로 끝낸 응답을 막는다 (CLAUDE.md Communication).

코드 블록·인라인 코드·URL·경로를 뺀 글자 중 한글 비율이 낮으면 block 한다.
"""

import json
import re
import sys

MIN_LETTERS = 40
MIN_HANGUL_SHARE = 0.05

NON_PROSE = [
    re.compile(r"```.*?(?:```|\Z)", re.DOTALL),
    re.compile(r"`[^`\n]*`"),
    re.compile(r"https?://\S+"),
    re.compile(r"(?:~|\.{0,2})?/[\w.\-/@]+"),
]
HANGUL = re.compile(r"[가-힣]")
LATIN = re.compile(r"[A-Za-z]")


def main() -> None:
    hook_input = json.load(sys.stdin)
    # 같은 턴에 한 번만 막는다 — 무한 반복 방지
    if hook_input.get("stop_hook_active"):
        return
    # transcript 에는 최종 답이 늦게 기록될 수 있어 Stop 입력의 최종 답을 읽는다
    prose = strip_non_prose(hook_input["last_assistant_message"])
    hangul_count = len(HANGUL.findall(prose))
    letter_count = hangul_count + len(LATIN.findall(prose))
    if letter_count < MIN_LETTERS:
        return
    if hangul_count / letter_count >= MIN_HANGUL_SHARE:
        return
    reason = (
        "응답은 한국어로 (CLAUDE.md Communication). 같은 내용을 한국어로 다시 답할 것"
    )
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))


def strip_non_prose(text: str) -> str:
    for pattern in NON_PROSE:
        text = pattern.sub(" ", text)
    return text


if __name__ == "__main__":
    main()
