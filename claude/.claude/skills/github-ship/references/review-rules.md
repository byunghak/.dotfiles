# Code Review Rules

## 리뷰 대상 판단

리뷰를 **건너뛰는** 조건 (모두 해당 시 Phase 4 전체 skip):

- 설정 파일만 변경 (`.json`, `.yaml`, `.toml`, `.ini`, `.env.example`)
- 문서만 변경 (`.md`, `LICENSE`, `CHANGELOG`)
- Skill/agent 정의만 변경 (`SKILL.md`, `.claude/agents/*.md`)
- lock 파일만 변경 (`package-lock.json`, `Cargo.lock`, `poetry.lock`)
- 단일 파일 5줄 이하 수정 (typo, import 정리 수준)

## 리뷰 강도 결정

| 조건                            | 강도         | Agent                           |
| ------------------------------- | ------------ | ------------------------------- |
| 변경 파일 ≤ 3개, 총 50줄 미만   | **Lite**     | #1 (CLAUDE.md 준수) + #2 (버그) |
| 변경 파일 ≤ 5개, 총 200줄 미만  | **Standard** | #1 + #2 + #3 (설계)             |
| 변경 파일 > 5개 또는 200줄 이상 | **Full**     | #1 ~ #5 전체                    |

## Agent 구성

Agent tool (subagent_type: code-reviewer)로 병렬 호출.

각 agent에게 PR diff, CLAUDE.md 규칙, 관련 컨텍스트를 전달하되 집중 영역 분리:

| Agent | 집중 영역                                    |
| ----- | -------------------------------------------- |
| #1    | **CLAUDE.md 준수** — 프로젝트 규칙 위반      |
| #2    | **버그 탐지** — 로직 오류, edge case, null   |
| #3    | **설계 분석** — 아키텍처, 레이어, 의존성     |
| #4    | **보안/성능** — injection, 메모리, N+1       |
| #5    | **테스트 커버리지** — 누락, edge case 미검증 |

각 agent 프롬프트:

```
당신은 code-reviewer 에이전트입니다.

PR diff:
[diff]

CLAUDE.md 규칙:
[규칙 목록]

집중 영역: [위 테이블에서 해당 영역]

발견한 이슈를 아래 형식으로 반환:
- [severity: critical/major/minor] <이슈 설명>
  파일: <path>:<line>
  근거: <왜 이것이 문제인가>
  제안: <수정 방향>
```

## 이슈 필터링

신뢰도 점수(0-100):

| 점수   | 의미                                      |
| ------ | ----------------------------------------- |
| 0-25   | False positive, 기존 이슈, lint가 잡을 것 |
| 25-50  | 가능성 있으나 사소                        |
| 50-75  | 실제 이슈이나 영향 낮음                   |
| 75-100 | 검증된 실제 이슈, 기능에 직접 영향        |

**75 이상만** 최종 보고. False positive 제외:

- PR에서 수정하지 않은 라인의 기존 문제
- Lint/타입체커/CI가 잡을 이슈
- 의도적 변경, 스타일 nitpick

## 이슈 처리

이슈가 있으면 각 이슈에 대해 AskUserQuestion:

- **수정** — 코드 수정 후 추가 커밋, push
- **Skip** — 무시하고 진행

수정 후 push가 발생하면 리뷰를 **한 번만** 재실행 (최대 2회, 무한 루프 방지).
