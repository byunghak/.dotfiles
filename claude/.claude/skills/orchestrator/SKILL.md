---
name: orchestrator
description: 세션 묶음의 orchestrator 를 맡을 때 쓴다 — worker·design 세션을 띄우고, 결정을 모아 사용자에게 묻고, 머지·정리·세션 닫기와 상태 파일을 관리한다. worker·design 쪽 규칙은 session-worker skill.
---

# Orchestrator

시작할 때 `~/.claude/references/decision-table.md` 를 읽는다. 결정 규칙표와, worker 와 함께 지키는 공통 규칙(세션·pane 이름, 무엇이 승인인지, 권한 프롬프트, 착수 인터뷰, `pr-ship-guard`, 설정 파일 수정, subagent 띄우기)이 있다. 아래는 orchestrator 쪽 동작이다.

- 세션이 orchestrator 를 맡으면(새로 시작·resume 모두) 맨 먼저 `ListAgents` 첫 줄 "This session is <name>" 으로 자기 이름을 본다. `<group>-orchestrator` 가 아니면 첫 답의 첫 줄에서 사용자에게 `/rename <group>-orchestrator` 입력을 요청하고, 이름이 바뀐 것을 확인하기 전에는 worker 를 띄우지 않는다. Claude 는 `/rename` 을 스스로 실행할 수 없고, 자기 pane 에 send-keys 하는 것은 실행 중인 턴과 겹친다. worker 는 이름 접두어로 orchestrator 를 찾으므로, 이름이 다르면 결정 필요를 orchestrator 대신 자기 pane 에서 사용자에게 묻는다.
- worker·design 세션은 `~/.dotfiles/tmux/spawn-claude-worker.sh <group>-worker-<issue>-<topic> "<task prompt>"` 로 띄운다. 스크립트가 orchestrator 의 window 안에 새 pane 을 만들고(새 window 로 띄우지 않는다), 시작 prompt 첫 문장에 `session-worker` skill 을 부르게 넣고, window 를 다시 배치한다(orchestrator 는 왼쪽, worker 는 오른쪽에 쌓고 focus 없는 worker 는 제목 줄로 접는다). 이름은 전체 이름을 준다 — 그룹 이름만 주면 같은 이름 세션이 여럿 생겨 SendMessage 가 엉뚱한 worker 로 간다. 이슈가 아직 없으면 `<group>-worker-<topic>`. This applies to every workflow; `/work` is one possible task, not a dependency.
- Every new task (new issue, new PR to finish, follow-up outside the worker's issue) gets a new worker session; never hand it to an existing worker, even an idle one.
- worker 가 `병렬 착수: <PR 분리 이름>… · plan <경로>` 를 보내면 묻지 않고 PR 마다 새 worker 를 띄운다. PR 분리는 승인 ① 에서 이미 받았다. 시작 prompt 의 task 는 `/work <plan 경로> — <PR 분리 이름> 만 맡는다. 승인 ①·사전 승인은 DESIGN.md 에 있다`. 이름은 `<group>-worker-<issue>-<PR 분리 이름>`
- worker 가 지키는 규칙(결정 필요 형식, 진척 적기, 사용자에게 직접 묻지 않기, 닫음 보고 줄)은 `~/.claude/skills/session-worker/SKILL.md` 에 있다. worker 에 규칙 변경을 알릴 때 그 파일을 기준으로 한다.
- 자기 칸 결정:
  - orchestrator 는 자기 칸 결정을 worker 에 `orchestrator 결정: <선택> — <이유 한 줄>` 로 중계하고, 상태 파일 "자체 결정" 칸에 적는다. 사용자에게는 다음 보고 끝에 한 줄씩 묶어 알린다. 확인을 묻지 않는다.
  - 사용자에게 올릴 결정이 생기면 AskUserQuestion 직전에 `PushNotification` 으로 한 줄 알린다 (예: `결정 2건 대기: #123 머지, Slack 공지`). 사용자가 터미널을 보고 있으면 도구가 알아서 보내지 않는다.
  - 권한 프롬프트에 `send-keys 1` 로 답하는 것은 이 표와 무관하게 사용자가 승인한 명령에만 한다. auto mode classifier 가 다른 세션의 승인을 사용자 승인으로 보지 않을 수 있기 때문이다.
- 쌓인 결정은 AskUserQuestion 한 번에 묻는다. 전역 CLAUDE.md "한 턴에 질문 1개" 의 orchestrator 예외다.
  - 배경: orchestrator 에는 여러 worker 의 `결정 필요` 가 동시에 쌓인다. 한 턴에 하나씩 물으면 사용자가 여러 번 오가야 하고, 그동안 나머지 worker 는 답을 기다리며 논다.
  - 방식: 결정이 2건 이상이면 질문 하나에 결정 하나씩, 최대 4개. 각 질문은 맥락 한두 문장(무엇을 바꾸는가, 되돌릴 수 있는가) + 선택지 2개에서 4개, 권장안을 첫 칸에 "(Recommended)". 선택지 description 에 고르면 실제로 일어나는 일(머지 명령의 head, 다시 뜨는 pod, 비용)을 적는다. 사용자는 대화창 위 본문보다 이 대화상자를 먼저 읽는다.
  - 질문에 처음 나오는 내부 이름에는 한 줄 설명을 붙이고(전역 CLAUDE.md "결정은 선택 창으로"), 다른 이슈의 결정 모음은 항목을 펼쳐 보인다. 설계·계약 질문은 기준 구현(예: MAX)이 같은 문제를 어떻게 푸는지 먼저 조사해(아래 "조사는 맡긴다") 질문 맥락에 넣는다. 설계·계약 질문은 권장안 채택이 낮고 기준 구현을 되묻는 일이 잦다.
  - 머지 질문 (머지 대기 `결정 필요` 가 가장 많다): 리뷰·검증 증거를 통과한 머지 대기 PR 이 여럿이면 질문 하나에 multiSelect 로 묶는다 (선택지 하나가 PR 하나, 고르지 않은 PR 은 보류). 머지 뒤 배포가 따르는 PR 은 "머지 + 배포" 를 선택지로 함께 둔다 — 사용자가 권장안 대신 고른 답에 "머지 + 배포" 가 반복됐다. 증거가 빠졌거나 base 가 main·develop 인 PR 은 묶지 않고 따로 묻는다.
  - 4개를 넘으면 되돌리기 어려운 순(머지·삭제·외부 게시 → wire·계약 → 나머지)으로 앞 4개를 묻고, 나머지는 답 받은 뒤 이어 묻는다. 1건이면 평소처럼 한 질문.
  - 질문별 설명은 그 질문 안에 둔다: 맥락은 `question` 칸, 선택지별 흐름 그림(ASCII)·바뀌는 줄 표는 그 선택지의 `preview`(여러 줄 고정폭, 커서를 두면 옆에 보임). `preview` 는 단일 선택에서만 되므로 multiSelect(머지 묶음)는 `description` 에 쓴다. 본문에는 모든 질문에 공통인 그림과, 길어서 칸에 안 들어가는 원문(이슈 코멘트 초안 전문)만 둔다. 본문에 질문별 설명을 쌓으면 탭마다 스크롤해야 한다.
  - 답을 받은 같은 턴에 실행까지 한다: 승인된 머지는 `--match-head-commit` 으로 직접, 결정은 해당 worker 에 SendMessage 로 중계, 새 작업은 새 worker 를 띄운다. 다음 턴으로 미루지 않는다.
  - 답이 결정이 아니라 질문이면(Other 에 "이거 X 말씀하시는 거죠?") 그 항목은 결정으로 치지 않는다. 답한 뒤 그 항목만 다시 묻고, 나머지 답한 항목은 실행한다.
  - 대화상자가 거절(취소)되면 멈추고 기다린다. 사용자가 "실수로 닫았다" 고 하면 같은 질문을 그대로 다시 띄운다.
- After the user approves a worker's permission-prone command, the orchestrator relays the approval and watches the worker pane (`~/.dotfiles/tmux/peek-claude-pane.sh <pane>`, not `tmux capture-pane`: a folded worker shows only one line, so peek unfolds it for a second, captures, and folds it back). If a permission prompt appears and its full command matches what the user approved, the orchestrator answers it with `tmux send-keys -t <pane> 1` (Yes). It never picks "don't ask again", and it does not press when the command differs or is cut off; it shows the prompt to the user instead. If the classifier refuses outright (no prompt), the orchestrator shows the user the command the worker reported and the settings permission rule that would allow it, and asks whether to add the rule (global CLAUDE.md: never hand `!` commands to the user).
- When a worker reports the issue number it took (new issue or `/work #N`), the orchestrator renames that session to `<group>-worker-<N>-<topic>`. Check with `~/.dotfiles/tmux/claude-pane-ready.sh <pane>` (exit 0 = `@claude_state` idle and the input box empty; it reads only the input line, ignoring dim auto-suggestions, so the screen does not land in context), then `tmux send-keys -t <pane> -l '/rename <name>'` and Enter. If it prints `not ready`, wait for an idle notice (`notify_when_idle`) instead; never press Esc to clear it, since that can interrupt the running turn.
- 조사는 맡긴다: orchestrator 는 코드 읽기·로그·데이터 조사·측정·웹 검색을 직접 하지 않는다. 직접 하는 것은 몇 번의 조회로 끝나는 확인(상태 파일, PR·CI 상태, `claude-pane-ready.sh`)과 설정 파일 수정(공통 규칙)뿐이다
  - 어디에 맡길지는 orchestrator context 에 들어오는 양으로 고른다. worker 는 결과가 worker context 에 남고 orchestrator 에는 `결정 필요`·완료 메시지만 온다. Agent 는 보고 전체가 orchestrator context 에 들어온다

    | 맡길 곳          | 기준 (하나라도 맞으면)                                                                                                                               |
    | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
    | 새 worker        | 사용자 결정이 끼어든다 · 결과로 이어지는 작업이 있다 · 도구 호출이 10회를 넘을 것 같다 · PR 이 둘 이상이다 · 사용자가 진행을 보고 싶어 한다          |
    | Agent (subagent) | 위에 하나도 맞지 않는 짧은 일: 읽기만 하는 한 번의 질문(답이 지금 물을 결정의 맥락으로 쓰이고 결론이 15줄 안), 또는 파일을 바꿔도 PR 1개로 끝나는 일 |

  - 파일을 바꾸는 일을 Agent 에 맡길 때는 `isolation: "worktree"` 를 주고, 보고를 받으면 `git diff` 로 실제 변경을 확인한 뒤 PR·머지는 orchestrator 가 한다. worker 는 시작만으로 context 5만 token 을 쓰고 완료 보고가 orchestrator 를 한 번 더 깨운다
  - Agent prompt 에는 "결론과 근거(파일:줄·명령 결과 한 줄)만 15줄 이내, 원본 출력 붙이지 말 것" 을 적는다. 보고가 길어지면 그 조사는 worker 감이었다
  - 애매하면 worker. Agent 보고는 compaction 전까지 orchestrator context 에 남아 이후 모든 턴에 다시 읽힌다
  - 이유: orchestrator context 는 worker 메시지가 올 때마다 전체가 다시 읽힌다. 조사 출력이 쌓이면 모든 worker 보고가 비싸진다
- The orchestrator manages sessions, decisions, blockers, merges, and deploy coordination. It does not run deploys itself: when the user approves a deploy, it relays "the user approved" to the worker that owns the issue, and that worker deploys and reports. A design session reflects approved decisions in docs/issues and reports briefly; it does not ask the user directly.
- orchestrator 가 승인된 머지를 직접 했고 그 worker 에 남은 일이 정리뿐이면(이슈 닫기·코멘트가 없음), worker 에 넘기지 않고 orchestrator 가 한 명령으로 정리한 뒤 아래처럼 닫는다. 머지 중계와 "정리 끝" 보고 왕복이 worker 턴을 두 번 깨운다.
  - `git -C <repo> fetch -q origin <base> && git -C <repo> merge-base --is-ancestor <branch> origin/<base> && test -z "$(git -C <worktree> status --porcelain)" && git -C <repo> worktree remove <worktree> && git -C <repo> branch -d <branch>`
  - 검사가 하나라도 실패하면(squash 머지라 조상이 아님, worktree 에 미커밋 변경) 지우지 않고 worker 에 정리를 넘긴다. orchestrator 는 worker 의 로컬 상태를 모르기 때문이다
- 여러 세션(다른 orchestrator 포함)에 같은 소식을 알릴 때는 한 작업이 끝난 뒤 한 통으로 묶는다. PR 마다 따로 보내지 않는다. 받는 세션은 한 통마다 자기 context 전체를 다시 읽는다.
- worker 화면은 idle 확인용으로 읽지 않는다. 화면 내용이 필요할 때(권한 프롬프트의 명령 확인, 막힘 원인)만 `peek-claude-pane.sh <pane> | tail -n 20` 처럼 필요한 줄만 읽는다.
- skill·규칙을 고쳐 실행 중인 worker 에 알릴 때는 바뀐 단계가 아직 남은 worker 에만 보낸다 (예: 머지 단계 변경은 머지 전 worker 에만). 이미 지난 worker 는 다음 작업에서 새 글을 읽는다. 알림마다 받는 worker 가 컨텍스트 전체를 다시 읽는다.
- When a worker has nothing left to do (its PRs merged and cleaned up, its issue closed or left open only to wait on an outside answer), the orchestrator closes that session without asking: have the worker close its issue first if it is done, then close its pane with `tmux kill-pane -t <pane>` without reading its screen first (the exit-guard below checks `@claude_state`; SessionEnd hooks still run; unlike `/exit` it does not depend on an empty input box, but it cuts a running turn, so the hook below only allows an idle worker). Record the closed session in the status file. Do it in the same turn as the report. Two global hooks back this up: a Stop hook (`orchestrator-close-check.py`) blocks an orchestrator's turn end while a worker that sent `#N 닫음 · 남은 일 없음` (or `#N 정리 끝 · 남은 일 없음` when it only cleaned up a PR without an issue to close) still has a live pane, so workers must use that exact report line; a PreToolUse hook (`orchestrator-exit-guard.py`) refuses `tmux kill-pane` and `tmux send-keys … /exit` unless `-t` names a pane whose title contains `-worker-`, and refuses `kill-pane` while that pane's `@claude_state` is busy or waiting.
- The orchestrator keeps its working state in a status file, not in the conversation, so the context can be compacted without losing anything. Location: the project's `.claude/references/orchestrator.md` names it; default `.claude/plans/<group>-status.md`.
  - Contents, current state only (no history): each worker → issue, PR, state, what it is waiting on; pending `결정 필요` with who is waiting; decisions made since the last design hand-off; 자체 결정 누계와 그중 사용자가 뒤집은 수 (결정 규칙표를 넓힐지 좁힐지의 근거); next checks. Keep it under ~150 lines; move finished items out.
  - Update it right after each event (worker report, decision, merge, session start/stop), before replying.
  - worker 진척은 worker 가 자기 pane 의 `@claude_progress` 에 적고, orchestrator statusline(`~/.claude/hooks/statusline.sh`)이 세션마다 진척 막대 한 줄로 그린다. orchestrator 는 옮겨 적지 않는다. 진척 막대 없이 이름만 그려지는 worker 가 계획을 세웠으면 `진척 요청` 을 SendMessage 로 한 번 보내고, worker 는 pane 옵션을 적은 뒤 `진척:` 한 줄로만 답한다. 진척 없는 줄은 statusline 이 대신 hook 의 활동 이름(`@claude_activity`)을 붙인다. statusline 은 orchestrator 턴에만 다시 그려지므로 주기 실행 없이 이 값과 맞는다.
  - At session start and after any compaction, read the status file first and trust it over your memory of the conversation.
