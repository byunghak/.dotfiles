#!/bin/sh
# claude pane 이 idle 이고 입력 칸이 비었는지 본다. 됐으면 exit 0, 아니면 이유를 한 줄 내고 exit 1
# 화면 전체를 읽지 않게 상태는 hook 이 적는 @claude_state 로, 입력 칸은 ❯ 줄 하나만 본다
# 호출: claude-pane-ready.sh <pane>
set -eu

pane_id=$1
state=$(tmux display-message -p -t "$pane_id" '#{@claude_state}')
if [ "$state" != idle ]; then
	echo "not ready: $pane_id state=${state:-none}"
	exit 1
fi
# 접힌 worker pane 은 capture-pane 에 1줄만 나오므로 peek 로 잠깐 펼쳐 읽는다
# 흐린 글씨(자동 제안)와 색 지시자·공백을 빼고 남는 글자가 있으면 사용자가 쓰던 글이다
typed=$("$(dirname "$0")/peek-claude-pane.sh" "$pane_id" -e | grep '❯' | tail -1 |
	perl -CSD -pe 's/\e\[2m.*?(\e\[(0|22)m|$)//g; s/\e\[[0-9;]*m//g; s/[\x{276f}\s\x{a0}]//g')
if [ -n "$typed" ]; then
	echo "not ready: $pane_id input box has text: $typed"
	exit 1
fi
