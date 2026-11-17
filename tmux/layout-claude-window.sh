#!/bin/sh
# claude window 의 pane 을 배치한다
# 제목에 -orchestrator 가 든 pane 이 있으면 그 pane 을 왼쪽(main-pane-width)에 두고 나머지는 오른쪽에 한 줄로 쌓는다 (main-vertical)
# orchestrator 가 없으면 같은 크기로 편다 (tiled)
# 호출: bind R·bind x·claude-grid.sh·even-claude-grids.sh·tmux-pane-claude.sh hook
set -e

window_id=$1

# zoom 중에 layout 을 바꾸면 zoom 이 풀린다
if [ "$(tmux display-message -p -t "$window_id" '#{window_zoomed_flag}')" = "1" ]; then
	exit 0
fi

orchestrator_pane=$(tmux list-panes -t "$window_id" -F '#{pane_id} #{pane_title}' | awk '/-orchestrator/ { print $1; exit }')
if [ -z "$orchestrator_pane" ]; then
	tmux select-layout -t "$window_id" tiled
	exit 0
fi

# main-vertical 은 첫 번째 pane 을 왼쪽에 두므로 orchestrator 를 첫 자리로 옮긴다
# swap-pane 은 focus 를 자리 기준으로 남기므로, 보던 pane 을 다시 고른다
first_pane=$(tmux list-panes -t "$window_id" -F '#{pane_id}' | head -1)
if [ "$orchestrator_pane" != "$first_pane" ]; then
	active_pane=$(tmux display-message -p -t "$window_id" '#{pane_id}')
	tmux swap-pane -d -s "$orchestrator_pane" -t "$first_pane" \; select-pane -t "$active_pane"
fi
tmux select-layout -t "$window_id" main-vertical
