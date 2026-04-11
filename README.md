# Dotfiles

[GNU Stow](https://www.gnu.org/software/stow/) 기반 dotfiles 관리

## 🚀 Getting Started

```sh
git clone https://github.com/byunghak/.dotfiles.git
cd .dotfiles

brew install stow # macOS
stow nvim # symlink 예시: nvim
```

## 📦 Configurations

| Directory   | Description                                                                                     |
| ----------- | ----------------------------------------------------------------------------------------------- |
| `alacritty` | [Alacritty](https://alacritty.org/) 터미널 설정                                                 |
| `claude`    | [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 커맨드, 스킬, 규칙, hooks, agents |
| `ghostty`   | [Ghostty](https://ghostty.org/) 터미널 설정                                                     |
| `git`       | Git 설정 — [Delta](https://github.com/dandavison/delta) pager, pre-push hook                    |
| `hypr`      | [Hyprland](https://hyprland.org/) 윈도우 매니저 (Linux)                                         |
| `karabiner` | [Karabiner-Elements](https://karabiner-elements.pqrs.org/) 키보드 리매핑 (macOS)                |
| `kime`      | [Kime](https://github.com/Riey/kime) 한글 입력기 (Linux)                                        |
| `lazygit`   | [Lazygit](https://github.com/jesseduffield/lazygit) Git TUI 설정                                |
| `linux`     | Linux 전용 스크립트                                                                             |
| `nvim`      | [Neovim](https://neovim.io/) — LazyVim 기반 설정                                                |
| `tmux`      | [Tmux](https://github.com/tmux/tmux) 터미널 멀티플렉서 설정                                     |
| `zsh`       | [Zsh](https://www.zsh.org/) — Zinit, aliases, prompt                                            |

## ⚡️ Requirements

### Neovim

- Neovim >= **0.10.0**
- [Nerd Font](https://www.nerdfonts.com/) **_(optional)_**
- [Lazygit](https://github.com/jesseduffield/lazygit)
- [fzf](https://github.com/junegunn/fzf)
