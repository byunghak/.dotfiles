#!/usr/bin/env bash
# Claude Code SessionStart hook (matcher clear|compact): 세션 묶음의 orchestrator·worker 세션이면 /clear·compact 뒤 첫 응답 전에 자기 skill 을 다시 부르게 한다
# /clear 는 불러온 skill 을 비우고, compact 는 처음 불렀을 때 판의 skill 본문을 다시 붙여 그 뒤 고친 절차가 빠진다. 둘 다 -n·/rename 으로 준 세션 이름은 남는다. 이름은 ~/.claude/sessions/<claude pid>.json 의 name 에서 읽는다 (비공식 파일)
# hook 은 claude 의 자식 셸에서 돌므로, 부모 프로세스를 거슬러 올라가며 registry 파일이 있는 pid 를 찾는다

source=$(jq -r '.source // ""')
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
*-orchestrator) skill_name="orchestrator" ;;
*-worker-*) skill_name="session-worker" ;;
*) exit 0 ;;
esac

case "$source" in
compact) reason="compact 뒤 붙은 $skill_name skill 본문은 처음 불렀을 때 판이라 이후 바뀐 절차가 빠져 있으니" ;;
*) reason="/clear 로 $skill_name skill 이 비워졌으니" ;;
esac

jq -n --arg name "$session_name" --arg reason "$reason" --arg skill "$skill_name" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: "이 세션은 \($name) 이다. \($reason), 첫 응답 전에 Skill 도구로 \($skill) skill 을 다시 불러 따른다."}}'
