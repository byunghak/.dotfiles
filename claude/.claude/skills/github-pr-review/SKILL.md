---
name: github-pr-review
model: opus
allowed-tools: Bash(gh pr view:*), Bash(gh pr diff:*), Bash(gh api:*), Bash(gh pr list:*), Bash(gh pr comment:*), Bash(gh pr review:*), Bash(gh repo view:*), Bash(git log:*), Bash(git blame:*), Read, Glob, Grep, Agent
description: GitHub PR 코드 품질 심층 리뷰 (버그, 컨벤션, 보안, 설계). Use when PR 번호를 지정하여 코드 리뷰를 요청할 때.
---

## Context

- Current branch: !`git branch --show-current`
- Repository: !`gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null`
- CLAUDE.md: !`cat CLAUDE.md 2>/dev/null | head -50 || echo "__NO_CLAUDE_MD__"`

## Your Task

PR의 코드 품질을 **심층 리뷰**하여 버그, 설계 이슈, 잠재적 문제점을 찾으세요.

Arguments가 없으면 현재 브랜치의 PR을 찾으세요: `gh pr view --json number,url`
Arguments가 PR 번호 또는 URL이면 해당 PR을 리뷰하세요.

### Step 1: PR 정보 수집

병렬로 실행:

```bash
gh pr view <number> --json title,body,files,additions,deletions,baseRefName,headRefName
gh pr diff <number>
```

### Step 2: CLAUDE.md 규칙 수집

Agent tool (subagent_type: general-purpose, model: haiku)로 CLAUDE.md 규칙 수집:

```
PR이 수정한 디렉토리 경로를 기반으로 프로젝트 내 CLAUDE.md 파일을 모두 찾아
(루트, 서브디렉토리, .claude/ 내부) 규칙 목록을 추출하세요.
각 규칙을 한 줄로 정리하여 반환하세요.
```

### Step 3: code-reviewer 에이전트 병렬 리뷰

Agent tool (subagent_type: general-purpose, model: sonnet) × 최대 5개를 **병렬로** 호출.

각 agent에게 PR diff, CLAUDE.md 규칙, 관련 컨텍스트를 전달하되 집중 영역을 분리:

```
당신은 code-reviewer 에이전트입니다.

PR diff:
[전체 diff]

CLAUDE.md 규칙:
[Step 2 결과]

집중 영역: [아래 테이블에서 해당 영역]

발견한 이슈를 아래 형식으로 반환:
- [severity: critical/major/minor] <이슈 설명>
  파일: <path>:<line>
  근거: <왜 이것이 문제인가>
  제안: <수정 방향>
```

| Agent | 집중 영역                                                        |
| :---- | :--------------------------------------------------------------- |
| #1    | **CLAUDE.md 준수** — 프로젝트 규칙 위반 여부                     |
| #2    | **버그 탐지** — 로직 오류, edge case, off-by-one, null/undefined |
| #3    | **설계 분석** — 아키텍처 적합성, 레이어 위반, 의존성 방향        |
| #4    | **보안/성능** — injection, 메모리 누수, N+1 쿼리, 무한 루프      |
| #5    | **테스트 커버리지** — 테스트 누락, edge case 미검증, mock 적절성 |

> 변경 파일이 5개 이하면 agent #3~#5를 생략하여 비용 절감.

### Step 4: 이슈 검증 및 필터링

Agent tool (subagent_type: general-purpose, model: haiku)로 각 이슈의 신뢰도 점수(0-100)를 매기세요:

| 점수   | 의미                                               |
| :----- | :------------------------------------------------- |
| 0-25   | False positive, 기존 이슈, lint/타입체커가 잡을 것 |
| 25-50  | 가능성 있으나 미검증, 사소한 스타일 이슈           |
| 50-75  | 실제 이슈이나 실무 영향 낮음, nitpick              |
| 75-100 | 검증된 실제 이슈, 기능에 직접 영향                 |

**False positive 기준** (제외 대상):

- 기존 코드의 문제 (PR에서 수정하지 않은 라인)
- Lint, 타입체커, CI가 잡을 이슈
- 의도적 변경으로 보이는 기능 변경
- CLAUDE.md에 명시되지 않은 스타일 nitpick

### Step 5: 결과 출력

**신뢰도 75 이상 이슈만** 최종 리포트에 포함.

````markdown
## PR #<number> 코드 리뷰: `<title>`

### 요약

- 변경 규모: +<additions> / -<deletions> (파일 <count>개)
- 발견 이슈: critical <n>, major <n>, minor <n>

### Issues

#### 1. [critical] <이슈 제목>

**파일:** `<path>:<line>` (신뢰도: <score>)

<문제 설명>

```diff
- <문제 코드>
+ <제안 코드>
```
````

이슈가 없으면:

```markdown
## PR #<number> 코드 리뷰: `<title>`

### 요약

변경 규모: +<additions> / -<deletions> (파일 <count>개)

신뢰도 75 이상 이슈 없음. CLAUDE.md 준수 확인 완료.
```

### Step 6: 이슈별 게시 확인

이슈가 없으면 이 단계를 건너뜁니다.

**각 이슈에 대해 순차적으로** AskUserQuestion을 사용하여 게시 여부를 확인합니다:

```
### 이슈 N/M: [severity] <이슈 제목>

**파일:** `<path>:<line>`
**문제:** <문제 설명 요약>
**제안:** <수정 방향 요약>
```

선택지:

- **Inline Comment** — PR diff의 해당 라인에 inline comment로 게시
- **Comment** — PR 일반 코멘트로 게시
- **Skip** — 게시하지 않음

### Step 7: 일괄 게시

모든 이슈 확인 완료 후, 선택 결과에 따라 게시합니다.

**Inline Comment 선택 건:** 하나의 PR Review로 묶어 일괄 제출

```bash
gh api repos/<owner>/<repo>/pulls/<number>/reviews \
  -X POST \
  -f event='COMMENT' \
  -f body='Claude Code 리뷰' \
  --input - <<EOF
{
  "event": "COMMENT",
  "body": "Claude Code 리뷰",
  "comments": [
    {"path": "<file>", "line": <line>, "body": "<comment>"}
  ]
}
EOF
```

**Comment 선택 건:** 개별 PR 코멘트로 게시

```bash
gh pr comment <number> --body '<comment>'
```

게시 완료 후 결과 요약 테이블 출력:

```
| 이슈 | 게시 방식 |
|------|-----------|
| [severity] <요약> | Inline / Comment / Skip |
```
