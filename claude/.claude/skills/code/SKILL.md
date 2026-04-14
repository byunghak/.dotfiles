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

| 경로              | 입력                                | 동작                             |
| ----------------- | ----------------------------------- | -------------------------------- |
| **Brainstorming** | 텍스트 설명, 빈 값, draft 상태 plan | 요구사항 탐색 → 설계 → plan 작성 |
| **Pipeline**      | .claude/plans/<dir>/ (ready 상태)   | code-pipeline spawn → 자동 실행  |

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

`code-pipeline` 에이전트를 spawn하여 자동 실행:

```
code-pipeline 에이전트를 호출합니다.

plan 디렉토리: [$ARGUMENTS]
[--security / --coverage 옵션이 있으면 포함]
[프로젝트별 검증 명령어가 있으면 포함]

_dag.yaml의 sub-task를 위상정렬 순서로 파이프라인에 태워주세요.
```

code-pipeline가 Pre → Impl → Post → Fix → Clean을 자체 완결 실행한다.

### Agent spawn 실패 시

code-pipeline 에이전트 spawn이 실패하면:

1. **직접 실행으로 우회하지 않는다**
2. 사용자에게 실패 사유를 보고하고 대기한다
3. 사용자가 재시도를 요청하면 다시 Agent tool로 spawn을 시도한다

### code-style 정보

code-style.md가 존재하면 code-pipeline 호출 시 포함:

```
코드 스타일: [code-style.md 내용]
```
