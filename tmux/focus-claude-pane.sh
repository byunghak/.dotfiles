#!/bin/sh
# 알림을 눌렀을 때 그 claude pane 이 있는 session·window·pane 으로 옮긴다 (terminal-notifier -execute 가 부른다)
# 호출: focus-claude-pane.sh <pane>  예) focus-claude-pane.sh %209
set -e
# 알림에서 실행되면 login shell PATH 가 없다
PATH=/opt/homebrew/bin:/usr/local/bin:$PATH

pane_id=$1
tmux switch-client -t "$pane_id"
tmux select-window -t "$pane_id"
tmux select-pane -t "$pane_id"
