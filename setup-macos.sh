#!/bin/zsh
# macOS 패키지 설치
# setup.sh에서 호출됨
set -e

DOTFILES="$HOME/.dotfiles"

title "Xcode Command Line Tools"
if ! xcode-select -p &>/dev/null; then
	info "설치 중..."
	xcode-select --install
	until xcode-select -p &>/dev/null; do sleep 5; done
else
	ok "이미 설치됨"
fi

title "Homebrew"
if ! command -v brew &>/dev/null; then
	info "설치 중..."
	/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
	eval "$(/opt/homebrew/bin/brew shellenv)"
else
	ok "이미 설치됨"
fi

title "Brew 패키지 (Brewfile)"
# 일부 패키지가 실패해도(disabled cask, 이름 변경 등) 나머지 설치는 계속 진행.
if brew bundle --file="$DOTFILES/Brewfile"; then
	ok "완료"
else
	info "일부 패키지 설치 실패 — 건너뛰고 계속 진행합니다"
	brew bundle check --verbose --file="$DOTFILES/Brewfile" 2>/dev/null | grep '^→' || true
fi

title "Alacritty"
# brew cask alacritty는 Gatekeeper 검사 미통과로 2026-09-01 disabled 상태.
# 앱이 없으면 수동 설치 안내만 하고 넘어감.
if [[ -d /Applications/Alacritty.app ]]; then
	ok "이미 설치됨"
else
	info "brew cask disabled 상태입니다. 수동 설치:"
	info "  https://github.com/alacritty/alacritty/releases"
fi

title "Alacritty 메뉴 단축키 override"
# macOS의 Cmd+H(Hide Application)는 AppKit 메뉴 레벨에서 가로채져
# alacritty.toml의 `Cmd+H → M-h` 바인딩이 동작하지 않음.
# NSUserKeyEquivalents로 Hide 메뉴 항목의 단축키를 제거해 alacritty가 Cmd+H를 수신하도록 함.
defaults write org.alacritty NSUserKeyEquivalents -dict-add "Hide Alacritty" ""
ok "Cmd+H → M-h 바인딩 활성화 (alacritty 재시작 필요)"
