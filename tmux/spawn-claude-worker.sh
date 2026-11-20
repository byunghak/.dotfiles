#!/bin/sh
# 세션 묶음 worker 를 orchestrator 의 tmux window 에 새 pane 으로 띄우고 window 를 다시 배치한다. 새 pane ID 를 출력한다
# worker 가 있으면 가장 높은 worker pane 을 위아래로 나눈다 (접힌 worker 는 1줄이라 tmux 가 나누지 못한다). 없으면 orchestrator pane 을 좌우로 나눈다
# -d 로 커서를 지금 pane 에 둔다. 빼면 새 worker 로 옮겨 가 사용자가 보던 화면이 바뀐다
# 호출 (orchestrator pane 에서): spawn-claude-worker.sh <세션 이름> <task prompt>
set -eu

worker_name=$1
task_prompt=$2
case "$worker_name" in
*[!a-z0-9-]*)
	echo "spawn-claude-worker: session name allows only a-z, 0-9, - (got: $worker_name)" >&2
	exit 1
	;;
*-worker-*) ;;
*)
	echo "spawn-claude-worker: session name must contain -worker- (got: $worker_name)" >&2
	exit 1
	;;
esac

orchestrator_pane=$TMUX_PANE
window_id=$(tmux display-message -p -t "$orchestrator_pane" '#{window_id}')
start_dir=$(tmux display-message -p -t "$orchestrator_pane" '#{pane_current_path}')

# 새 pane 의 셸 명령에 작은따옴표로 넣을 수 있게 prompt 안의 작은따옴표를 닫고-이스케이프-다시 여는 꼴로 바꾼다
first_prompt="Skill 도구로 session-worker skill 을 불러 따른다. 이 세션은 $worker_name. $task_prompt"
quoted_prompt=$(printf '%s' "$first_prompt" | sed "s/'/'\\\\''/g")

tallest_worker_pane=$(tmux list-panes -t "$window_id" -F '#{pane_height} #{pane_id}' |
	grep -v " $orchestrator_pane\$" | sort -n | tail -1 | cut -d' ' -f2)
if [ -n "$tallest_worker_pane" ]; then
	split_target=$tallest_worker_pane
	split_direction=-v
else
	split_target=$orchestrator_pane
	split_direction=-h
fi

tmux split-window -d "$split_direction" -t "$split_target" -c "$start_dir" -P -F '#{pane_id}' \
	"claude -n $worker_name '$quoted_prompt'"
"$(dirname "$0")/layout-claude-window.sh" "$window_id"
