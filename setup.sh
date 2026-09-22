#!/bin/zsh
# Dotfiles 풀 부트스트랩
# Usage: ./setup.sh
set -e

DOTFILES="$HOME/.dotfiles"
OS=$(uname -s)

info() { echo "\033[34m-->\033[0m $*"; }
ok() { echo "\033[32m✓\033[0m $*"; }
title() { echo "\n\033[1m==> $*\033[0m"; }

# ─── OS별 패키지 설치 ─────────────────────────────────────
if [[ "$OS" == "Darwin" ]]; then
	source "$DOTFILES/setup-macos.sh"
elif [[ "$OS" == "Linux" ]]; then
	source "$DOTFILES/setup-linux.sh"
fi

# ─── Dotfiles stow ────────────────────────────────────────
title "Dotfiles symlink (stow)"
cd "$DOTFILES"

# 모듈 하나가 실패해도 나머지는 계속 stow
stow_modules() {
	for m in "$@"; do
		[[ -d "$DOTFILES/$m" ]] || continue
		if stow --restow "$m"; then
			info "stow: $m"
		else
			info "stow 실패: $m — 건너뜁니다"
		fi
	done
}

# 공통 모듈
stow_modules claude git lazygit nvim tmux obsidian zsh

# OS 전용 모듈
if [[ "$OS" == "Darwin" ]]; then
	stow_modules ghostty karabiner
elif [[ "$OS" == "Linux" ]]; then
	stow_modules hypr kime linux
fi

ok "완료"

# ─── Second Brain ─────────────────────────────────────────
title "Second Brain vault"

# vault 위치를 하드코딩하지 않는다.
# 디렉토리 이름이 아니라 remote 소유자로 찾는 이유: second-brain 이라는 이름의
# 저장소가 개인·회사 두 개라, 이름으로 찾으면 회사 vault 를 잘못 잡는다.
# (N) 은 매칭이 없을 때 글롭을 비우는 zsh 한정자 — 없으면 set -e 에 걸려 죽는다.
find_repo_by_remote() {
	local d
	for d in "$HOME"/*/.git(N) "$HOME"/*/*/.git(N); do
		d="${d:h}"
		if git -C "$d" config --get remote.origin.url 2>/dev/null | grep -qE "$1"; then
			print -r -- "$d"
			return 0
		fi
	done
	return 1
}

# 우선순위: 환경변수 > 이미 클론된 위치 > 기본 위치(신규 클론용)
# 소유자 패턴이 byunghak[^/]* 인 것은 byunghak 과 byunghak-dable 을 모두 받기 위함.
SECOND_BRAIN="${SECOND_BRAIN:-$(find_repo_by_remote 'byunghak[^/]*/second-brain' || true)}"
SECOND_BRAIN="${SECOND_BRAIN:-$HOME/second-brain}"

if [ ! -d "$SECOND_BRAIN" ]; then
	info "클론 중... ($SECOND_BRAIN)"
	mkdir -p "${SECOND_BRAIN:h}"
	if git clone https://github.com/byunghak-dable/second-brain.git "$SECOND_BRAIN"; then
		ok "클론 완료"
	else
		info "클론 실패 — 건너뜁니다 (git 인증 확인 후 재실행)"
	fi
elif ! git -C "$SECOND_BRAIN" fetch origin main --quiet; then
	info "원격 확인 실패 — 건너뜁니다"
else
	info "원격 변경사항 확인 중... ($SECOND_BRAIN)"
	LOCAL=$(git -C "$SECOND_BRAIN" rev-parse HEAD)
	REMOTE=$(git -C "$SECOND_BRAIN" rev-parse origin/main)
	if [[ "$LOCAL" == "$REMOTE" ]]; then
		ok "이미 최신 상태"
	elif git -C "$SECOND_BRAIN" pull --rebase origin main; then
		ok "업데이트 완료"
	else
		info "업데이트 실패 — 건너뜁니다"
	fi
fi

title "완료"
echo "쉘 재시작 후 모든 설정이 적용됩니다: exec zsh"
