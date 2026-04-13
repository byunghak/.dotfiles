#!/bin/bash
# PostToolUse hook: Hugo 프로젝트에서 content/** 수정 시 빌드 검증

FILE_PATH=$(jq -r '.tool_input.file_path // empty')
[ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ] && exit 0

# content/ 하위 파일인지 확인
case "$FILE_PATH" in
*/content/*) ;;
*)
	exit 0
	;;
esac

# Hugo 프로젝트인지 확인 (hugo.toml 또는 config.toml 존재)
PROJECT_DIR="$FILE_PATH"
while [ "$PROJECT_DIR" != "/" ]; do
	PROJECT_DIR=$(dirname "$PROJECT_DIR")
	if [ -f "$PROJECT_DIR/hugo.toml" ] || [ -f "$PROJECT_DIR/config.toml" ] || [ -f "$PROJECT_DIR/config.yaml" ]; then
		# Hugo 빌드 검증
		OUTPUT=$(cd "$PROJECT_DIR" && hugo --quiet 2>&1)
		EXIT_CODE=$?
		if [ $EXIT_CODE -ne 0 ]; then
			echo "⚠️ Hugo build failed after editing $FILE_PATH"
			echo "$OUTPUT" | tail -10
		fi
		exit 0
	fi
done
