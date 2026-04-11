#!/bin/zsh
# Dotfiles 풀 부트스트랩
# Usage: ./setup.sh
set -e

DOTFILES="$HOME/.dotfiles"
OS=$(uname -s)

info()  { echo "\033[34m-->\033[0m $*" }
ok()    { echo "\033[32m✓\033[0m $*" }
title() { echo "\n\033[1m==> $*\033[0m" }

# ─── OS별 패키지 설치 ─────────────────────────────────────
if [[ "$OS" == "Darwin" ]]; then
  source "$DOTFILES/setup-macos.sh"
elif [[ "$OS" == "Linux" ]]; then
  source "$DOTFILES/setup-linux.sh"
fi

# ─── Dotfiles stow ────────────────────────────────────────
title "Dotfiles symlink (stow)"
cd "$DOTFILES"

# 공통 모듈
COMMON_MODULES=(claude git lazygit nvim tmux obsidian zsh)
for m in $COMMON_MODULES; do
  [[ -d "$DOTFILES/$m" ]] && { stow --restow "$m" && info "stow: $m" }
done

# macOS 전용 모듈
if [[ "$OS" == "Darwin" ]]; then
  MACOS_MODULES=(alacritty karabiner)
  for m in $MACOS_MODULES; do
    [[ -d "$DOTFILES/$m" ]] && { stow --restow "$m" && info "stow: $m" }
  done
fi

# Linux 전용 모듈
if [[ "$OS" == "Linux" ]]; then
  LINUX_MODULES=(hypr kime linux)
  for m in $LINUX_MODULES; do
    [[ -d "$DOTFILES/$m" ]] && { stow --restow "$m" && info "stow: $m" }
  done
fi
ok "완료"

# ─── Second Brain ─────────────────────────────────────────
title "Second Brain vault"
if [ ! -d "$HOME/second-brain" ]; then
  info "클론 중..."
  git clone https://github.com/byunghak-dable/second-brain.git "$HOME/second-brain"
else
  info "원격 변경사항 확인 중..."
  git -C "$HOME/second-brain" fetch origin main --quiet
  LOCAL=$(git -C "$HOME/second-brain" rev-parse HEAD)
  REMOTE=$(git -C "$HOME/second-brain" rev-parse origin/main)
  if [[ "$LOCAL" != "$REMOTE" ]]; then
    git -C "$HOME/second-brain" pull --rebase origin main
    ok "업데이트 완료"
  else
    ok "이미 최신 상태"
  fi
fi

# obsidian-cli 기본 vault 등록 (미등록 시에만)
if command -v obsidian-cli &>/dev/null; then
  if [[ "$(obsidian-cli print-default 2>/dev/null)" != *"second-brain"* ]]; then
    if obsidian-cli set-default second-brain 2>/dev/null; then
      ok "obsidian-cli 기본 vault 설정 완료"
    else
      info "obsidian-cli: Obsidian 앱에서 second-brain vault를 먼저 등록하세요"
    fi
  else
    ok "obsidian-cli 기본 vault 이미 설정됨"
  fi
fi

title "완료"
echo "쉘 재시작 후 모든 설정이 적용됩니다: exec zsh"
