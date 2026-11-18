#!/usr/bin/env bash
# Claude Code SessionStart hook (matcher clear): orchestrator 세션이면 /clear 뒤 첫 응답 전에 orchestrator skill 을 다시 부르게 한다
# /clear 는 불러온 skill 을 비우지만 -n·/rename 으로 준 세션 이름은 남는다. 이름은 ~/.claude/sessions/<claude pid>.json 의 name 에서 읽는다 (비공식 파일)
# hook 은 claude 의 자식 셸에서 돌므로, 부모 프로세스를 거슬러 올라가며 registry 파일이 있는 pid 를 찾는다

session_name=""
pid=$PPID
for _ in 1 2 3 4 5; do
	registry="$HOME/.claude/sessions/$pid.json"
	if [ -f "$registry" ]; then
		session_name=$(jq -r '.name // ""' "$registry")
		break
	fi
	pid=$(ps -o ppid= -p "$pid" | tr -d ' ')
	[ -n "$pid" ] && [ "$pid" -gt 1 ] || break
done

case "$session_name" in
*-orchestrator) ;;
*) exit 0 ;;
esac

jq -n --arg name "$session_name" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: "이 세션은 \($name) 이다. /clear 로 orchestrator skill 이 비워졌으니, 첫 응답 전에 Skill 도구로 orchestrator skill 을 불러 따른다."}}'
