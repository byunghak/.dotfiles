# gh 는 로그인 계정이 여러 개여도 "활성 계정" 하나로만 API 를 호출한다.
# 업무 계정이 활성인 상태에서 개인 repo 에 PR 을 만들면 must be a collaborator 로
# 거부되는데, git push 는 osxkeychain 이 useHttpPath 로 repo 별 자격증명을 찾아가
# 성공한다. 같은 repo 에서 push 는 되고 gh 만 실패해 원인을 짚기 어렵다.
#
# remote owner 와 이름이 같은 계정이 로그인돼 있으면 그 토큰을 이 호출에만 주입한다.
# 조직 repo(owner 가 계정명과 다름)는 일치가 없어 활성 계정 그대로 동작한다.
#
# 한계: cwd 의 remote 로만 판단하므로 -R/--repo 로 다른 repo 를 지정한 호출은
# 보정하지 않는다. 그 경우는 GH_TOKEN 을 직접 지정할 것.
function gh() {
	# auth 서브커맨드는 GH_TOKEN 이 있으면 환경변수 토큰을 보고해 상태 파악을 방해한다
	if [[ "$1" == "auth" ]]; then
		command gh "$@"
		return
	fi

	local url="$(command git config --get remote.origin.url 2>/dev/null)"
	if [[ "$url" != *github.com* ]]; then
		command gh "$@"
		return
	fi

	local rest="${url##*github.com}"
	rest="${rest#:}"
	rest="${rest#/}"
	local owner="${rest%%/*}"

	local token=""
	if [[ -n "$owner" ]]; then
		token="$(command gh auth token --user "$owner" 2>/dev/null)"
	fi

	if [[ -z "$token" ]]; then
		command gh "$@"
		return
	fi

	GH_TOKEN="$token" command gh "$@"
}
