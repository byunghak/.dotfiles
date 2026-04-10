# Stage: Impl — 병렬 구현 실행

각 sub-task 파이프라인의 **두 번째 단계**. Stage Pre 에서 수립한 계획을 기반으로 **에이전트 팀**을 구성하여 병렬 구현을 실행한다.

## 전제조건

- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 필요
- 설정 없으면: halt 하고 사용자에게 환경변수 설정 요청

## Step 1: 계획 확인

Stage Pre 에서 생성된 plan (sub-task 문서의 `## Plan` 섹션) 을 기반으로:

1. 변경 필요 파일 목록 생성
2. 파일별 도메인 분류
3. 작업 복잡도 추정

단순 구현(파일 1-2개)이면 팀 구성 없이 리더가 직접 구현해도 된다.

## Step 2: 팀 구성

최대 팀원 수: **Lead 1 + Teammates 3** (총 4명)

| 작업 규모          | 팀원 수 | 구성                             |
| ------------------ | ------- | -------------------------------- |
| 소 (파일 1-3개)    | 1-2명   | 구현1 (+테스트1)                 |
| 중 (파일 4-8개)    | 2-3명   | 구현1-2 + 테스트1                |
| 대 (파일 9개 이상) | 3명     | 구현2 + 테스트1 또는 패턴별 분리 |

### 역할 템플릿

**풀스택 기능 구현**:

- Frontend Dev (general-purpose) — UI, 컴포넌트
- Backend Dev (general-purpose) — API, DB, 로직
- QA Engineer (general-purpose) — 테스트, E2E

**리팩토링**:

- Analyzer (Explore) — 코드 분석/계획
- Implementer (general-purpose) — 리팩토링 실행
- Verifier (general-purpose) — 테스트/검증

**버그 조사**:

- Investigator 1 (Explore) — 코드 분석
- Investigator 2 (Explore) — 로그/환경 분석
- Fixer (general-purpose) — 수정 구현

## Step 3: 파일 소유권 분리 (CRITICAL)

**같은 파일을 2명이 편집하면 덮어쓰기가 발생한다.** 반드시 팀원별로 파일 소유권을 분리:

1. 변경 예상 파일 목록 생성
2. 파일별 모듈/도메인 분류
3. 도메인 단위로 팀원 배정
4. 공유 파일(types, config)은 한 팀원에게 **독점 배정**

## Step 4: Task 생성 및 배정

팀원당 5-6개 Task 배정 (TaskCreate).

| Task 크기 | 판단 기준                           |
| --------- | ----------------------------------- |
| 너무 작음 | 조율 오버헤드 > 이점 → 하나로 합침  |
| 적절함    | 명확한 결과물이 있는 자체 포함 단위 |
| 너무 큼   | 체크인 없이 오래 작동 → 더 분할     |

의존성: TaskCreate 의 `addBlockedBy` 필드로 설정.

## Step 5: Context Inheritance (CRITICAL)

팀원은 프로젝트 컨텍스트(CLAUDE.md, MCP, skills)를 자동 로드하지만, **리더의 대화 기록은 상속하지 않는다.**

팀원 생성 프롬프트에 반드시 포함:

- 작업 목적과 배경
- 관련 파일 경로
- 기대하는 결과물
- 주의사항/제약사항
- 선행 task(의존)의 산출물 위치/내용

## Step 6: 실행

1. 팀원 spawn (SendMessage)
2. 각 팀원이 자신의 Task 수행
3. 리더는 조율만 수행 (**직접 구현 금지**)
4. 작업 마친 팀원은 다음 미할당·차단되지 않은 작업을 자체 청구
5. 팀원 완료 시 SendMessage 로 보고

## Step 7: 종료

1. 모든 팀원 종료 (shutdown_request)
2. 결과 집계 (완료/실패 Task 수, 팀원별 상태)
3. `git status --short` 로 변경사항 확인

## Error Recovery

### 팀원 무응답

1. SendMessage 로 상태 확인 (1회)
2. 5분 초과 시 Task 재배정
3. 필요 시 새 팀원 생성

### 파일 충돌 감지

1. 리더가 `git status` 로 충돌 감지
2. 한 팀원에게 해당 파일 소유권 위임
3. 다른 팀원은 대기 후 진행

### Task 의존성 데드락

1. 순환 의존성 감지
2. 독립적인 Task 우선 실행
3. 리더가 수동으로 의존성 해소

## 성공/실패 기준

- **성공**: 모든 Task `completed`, `git status` 에 변경사항 존재
- **실패**: Task 실패율 > 0, 또는 복구 불가 에러 → 전체 halt (retry 하지 않음)

## 자동 모드 제약

- **팀 구성 승인 AskUserQuestion 생략** — plan 기반 자동 구성으로 바로 진행
- 대신 Step 2-4 결과를 리포트에 "팀 구성: ..." 로 기록
