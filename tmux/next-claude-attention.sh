#!/bin/sh
# 사람이 봐야 하는 다음 claude pane 으로 이동한다 (bind a)
# 결정 대기(@claude_state=waiting) pane 을 먼저, 그다음 턴이 끝났는데 안 본 window(@claude_done)의 claude pane 을 고른다
# 현재 pane 이 목록에 있으면 그 다음 것으로 넘어가서, 여러 번 누르면 차례로 돈다
# 상태 옵션은 claude/.claude/hooks/tmux-pane-claude.sh 가 적는다
set -e

client_tty=$1
current_pane=$2

# waiting pane 전부, done window 에서는 claude pane 하나씩
targets=$(tmux list-panes -a -F '#{pane_id} #{window_id} #{@claude_state} #{@claude_done}' | awk '
	$3 == "waiting" { waiting[++w] = $1 }
	$3 != "waiting" && $3 != "" && $4 == "1" && !($2 in seen) { seen[$2] = 1; done[++d] = $1 }
	END {
		for (i = 1; i <= w; i++) print waiting[i]
		for (i = 1; i <= d; i++) print done[i]
	}')

if [ -z "$targets" ]; then
	tmux display-message -c "$client_tty" "no claude pane waiting for decision or unseen"
	exit 0
fi

target=$(printf '%s\n' "$targets" | awk -v current="$current_pane" '
	NR == 1 { first = $1 }
	found && !picked { print $1; picked = 1 }
	$1 == current { found = 1 }
	END { if (!picked) print first }')

tmux switch-client -c "$client_tty" -t "$target" \; select-window -t "$target" \; select-pane -t "$target"
