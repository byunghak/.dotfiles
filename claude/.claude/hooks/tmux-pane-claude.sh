#!/usr/bin/env bash
# Claude Code hook: tmux pane 옵션에 세션 ID 와 상태를 적는다
# - @claude_session: tmux bind C-r(restart-claude-pane.sh)이 같은 세션을 다시 열 때 쓴다
# - @claude_state: .tmux.conf 의 pane-border-format·pane-border-style 이 라벨과 테두리 색을 고를 때 쓴다 (busy | waiting | idle)
# - @claude_activity: busy 일 때 제목줄에 보일 활동 이름. 막 호출한 도구로 추정하므로 다음 도구 호출에서 바뀐다
# - @claude_agent_<id> / @claude_agents_running: 실행 중인 subagent. 제목줄에 (agent N) 으로 붙는다
#   subagent 의 도구 이벤트(agent_id 있음)는 main 의 상태를 바꾸지 않는다. main 이 입력 대기인데 작업 중으로 보이지 않게
# - @claude_orchestrator: 제목에 -orchestrator 가 보인 적 있는 pane 이면 1. claude 가 다시 시작하며 제목을 잠깐 바꿔도 layout-claude-window.sh 가 orchestrator 를 찾게 한다
# - @claude_done (window 옵션): 보고 있지 않은 window 에서 턴이 끝났다는 표시. status bar 탭에 ✅ 로 붙고,
#   그 window 로 들어가면 .tmux.conf 의 session-window-changed hook 이 지운다
# 여러 이벤트에 같은 스크립트를 걸고 hook_event_name 으로 나눠, 상태 규칙을 한곳에 둔다
# 일부 이벤트의 stdout 은 모델 컨텍스트로 들어가므로 아무것도 출력하지 않는다
# 알려진 공백: 권한 거부·Esc 중단 뒤에는 실행되는 hook 이 없어 다음 이벤트까지 이전 상태가 남는다
# 모든 도구 호출마다 두 번씩 돌므로, 현재 값은 tmux 한 번으로 읽고 바뀐 값만 tmux 한 번에 묶어 쓴다

if [ -z "$TMUX_PANE" ] || ! command -v jq &>/dev/null; then
	exit 0
fi

# TOOL_COMMAND 를 마지막에 둔다: @tsv 가 명령 안의 tab·줄바꿈을 escape 하므로 필드가 밀리지 않는다
IFS=$'\t' read -r EVENT SESSION_ID AGENT_ID TOOL_NAME NOTIFICATION_TYPE TOOL_COMMAND < <(
	jq -r '[.hook_event_name, (.session_id // "-"), (.agent_id // "-"), (.tool_name // "-"), (.notification_type // "-"), (.tool_input.command // "-")] | @tsv'
)

# 구분자는 공백류가 아닌 \x1f: tab 은 IFS 공백으로 취급돼 연속된 빈 값이 한 칸으로 합쳐진다
# agent_id 가 없으면 존재하지 않는 옵션 이름을 읽어 빈 값이 되게 한다
SEP=$'\x1f'
# WINDOW_SEEN: 이 pane 의 window 가 attach 된 session 의 현재 window 면 1
IFS=$SEP read -r CUR_STATE CUR_SESSION CUR_ACTIVITY CUR_BEFORE_WAIT CUR_BORDER CUR_AGENT CUR_DONE WINDOW_SEEN CUR_ORCHESTRATOR TITLE_ORCHESTRATOR < <(
	tmux display-message -p -t "$TMUX_PANE" \
		"#{@claude_state}${SEP}#{@claude_session}${SEP}#{@claude_activity}${SEP}#{@claude_state_before_wait}${SEP}#{pane-border-status}${SEP}#{@claude_agent_${AGENT_ID//-/_}}${SEP}#{@claude_done}${SEP}#{&&:#{window_active},#{session_attached}}${SEP}#{@claude_orchestrator}${SEP}#{m:*-orchestrator*,#{pane_title}}" 2>/dev/null
)

TMUX_COMMANDS=()

