#!/usr/bin/env python3
"""Stop hook: 한국어로 답해야 하는데 영어로 끝낸 응답을 막는다 (CLAUDE.md Communication).

코드 블록·인라인 코드·URL·경로를 뺀 글자 중 한글 비율이 낮으면 block 한다.
"""

import json
import os
import re
import sys

MIN_LETTERS = 40
MIN_HANGUL_SHARE = 0.05
# transcript 끝에서 이만큼만 읽는다
TAIL_BYTES = 256 * 1024

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
    prose = strip_non_prose(final_assistant_text(hook_input["transcript_path"]))
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


def final_assistant_text(transcript_path: str) -> str:
    with open(transcript_path, "rb") as transcript:
        transcript.seek(0, os.SEEK_END)
        start = max(0, transcript.tell() - TAIL_BYTES)
        transcript.seek(start)
        raw_lines = transcript.read().decode("utf-8", errors="replace").splitlines()
    # 꼬리 첫 줄은 중간에서 잘렸을 수 있다
    if start > 0:
        raw_lines = raw_lines[1:]
    for line in reversed(raw_lines):
        if '"assistant"' not in line:
            continue
        entry = json.loads(line)
        if entry.get("type") != "assistant":
            continue
        content = entry.get("message", {}).get("content", [])
        texts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        if texts:
            return "\n".join(texts)
    return ""


def strip_non_prose(text: str) -> str:
    for pattern in NON_PROSE:
        text = pattern.sub(" ", text)
    return text


if __name__ == "__main__":
    main()
