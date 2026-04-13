---
name: code
model: opus
effort: high
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git:*), Bash(npm:*), Bash(npx:*), Bash(pnpm:*), Bash(python:*), Bash(go:*), Bash(cargo:*), Bash(pip:*), Bash(make:*), Bash(ls:*), Bash(rm:*), Bash(mkdir:*), Agent, AskUserQuestion, TaskCreate, TaskGet, TaskUpdate, SendMessage
description: 코드 구현 전체 사이클. 요구사항 탐색 → 설계 → 자동 파이프라인 실행. plan 디렉토리 전달 시 바로 실행, 텍스트 전달 시 brainstorming부터 시작. Use when 코드 구현이 필요하거나, 접근법을 결정해야 할 때.
argument-hint: <구현할 기능 설명> | <.claude/plans/<dir>/ 경로> [--security] [--coverage]
---

## Context

- 코드 스타일: !`cat .claude/code-style.md 2>/dev/null || echo "__NO_CODE_STYLE__"`

---

# Code — Brainstorming + Pipeline 통합

하나의 skill로 **두 가지 경로**를 자동 감지합니다.

| 경로              | 입력                                | 동작                                      |
| ----------------- | ----------------------------------- | ----------------------------------------- |
| **Brainstorming** | 텍스트 설명, 빈 값, draft 상태 plan | 요구사항 탐색 → 설계 → plan 작성          |
| **Pipeline**      | .claude/plans/<dir>/ (ready 상태)   | pre → impl → post → fix → clean 자동 실행 |

---

## Step 0: 입력 판별 + 라우팅

`$ARGUMENTS` 를 다음 순서로 확인:

1. **기존 plan 디렉토리** (`.claude/plans/<topic>/` 또는 내부 NN-\*.md):
   - `_dag.yaml` 존재 + 각 NN-\*.md 의 frontmatter `status` 확인
   - 모든 대상 sub-task 가 `ready` → **Pipeline** 경로
   - `draft` 포함 → **Brainstorming 재진입** (`references/brainstorming.md` Step 8)

2. **텍스트 설명 또는 빈 값**:
   - **신규 Brainstorming** (`references/brainstorming.md` Step 1)

옵션 (`--security`, `--coverage`): Pipeline 경로에서만 유효.

---

## Path A: Brainstorming

> `references/brainstorming.md` 를 Read 하여 진행

요구사항 탐색 → 접근법 결정 → PM 분리 판단 → 설계 문서/plan 작성 → architect 리뷰.

산출물:

```
.claude/plans/YYYY-MM-DD-<topic>/
  DESIGN.md / _dag.yaml / NN-<task>.md
```

Brainstorming 완료 + 모든 sub-task ready 시, Pipeline 자동 전환 여부를 AskUserQuestion 으로 확인.

## Path B: Pipeline Execution

> `references/pipeline.md` 를 Read 하여 진행

`_dag.yaml` 의 sub-task 를 위상정렬 순서로 파이프라인에 태움. 자체 완결형, 자동 모드.

세부 stage 는 필요 시점에 Read:

| 시점        | 파일                         |
| :---------- | :--------------------------- |
| DAG 파싱    | `references/dag-format.md`   |
| Stage Pre   | `references/stage-pre.md`    |
| Stage Impl  | `references/stage-impl.md`   |
| Stage Post  | `references/stage-post.md`   |
| Stage Fix   | `references/stage-fix.md`    |
| Stage Clean | `references/stage-clean.md`  |
| Halt 정책   | `references/halt-policy.md`  |
| Retry 정책  | `references/retry-policy.md` |
| 리포트      | `references/reporting.md`    |