# 쓸 tmux 명령을 모아 두었다가 flush_tmux 에서 한 번에 실행한다
queue_tmux() {
	if [ ${#TMUX_COMMANDS[@]} -gt 0 ]; then
		TMUX_COMMANDS+=(";")
	fi
	TMUX_COMMANDS+=("$@")
}

# 값이 바뀔 때만 쓴다. 빈 값이면 옵션을 지운다
queue_pane_option() {
	local option_name=$1 new_value=$2 current_value=$3
	if [ "$new_value" = "$current_value" ]; then
		return
	fi
	if [ -z "$new_value" ]; then
		queue_tmux set-option -p -u -t "$TMUX_PANE" "$option_name"
	else
		queue_tmux set-option -p -t "$TMUX_PANE" "$option_name" "$new_value"
	fi
}

# window 옵션이라 같은 window 의 다른 claude pane 이 켠 표시도 함께 바뀐다
queue_window_done() {
	local new_value=$1
	if [ "$new_value" = "$CUR_DONE" ]; then
		return
	fi
	if [ -z "$new_value" ]; then
		queue_tmux set-option -w -u -t "$TMUX_PANE" @claude_done
	else
		queue_tmux set-option -w -t "$TMUX_PANE" @claude_done "$new_value"
	fi
}

flush_tmux() {
	if [ ${#TMUX_COMMANDS[@]} -gt 0 ]; then
		tmux "${TMUX_COMMANDS[@]}" >/dev/null 2>&1
	fi
}

# agent 마다 옵션 하나를 두어, 병렬 agent 의 hook 이 동시에 목록을 고쳐도 서로 덮어쓰지 않게 한다
# 이미 등록된 agent 의 도구 이벤트는 아무것도 쓰지 않는다 (subagent 도구 호출마다 오므로)
track_agent() {
	local agent_option="@claude_agent_${AGENT_ID//-/_}"
	if [ "$1" = "start" ] && [ -n "$CUR_AGENT" ]; then
		return
	fi
	if [ "$1" = "stop" ] && [ -z "$CUR_AGENT" ]; then
		return
	fi
	if [ "$1" = "start" ]; then
		tmux set-option -p -t "$TMUX_PANE" "$agent_option" 1 >/dev/null 2>&1
	else
		tmux set-option -p -u -t "$TMUX_PANE" "$agent_option" >/dev/null 2>&1
	fi
	local agent_count
	agent_count=$(tmux show-options -p -t "$TMUX_PANE" 2>/dev/null | grep -c '^@claude_agent_')
	queue_tmux set-option -p -t "$TMUX_PANE" @claude_agents_running "$agent_count"
}

# 새 claude pane 이 window 에 들어오면 pane 을 다시 배치한다 (tmux bind R 과 같은 layout-claude-window.sh)
# nvim·shell 과 섞인 window 의 배치는 깨지 않도록 bind g 로 만든 window 또는 pane 이 전부 claude 인 window 만
tile_claude_window() {
	local window_id non_claude_panes
	window_id=$(tmux display-message -p -t "$TMUX_PANE" '#{window_id}' 2>/dev/null)
	non_claude_panes=$(tmux list-panes -t "$window_id" -F '#{pane_current_command}' 2>/dev/null | grep -vc '^claude$')
	if [ "$(tmux show-options -w -v -t "$window_id" @claude_grid 2>/dev/null)" != "1" ] && [ "$non_claude_panes" -ne 0 ]; then
		return
	fi
	~/.dotfiles/tmux/layout-claude-window.sh "$window_id" >/dev/null 2>&1
	# 이후 pane 이 닫힐 때도 .tmux.conf 의 pane-exited hook 이 다시 펴도록 표시한다
	tmux set-option -w -t "$window_id" @claude_grid 1 >/dev/null 2>&1
}

clear_agents() {
	tmux show-options -p -t "$TMUX_PANE" 2>/dev/null | awk '/^@claude_agent_/ { print $1 }' | while read -r agent_option; do
		tmux set-option -p -u -t "$TMUX_PANE" "$agent_option" >/dev/null 2>&1
	done
	queue_tmux set-option -p -u -t "$TMUX_PANE" @claude_agents_running
}

# Bash 명령의 명령 위치(맨 앞, ; & | ( 뒤, 줄바꿈 뒤)에 $1 이 오는지 본다
# 앞에 붙는 환경변수 대입(KUBECONFIG=…)·rtk 는 건너뛴다. @tsv 가 줄바꿈을 글자 \n 으로 바꾸므로 그것도 경계로 본다
# grep 프로세스를 띄우지 않도록 bash 정규식으로 맞춘다
runs_command() {
	local command_start='(^|[;&|(]|\\n)[[:space:]]*([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+|rtk[[:space:]]+)*'
	[[ $TOOL_COMMAND =~ ${command_start}($1) ]]
}

# 도구 이름·Bash 명령으로 활동을 추정한다. 규칙에 없으면 빈 값 → 제목줄은 "작업 중"
# 배포·테스트 명령 목록은 환경마다 다르므로 여기서 고친다. 위에서부터 먼저 맞는 규칙이 이긴다
classify_activity() {
	case "$TOOL_NAME" in
	Edit | Write | NotebookEdit) echo "코드 작업" ;;
	Read | Grep | Glob | WebFetch | WebSearch) echo "분석" ;;
	Agent) echo "위임" ;;
	Bash)
		# 배포·push 는 명령 위치에 있는 단어만 본다. 문자열 어디든 보면 local/helm 경로·argocd-ui 브랜치 이름에도 걸린다
		if runs_command 'kubectl[^;&|]*[[:space:]](apply|delete|rollout|scale|patch|edit|replace|create|set[[:space:]]+image)([[:space:]]|$)|helm[^;&|]*[[:space:]](install|upgrade|rollback|uninstall)([[:space:]]|$)|argocd[[:space:]]+app[[:space:]]+(sync|rollback)|terraform[^;&|]*[[:space:]]apply|gh[[:space:]]+workflow[[:space:]]+run'; then
			echo "배포"
			return
		fi
		# 브랜치 정리(push --delete)·PR 용 push 도 있으므로 배포와 나눈다
		if runs_command 'git([[:space:]]+-C[[:space:]]+[^[:space:]]+)?[[:space:]]+push'; then
			echo "push"
			return
		fi
		case "$TOOL_COMMAND" in
		*"go test"* | *"cargo test"* | *"cargo build"* | *pytest* | *"npm test"* | *"npm run build"* | *make*) echo "테스트·빌드" ;;
		*bq* | *psql* | *grep* | "rg "* | *" rg "* | *"git log"* | *"git diff"*) echo "분석" ;;
		esac
		;;
	esac
}

