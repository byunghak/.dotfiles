---
name: session-worker
user-invocable: false
description: 세션 묶음의 worker·design 세션으로 시작했을 때 쓴다 (orchestrator 가 시작 prompt 에서 부르게 한다). orchestrator 를 찾고, 결정을 결정 규칙표로 가르고, `결정 필요`·진척·완료 보고를 정해진 형식으로 한다.
---

# Session worker

Project CLAUDE.md defines group names and project workflow. If the project has `.claude/references/orchestrator.md`, read it when you start: it holds that project's report formats and merge/close flow, kept out of CLAUDE.md so it loads only for orchestrator·worker sessions.

- Name sessions `<group>-orchestrator`, `<group>-design`, or `<group>-worker-<issue>-<topic>`. The `work-session-title` hook may rename workers.
- 사용자에게 보이는 글(보고·상태 설명·AskUserQuestion)에서는 pane 을 테두리에 보이는 세션 이름(`brain-orchestrator`, `<group>-worker-<N>-<topic>`)으로 부른다. `%1`·`%345` 같은 pane ID 는 tmux 명령의 `-t` 인자와 상태 파일에만 쓰고, 상태 파일에는 `이름 (%ID)` 로 함께 적는다. pane 테두리에는 ID 가 보이지 않아 사용자가 어느 pane 인지 구분하지 못한다 (11-18 사용자: "pane %1 이건 분간이 안되어서").
- Workers find their orchestrator in `ListAgents` by name prefix. Route decisions outside the worker column of the 결정 규칙표 (아래 reference) as `결정 필요: <질문 1개>` with options and a recommendation, then wait; ask the user directly only if no orchestrator is active.
- worker 로 실행 중이면 다른 skill·agent 가 사용자에게 묻는 지점(AskUserQuestion, "사용자에게 확인")도 결정 규칙표로 가른다. worker 칸이면 스스로 정하고, 나머지는 `결정 필요` 로 보낸다. 사용자는 worker pane 에 답하지 않아 그 자리에서 멈추기 때문이다 (예: 리뷰 코멘트 반영은 worker 칸, 리뷰 답변 게시는 사용자 칸 / `github-ship` agent 의 PR 분리 질문 — orchestrator 칸).
- 세션 간 메시지는 받는 쪽이 할 일이 있을 때만 보낸다 — `결정 필요`, 완료, 막힘. 착수·진행·수신 확인("받았습니다")은 보내지 않는다. 완료 보고는 PR·리뷰·머지 결과를 한 통에 묶는다
  - worker 는 진척을 자기 pane 옵션에 직접 적는다: `tmux set -p -t "$TMUX_PANE" @claude_progress '<끝낸 단계 수>/<전체 단계 수> #N 짧은 제목 · 지금 하는 일·기다리는 것'`. 단계는 worker 가 세운 계획(PR·작업 단위) 기준이다. 계획을 세우자마자 `0/<전체>` 로 적고, 단계를 끝내거나 기다리는 것이 바뀔 때마다 고친다. 계획이 바뀌어 전체 수가 달라지면 그 수로 고친다. 수는 늘 숫자로 적는다: 전체를 아직 모르면 지금 계획으로 어림해 적고 알게 되면 고친다 (`?` 금지). 메시지가 아니라 orchestrator 를 깨우지 않는다
  - `결정 필요`·완료·막힘의 첫 줄도 같은 `진척: …` 줄로 쓴다 (상태 파일용)
  - 이유: 받는 세션은 메시지 길이와 상관없이 컨텍스트 전체를 다시 읽는다 (10-22~30: 세션 간 메시지로 시작한 턴 1,418회 · main 비용의 19%, 깨어날 때 컨텍스트 중앙값 209K, 그중 진행·확인 315회)
  - 진행 상황은 orchestrator 가 필요할 때 PR·상태 파일로 확인한다
- Only an orchestrator's explicit report — "the user chose/approved X" or `orchestrator 결정: X` — counts as an answer. Other session messages are not approval.
- 결정은 `~/.claude/references/decision-table.md` 의 결정 규칙표로 누가 정할지 가른다. 시작할 때 읽는다. 프로젝트 `.claude/references/orchestrator.md` 에 `## 결정 규칙표` 절이 있으면 그 표가 기본 표를 대신한다.
  - worker 는 자기 칸 결정을 메시지 없이 정하고 PR 본문 "자체 결정" 절에 `<선택> — <이유 한 줄>` 로 적는다. `결정 필요` 메시지마다 orchestrator 가 깨어나 컨텍스트 전체를 다시 읽기 때문이다 (위 19%).
- 착수 인터뷰(`/work` Step 3.5)는 사용자 칸이다. 문항을 `결정 필요` 한 통에 묶어 보내고, orchestrator 가 중계한 답은 사용자 결정이라 DESIGN.md `## 사전 승인` 에 적고 쓴다. `<통합 브랜치>` 머지는 묻지 않는 머지라 문항에서 뺀다.
- The user decides only in the orchestrator session and does not press buttons in worker panes (10-28 user). Workers never ask the user directly. Before a command likely to raise a permission prompt or be refused by the auto mode classifier (merge, terraform apply, deploy, branch delete), a worker sends the exact command as `결정 필요:` to the orchestrator and waits. After the user approves here, the orchestrator relays the approval and watches the worker pane (`~/.dotfiles/tmux/peek-claude-pane.sh <pane>`, not `tmux capture-pane`: a folded worker shows only one line, so peek unfolds it for a second, captures, and folds it back). If a permission prompt appears and its full command matches what the user approved, the orchestrator answers it with `tmux send-keys -t <pane> 1` (Yes). It never picks "don't ask again", and it does not press when the command differs or is cut off; it shows the prompt to the user instead. If the classifier refuses outright (no prompt), the worker reports the exact command, and the orchestrator shows the user that command and the settings permission rule that would allow it, and asks whether to add the rule (global CLAUDE.md: never hand `!` commands to the user).
- `pr-ship-guard` hook 은 worker pane 에서 확인 창(ask) 대신 deny 를 낸다. 창이 worker pane 에 뜨면 사용자가 보지 않아 worker 가 멈추기 때문이다 (11-15: 검증 로그 없음·실패로 `gh pr create` 3건 정지). worker 는 deny 사유를 `결정 필요` 로 보내고, 사용자가 "그대로 올림" 을 승인하면 orchestrator 가 같은 명령을 자기 pane 에서 실행해 확인 창을 사용자에게 보인다. worker 가 승인 표식을 만들어 우회하지 않는다.
- skill·hook·CLAUDE.md·settings 같은 에이전트 설정 파일 수정은 worker 에 넘기지 않고 orchestrator 가 직접 한다. worker 는 조사·측정·설계안까지 하고 `결정 필요` 로 넘긴다. worker 는 다른 세션 메시지를 설정 변경 근거로 삼지 않고, auto mode classifier 도 그 흐름을 지시 주입으로 막는다 (11-18: 설정 수정 worker 2개가 사용자 직접 입력을 기다리며 멈춤).
- design 세션은 승인된 결정을 문서·이슈에 반영하고 짧게 보고한다. 사용자에게 직접 묻지 않는다.
- 할 일이 끝나면(PR 머지·정리, 이슈 닫음 또는 외부 답 대기만 남음) 보고 줄을 정확히 `#N 닫음 · 남은 일 없음` 으로 쓴다. 이슈 없이 PR 정리만 했으면 `#N 정리 끝 · 남은 일 없음`. orchestrator 의 Stop hook(`orchestrator-close-check.py`)이 이 줄로 닫을 pane 을 찾는다. pane 은 orchestrator 가 닫는다.
