#!/bin/bash
# kubectl Secret Read Guard - PreToolUse Hook
# Secret 을 내용이 찍히는 출력 형식으로 조회하는 kubectl 명령을 차단한다.
#
# Hook trigger: PreToolUse, matcher: Bash
# Exit codes: 0 = 허용, 2 = 차단
#
# 근거 (업무 repo 2026-11-03): 운영 Secret 의 관리 주체를 보려고
#   `kubectl get secret -o jsonpath='{.metadata.annotations}'` 를 찍었더니
#   `kubectl apply` 로 만든 Secret 의 last-applied-configuration annotation 에 data 사본이 있어
#   PG 비밀번호가 대화에 노출됐다. "data 만 안 보면 된다" 는 판단이 틀렸으므로,
#   Secret 은 내용이 안 나오는 형식(기본 표·-o name·-o wide)과 describe 로만 본다.
#
# 범위: 모든 context (kind 포함) — 로컬 Secret 에도 실제 토큰을 넣는 경우가 있다.
# 정책: Secret 을 가리키는 get 에 -o 가 기본 표·name·wide 가 아니면 차단 (fail-closed).
#   `get --raw` 경로에 /secrets 가 있으면 차단.

INPUT=$(cat)

if ! command -v python3 &>/dev/null; then
	echo "BLOCKED: kubectl-secret-read-guard cannot inspect the command (python3 not found)" >&2
	exit 2
fi
if ! COMMAND=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
print(json.load(sys.stdin).get("tool_input", {}).get("command", ""))
' 2>/dev/null); then
	echo "BLOCKED: kubectl-secret-read-guard cannot parse the hook input JSON" >&2
	exit 2
fi

if [[ "$COMMAND" != *kubectl* ]]; then
	exit 0
fi

export _KSGUARD_CMD="$COMMAND"
export _HOOK_LIB="${0%/*}/lib"
python3 <<'GUARD_SCRIPT'
import os
import re
import shlex
import sys

sys.path.insert(0, os.environ.get("_HOOK_LIB", ""))
try:
    from shell_unwrap import nested_commands
except ImportError as error:
    print(f"BLOCKED: kubectl-secret-read-guard cannot load hooks/lib/shell_unwrap.py ({error})", file=sys.stderr)
    sys.exit(2)

command = os.environ.get("_KSGUARD_CMD", "")

# 내용(data·annotations)이 나오지 않는 출력 형식만 허용
SAFE_OUTPUTS = {"name", "wide"}
SECRET_RESOURCE = re.compile(r"^(secrets?|secret\.v1|secrets\.v1)(/.*)?$")


def segments(cmd):
    return re.split(r'\|\||&&|\||;|\n', cmd)


def tokens_after_kubectl(segment):
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()
    for i, tok in enumerate(tokens):
        if tok == "kubectl" or tok.endswith("/kubectl"):
            return tokens[i + 1:]
    return None


def output_format(rest):
    """-o / --output 값. 없으면 None (기본 표)."""
    for i, tok in enumerate(rest):
        for prefix in ("--output=", "-o="):
            if tok.startswith(prefix):
                return tok[len(prefix):]
        if tok in ("-o", "--output") and i + 1 < len(rest):
            return rest[i + 1]
        # -ojson, -ojsonpath=... 처럼 붙여 쓴 꼴
        if tok.startswith("-o") and not tok.startswith("--") and len(tok) > 2:
            return tok[2:]
    return None


def names_secret(rest):
    for tok in rest:
        if tok.startswith("-"):
            continue
        for part in tok.split(","):
            if SECRET_RESOURCE.match(part.lower()):
                return True
    return False


def raw_secret_path(rest):
    for i, tok in enumerate(rest):
        value = None
        if tok.startswith("--raw="):
            value = tok.split("=", 1)[1]
        elif tok == "--raw" and i + 1 < len(rest):
            value = rest[i + 1]
        if value and "/secrets" in value:
            return True
    return False


reason = None
# sh -c '…'·eval '…' 안쪽 명령도 같은 검사에 넣는다
for segment in (seg for text in nested_commands(command) for seg in segments(text)):
    rest = tokens_after_kubectl(segment)
    if rest is None or "get" not in rest:
        continue
    if raw_secret_path(rest):
        reason = "get --raw .../secrets"
        break
    if not names_secret(rest):
        continue
    fmt = output_format(rest)
    if fmt is None:
        continue
    if fmt.split("=", 1)[0] in SAFE_OUTPUTS:
        continue
    reason = f"get secret -o {fmt.split('=', 1)[0]}"
    break

if reason is None:
    sys.exit(0)

print(
    f"""[BLOCKED] kubectl {reason} — Secret 의 내용이 찍히는 조회는 금지되어 있다.

근거: 2026-11-03 annotations 를 찍었다가 last-applied-configuration 안의 PG 비밀번호가 노출됐다.
metadata(annotations)에도 data 사본이 들어 있을 수 있다.

대신 할 것:
  - 키 이름·크기       → kubectl describe secret <s>
  - 있는지·목록        → kubectl get secret [-o name]
  - 관리 주체          → 그 Secret 을 만드는 Helm 차트·ArgoCD Application 을 repo 에서 찾는다""",
    file=sys.stderr,
)
sys.exit(2)
GUARD_SCRIPT