# subagent 이벤트: agent 수만 고치고 main 상태는 그대로 둔다
# SubagentStart 없이 도구 이벤트가 먼저 와도(teammate 등) 세도록 도구 이벤트에서도 등록한다
if [ "$AGENT_ID" != "-" ]; then
	case "$EVENT" in
	SubagentStop) track_agent stop ;;
	SubagentStart | PreToolUse) track_agent start ;;
	PostToolUse | PostToolUseFailure)
		track_agent start
		# subagent 의 권한 요청이 승인됐으면 결정 대기 직전 상태(main 의 상태)로 되돌린다
		if [ -n "$CUR_BEFORE_WAIT" ]; then
			queue_pane_option @claude_state "$CUR_BEFORE_WAIT" "$CUR_STATE"
			queue_pane_option @claude_state_before_wait "" "$CUR_BEFORE_WAIT"
		fi
		;;
	PermissionRequest)
		if [ "$CUR_STATE" != "waiting" ]; then
			queue_pane_option @claude_state_before_wait "$CUR_STATE" "$CUR_BEFORE_WAIT"
		fi
		queue_pane_option @claude_state waiting "$CUR_STATE"
		;;
	esac
	flush_tmux
	exit 0
fi

# 한 번 orchestrator 로 보인 pane 은 표시를 남긴다 (pane 이 닫히면 옵션도 사라진다)
if [ "$TITLE_ORCHESTRATOR" = "1" ]; then
	queue_pane_option @claude_orchestrator 1 "$CUR_ORCHESTRATOR"
fi

ACTIVITY=$CUR_ACTIVITY

