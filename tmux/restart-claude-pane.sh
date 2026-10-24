#!/bin/sh
# 현재 pane 의 claude 만 종료하고 같은 세션으로 다시 연다 (bind C-r).
# 세션 ID 는 SessionStart hook(claude/.claude/hooks/tmux-pane-claude.sh)이 pane 옵션 @claude_session 에 적어 둔다.
# claude -c 를 쓰지 않는 이유: 같은 디렉토리에 claude pane 이 여럿이면 다른 pane 의 세션이 열린다.
set -e

pane_id=$1

session_id=$(tmux show-options -p -v -t "$pane_id" @claude_session 2>/dev/null || true)
if [ -z "$session_id" ]; then
	tmux display-message "claude session id not recorded for pane $pane_id"
	exit 0
fi

# 세션은 프로젝트 디렉토리별로 저장되므로 claude 가 돌던 cwd 에서 resume 해야 찾는다
dir=$(tmux display-message -p -t "$pane_id" '#{pane_current_path}')
tmux respawn-pane -k -t "$pane_id" -c "$dir" "claude --resume $session_id"
