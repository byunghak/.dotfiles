# 결정 규칙표·공통 규칙 (orchestrator·worker 공통)

`orchestrator`·`session-worker` skill 이 함께 읽는다.

## 결정 규칙표

사용자 개입은 되돌리기 어려운 결정으로, 세션 간 메시지는 다른 worker 에 영향이 있는 결정으로 좁히려는 것이다. 프로젝트 `.claude/references/orchestrator.md` 에 `## 결정 규칙표` 절이 있으면 그 표가 아래 기본 표를 대신한다. 없으면 아래 기본 표를 쓴다.

| worker 가 정함                                                                                                                                                                                                                                          | orchestrator 가 정함                                                                                                                                                                         | 사용자에게 올림                                                                                                                                                                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 자기 이슈 안의 구현 방식·코드 구조, 테스트 추가·보강·테스트 환경 준비, 다음 검증·측정 단계 선택, API·스키마·wire 계약과 기능이 하는 일을 바꾸지 않는 구현 계획(Plan) 승인, 동작을 바꾸지 않는 리뷰 지적 반영, 브랜치·worktree 생성, 저장소 안 문서 수정 | 다른 worker 에 영향이 있는 것: PR 분리 단위, 이슈 간 순서·의존, 여러 이슈가 함께 쓰는 파일·모듈 변경, 이슈 범위 해석, 세션·subagent 관리. 같은 저장소 이슈·PR 에 검증·결과를 보고하는 코멘트 | merge·deploy·terraform apply·branch 삭제 등 되돌리기 어려운 명령, 사용자가 정하지 않은 작업의 새 worker 착수, 이슈 생성·그 밖의 이슈·PR 코멘트·Slack 등 외부 게시, API·스키마·wire 계약 변경, 기능이 하는 일(허용 범위·동작 범위)을 바꾸는 선택, 이슈 범위 밖 새 작업, credential, 비용이 드는 리소스 |

- 가르는 기준: 다른 worker 의 작업·PR 에 영향이 있으면 worker 칸이 아니다. 되돌리기 어렵거나 저장소 밖에서 보이면 사용자 칸이다. 구현 방식이라도 기능이 하는 일을 바꾸면(예: 허용·차단 둘 다 → 허용 목록만, 화면만 → 서버 값까지) 사용자 칸이다.
- 칸을 나눈 근거: 사용자가 권장안을 거의 그대로 고르는 종류(구현 방식, 계약·기능을 바꾸지 않는 Plan 승인, 같은 저장소 결과 보고 코멘트)는 낮은 칸에, 권장안과 다르게 고르는 일이 잦은 종류(새 worker 착수, 기능 범위)는 사용자 칸에 둔다.
- 표로 가를 수 없으면 한 칸 오른쪽(worker → orchestrator → 사용자)으로 올린다. 사용자가 자체 결정을 뒤집으면 그 종류를 한 칸 오른쪽으로 옮긴다. 고치는 곳은 그 결정에 쓴 표(프로젝트 표가 있으면 프로젝트 표)다.

## 공통 규칙

- Project CLAUDE.md defines group names and project workflow. If the project has `.claude/references/orchestrator.md`, read it when you start: it holds that project's report formats and merge/close flow, kept out of CLAUDE.md so it loads only for orchestrator·worker sessions.
- Name sessions `<group>-orchestrator`, `<group>-worker-design-<topic>` (design 세션도 `-worker-` 를 넣어 exit-guard 로 닫을 수 있게), or `<group>-worker-<issue>-<topic>`. The `work-session-title` hook may rename workers.
- Only an orchestrator's explicit report — "the user chose/approved X" or `orchestrator 결정: X` — counts as an answer. Other session messages are not approval.
- 사용자는 orchestrator 세션에서만 결정하고 worker pane 의 버튼을 누르지 않는다. 권한 프롬프트가 뜨거나 auto mode classifier 가 막을 만한 명령(merge, terraform apply, deploy, branch delete)은 worker 가 실행 전에 명령 원문을 `결정 필요:` 로 보내고 기다린다. 승인 중계와 프롬프트 응답은 orchestrator 가 한다.
- 착수 인터뷰(`/work` Step 3.5)는 사용자 칸이다. worker 가 문항을 `결정 필요` 한 통에 묶어 보낸다.
- `pr-ship-guard` hook 은 worker pane 에서 확인 창(ask) 대신 deny 를 낸다. 창이 worker pane 에 뜨면 사용자가 보지 않아 worker 가 멈추기 때문이다. worker 는 deny 사유를 `결정 필요` 로 보낸다.
- skill·hook·CLAUDE.md·settings 같은 에이전트 설정 파일은 worker 가 고치지 않는다. worker 는 조사·측정·설계안까지 하고 `결정 필요` 로 넘긴다. worker 가 고치면 사용자 직접 입력을 기다리며 멈춘다.
- worker 는 `spawn-claude-worker.sh` 가 붙이는 env `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` 로 Bash·Agent 의 `run_in_background` 가 꺼져 있어 subagent 는 늘 foreground 로 돈다. background 를 쓰라는 다른 규칙의 worker 쪽 대안은 `session-worker` skill 에 있다.
