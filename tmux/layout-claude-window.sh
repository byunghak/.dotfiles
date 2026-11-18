#!/bin/sh
# claude window 의 pane 을 배치한다
# 제목에 -orchestrator 가 든 pane 이 있으면 그 pane 을 왼쪽(main-pane-width)에 두고 나머지는 오른쪽에 한 줄로 쌓는다 (main-vertical)
# 오른쪽 맨 아래에는 셸 pane(@claude_shell) 하나를 두고, 없으면 만든다
# worker 는 1줄로 접어 제목줄 목록처럼 보이게 하고, focus 된 worker(또는 인자 2 의 peek 대상)만 펼친다
# 펼친 worker 가 없으면 셸이 남은 높이를 갖고, 있으면 셸은 shell_height 줄로 줄인다
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

shell_height=10

shell_pane=$(tmux list-panes -t "$window_id" -F '#{pane_id} #{@claude_shell}' | awk '$2 == 1 { print $1; exit }')
if [ -z "$shell_pane" ]; then
	shell_dir=$(tmux display-message -p -t "$orchestrator_pane" '#{pane_current_path}')
	shell_pane=$(tmux split-window -d -v -P -F '#{pane_id}' -t "$window_id.{bottom-right}" -c "$shell_dir")
	tmux set-option -pq -t "$shell_pane" @claude_shell 1
fi

# main-vertical 은 첫 번째 pane 을 왼쪽에 두므로 orchestrator 를 첫 자리로, 셸은 마지막 자리로 옮긴다
# swap-pane 은 focus 를 자리 기준으로 남기므로, 보던 pane 을 다시 고른다
active_pane=$(tmux display-message -p -t "$window_id" '#{pane_id}')
first_pane=$(tmux list-panes -t "$window_id" -F '#{pane_id}' | head -1)
if [ "$orchestrator_pane" != "$first_pane" ]; then
	tmux swap-pane -d -s "$orchestrator_pane" -t "$first_pane" \; select-pane -t "$active_pane"
fi
last_pane=$(tmux list-panes -t "$window_id" -F '#{pane_id}' | tail -1)
if [ "$shell_pane" != "$last_pane" ]; then
	tmux swap-pane -d -s "$shell_pane" -t "$last_pane" \; select-pane -t "$active_pane"
fi
tmux select-layout -t "$window_id" main-vertical

worker_panes=$(tmux list-panes -t "$window_id" -F '#{pane_id}' | grep -vx -e "$orchestrator_pane" -e "$shell_pane" || true)
expanded_pane=
if [ -n "$peek_pane" ]; then
	expanded_pane=$peek_pane
elif printf '%s\n' "$worker_panes" | grep -qx "$active_pane"; then
	expanded_pane=$active_pane
fi

# 접을 pane 을 먼저 1줄로 줄이고, 펼칠 pane 에 남은 높이를 몰아준다 (줄인 높이는 바로 옆 pane 으로만 가기 때문)
window_height=$(tmux display-message -p -t "$window_id" '#{window_height}')
for pane in $worker_panes; do
	if [ "$pane" != "$expanded_pane" ]; then
		tmux resize-pane -t "$pane" -y 1
	fi
done
if [ -z "$expanded_pane" ]; then
	tmux resize-pane -t "$shell_pane" -y "$window_height"
	exit 0
fi
tmux resize-pane -t "$expanded_pane" -y "$window_height"
tmux resize-pane -t "$shell_pane" -y "$shell_height"
