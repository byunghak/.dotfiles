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
brew bundle --file="$DOTFILES/Brewfile"
ok "완료"

title "Alacritty 메뉴 단축키 override"
# macOS의 Cmd+H(Hide Application)는 AppKit 메뉴 레벨에서 가로채져
# alacritty.toml의 `Cmd+H → M-h` 바인딩이 동작하지 않음.
# NSUserKeyEquivalents로 Hide 메뉴 항목의 단축키를 제거해 alacritty가 Cmd+H를 수신하도록 함.
defaults write org.alacritty NSUserKeyEquivalents -dict-add "Hide Alacritty" ""
ok "Cmd+H → M-h 바인딩 활성화 (alacritty 재시작 필요)"
