#!/bin/bash
# Claude Code statusline: 왼쪽에 모델·Context·5시간·주간 사용량(%), 오른쪽 끝에 프로젝트·git 브랜치
# orchestrator 세션이면 같은 tmux window 의 worker 마다 진척 한 줄 (orchestrator 가 pane 옵션 @claude_progress 에 적은 값)

DIM=$'\033[2m'
RESET=$'\033[0m'
CYAN=$'\033[36m'
MAGENTA=$'\033[35m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
RED=$'\033[31m'

IFS=$'\t' read -r model cwd context_percent five_hour_percent five_hour_resets_at weekly_percent weekly_resets_at < <(
	jq -r '[
		.model.display_name // "?",
		.workspace.current_dir // .cwd // "",
		(.context_window.used_percentage // "" | tostring),
		(.rate_limits.five_hour.used_percentage // "" | tostring),
		(.rate_limits.five_hour.resets_at // "" | tostring),
		(.rate_limits.seven_day.used_percentage // "" | tostring),
		(.rate_limits.seven_day.resets_at // "" | tostring)
	] | @tsv'
)

main() {
	print_model_line
	print_progress_lines
}

print_model_line() {
	local left right branch
	left="${CYAN}[${model}]${RESET} $(usage_summary)"
	right="${cwd##*/}"
	branch=$(git -C "$cwd" branch --show-current 2>/dev/null)
	if [ -n "$branch" ]; then
		# untracked 는 보지 않는다 (큰 저장소에서 메시지마다 도는 비용)
		if [ -n "$(git -C "$cwd" --no-optional-locks status --porcelain -uno 2>/dev/null | head -1)" ]; then
			branch="${branch}*"
		fi
		right="${right} ${MAGENTA}git:(${branch})${RESET}"
	fi
	echo "${left}$(padding "$left" "$right")${right}"
}

# 오른쪽 글을 줄 끝에 붙이는 공백. 폭은 Claude Code 가 넘기는 COLUMNS, 색 코드는 폭에서 뺀다
padding() {
	local visible_left visible_right width
	visible_left=$(printf '%s' "$1" | sed $'s/\033\[[0-9;]*m//g')
	visible_right=$(printf '%s' "$2" | sed $'s/\033\[[0-9;]*m//g')
	# Claude Code 가 statusline 앞뒤에 두는 여백만큼 덜 채운다
	width=$((${COLUMNS:-80} - ${#visible_left} - ${#visible_right} - 4))
	[ "$width" -lt 1 ] && width=1
	printf '%*s' "$width" ""
}

# "▓▓▓▓▓▓░░░░ 3/5 5027-kafka-spread — #5027 Kafka 노드 쏠림 · 머지 결정 대기", 이름은 tmux 제목줄과 같은 상태 색
print_progress_lines() {
	[ -n "$TMUX_PANE" ] || return 0
	local own_title group
	own_title=$(tmux display-message -p -t "$TMUX_PANE" '#{pane_title}' 2>/dev/null)
	case "$own_title" in
	*-orchestrator*) ;;
	*) return 0 ;;
	esac
	group=${own_title#✳ }
	group=${group%%-orchestrator*}
	tmux list-panes -t "$TMUX_PANE" -F '#{pane_id}	#{@claude_state}	#{@claude_agents_running}	#{pane_title}	#{@claude_progress}	#{@claude_activity}' |
		awk -F '\t' -v own="$TMUX_PANE" -v group="$group" '
			$1 == own { next }
			{
				name = $4
				sub(/^✳ /, "", name)
				sub("^" group "-worker-", "", name)
				sub("^" group "-", "", name)
				# tmux 조건식처럼 agent 수 0 은 없는 것으로 본다
				has_agents = ($3 != "" && $3 != "0")
				if ($2 == "waiting") color = "\033[1;31m"
				else if ($2 == "busy" || ($2 == "idle" && has_agents)) color = "\033[32m"
				else if ($2 == "idle") color = "\033[1;33m"
				else color = "\033[2m"
				# 진척 "3/5 설명" 에서 수를 떼어 10칸 막대로
				progress = $5
				fraction = "?/?"
				detail = progress
				if (match(progress, /^[0-9?]+\/[0-9?]+/)) {
					fraction = substr(progress, 1, RLENGTH)
					detail = substr(progress, RLENGTH + 2)
				}
				split(fraction, parts, "/")
				filled = (parts[2] > 0 && parts[1] ~ /^[0-9]+$/) ? int(parts[1] * 10 / parts[2] + 0.5) : 0
				if (filled > 10) filled = 10
				bar = ""
				for (i = 0; i < 10; i++) bar = bar (i < filled ? "▓" : "░")
				line = "\033[34m" bar "\033[0m " fraction " " color name "\033[0m"
				if (has_agents) line = line " \033[36m⚙" $3 "\033[0m"
				# 진척을 아직 못 받은 worker 는 hook 이 적는 활동 이름(분석·코드 작업 등)이라도 붙인다
				if (detail == "" && $6 != "") detail = "\033[2m" $6 "\033[0m"
				if (detail != "") line = line " — " detail
				print line
			}
		'
}

# "Context 16% · 5h 12% (2h 30m) · Weekly 21% (3d 7h)", 퍼센트는 쓴 정도에 따라 초록·노랑·빨강
usage_summary() {
	local summary
	summary="${DIM}Context${RESET} $(percent "${context_percent:-0}")"
	if [ -n "$five_hour_percent" ]; then
		summary="${summary} ${DIM}· 5h${RESET} $(percent "$five_hour_percent")$(reset_in "$five_hour_resets_at")"
	fi
	if [ -n "$weekly_percent" ]; then
		summary="${summary} ${DIM}· Weekly${RESET} $(percent "$weekly_percent")$(reset_in "$weekly_resets_at")"
	fi
	printf '%s' "$summary"
}

percent() {
	printf '%s%s%%%s' "$(usage_color "$1")" "${1%.*}" "$RESET"
}

usage_color() {
	local percent=${1%.*}
	if [ "$percent" -ge 85 ]; then
		echo "$RED"
	elif [ "$percent" -ge 70 ]; then
		echo "$YELLOW"
	else
		echo "$GREEN"
	fi
}

# 초기화까지 남은 시간 " (3d 7h)"
reset_in() {
	local resets_at=${1%.*} remaining
	[ -n "$resets_at" ] || return 0
	remaining=$((resets_at - $(date +%s)))
	[ "$remaining" -gt 0 ] || return 0
	if [ "$remaining" -ge 86400 ]; then
		printf ' %s(%dd %dh)%s' "$DIM" $((remaining / 86400)) $((remaining % 86400 / 3600)) "$RESET"
	else
		printf ' %s(%dh %dm)%s' "$DIM" $((remaining / 3600)) $((remaining % 3600 / 60)) "$RESET"
	fi
}

main
