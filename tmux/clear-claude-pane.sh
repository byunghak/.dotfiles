#!/bin/sh
# claude pane 이 idle·입력 칸이 비면 `/clear` 를 보내고, 새 세션에 이어갈 prompt 를 입력한다 (세션 이름은 /clear 뒤에도 남는다)
# 주제가 바뀌면 Claude 가 상태를 파일에 적고 이 스크립트를 background 로 띄운 뒤 턴을 끝낸다
# 호출: clear-claude-pane.sh <pane> <이어갈 prompt>
set -eu

pane_id=$1
next_prompt=$2

# /clear 는 불러온 skill 도 비우므로, orchestrator 세션이면 새 세션 첫 입력에서 orchestrator skill 을 다시 부른다
case "$(tmux display-message -p -t "$pane_id" '#{pane_title}')" in
	*-orchestrator*) next_prompt="/orchestrator $next_prompt" ;;
esac

wait_idle() {
	# 0.5초 간격, 최대 60초
	for _ in $(seq 120); do
		if [ "$(tmux display-message -p -t "$pane_id" '#{@claude_state}')" = idle ]; then
			return 0
		fi
		sleep 0.5
	done
	echo "clear-claude-pane: $pane_id did not become idle within 60s" >&2
	return 1
}

require_empty_input() {
	# 입력 칸(❯ 줄)에서 흐린 글씨(자동 제안)와 색 지시자·공백을 빼고 남는 글자가 있으면 사용자가 쓰던 글이다
	typed=$(tmux capture-pane -p -e -t "$pane_id" | grep '❯' | tail -1 |
		perl -CSD -pe 's/\e\[2m.*?(\e\[(0|22)m|$)//g; s/\e\[[0-9;]*m//g; s/[\x{276f}\s\x{a0}]//g')
	if [ -n "$typed" ]; then
		echo "clear-claude-pane: input box of $pane_id has text, not clearing: $typed" >&2
		return 1
	fi
}

send_prompt() {
	# clear 직후 화면이 다시 그려지는 동안 보낸 글은 사라질 수 있어, 턴이 시작(busy)될 때까지 확인하고 최대 3번 다시 보낸다
	for _ in 1 2 3; do
		# 입력 칸에 글이 남아 있으면 앞서 보낸 prompt 의 Enter 만 빠진 것이다
		if require_empty_input 2>/dev/null; then
			tmux send-keys -t "$pane_id" -l "$next_prompt"
		fi
		tmux send-keys -t "$pane_id" Enter
		for _ in $(seq 20); do
			sleep 0.5
			[ "$(tmux display-message -p -t "$pane_id" '#{@claude_state}')" != idle ] && return 0
		done
	done
	echo "clear-claude-pane: prompt did not start a turn in $pane_id after 3 tries" >&2
	return 1
}

wait_idle
require_empty_input
tmux send-keys -t "$pane_id" -l "/clear"
tmux send-keys -t "$pane_id" Enter
# 새 세션이 그려지고 SessionStart hook 이 상태를 적을 시간
sleep 3
wait_idle
require_empty_input
send_prompt
