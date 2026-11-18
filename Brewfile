# Dotfiles 의존 패키지
# brew bundle 로 일괄 설치

# 필수
brew "stow"
brew "git"

# Zsh
brew "zinit"          # zsh 플러그인 매니저 (plugins.zsh)
brew "direnv"         # 디렉토리별 env 로더 (plugins.zsh)

# 터미널 도구
brew "tmux"
brew "fzf"
brew "fd"             # fzf 기본 명령어 (aliases.zsh: FZF_DEFAULT_COMMAND)
brew "ripgrep"        # nvim snacks.nvim grep 기능 의존 (rg)
brew "zoxide"         # 디렉토리 점프 (.zshrc: zoxide init zsh)
brew "lazygit"
brew "neovim"
brew "git-delta"      # git diff pager (.gitconfig, lazygit config)
brew "terminal-notifier"  # 결정 대기 알림, 누르면 그 pane 으로 이동 (hooks/tmux-pane-claude.sh)

# Git / DevOps
brew "gh"             # GitHub CLI (PR, issue, workflow)
brew "ankitpokhrel/jira-cli/jira-cli"  # Jira CLI
brew "4ier/tap/notion-cli"             # Notion CLI (page, db, block, comment)

# AI
cask "claude-code"    # Claude Code CLI (aliases.zsh: c·zrc 등, tmux: bind g·i·C-r)
brew "rtk"            # Claude Code Bash hook (settings.json: rtk hook claude, RTK.md)

# Obsidian
brew "yakitrak/yakitrak/notesmd-cli"  # 구 obsidian-cli (0.3.x에서 이름 변경)
cask "obsidian"

# 터미널 에뮬레이터
cask "ghostty"  # ghostty/.config/ghostty 설정 의존

# 키보드 / 윈도우 관리
cask "karabiner-elements"  # karabiner/.config/karabiner 설정 의존
cask "rectangle"           # 윈도우 스냅/타일링
