#!/bin/bash
set -e

DOTFILES="$HOME/.dotfiles"
DOTFILES_REPO="https://github.com/byunghak/.dotfiles.git"

info() { echo -e "\033[34m-->\033[0m $*"; }
ok() { echo -e "\033[32m✓\033[0m $*"; }

# ─── dotfiles clone/pull ──────────────────────────────────
if [ ! -d "$DOTFILES" ]; then
	info "dotfiles 클론 중..."
	git clone "$DOTFILES_REPO" "$DOTFILES"
else
	info "dotfiles 업데이트 중..."
	git -C "$DOTFILES" pull --rebase --quiet 2>/dev/null || true
fi
ok "dotfiles 준비 완료"

# ─── stow (개발 모듈) ─────────────────────────────────────
cd "$DOTFILES"
MODULES=(claude git lazygit nvim obsidian tmux zsh)
for m in "${MODULES[@]}"; do
	[[ -d "$DOTFILES/$m" ]] && stow --restow "$m" 2>/dev/null && info "stow: $m"
done
ok "stow 완료"

# ─── 프로필 gitconfig 적용 ────────────────────────────────
if [ -f "$HOME/.gitconfig.profile" ]; then
	# dev 스크립트가 프로필 gitconfig를 ~/.gitconfig.profile로 마운트
	git config --global include.path "$HOME/.gitconfig.profile"
	ok "프로필 gitconfig 적용"
fi

# ─── neovim 플러그인 설치 (최초 실행 시만) ────────────────
NVIM_DATA="$HOME/.local/share/nvim"
if [ ! -d "$NVIM_DATA/lazy" ]; then
	info "neovim 플러그인 설치 중..."
	nvim --headless "+Lazy! sync" +qa 2>/dev/null || true
	ok "neovim 플러그인 설치 완료"
fi

# ─── tmux 세션 시작 ───────────────────────────────────────
PROJECT_DIR="${PROJECT_DIR:-$HOME}"
cd "$PROJECT_DIR"

if [ -n "$TMUX" ] || [ -n "$NO_TMUX" ]; then
	exec zsh
else
	exec tmux new-session -s dev -c "$PROJECT_DIR"
fi
