#!/usr/bin/env bash
# PostToolUse hook: docs/design/ 설계 문서를 저장하면 doc_lint 를 자동으로 돌린다
# 위반을 모델 컨텍스트로 돌려보내, 사람이 "lint 돌려줘" 라고 말할 필요를 없앤다

LINT="$HOME/.claude/skills/design-doc/scripts/doc_lint.py"

if [ ! -f "$LINT" ] || ! command -v python3 &>/dev/null || ! command -v jq &>/dev/null; then
	exit 0
fi

FILE_PATH=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty')

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
	exit 0
fi

# docs/design/ 아래 .md 만 대상. decision-log.md 는 doc_lint 가 자체 skip 한다
case "$FILE_PATH" in
*/docs/design/*.md) ;;
*) exit 0 ;;
esac

# exit 0 = 위반 없음. 조용히 통과시켜 정상 흐름을 방해하지 않는다
if OUTPUT=$(python3 "$LINT" "$FILE_PATH" 2>&1); then
	exit 0
fi

# 오래된 문서는 위반이 수십 건씩 쌓여 있다. 매 저장마다 전부 넣으면 컨텍스트를 먹으므로 자른다
MAX_LINES=60
if [ "$(printf '%s\n' "$OUTPUT" | wc -l)" -gt "$MAX_LINES" ]; then
	OUTPUT=$(printf '%s\n' "$OUTPUT" | head -n "$MAX_LINES")
	OUTPUT="$OUTPUT
… 생략됨. 전체는 python3 $LINT $FILE_PATH"
fi

jq -n --arg out "$OUTPUT" '{
  hookSpecificOutput: {
    hookEventName: "PostToolUse",
    additionalContext: ("doc_lint 위반 — 걸린 줄을 0 으로 만들 것. 오탐이면 그 줄을 사용자에게 보일 것:\n" + $out)
  }
}'
exit 0
