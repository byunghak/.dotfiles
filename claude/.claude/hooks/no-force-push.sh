#!/bin/bash
# no-force-push Guard - PreToolUse Hook
# 모든 형태의 git force push 를 차단한다.
#
# Hook trigger: PreToolUse, matcher: Bash
# Exit codes: 0 = 허용, 2 = 차단
#
# 근거: 사용자 지시 (2026-09-21) — "force push 는 항상 금지".
#   force push 는 원격 이력을 덮어써 되돌릴 수 없다. 남의 커밋을 지우거나,
#   리뷰어가 본 diff 를 사라지게 하거나, CI 가 검증한 커밋을 무효화한다.
#
# 차단 대상 (git push 명령 안에서만 판정):
#   --force / -f / 번들 단축플래그(-fu 등)
#   --force-with-lease / --force-with-lease=... / --force-if-includes
#   refspec 앞 '+' (git push origin +main, +HEAD:main)
#
# 정책: 차단만 한다. 우회 경로를 제시하지 않는다 — 되돌리기가 목적이면
#   revert 커밋이 정답이고, 그건 force 없이 된다.

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | python3 -c '
import sys, json
try:
    print(json.load(sys.stdin).get("tool_input", {}).get("command", ""))
except Exception:
    pass
' 2>/dev/null)

if [[ -z "$COMMAND" ]]; then
	exit 0
fi

# git push 가 아예 없으면 빠르게 통과 (대부분의 Bash 호출)
if [[ "$COMMAND" != *push* ]]; then
	exit 0
fi

export _NFP_CMD="$COMMAND"
python3 <<'GUARD_SCRIPT'
import os
import re
import shlex
import sys

command = os.environ.get("_NFP_CMD", "")


def segments(cmd):
    """파이프·체이닝·개행으로 이어붙인 명령을 개별 조각으로 나눈다."""
    return re.split(r'\|\||&&|\||;|\n', cmd)


def force_reason(segment):
    """이 조각이 force push 면 사유 문자열, 아니면 None."""
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()

    # `git` 위치 찾기 (env 접두사나 절대경로가 앞에 붙어도 동작)
    idx = None
    for i, tok in enumerate(tokens):
        if tok == "git" or tok.endswith("/git"):
            idx = i
            break
    if idx is None:
        return None

    rest = tokens[idx + 1:]

    # push 서브커맨드인지 확인 (-C <dir> 등 git 전역 플래그 건너뛰기)
    sub = None
    for j, tok in enumerate(rest):
        if not tok.startswith("-"):
            sub = tok
            rest = rest[j + 1:]
            break
    if sub != "push":
        return None

    for tok in rest:
        if tok == "--force" or tok.startswith("--force-with-lease") \
                or tok.startswith("--force-if-includes"):
            return tok
        # 단축 플래그: -f, -fu 등 (단, --long 은 위에서 처리)
        if tok.startswith("-") and not tok.startswith("--") and "f" in tok:
            return tok
        # refspec 강제 형식: +main, +HEAD:main
        if tok.startswith("+") and len(tok) > 1:
            return tok

    return None


for segment in segments(command):
    reason = force_reason(segment)
    if reason is None:
        continue

    print(
        f"""[BLOCKED] git force push — '{reason}' 는 금지되어 있다.

근거: 사용자 지시 (2026-09-21) — force push 는 항상 금지.
원격 이력을 덮어쓰면 되돌릴 수 없다. 남의 커밋이 사라지고, 리뷰어가 본 diff 가
없어지고, CI 가 검증한 커밋이 무효화된다.

대신 할 것:
  - 커밋 내용을 바꾸고 싶다  → 새 커밋을 쌓는다 (amend 대신)
  - 잘못된 커밋을 되돌린다   → git revert <sha> (새 커밋으로 취소, force 불필요)
  - PR 을 정리하고 싶다      → 머지 시 squash 옵션을 쓴다

이미 push 한 커밋은 고치지 말고 그 위에 쌓을 것.""",
        file=sys.stderr,
    )
    sys.exit(2)

sys.exit(0)
GUARD_SCRIPT
