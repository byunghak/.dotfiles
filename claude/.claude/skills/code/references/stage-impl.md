# Stage: Impl — TDD 기반 구현 실행

각 sub-task 파이프라인의 **두 번째 단계**. Stage Pre 에서 수립한 계획을 기반으로 **TDD 사이클(Red → Green → Refactor)** 로 구현한다.

## 전제조건

- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 필요
- 설정 없으면: halt 하고 사용자에게 환경변수 설정 요청

## TDD 원칙

1. **Red**: 실패하는 테스트를 먼저 작성
2. **Green**: 테스트를 통과하는 최소한의 코드 구현
3. **Refactor**: 테스트 통과를 유지하면서 코드 정리

> code-style.md 의 Test Conventions (프레임워크, 파일 배치, 구조 패턴, fixture 방식, mock 정책) 를 준수.

---

## Step 1: 계획 확인 + 테스트 전략 수립

Stage Pre 에서 생성된 plan (sub-task 문서의 `## Plan` 섹션) 을 기반으로:

1. 변경 필요 파일 목록 생성
2. 파일별 도메인 분류
3. **테스트 대상 식별**: 각 변경에 대해 어떤 테스트가 필요한지 결정
   - 단위 테스트: 개별 함수/메서드 동작 검증
   - 통합 테스트: 모듈 간 연동 검증 (해당 시)
4. **테스트 파일 위치 결정**: code-style.md 의 파일 배치 규칙 따름

단순 구현(파일 1-2개)이면 팀 구성 없이 리더가 직접 TDD 사이클 수행.

## Step 2: 팀 구성

최대 팀원 수: **Lead 1 + Teammates 3** (총 4명)

| 작업 규모          | 팀원 수 | 구성                     |
| ------------------ | ------- | ------------------------ |
| 소 (파일 1-3개)    | 1-2명   | TDD Dev 1 (+TDD Dev 2)   |
| 중 (파일 4-8개)    | 2-3명   | TDD Dev 1-2 + Integrator |
| 대 (파일 9개 이상) | 3명     | TDD Dev 2 + Integrator   |

### 역할 템플릿

**TDD Dev** (general-purpose):

- Red: 실패 테스트 작성 → Green: 구현 → Refactor
- 자신의 소유 파일에 대해 전체 TDD 사이클 수행

**Integrator** (general-purpose):

- 통합 테스트 작성 + 모듈 간 연동 검증
- 공유 타입/인터페이스 정의 담당

## Step 3: 파일 소유권 분리 (CRITICAL)

**같은 파일을 2명이 편집하면 덮어쓰기가 발생한다.** 반드시 팀원별로 파일 소유권을 분리:

1. 변경 예상 파일 목록 생성 (**테스트 파일 포함**)
2. 파일별 모듈/도메인 분류
3. 도메인 단위로 팀원 배정 (구현 파일 + 해당 테스트 파일을 같은 팀원에게)
4. 공유 파일(types, config)은 한 팀원에게 **독점 배정**

## Step 4: Task 생성 및 배정

각 팀원의 Task를 **TDD 사이클 단위**로 생성 (TaskCreate):

```
Task 1: [Red] UserService 단위 테스트 작성
Task 2: [Green] UserService 구현
Task 3: [Red] UserRepository 통합 테스트 작성
Task 4: [Green] UserRepository 구현
Task 5: [Refactor] 코드 정리 + 전체 테스트 통과 확인
```

의존성: Red → Green 은 순차, 독립 모듈의 Red 끼리는 병렬 가능.

## Step 5: Context Inheritance (CRITICAL)

팀원은 프로젝트 컨텍스트(CLAUDE.md, MCP, skills)를 자동 로드하지만, **리더의 대화 기록은 상속하지 않는다.**

팀원 생성 프롬프트에 반드시 포함:

- 작업 목적과 배경
- **code-style.md 의 Test Conventions 섹션** (프레임워크, 구조 패턴, mock 정책)
- 관련 파일 경로
- 기대하는 결과물 (테스트 파일 + 구현 파일)
- 주의사항/제약사항
- 선행 task(의존)의 산출물 위치/내용

## Step 6: TDD 실행

### 리더가 직접 수행하는 경우 (소규모)

```
loop per feature unit:
  1. [Red] 테스트 작성 → 실행 → 실패 확인
  2. [Green] 최소 구현 → 테스트 실행 → 통과 확인
  3. [Refactor] 코드 정리 → 테스트 재실행 → 통과 유지 확인
```

### 팀 실행인 경우

1. 팀원 spawn (SendMessage)
2. 각 팀원이 자신의 TDD Task 수행
3. 리더는 조율만 수행 (**직접 구현 금지**)
4. 작업 마친 팀원은 다음 미할당·차단되지 않은 작업을 자체 청구
5. 팀원 완료 시 SendMessage 로 보고

### TDD 사이클 검증

각 팀원의 Green 단계 완료 시 리더가 확인:

```bash
# 테스트 실행 명령 (프로젝트 타입별)
npm test / pytest / go test ./... / cargo test
```

테스트 실패 시 해당 팀원에게 수정 지시 (Green 재시도).

## Step 7: 종료

1. 모든 팀원 종료 (shutdown_request)
2. **전체 테스트 스위트 실행** — 개별 통과와 별개로 전체 통합 확인
3. 결과 집계 (완료/실패 Task 수, 테스트 통과율)
4. `git status --short` 로 변경사항 확인

## Error Recovery

### 팀원 무응답

1. SendMessage 로 상태 확인 (1회)
2. 5분 초과 시 Task 재배정
3. 필요 시 새 팀원 생성

### 파일 충돌 감지

1. 리더가 `git status` 로 충돌 감지
2. 한 팀원에게 해당 파일 소유권 위임
3. 다른 팀원은 대기 후 진행

### 테스트 실패 복구

1. Green 단계에서 테스트 실패 → 해당 팀원이 수정 (최대 3회)
2. 3회 초과 시 리더에게 에스컬레이션
3. 리더가 원인 분석 후 plan 수정 또는 halt

### Task 의존성 데드락

1. 순환 의존성 감지
2. 독립적인 Task 우선 실행
3. 리더가 수동으로 의존성 해소

## 성공/실패 기준

- **성공**: 모든 Task `completed`, 전체 테스트 스위트 통과, `git status` 에 변경사항 존재
- **실패**: 테스트 실패 미해결, 또는 복구 불가 에러 → 전체 halt (retry 하지 않음)

## 자동 모드 제약

- **팀 구성 승인 AskUserQuestion 생략** — plan 기반 자동 구성으로 바로 진행
- 대신 Step 2-4 결과를 리포트에 "팀 구성: ..." 로 기록