# 결정 대기로 막 바뀐 orchestrator·단독 세션을 사용자가 보고 있지 않으면 macOS 알림을 띄운다
# worker·design 의 대기는 orchestrator 가 보므로 알리지 않는다. 알림이 hook 을 늦추지 않게 background 로
notify_waiting() {
	local title focused_pane
	title=$(tmux display-message -p -t "$TMUX_PANE" '#{pane_title}' 2>/dev/null)
	title=${title#✳ }
	case "$title" in
	*-worker-* | *-design*) return ;;
	esac
	# focus-events 로 tmux 가 터미널 focus 를 안다. focus 된 client 가 이 pane 을 보고 있으면 이미 보는 중
	focused_pane=$(tmux list-clients -F '#{?#{m:*focused*,#{client_flags}},#{pane_id},}' 2>/dev/null | grep -m1 .)
	if [ "$focused_pane" = "$TMUX_PANE" ]; then
		return
	fi
	# terminal-notifier 가 있으면 알림을 눌렀을 때 Ghostty 를 앞으로 가져오고 이 pane 으로 옮긴다
	if command -v terminal-notifier >/dev/null 2>&1; then
		terminal-notifier -title "✋ ${title}" -message "결정 대기" -group "claude-waiting-${TMUX_PANE}" \
			-activate com.mitchellh.ghostty \
			-execute "$HOME/.dotfiles/tmux/focus-claude-pane.sh ${TMUX_PANE}" >/dev/null 2>&1 &
		return
	fi
	osascript -e 'on run argv' -e 'display notification (item 1 of argv) with title (item 2 of argv)' -e 'end run' \
		"결정 대기" "✋ ${title}" >/dev/null 2>&1 &
}

case "$EVENT" in
SessionStart)
	# resume·clear 로 다시 시작하면 이전 프로세스의 agent 는 이미 없다
	clear_agents
	tile_claude_window
	queue_window_done ""
	STATE=idle
	;;
SessionEnd)
	queue_pane_option @claude_state "" "$CUR_STATE"
	clear_agents
	queue_window_done ""
	flush_tmux
	exit 0
	;;
UserPromptSubmit)
	# 새 턴은 아직 도구를 고르지 않았으므로 이전 턴의 활동을 지운다
	ACTIVITY=""
	queue_window_done ""
	STATE=busy
	;;
PostToolUse | PostToolUseFailure)
	STATE=busy
	;;
PreToolUse)
	if [ "$TOOL_NAME" = "AskUserQuestion" ]; then
		STATE=waiting
	# 병렬 subagent 의 도구 호출이 main 의 권한 대기 표시를 덮지 않게 한다. 해제는 PostToolUse 가 한다
	elif [ "$CUR_STATE" = "waiting" ]; then
		exit 0
	else
		STATE=busy
		ACTIVITY=$(classify_activity)
	fi
	;;
PermissionRequest)
	STATE=waiting
	;;
Stop)
	# 사용자가 보고 있는 window 면 끝난 걸 이미 봤으므로 표시하지 않는다
	if [ "$WINDOW_SEEN" != "1" ]; then
		queue_window_done 1
	fi
	STATE=idle
	;;
Notification)
	case "$NOTIFICATION_TYPE" in
	idle_prompt) STATE=idle ;;
	permission_prompt | elicitation_dialog | elicitation_url_dialog) STATE=waiting ;;
	*) exit 0 ;;
	esac
	;;
*)
	exit 0
	;;
esac

queue_pane_option @claude_activity "$ACTIVITY" "$CUR_ACTIVITY"
queue_pane_option @claude_state "$STATE" "$CUR_STATE"
queue_pane_option @claude_state_before_wait "" "$CUR_BEFORE_WAIT"
# 모든 hook 입력에 session_id 가 있으므로 매번 본다. SessionStart 에서만 적으면 hook 추가 전에 시작한 세션은 bind C-r 을 못 쓴다
if [ "$SESSION_ID" != "-" ]; then
	queue_pane_option @claude_session "$SESSION_ID" "$CUR_SESSION"
fi
# claude 가 도는 window 에만 제목줄을 켜서 다른 window 는 높이 1줄을 잃지 않게 한다
# SessionStart 에서만 켜면 hook 추가 전에 시작한 세션·window 를 옮긴 pane 은 계속 꺼져 있으므로 꺼져 있으면 켠다
if [ "$CUR_BORDER" != "top" ]; then
	queue_tmux set-option -w -t "$TMUX_PANE" pane-border-status top
fi
flush_tmux
if [ "$STATE" = "waiting" ] && [ "$CUR_STATE" != "waiting" ]; then
	notify_waiting
fi
exit 0
