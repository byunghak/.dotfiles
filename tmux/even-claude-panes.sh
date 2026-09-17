#!/bin/sh
# 가장 우측 세로 컬럼(= claude 컬럼)의 pane 높이를 균등하게 재조정한다.
# pane을 추가할 때(bind i)와 레이아웃을 되돌릴 때(bind R) 호출.
set -e

# zoom 중에는 모든 pane이 window 크기로 보고되어 컬럼 판별과 resize가 모두 실패한다.
if [ "$(tmux display-message -p '#{window_zoomed_flag}')" = "1" ]; then
	tmux resize-pane -Z
fi

# 호출 시점의 활성 pane이 어디든(예: 좌측 nvim에서 누른 bind R) claude 컬럼을 대상으로 한다.
column_left=$(tmux list-panes -F '#{pane_left}' | sort -n | tail -1)
window_height=$(tmux display-message -p '#{window_height}')

# 같은 컬럼(= pane_left 동일)의 pane을 위에서 아래 순서로 수집
pane_ids=$(tmux list-panes -F '#{pane_top} #{pane_id} #{pane_left}' |
	awk -v left="$column_left" '$3 == left { print $1, $2 }' |
	sort -n |
	awk '{ print $2 }')

pane_count=$(printf '%s\n' "$pane_ids" | wc -l | tr -d ' ')
[ "$pane_count" -lt 2 ] && exit 0

# pane 사이 구분선이 (n-1)줄을 차지하므로 이를 제외하고 n등분
usable_height=$((window_height - pane_count + 1))
each_height=$((usable_height / pane_count))
remainder=$((usable_height % pane_count))

# 나머지를 마지막 pane에 몰아주면 혼자 커지므로 위쪽부터 1줄씩 분산한다.
# 마지막 pane은 남은 높이를 자동으로 흡수하므로 대상에서 제외.
index=0
printf '%s\n' "$pane_ids" | sed '$d' | while read -r pane_id; do
	index=$((index + 1))
	pane_height=$each_height
	[ "$index" -le "$remainder" ] && pane_height=$((pane_height + 1))
	tmux resize-pane -t "$pane_id" -y "$pane_height"
done
