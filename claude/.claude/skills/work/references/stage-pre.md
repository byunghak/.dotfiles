# Stage: Pre — 분석 + 계획

각 sub-task 파이프라인의 **첫 단계**. architect + planner 에이전트를 순차 호출하여 구현 전 분석과 실행 계획을 수립한다.

## 입력

- sub-task 문서 경로 (`_dag.yaml` 의 `tasks[].file`, 예: `NN-<task>.md`)
- 상위 `DESIGN.md` (sub-task 문서가 참조)

## Step 1: 컨텍스트 수집

1. 프로젝트 타입 감지: `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`
2. `CLAUDE.md` 읽기 (있으면) — 프로젝트 규칙/패턴 파악
3. `git diff --name-only` — 현재 작업 상태 파악
4. sub-task 문서 Read — 목표/범위/제외/완료 기준 숙지
5. `DESIGN.md` 링크 따라 상위 설계 파악

## Step 2: architect 에이전트 — 구조 분석

Agent tool (subagent_type: architect):

```
당신은 architect 에이전트입니다.

프로젝트 타입: [감지된 타입]
분석 요청: [sub-task 문서 전문]
상위 설계: [DESIGN.md 요약]

수행할 분석:
1. 구조 분석 — 변경 대상의 현재 구조와 의존 관계
2. 의존성 분석 — 순환 참조, 버전 충돌
3. 리스크 식별 — 깨질 수 있는 곳, 하위 호환성, 외부 계약

핵심 원칙:
- READ-ONLY: 코드를 읽기만 하고 절대 수정하지 않음
- Evidence-based: 모든 발견에 file:line 참조 필수
- Trade-offs 명시, Concrete 권장사항

출력 형식:
  ## Summary — 1-2문장 요약
  ## Structure — 현재 구조, 의존 관계
  ## Impact — 영향받는 파일/모듈, 리스크
  ## Dependencies — 순환 참조, 버전 충돌
  ## Recommendations — 구체적 접근 방향 + 대상 파일/라인
  ## References — 분석에 사용된 파일 목록
```

## Step 3: planner 에이전트 — 실행 계획 수립

Agent tool (subagent_type: planner):

```
당신은 planner 에이전트입니다.

프로젝트 타입: [감지된 타입]
작업 요청: [sub-task 문서 전문]

선행 분석 결과:
[Step 2 의 architect 분석 결과 전문]

핵심 원칙:
- 계획만 수립, 구현 안 함 — 코드 작성 금지
- 3-6 단계 — 30개 미세 단계도, 2개 모호한 지시도 아닌
- 코드베이스 사실은 직접 조사 — Grep/Read 활용
- 각 단계에 acceptance criteria
- 선행 분석의 리스크/의존성을 계획에 반영

출력 형식:
  ## Plan: <작업 제목>
  ### 배경 — 왜 이 작업이 필요한가
  ### 단계 — 각 단계에 작업/대상 파일(file:line)/완료 조건
  ### 의존성 — 단계 간 순서 제약
  ### 리스크 — 주의할 점, 영향 범위
```

## Step 4: plan 저장

planner 결과를 sub-task 문서에 `## Plan` 섹션으로 append. 기존 spec 내용 유지.

## 성공/실패 기준

- **성공**: architect + planner 결과 모두 확보, plan 섹션이 sub-task 문서에 저장됨
- **실패**: 에이전트 에러, 또는 분석 불가 (파일 없음 등) → 전체 halt (retry 하지 않음, 입력 문제)

## 자동 모드 제약

- **AskUserQuestion 금지** — 사용자 선호도/우선순위 질문 생략, Claude 판단으로 진행
- 리스크가 크면 plan 의 "리스크" 섹션에 기록만 하고 계속 진행
- 정말 차단 수준의 리스크라면 halt 하고 리포트에 에스컬레이션
