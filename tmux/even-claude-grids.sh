#!/bin/sh
# bind g 로 만든 window(@claude_grid 표시)를 모두 다시 배치한다 (layout-claude-window.sh).
# pane-exited hook 에서 호출: hook 시점엔 닫힌 pane 이 없어 어느 window 였는지 format 으로 알 수 없으므로 표시된 window 를 전부 편다.

tmux list-windows -a -F '#{?@claude_grid,#{window_id},}' | while read -r window_id; do
	[ -n "$window_id" ] && "$(dirname "$0")/layout-claude-window.sh" "$window_id"
done
exit 0
