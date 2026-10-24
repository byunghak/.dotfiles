#!/bin/sh
# process by port
function port() {
  lsof -i :$1
}

# 포트 점유 프로세스 강제 종료 (macOS/Linux)
function killport() {
  if [[ -z "$1" ]]; then
    echo "Usage: killport <port>" >&2
    return 1
  fi
  lsof -ti :"$1" | xargs kill -9 2>/dev/null && echo "killed port $1" || echo "no process on port $1"
}

# config
alias src="source ~/.zshrc"
# subshell 로 띄워 현재 shell 의 cwd 는 그대로 둔다
alias zrc="(cd ~/.config/zsh/ && claude)"
alias nvimrc="(cd ~/.config/nvim/ && claude)"
alias krc="(cd ~/.config/karabiner/ && claude)"
alias glc="(cd ~/.config/ghostty/ && claude)"
alias hlc="(cd ~/.config/hypr/ && claude)"
alias tlc="(cd ~/.dotfiles/tmux/ && claude)"

# Claude Code 세션 목록을 제목과 함께 fzf로 조회 후 resume
function sessions() {
  local titles_dir="$HOME/.claude/session-titles"
  local projects_dir="$HOME/.claude/projects"

  local selected
  selected=$(
    find "$projects_dir" -name "*.jsonl" 2>/dev/null | while read -r path; do
      local ts
      ts=$(stat -f "%m" "$path" 2>/dev/null || stat -c "%Y" "$path" 2>/dev/null) || continue
      echo "$ts $path"
    done | sort -rn | head -40 | while read -r ts path; do
      local session_id=$(basename "$path" .jsonl)
      local title="—"
      [[ -f "$titles_dir/$session_id" ]] && title=$(< "$titles_dir/$session_id")
      local date
      date=$(date -r "$ts" "+%y/%m/%d %H:%M" 2>/dev/null || date -d "@$ts" "+%y/%m/%d %H:%M")
      # 프로젝트 이름: 인코딩된 경로의 마지막 세그먼트
      local project=$(basename "$(dirname "$path")" | sed 's/^-//' | awk -F- '{print $NF}')
      printf "%s  [%-10s]  %-25s  %s\n" "$date" "$project" "$title" "$session_id"
    done | fzf --reverse --no-sort --prompt="resume> " --height=40%
  )

  [[ -z "$selected" ]] && return
  local session_id=$(echo "$selected" | awk '{print $NF}')
  claude --resume "$session_id"
}

# util
alias f="fd --hidden --exclude .git | fzf-tmux -p --reverse | xargs nvim"
alias nv="nvim"
alias cl="clear"
alias tl="tmux clear-history"
alias g="lazygit"
alias c="claude"
alias cr="caffeinate -i claude remote-control"

# confirm before overwriting something
alias cp="cp -i"
alias mv="mv -i"
alias rm="rm -i"

# env
# xargs 는 따옴표·공백이 든 값을 깨뜨리므로 shell 이 직접 읽게 한다
alias setenv='set -a; source .env; set +a'
