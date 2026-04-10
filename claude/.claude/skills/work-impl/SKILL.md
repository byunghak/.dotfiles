---
name: work-impl
model: opus
allowed-tools: Read, Grep, Glob, Agent, AskUserQuestion, Bash(git:*), TaskCreate, TaskGet, TaskUpdate, SendMessage
description: work-pre 계획을 기반으로 병렬 에이전트 팀을 구성하여 구현 실행. `/work` 파이프라인의 Stage 2 로 내부 호출되며, 단독 사용도 가능. Use when 독립 작업 2개 이상을 병렬로 처리하거나, plan 기반 구현을 체계적으로 실행할 때.
---

# Work Impl — 구현 실행

work-pre에서 수립한 계획을 기반으로 **에이전트 팀을 구성**하여 병렬 구현을 실행합니다.

> **단순 구현**(파일 1-2개, 순차 작업)은 이 skill 없이 직접 구현하세요.
> **병렬 구현**(독립 작업 2개 이상)일 때 사용합니다.

## 전제조건

- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`를 `1`로 설정해야 동작
- 설정 위치: settings.json의 `env` 또는 셸 환경변수

---

## Step 1: 계획 확인

다음 순서로 계획 문서를 탐색한다:

1. `.claude/plans/*.md` — work-brainstorming에서 생성된 spec+plan 문서 (최신 파일 우선)
2. `prompt_plan.md`, `spec.md` — 기존 방식
3. 직전 `/work-pre` 결과 — 대화 컨텍스트에 있는 경우

계획 문서를 찾으면:

1. 변경 필요 파일 목록 생성
2. 파일별 도메인 분류
3. 작업 복잡도 추정

계획이 없으면 안내 후 중단:

```
⚠️ 실행할 계획이 없습니다.
/work-brainstorming "아이디어"로 요구사항을 정리하거나,
/work-pre "작업 설명"으로 분석 + 계획을 수립하세요.
```

## Step 2: 팀 구성

최대 팀원 수: Lead 1 + Teammates 3 (총 4명)

| 작업 규모          | 팀원 수 | 구성                             |
| ------------------ | ------- | -------------------------------- |
| 소 (파일 1-3개)    | 1-2명   | 구현1 (+테스트1)                 |
| 중 (파일 4-8개)    | 2-3명   | 구현1-2 + 테스트1                |
| 대 (파일 9개 이상) | 3명     | 구현2 + 테스트1 또는 패턴별 분리 |

### 역할 템플릿

**풀스택 기능 구현:**

| 역할         | subagent_type   | 담당              |
| ------------ | --------------- | ----------------- |
| Frontend Dev | general-purpose | UI 구현, 컴포넌트 |
| Backend Dev  | general-purpose | API, DB, 로직     |
| QA Engineer  | general-purpose | 테스트, E2E       |

**리팩토링:**

| 역할        | subagent_type   | 담당           |
| ----------- | --------------- | -------------- |
| Analyzer    | Explore         | 코드 분석/계획 |
| Implementer | general-purpose | 리팩토링 실행  |
| Verifier    | general-purpose | 테스트/검증    |

**버그 조사:**

| 역할           | subagent_type   | 담당           |
| -------------- | --------------- | -------------- |
| Investigator 1 | Explore         | 코드 분석      |
| Investigator 2 | Explore         | 로그/환경 분석 |
| Fixer          | general-purpose | 수정 구현      |

## Step 3: 파일 소유권 분리 (CRITICAL)

같은 파일을 2명이 편집하면 덮어쓰기가 발생한다.
반드시 팀원별로 파일 소유권을 분리한다.

```

파일 소유권 결정 로직:

1. 변경 예상 파일 목록 생성
2. 파일별 모듈/도메인 분류
3. 도메인 단위로 팀원 배정
4. 공유 파일(types, config)은 한 팀원에게 독점 배정

```

## Step 4: Task 생성 및 배정

팀원당 5-6개 Task를 배정한다.

| Task 크기 | 판단 기준                           | 설명                    |
| --------- | ----------------------------------- | ----------------------- |
| 너무 작음 | 조율 오버헤드 > 이점                | 하나로 합치기           |
| 적절함    | 명확한 결과물이 있는 자체 포함 단위 | 함수, 테스트 파일, 검토 |
| 너무 큼   | 체크인 없이 오래 작동               | 더 작게 분할            |

의존성: TaskCreate에서 `addBlockedBy` 필드로 설정.

### 팀 구성 승인

AskUserQuestion으로 팀 구성을 보여주고 확인을 받는다:

```
팀원 [N]명, Task [N]개 구성:

[역할1]: [담당 파일/영역] (Task N개)
[역할2]: [담당 파일/영역] (Task N개)
...

진행할까요?
```

- **승인** → Step 5로 진행
- **수정 요청** → 팀 구성/Task 조정 후 재확인

## Step 5: Context Inheritance (CRITICAL)

팀원은 프로젝트 컨텍스트(CLAUDE.md, MCP servers, skills)를 자동 로드하지만,
**리더의 대화 기록은 상속하지 않는다.**

팀원 생성 프롬프트에 반드시 포함:

- 작업 목적과 배경
- 관련 파일 경로
- 기대하는 결과물
- 주의사항/제약사항

## Step 6: 실행

```

1. 팀원 spawn (SendMessage)
2. 각 팀원이 자신의 Task 수행
3. 리더는 조율만 수행 (직접 구현 금지)
4. 작업을 마친 팀원은 다음 미할당, 차단되지 않은 작업을 자체 청구
5. 팀원 완료 시 SendMessage로 보고

```

## Step 7: 결과 집계

```

═══════════════════════════════════════════
Work — 구현 결과
═══════════════════════════════════════════

팀원: [N]명
총 Task: [N]개
완료: [N]개 | 실패: [N]개

팀원별 결과:
[역할 1]: [완료]/[배정] - [상태]
[역할 2]: [완료]/[배정] - [상태]

다음 단계: /work-post
═══════════════════════════════════════════

```

## Step 8: Post-Completion Review (CRITICAL)

**워커는 Skill tool과 sub-agent 스폰이 불가능하므로, 리뷰는 반드시 리더(메인 세션)가 수행한다.**

1. 모든 팀원 종료 (shutdown_request)
2. `/work-post` 실행 안내
3. 팀원 완료 → 즉시 커밋은 **금지**. 반드시 review 단계를 거쳐야 한다.

---

## Error Recovery

### 팀원 무응답

1. SendMessage로 상태 확인 (1회)
2. 5분 초과 시 Task 재배정
3. 필요시 새 팀원 생성

### 파일 충돌 감지

1. 리더가 git status로 충돌 감지
2. 한 팀원에게 해당 파일 소유권 위임
3. 다른 팀원은 대기 후 진행

### Task 의존성 데드락

1. 순환 의존성 감지
2. 의존성 체인에서 가장 독립적인 Task 우선 실행
3. 리더가 수동으로 의존성 해소

---

## 다음 단계

| 구현 완료 후 | 커맨드        |
| :----------- | :------------ |
| 종합 점검    | `/work-post`  |
| 이슈 수정    | `/work-fix`   |
| 코드 정리    | `/work-clean` |
