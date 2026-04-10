---
name: code
model: opus
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git:*), Bash(npm:*), Bash(npx:*), Bash(pnpm:*), Bash(python:*), Bash(go:*), Bash(cargo:*), Bash(pip:*), Bash(make:*), Bash(ls:*), Bash(rm:*), Agent, TaskCreate, TaskGet, TaskUpdate, SendMessage
description: code-brainstorming 산출 디렉토리(.claude/plans/<dir>/)를 받아 pre→impl→post→fix→clean 파이프라인을 DAG 순서로 자체 실행. 자체 완결형.
argument-hint: <.claude/plans/YYYY-MM-DD-<topic>/ 디렉토리 경로> [--security] [--coverage]
---

# Code — 자체 완결 파이프라인 오케스트레이터

`/code-brainstorming` 에서 생성한 plan 디렉토리를 받아, `_dag.yaml` 에 정의된 sub-task 들을 **위상정렬 순서**로 `pre → impl → post → (fix) → clean` 파이프라인에 태웁니다.

**이 스킬은 자체 완결형입니다.** `references/stage-*.md` 에 정의된 각 단계를 Claude 가 직접 수행합니다.

> **전제**: 입력 디렉토리는 `DESIGN.md`, `_dag.yaml`, `NN-*.md` 를 포함해야 합니다 (`/code-brainstorming` 산출물).
> **자동 모드**: 전 파이프라인에서 사용자 질문(AskUserQuestion 또는 대화형 프롬프트)은 **실패로 간주**되며, 중단 시점에만 사용자에게 에스컬레이션합니다.

---

## 세부 규칙 참조

이 SKILL.md 는 얇은 오케스트레이션만 담고, 세부 로직은 `references/` 에 있습니다. **필요한 시점에만** Read 로 불러오세요:

| 시점                            | 파일                         |
| :------------------------------ | :--------------------------- |
| DAG 파싱/위상정렬               | `references/dag-format.md`   |
| Stage 1 (분석 + 계획) 수행 방법 | `references/stage-pre.md`    |
| Stage 2 (병렬 구현) 수행 방법   | `references/stage-impl.md`   |
| Stage 3 (종합 검증) 수행 방법   | `references/stage-post.md`   |
| Stage 4 (자동 수정) 수행 방법   | `references/stage-fix.md`    |
| Stage 5 (코드 정리) 수행 방법   | `references/stage-clean.md`  |
| 이슈 분류 + 중단 판단           | `references/halt-policy.md`  |
| fix 재시도 정책                 | `references/retry-policy.md` |
| 중간/최종 리포트 포맷           | `references/reporting.md`    |

---

## Step 0: 입력 파싱 + 검증

`$ARGUMENTS` 에서 plan 디렉토리 경로와 옵션을 추출:

- 위치 인자: plan 디렉토리 경로 (필수)
- `--security`: Stage Fix 에서 보안 검증 포함 (선택)
- `--coverage`: Stage Fix 에서 커버리지 분석 포함 (선택)

검증:

1. 경로가 디렉토리인가? (아니면 즉시 halt + 에러)
2. `DESIGN.md`, `_dag.yaml` 존재 확인 (없으면 halt)
3. `git status --short` — working tree 가 dirty 하면 리포트에 경고 기록 후 진행

## Step 1: DAG 로드

`references/dag-format.md` 를 Read 로 불러와 스키마/규칙 확인.

1. `_dag.yaml` 을 Read + 파싱
2. 스키마 검증 (`dag-format.md` 의 검증 규칙)
3. `tasks[]` 를 **위상정렬** (depends_on 기준, 선형)
4. 실행 순서 확정
5. TaskCreate 로 각 sub-task 를 tracking task 로 등록

검증 실패 시 즉시 halt. `reporting.md` 기반으로 halt 리포트 출력.

## Step 2: 각 sub-task 파이프라인 실행

위상정렬 순서대로 각 sub-task 에 대해:

### 2-0. 진입 배너

`reporting.md` 의 sub-task 배너 포맷으로 시작 표시.

### 2-1. Stage Pre (분석 + 계획)

`references/stage-pre.md` 를 Read → 지시대로 architect + planner 호출 → sub-task 문서에 `## Plan` append.

- 실패 시: 즉시 halt (retry 없음)

### 2-2. Stage Impl (병렬 구현)

`references/stage-impl.md` 를 Read → 지시대로 팀 구성 + Task 배정 + 팀원 spawn + 실행.

- 실패 시: 즉시 halt (retry 없음)
- 자동 모드: 팀 구성 승인 AskUserQuestion 생략, 자동 진행

### 2-3. Stage Post (종합 검증)

`references/stage-post.md` 를 Read → 지시대로 4개 에이전트 병렬 호출 → 종합 판정.

- PASS → 2-5 (clean) 로
- NEEDS ATTENTION → 리포트 기록 후 2-5 로
- FAIL → 2-4 (fix loop) 진입

`references/halt-policy.md` 의 분류 규칙을 적용하여 판정.

### 2-4. Stage Fix loop (조건부)

`references/stage-fix.md` 와 `references/retry-policy.md` 를 Read.

```
attempt = 0
loop:
  attempt += 1
  Stage Fix 수행 (verify-agent 1회 호출)
  Stage Post 재실행
  PASS / NEEDS ATTENTION → break (2-5 로)
  FAIL + attempt < 3 → continue
  FAIL + attempt >= 3 → 전체 halt
  동일 에러 2회 연속 → 전체 halt (정체 탐지)
```

### 2-5. Stage Clean (정리)

`references/stage-clean.md` 를 Read → refactor-cleaner 호출.

- 실패해도 halt 하지 않음 (clean 은 non-critical, 리포트에 warning 기록)
- **예외**: clean 이 build 를 깨뜨리면 Stage Post 재실행으로 탐지됨 → 2-4 fix loop 진입

### 2-6. sub-task 완료

TaskUpdate 로 해당 sub-task 를 `completed` 로 마크. `reporting.md` 의 sub-task 완료 요약 출력.

## Step 3: 종합 리포트

모든 sub-task 완료 또는 halt 시 `references/reporting.md` 를 Read 하여 최종 리포트 출력.

포함 내용:

- 각 sub-task 별 결과 (PASS / NEEDS ATTENTION / FAIL)
- 누적 변경 통계 (`git diff --stat`)
- 경고/이슈 목록
- 다음 권장 액션 (`/git-commit`, `/github-pr-push` 등)

---

## 중단 정책 요약

`references/halt-policy.md` 에 상세, 핵심만:

1. **자동 모드 위반 = 실패**: 어떤 stage 든 사용자 질문을 시도하면 즉시 halt
2. **critical 이슈 = 자동 fix 시도**: Stage Post FAIL → Stage Fix loop
3. **task 실패 = 전체 halt**: downstream sub-task 는 실행하지 않음
4. **warning only = 진행**: NEEDS ATTENTION 은 기록만 하고 계속

---

## 다음 단계

| 결과         | 권장 커맨드                              |
| :----------- | :--------------------------------------- |
| 전체 성공    | `/git-commit` → `/github-pr-push`        |
| warning 존재 | 수동 리뷰 후 `/git-commit`               |
| 중간 halt    | `/code-debug` 로 root cause 분석 후 재개 |
