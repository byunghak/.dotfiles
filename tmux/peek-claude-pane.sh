#!/bin/sh
# 접힌 worker pane 을 잠깐 펼쳐 화면을 읽고 다시 접는다 (접힌 pane 은 capture-pane 에 1줄만 나오기 때문)
# 호출: peek-claude-pane.sh <pane> [capture-pane 옵션...]  예) peek-claude-pane.sh %287 -e
set -e

pane_id=$1
shift
window_id=$(tmux display-message -p -t "$pane_id" '#{window_id}')
layout="$(dirname "$0")/layout-claude-window.sh"

"$layout" "$window_id" "$pane_id"
# claude 가 늘어난 높이로 다시 그릴 시간 (worker 다시 그리기는 0.2초 안팎)
sleep 0.5
tmux capture-pane -p "$@" -t "$pane_id"
"$layout" "$window_id"
