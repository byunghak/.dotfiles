ZDOTDIR=$HOME/.config/zsh

# --- settings ---
for _zsh_conf in $ZDOTDIR/*.zsh(N); do
  source "$_zsh_conf"
done
unset _zsh_conf

# PATH 설정 (eval 없이 직접 추가)
[[ -d /opt/homebrew/bin ]] && export PATH="/opt/homebrew/bin:$PATH"
[[ -d $HOME/.volta/bin ]] && export VOLTA_HOME="$HOME/.volta" && export PATH="$VOLTA_HOME/bin:$PATH"
[[ -d $HOME/.cargo/bin ]] && export PATH="$HOME/.cargo/bin:$PATH"
# brew rustup은 shim을 ~/.cargo/bin이 아닌 자체 prefix에 둔다 (cargo/rustc/rust-analyzer)
[[ -d /opt/homebrew/opt/rustup/bin ]] && export PATH="/opt/homebrew/opt/rustup/bin:$PATH"
[[ -d $HOME/.local/share/bob/nvim-bin ]] && export PATH="$HOME/.local/share/bob/nvim-bin:$PATH"
[[ -d $HOME/.sdkman/candidates/java/current/bin ]] && export PATH="$HOME/.sdkman/candidates/java/current/bin:$PATH"
(( $+commands[zoxide] )) && eval "$(zoxide init zsh)"

# pyenv PATH (초기화는 zinit에서 lazy loading)
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT ]] && export PATH="$PYENV_ROOT/bin:$PATH"

# gvm (go version manager)
[[ -s $HOME/.gvm/scripts/gvm ]] && source "$HOME/.gvm/scripts/gvm"

# go PATH lazy loading
if (( $+commands[go] )); then
  __go_lazy_init() {
    unfunction go 2>/dev/null
    export PATH="$(command go env GOPATH)/bin:$PATH"
  }
  go() { __go_lazy_init && command go "$@" }
fi

# --- bash word select ---
autoload -U select-word-style
select-word-style bash

# --- completion ---
zmodload zsh/complist
zstyle ':completion:*' menu select
bindkey -M menuselect 'h' vi-backward-char
bindkey -M menuselect 'k' vi-up-line-or-history
bindkey -M menuselect 'l' vi-forward-char
bindkey -M menuselect 'j' vi-down-line-or-history

# --- history ---
HISTSIZE=1000000
SAVEHIST=1000000
HISTFILE=$HOME/.cache/.zsh_history

# zsh 기본 동작은 셸이 정상 종료될 때 한 번만 HISTFILE에 기록한다.
# tmux에서는 kill-pane/kill-window로 패널을 죽이는 경우가 많아
# 그 세션 히스토리가 통째로 유실되므로 즉시 기록으로 바꾼다.
setopt INC_APPEND_HISTORY     # 명령 실행 즉시 HISTFILE에 기록
setopt EXTENDED_HISTORY       # 타임스탬프 함께 기록
setopt HIST_IGNORE_DUPS       # 직전과 동일한 명령은 저장 안 함
setopt HIST_IGNORE_SPACE      # 공백으로 시작하는 명령은 저장 안 함
setopt HIST_REDUCE_BLANKS     # 불필요한 공백 정리 후 저장
setopt HIST_EXPIRE_DUPS_FIRST # 용량 초과 시 중복 항목부터 제거

bindkey '^p' history-search-backward
bindkey '^n' history-search-forward

# --- config for os ---
case "$(uname -s)" in
Darwin) # mac
  export XDG_CONFIG_HOME=$HOME/.config
  alias brew86="arch -x86_64 /usr/local/bin/brew"
  alias pyenv86="arch -x86_64 pyenv"
  alias ls="ls -G"
  alias ll="ls -lGFh"
  alias la="ls -laGFh"
  ;;
Linux) # linux
  alias ls='ls --color=auto'
  alias ll='ls -l --color=auto'
  alias la='ls -al --color=auto'
  ;;
esac

# --- fzf ---
export FZF_DEFAULT_OPTS="--layout reverse"
export FZF_DEFAULT_COMMAND='fd --type f'

# --- devcontainer dev CLI ---
[[ -d $HOME/.dotfiles/devcontainer/bin ]] && export PATH="$HOME/.dotfiles/devcontainer/bin:$PATH"

# --- custom ---
[[ -n $REPO_PATH ]] && export PYTHONPATH="${REPO_PATH}:$PYTHONPATH"
