#!/bin/bash
# pane 의 Claude 세션 context 크기를 `<N>k tokens · compaction <M> · session <id>` 한 줄로 낸다.
# 세션 ID 는 pane 옵션 @claude_session (tmux-pane-claude.sh 가 적음), transcript 는 ~/.claude/projects/*/<id>.jsonl 이다.
# context 크기는 마지막 assistant usage 의 input + cache_creation + cache_read (idle-compact.py 와 같은 계산).
# compaction 수는 transcript 의 compact_boundary 기록 수다.
set -euo pipefail

pane_id=${1:-}
[ -n "$pane_id" ] || {
	echo "usage: claude-pane-context.sh <pane>" >&2
	exit 1
}

session_id=$(tmux show-options -p -v -t "$pane_id" @claude_session 2>/dev/null || true)
[ -n "$session_id" ] || {
	echo "claude session id not recorded for pane $pane_id" >&2
	exit 1
}

transcript=$(compgen -G "$HOME/.claude/projects/*/$session_id.jsonl" | head -1 || true)
[ -n "$transcript" ] || {
	echo "transcript not found for pane $pane_id session $session_id" >&2
	exit 1
}

# usage 줄은 파일 끝쪽에 있으므로 뒤 8MB 만 본다
tokens=$(tail -c 8000000 "$transcript" | grep '"usage"' |
	jq -r 'select(.message.usage != null) | .message.usage | (.input_tokens // 0) + (.cache_creation_input_tokens // 0) + (.cache_read_input_tokens // 0) | select(. > 0)' 2>/dev/null | tail -1 || true)
[ -n "$tokens" ] || {
	echo "no usage record in transcript $transcript for pane $pane_id" >&2
	exit 1
}

compactions=$(grep -c '"subtype":"compact_boundary"' "$transcript" || true)

echo "$((tokens / 1000))k tokens · compaction $compactions · session $session_id"
