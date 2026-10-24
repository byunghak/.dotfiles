#!/bin/sh
# 현재 window 에 claude pane 을 하나 추가하고 전체를 같은 크기로 편다 (bind g).
# 4x4 를 넘기면 pane 이 너무 작아 쓸 수 없으므로 16개에서 멈춘다.
set -e

window_id=$1
dir=$2
max_panes=16

pane_count=$(tmux display-message -p -t "$window_id" '#{window_panes}')
if [ "$pane_count" -ge "$max_panes" ]; then
	tmux display-message "claude grid is full: $pane_count/$max_panes panes"
	exit 0
fi

# 분할 전에 먼저 펴야 활성 pane 이 작아도 "no space for new pane" 없이 나뉜다
tmux select-layout -t "$window_id" tiled
tmux split-window -t "$window_id" -c "$dir" 'claude'
tmux select-layout -t "$window_id" tiled

# pane 이 닫힐 때도 다시 펴도록 .tmux.conf 의 hook 이 이 표시를 본다
tmux set-option -w -t "$window_id" @claude_grid 1
