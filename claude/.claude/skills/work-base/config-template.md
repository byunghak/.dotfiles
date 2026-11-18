---
name: work
description: <프로젝트> 이슈를 분석·진행 상황 파악 → Brainstorm(문제 정의·현 시스템 파악) → PR 분리 → Plan → (PR마다) TDD Code → 리뷰 → Ship 판단 → Ship 으로 진행한다. 이슈 링크·번호, 작업 설명, 또는 기존 plan 디렉토리를 받는다.
disable-model-invocation: true
argument-hint: "<이슈 URL | #이슈 | 작업 설명 | .claude/plans/<dir>/>"
---

# work

<프로젝트> 전용 개발 흐름. 공통 흐름은 `~/.claude/skills/work-base/` 이고, 이 파일은 프로젝트 값과 추가 규칙만 담는다.

## 설정

| 칸                | 값                                     | 뜻                                                               |
| ----------------- | -------------------------------------- | ---------------------------------------------------------------- |
| `<BASE>`          | `main`                                 | 기준 브랜치. 활성 브랜치가 바뀌면 이 칸만 고친다                 |
| `<통합 브랜치>`   | `없음`                                 | 리뷰 통과 뒤 묻지 않고 머지하는 기능 묶음 브랜치 패턴            |
| `<확인 base>`     | `main`                                 | 머지 전에 사용자 확인을 받는 base                                |
| `<repo>`          | `<owner>/<repo>`                       | 이슈·PR 리포 (여럿이면 찾는 순서대로)                            |
| `<worktree 루트>` | `../<repo>.worktrees`                  | PR·lane worktree 를 만드는 곳                                    |
| `<planner>`       | `<agent>`                              | Step 4 Plan 작성 agent                                           |
| `<plan-reviewer>` | `<agent>`                              | Step 4 Plan 검토 agent                                           |
| `<implementer>`   | `<agent>`                              | Step 5 lane 구현 agent                                           |
| `<계약>`          | `wire·스키마 마이그레이션`             | 되돌리기 어려워 진행 중에 묻는 계약 변경 종류                    |
| `<커밋 제외>`     | `.claude/`                             | 커밋하지 않는 경로                                               |
| `<규칙 파일>`     | `없음`                                 | planner·implementer·리뷰어 프롬프트에 경로로 넘길 코드 규칙 파일 |
| `<controller>`    | `ListAgents` 의 `<group>-orchestrator` | Step 0 PLAN.md `- controller:` 를 찾는 규칙                      |

!`cat ~/.claude/skills/work-base/core.md`

- 위 줄이 실행 안내(`run this first`)로 바뀌어 있으면 그 명령을 먼저 실행해 공통 흐름을 읽는다. compaction 뒤에도 같다

## 이 프로젝트 추가 규칙

- <공통 규칙에 더하거나 바꾸는 줄>
