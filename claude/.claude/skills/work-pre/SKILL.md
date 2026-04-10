---
name: work-pre
model: opus
allowed-tools: Read, Grep, Glob, Bash(git log:*), Bash(git blame:*), Bash(git diff:*), Agent, Write, Edit, AskUserQuestion
description: 구현 전 코드베이스 분석 + 실행 계획 수립. brainstorming 후 구현 전에 사용. Use when 3개 이상 파일 수정, 설계 결정, 대규모 변경 전 분석이 필요할 때.
argument-hint: <작업 설명 또는 spec 파일 경로 (.claude/plans/*.md)>
---

# Work Pre — 구현 전 분석 + 계획

구현 전 **분석(architect)**과 **계획(plan)**을 한 번에 수행합니다.

## Step 0: 입력 판별

$ARGUMENTS를 확인한다:

1. **파일 경로인 경우** (`.md`로 끝나거나 `.claude/plans/` 포함):
   - 해당 파일을 Read로 읽는다
   - 파일 내용을 spec으로 사용한다
   - `SPEC_FILE` = 해당 파일 경로 (Step 4에서 plan append 용)
2. **텍스트 설명인 경우**:
   - 그대로 작업 설명으로 사용한다
   - `SPEC_FILE` = 없음 (plan은 대화에만 출력)

## Step 1: 컨텍스트 수집

1. 프로젝트 타입 감지: `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`
2. CLAUDE.md 읽기 (있으면) — 프로젝트 규칙/패턴 파악
3. `git diff --name-only` — 현재 작업 상태 파악

## Step 2: architect 에이전트 — 구조 분석

Agent tool (subagent_type: architect)로 호출:

```
당신은 architect 에이전트입니다.

프로젝트 타입: [감지된 타입]
분석 요청: $ARGUMENTS

수행할 분석:

1. 구조 분석
   - 변경 대상 코드의 현재 구조와 의존 관계
   - 영향받는 파일/모듈 목록 (file:line)

2. 의존성 분석
   - 순환 참조 여부
   - 패키지 버전 충돌 감지 (lock 파일 기반)

3. 리스크 식별
   - 변경 시 깨질 수 있는 곳
   - 하위 호환성 이슈
   - 외부 시스템 계약 (API, DB 스키마 등)

핵심 원칙:
- READ-ONLY: 코드를 읽기만 하고 절대 수정하지 않는다
- Evidence-based: 모든 발견에 file:line 참조 필수
- Trade-offs 명시: 모든 권장사항에 장단점을 함께 제시
- Concrete: "리팩토링을 고려하세요" ❌ → "auth.ts:42-80의 validation 로직을 분리" ✅

출력 형식:
  ## Summary — 1-2문장 요약
  ## Structure — 현재 구조, 의존 관계
  ## Impact — 영향받는 파일/모듈, 리스크
  ## Dependencies — 순환 참조, 버전 충돌
  ## Recommendations — 구체적 접근 방향 + 대상 파일/라인
  ## References — 분석에 사용된 파일 목록
```

## Step 3: 분석 결과 공유

architect 에이전트의 분석 결과를 사용자에게 전달한다.
리스크나 트레이드오프가 있으면 AskUserQuestion으로 사용자 의견을 확인한다.
질문 시 Claude 추천을 `⭐ 추천` 태그로 표시한다.

## Step 4: planner 에이전트 — 실행 계획 수립

분석 결과를 기반으로 Agent tool (subagent_type: planner)로 호출:

```
당신은 planner 에이전트입니다.

프로젝트 타입: [감지된 타입]
작업 요청: $ARGUMENTS

선행 분석 결과:
[Step 2의 architect 분석 결과 전문]

핵심 원칙:
- 계획만 수립, 구현 안 함 — 코드를 작성하지 않는다
- 3-6 단계 — 30개 미세 단계도, 2개 모호한 지시도 아닌
- 코드베이스 사실은 직접 조사 — 사용자에게 묻지 않고 Grep/Read로 확인
- 각 단계에 acceptance criteria — 완료 조건이 명확해야 함
- 선행 분석의 리스크/의존성을 계획에 반영
- 사용자에게는 선호도/우선순위만 AskUserQuestion으로 질문

출력 형식:
  ## Plan: <작업 제목>
  ### 배경 — 왜 이 작업이 필요한가
  ### 단계 — 각 단계에 작업/대상 파일(file:line)/완료 조건
  ### 의존성 — 단계 간 순서 제약
  ### 리스크 — 주의할 점, 영향 범위
```

## Step 5: Plan 저장 및 승인 대기

### SPEC_FILE이 있는 경우 (spec 파일 기반)

planner 에이전트의 계획을 **같은 spec 파일**에 `## Plan` 섹션으로 append한다.
기존 spec 내용은 유지하고, 파일 끝에 plan을 추가한다.

### SPEC_FILE이 없는 경우 (텍스트 설명 기반)

planner 에이전트의 계획을 대화에만 출력한다. (기존 동작 유지)

AskUserQuestion으로 계획을 전달하고 승인을 요청한다.
수정이 필요할 수 있는 부분이 있으면 Claude 추천을 `⭐ 추천` 태그로 함께 제시한다.

---

## 다음 단계

| 계획 승인 후         | 커맨드        |
| :------------------- | :------------ |
| 병렬 구현 (2+ 작업)  | `/work-impl`  |
| 단순 구현 (1-2 파일) | 직접 구현     |
| 구현 후 종합 점검    | `/work-post`  |
| 이슈 수정 후 검증    | `/work-fix`   |
| 코드 정리            | `/work-clean` |
