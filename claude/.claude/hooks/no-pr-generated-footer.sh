#!/bin/bash
# no-pr-generated-footer Guard - PreToolUse Hook
# PR 본문에 생성 도구 표기(`Generated with ...`)가 들어가는 것을 차단한다.
#
# Hook trigger: PreToolUse, matcher: Bash
# Exit codes: 0 = 허용, 2 = 차단
#
# 근거: 사용자 지시 — PR 본문에 생성 도구 표기 금지 (CLAUDE.md Git Workflow).
#   attribution reminder 가 매 세션 그 줄을 넣으라고 하고, 문서 규칙만으로는 3번 재발했다.
#   커밋의 Co-Authored-By 는 대상이 아니다 (git commit 은 검사하지 않는다).
#
# 검사 대상: gh pr create / gh pr edit / gh api ...pulls...
#   명령 문자열 자체(--body, heredoc) + --body-file / -F 로 넘긴 파일 내용

INPUT=$(cat)

# 파싱 실패·python3 없음은 막는다 (fail-closed): 검사하지 못한 명령을 통과시키지 않는다
if ! command -v python3 &>/dev/null; then
	echo "BLOCKED: no-pr-generated-footer cannot inspect the command (python3 not found)" >&2
	exit 2
fi
if ! COMMAND=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
print(json.load(sys.stdin).get("tool_input", {}).get("command", ""))
' 2>/dev/null); then
	echo "BLOCKED: no-pr-generated-footer cannot parse the hook input JSON" >&2
	exit 2
fi

# gh 가 없으면 빠르게 통과 (대부분의 Bash 호출)
if [[ -z "$COMMAND" || "$COMMAND" != *gh* ]]; then
	exit 0
fi

export _NPG_CMD="$COMMAND"
python3 <<'GUARD_SCRIPT'
from __future__ import annotations

import os
import re
import shlex
import sys

command = os.environ.get("_NPG_CMD", "")
MARKER = re.compile(r"Generated with", re.IGNORECASE)


def targets_pr_body(cmd: str) -> bool:
    if re.search(r"\bgh\s+pr\s+(create|edit)\b", cmd):
        return True
    return bool(re.search(r"\bgh\s+api\b", cmd)) and "pulls" in cmd


def body_files(cmd: str) -> list[str]:
    """--body-file / -F 로 넘긴 파일 경로. `-F body=@file` 형태도 포함."""
    try:
        tokens = shlex.split(cmd, comments=False)
    except ValueError:
        tokens = cmd.split()
    paths: list[str] = []
    for i, tok in enumerate(tokens):
        if tok.startswith("--body-file="):
            paths.append(tok.split("=", 1)[1])
        elif tok in ("--body-file", "-F", "--field") and i + 1 < len(tokens):
            value = tokens[i + 1]
            if value.startswith("body=@"):
                paths.append(value[len("body=@"):])
            elif tok == "--body-file":
                paths.append(value)
    return paths


def file_has_marker(path: str) -> bool:
    if path == "-":
        return False
    try:
        with open(os.path.expanduser(path), encoding="utf-8", errors="replace") as f:
            return bool(MARKER.search(f.read()))
    except OSError:
        return False


if not targets_pr_body(command):
    sys.exit(0)

hit = None
if MARKER.search(command):
    hit = "명령 본문"
else:
    for path in body_files(command):
        if file_has_marker(path):
            hit = path
            break

if hit is None:
    sys.exit(0)

print(
    f"""[BLOCKED] PR 본문에 'Generated with' 줄이 있다 ({hit}).

근거: 사용자 지시 — PR 본문에 생성 도구 표기를 넣지 않는다 (attribution reminder 보다 우선).
본문에서 그 줄을 지우고 다시 실행할 것. 커밋의 Co-Authored-By 는 유지한다.""",
    file=sys.stderr,
)
sys.exit(2)
GUARD_SCRIPT
