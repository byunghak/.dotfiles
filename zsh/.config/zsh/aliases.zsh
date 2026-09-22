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

# fabric-ai
function _fabric_ai() {
  fabric-ai "$*"
}


function nc() {
  if [[ -z "$TMUX" ]]; then
    echo "Not inside a tmux session. Run from within tmux."
    return 1
  fi

  # Determine working directory from argument
  local target="${1:-$PWD}"
  local dir
  if [[ -d "$target" ]]; then
    dir="$(realpath "$target")"
  else
    dir="$(realpath "$(dirname "$target")")"
  fi

  # nvim을 실행할 현재 pane ID 저장
  local nvim_pane
  nvim_pane="$(tmux display-message -p '#{pane_id}')"

  # Split right (30% width) for claude — full height
  tmux split-window -h -c "$dir" -l 30% "claude; exec $SHELL"

  # Go back to left pane and split bottom (20% height) for terminal only under neovim
  tmux select-pane -L
  tmux split-window -v -c "$dir" -l 15%

  # nvim pane으로 포커스 이동 후 neovim 실행
  tmux select-pane -t "$nvim_pane"
  nvim "$@"
}


# config
alias src="source ~/.zshrc"
alias zrc="nc ~/.config/zsh/"
alias nvimrc="nc ~/.config/nvim/"
alias krc="nc ~/.config/karabiner/"
alias glc="nc ~/.config/ghostty/"
alias hlc="nc ~/.config/hypr/"
alias tlc="nc ~/.tmux.conf"

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

# docker
alias decr='aws ecr get-login-password --region ${AWS_DEFAULT_REGION} | podman login -u AWS --password-stdin '
alias dbuild='podman build -f ${DOCKERFILE_PATH} -t local-build-app --build-arg NODE_ENV=${NODE_ENV} --build-arg AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} --build-arg AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} --build-arg AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION} --platform linux/x86_64 .'

# env
alias setenv='export $(xargs < .env)'

# ai
alias '??'='noglob _fabric_ai'
alias '?'="w3m"
