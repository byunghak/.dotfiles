#!/bin/sh
# claude window 의 pane 을 배치한다
# 제목에 -orchestrator 가 든 pane 이 있으면 그 pane 을 왼쪽(main-pane-width)에 두고 나머지는 오른쪽에 한 줄로 쌓는다 (main-vertical)
# 오른쪽 worker 는 하나만 펼치고 나머지는 1줄로 접어 제목줄 목록처럼 보이게 한다
#   펼칠 worker: 인자 2 (peek-claude-pane.sh) > focus 된 worker > 마지막으로 focus 했던 worker(@claude_expanded) > 첫 worker
# orchestrator 가 없으면 같은 크기로 편다 (tiled)
# 호출: after-select-pane hook·peek-claude-pane.sh·bind R·bind x·claude-grid.sh·even-claude-grids.sh·tmux-pane-claude.sh hook
set -e

window_id=$1
peek_pane=${2:-}

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
# pane 구성과 window 크기가 지난 배치 그대로면 main-vertical 을 건너뛴다
# main-vertical 은 worker 를 모두 같은 높이로 폈다가 다시 접게 해 claude 가 pane 마다 2~3번 다시 그린다
layout_key="$(tmux list-panes -t "$window_id" -F '#{pane_id}' | tr '\n' ' ')$(tmux display-message -p -t "$window_id" '#{window_width}x#{window_height}')"
if [ "$layout_key" != "$(tmux show-options -wqv -t "$window_id" @claude_layout_key)" ]; then
	tmux select-layout -t "$window_id" main-vertical
	tmux set-option -wq -t "$window_id" @claude_layout_key "$layout_key"
fi

worker_panes=$(tmux list-panes -t "$window_id" -F '#{pane_id}' | grep -vx "$orchestrator_pane")
if [ "$(printf '%s\n' "$worker_panes" | wc -l)" -le 1 ]; then
	exit 0
fi

active_pane=$(tmux display-message -p -t "$window_id" '#{pane_id}')
saved_pane=$(tmux show-options -wqv -t "$window_id" @claude_expanded)
if [ -n "$peek_pane" ]; then
	expanded_pane=$peek_pane
elif [ "$active_pane" != "$orchestrator_pane" ]; then
	expanded_pane=$active_pane
	tmux set-option -wq -t "$window_id" @claude_expanded "$active_pane"
elif printf '%s\n' "$worker_panes" | grep -qx "$saved_pane"; then
	expanded_pane=$saved_pane
else
	expanded_pane=$(printf '%s\n' "$worker_panes" | head -1)
fi

# 접을 pane 을 먼저 1줄로 줄이고, 펼칠 pane 에 남은 높이를 몰아준다 (줄인 높이는 바로 옆 pane 으로만 가기 때문)
for pane in $worker_panes; do
	if [ "$pane" != "$expanded_pane" ]; then
		tmux resize-pane -t "$pane" -y 1
	fi
done
tmux resize-pane -t "$expanded_pane" -y "$(tmux display-message -p -t "$window_id" '#{window_height}')"
