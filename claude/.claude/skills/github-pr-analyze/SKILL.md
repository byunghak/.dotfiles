---
name: github-pr-analyze
model: opus
disable-model-invocation: true
allowed-tools: Bash(gh pr view:*), Bash(gh pr diff:*), Bash(gh api:*), Bash(gh pr list:*), Bash(gh repo view:*), Bash(cat:*), Read, Glob, Grep, TaskCreate, TaskGet, TaskUpdate
description: PR 변경점을 구조적으로 분석하여 목적, 핵심 변경, 데이터 흐름, 인사이트를 정리
---

## Context

- Current branch: !`git branch --show-current`
- Repository: !`gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null`

## Your Task

PR의 변경 내용을 **구조적으로 분석**하여 코드 이해를 돕는 리포트를 생성하세요.

Arguments가 없으면 현재 브랜치의 PR을 찾으세요: `gh pr view --json number,url`
Arguments가 PR 번호 또는 URL이면 해당 PR을 분석하세요.

### Step 1: PR 메타데이터 수집

병렬로 실행:

```bash
gh pr view <number> --json title,body,files,additions,deletions,commits,baseRefName,headRefName
gh pr diff <number>
```

### Step 2: 변경 파일 분류

변경된 파일을 역할별로 분류:

| 분류                    | 예시                                         |
| ----------------------- | -------------------------------------------- |
| Config / Dependencies   | pyproject.toml, package.json, _.yaml, _.lock |
| Domain / Business Logic | entities, services, use_cases                |
| Infrastructure          | repositories, clients, adapters              |
| API / Entry Point       | controllers, routes, app.py, run.ts          |
| Test                    | _.spec.ts, \_\_test.py, test_\*.py           |

### Step 3: 핵심 변경 분석

각 핵심 변경에 대해:

1. **무엇이 변경되었는가** — 코드 레벨 변경 요약
2. **왜 변경되었는가** — PR description, 커밋 메시지, 코드 컨텍스트에서 추론
3. **어떻게 동작하는가** — 알고리즘, 수식, 패턴 설명 (해당 시 수식 포함)

`★ Insight` 블록으로 기술적 배경 지식이나 설계 의도를 보충 설명하세요.

### Step 4: 데이터/실행 흐름

변경이 여러 파일에 걸쳐있으면 데이터/실행 흐름을 ASCII 다이어그램으로 표현:

```
[입력] → [처리1] → [처리2] → [출력]
```

### Step 5: 부수적 변경

핵심 변경 외의 변경 사항을 테이블로 정리:

| 영역 | 변경 내용 |
| ---- | --------- |

### 출력 형식

```markdown
## PR #<number> 분석: `<title>`

### 목적

<1-2문장 요약>

### 핵심 변경 (N개)

#### 1. <변경명>

★ Insight ─────────────────────────────────────
<기술적 배경/설계 의도 2-3줄>
─────────────────────────────────────────────────

<코드 변경 설명>

#### 2. ...

### 데이터/실행 흐름

<ASCII 다이어그램>

### 부수적 변경

<테이블>
```
