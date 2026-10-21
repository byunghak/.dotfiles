#!/usr/bin/env bash
# 세션 jsonl 에서 학습 재료(사용자 메시지·답변·도구 호출·도구 결과)만 추려 출력한다.
# thinking·attachment·hook 메타는 버린다 — 결론이 아니라 과정의 잡음이라서.
#
# 사용: transcript.sh <session-id | jsonl 경로> [project-dir]
#   project-dir 생략 시 현재 디렉토리를 Claude Code 프로젝트 키로 변환해 찾는다.
set -euo pipefail

target="${1:?usage: transcript.sh <session-id|path.jsonl> [project-dir]}"
project_dir="${2:-$PWD}"

if [[ -f "$target" ]]; then
  file="$target"
else
  # Claude Code 는 cwd 의 영숫자 외 문자를 '-' 로 바꿔 디렉토리 키로 쓴다
  key=$(printf '%s' "$project_dir" | sed 's/[^A-Za-z0-9]/-/g')
  file="$HOME/.claude/projects/$key/$target.jsonl"
fi

[[ -f "$file" ]] || { echo "session transcript not found: $file" >&2; exit 1; }

# 도구 결과는 길어서 앞부분만 남긴다. 쿼리·로그의 핵심 수치는 대개 앞에 있다
jq -r '
  select(.type=="user" or .type=="assistant") | select(.isMeta|not)
  | .type as $role
  | (.message.content | if type=="string" then [{type:"text",text:.}] else . end)[]
  | if .type=="text" then "[\($role)] \(.text)"
    elif .type=="tool_use" then "[tool_use] \(.name): \(.input|tostring|.[0:400])"
    elif .type=="tool_result" then
      "[tool_result] \(.content|if type=="array" then map(.text? // "")|join("\n") else tostring end|.[0:1500])"
    else empty end
' "$file"
