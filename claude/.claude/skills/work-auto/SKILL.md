---
name: work-auto
model: opus
allowed-tools: Read, Grep, Glob, Bash(git:*), Bash(ls:*), Skill, Agent, AskUserQuestion, TaskCreate, TaskUpdate
description: brainstorming 산출 디렉토리(.claude/plans/<dir>/)를 받아 pre→work→post→fix→clean 파이프라인을 DAG 순서로 자동 실행. Use when 분리된 plan 을 끝까지 자동 실행할 때.
argument-hint: <.claude/plans/YYYY-MM-DD-<topic>/ 디렉토리 경로>
---

# Work Auto — 자동 파이프라인 오케스트레이터

`/work-brainstorming` 에서 생성한 plan 디렉토리를 받아, `_dag.yaml` 에 정의된 sub-task 들을 **위상정렬 순서**로 `pre → work → post → (fix) → clean` 파이프라인에 태웁니다.

> **전제**: 입력 디렉토리는 `DESIGN.md`, `_dag.yaml`, `NN-*.md` 를 포함해야 합니다 (`/work-brainstorming` 산출물).
> **자동 모드**: 전 파이프라인에서 `AskUserQuestion` 은 실패로 간주되며, 중단 시점에만 사용자에게 에스컬레이션합니다.

---

## 세부 규칙 참조

이 스킬은 얇은 오케스트레이터이며, 세부 규칙은 다음 reference 파일에 있습니다. **필요한 시점에만** Read 로 불러오세요:

| 시점                           | 파일                           |
| :----------------------------- | :----------------------------- |
| DAG 파싱/위상정렬              | `references/dag-format.md`     |
| 각 stage 호출 방법/입출력 계약 | `references/stage-pipeline.md` |
| post 이슈 분류, 중단 판단      | `references/halt-policy.md`    |
| fix 재시도 정책                | `references/retry-policy.md`   |
| 최종/중간 리포트 포맷          | `references/reporting.md`      |

---

## Step 0: 입력 검증

`$ARGUMENTS` 를 plan 디렉토리 경로로 취급:

1. 경로가 디렉토리인가? (아니면 즉시 중단 + 에러)
2. `DESIGN.md`, `_dag.yaml` 존재 확인 (없으면 중단)
3. `git status --short` — working tree 가 dirty 하면 사용자에게 경고 (진행 여부 확인)

## Step 1: DAG 로드

`references/dag-format.md` 를 Read 로 불러와 스키마/규칙 확인.

1. `_dag.yaml` 을 Read
2. `tasks[]` 를 **위상정렬** (depends_on 기준)
3. 사이클/누락 파일/orphan 의존성 검증 — 실패 시 즉시 중단
4. 실행 순서 확정 → TaskCreate 로 각 sub-task 를 tracking task 로 등록

## Step 2: 파이프라인 실행 (각 sub-task 별)

`references/stage-pipeline.md` 를 Read 하여 각 stage 호출 계약 확인.

각 sub-task 에 대해 순차적으로:

### 2-1. `/work-pre`

```
Skill tool: work-pre
args: <plan-dir>/NN-<task>.md
```

### 2-2. `/work`

```
Skill tool: work
(plan 은 직전 pre 결과 + NN-*.md 사용)
```

### 2-3. `/work-post`

```
Skill tool: work-post
```

post 결과 파싱 → `references/halt-policy.md` 의 분류 규칙 적용:

- **PASS**: 2-5 로 진행
- **NEEDS ATTENTION (warning only)**: 리포트에 기록, 2-5 로 진행
- **FAIL (critical)**: 2-4 (fix loop) 진입
- **Agent 가 사용자 질문 던짐**: 자동 모드 위반 → 즉시 halt + 에스컬레이션

### 2-4. `/work-fix` loop (critical 일 때만)

`references/retry-policy.md` 를 Read 하여 재시도 규칙 확인.

- 기본 최대 3회 재시도
- 각 시도 후 `/work-post` 재실행
- PASS 되면 2-5 로 진행
- 재시도 소진되면 **전체 파이프라인 halt** (정책 i: task 실패 = 전체 중단)
- halt 시 `references/reporting.md` 기반으로 실패 리포트 출력 + 사용자 에스컬레이션

### 2-5. `/work-clean`

```
Skill tool: work-clean
```

clean 실패는 critical 아님 — 리포트에 warning 으로만 기록하고 다음 sub-task 진행.

### 2-6. TaskUpdate

해당 sub-task 를 `completed` 로 마크.

## Step 3: 종합 리포트

모든 sub-task 가 완료되면 `references/reporting.md` 를 Read 하여 포맷 확인 후 최종 리포트 출력.

포함 내용:

- 각 sub-task 별 결과 (PASS / NEEDS ATTENTION / FAIL)
- 누적 변경 통계 (git diff --stat)
- 경고/이슈 목록
- 다음 권장 액션 (`/git-commit`, `/github-pr-push` 등)

---

## 중단 정책 요약

`references/halt-policy.md` 에 상세하지만, 핵심만:

1. **자동 모드 위반 = 실패**: 하위 skill 이 사용자 질문을 시도하면 즉시 halt
2. **critical 이슈 = 자동 fix 시도**: work-post FAIL → work-fix 루프
3. **task 실패 = 전체 halt**: downstream sub-task 는 실행하지 않음 (정책 i)
4. **warning only = 진행**: NEEDS ATTENTION 은 기록만 하고 계속

---

## 다음 단계

| 결과         | 권장 커맨드                              |
| :----------- | :--------------------------------------- |
| 전체 성공    | `/git-commit` → `/github-pr-push`        |
| warning 존재 | `/work-clean` 수동 실행 후 `/git-commit` |
| 중간 halt    | 수동 디버그 (`/work-debug`) 후 재개      |
