---
name: github-ship
model: opus
effort: medium
allowed-tools: Read, Edit, Glob, Grep, Agent, AskUserQuestion, Bash(git add:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git commit:*), Bash(git branch:*), Bash(git checkout:*), Bash(git remote:*), Bash(git pull:*), Bash(git push:*), Bash(git stash:*), Bash(git rev-parse:*), Bash(git blame:*), Bash(gh pr create:*), Bash(gh pr view:*), Bash(gh pr edit:*), Bash(gh pr diff:*), Bash(gh pr merge:*), Bash(gh pr comment:*), Bash(gh pr review:*), Bash(gh api:*), Bash(gh label list:*), Bash(gh repo view:*), Bash(mkdir:*), Bash(cat:*), Bash(npx eslint:*), Bash(npm run lint:*), Bash(npx pyright:*), Bash(python*), Bash(grep:*), Bash(jq:*)
description: branch → commit → push/PR → review → merge 전체 파이프라인. 디폴트 브랜치면 생성, PR 분리 필요 시 제안, 리뷰 후 머지까지.
argument-hint: <작업 설명 또는 브랜치명> [--no-merge]
---

## Pre-check: Git Repository 검증

이 skill 은 git repository 안에서만 동작합니다.

```
IF !`git rev-parse --is-inside-work-tree 2>/dev/null` != "true":
    ❌ 현재 디렉토리는 git repository 가 아닙니다.
    git init 또는 git clone 후 다시 시도하세요.
    → 즉시 종료
```

---

## Context

- Current branch: !`git branch --show-current`
- Default remote branch: !`git remote show origin 2>/dev/null | grep 'HEAD branch' | sed 's/.*: //'`
- Git status: !`git status --short`
- Uncommitted changes: !`git diff --stat HEAD`
- Unpushed commits: !`git log --oneline origin/HEAD..HEAD 2>/dev/null || echo "__NO_REMOTE__"`
- Recent branches: !`git branch --sort=-committerdate --all --format='%(refname:short)' --no-contains=HEAD | head -15`
- Branch convention: !`cat .claude/branch-convention.md 2>/dev/null || echo "__USE_DEFAULT__"`
- Commit convention: !`cat .claude/commit-convention.md 2>/dev/null || grep -A 60 -m 1 "## Commit" CLAUDE.md 2>/dev/null || echo "__USE_DEFAULT__"`
- Recent commits: !`git log --oneline -10`
- PR template: !`cat .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null || cat .github/pull_request_template.md 2>/dev/null || echo "__NO_TEMPLATE__"`
- Repository: !`gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null`

---

## Step 0: 변경 분류 — Phase skip 결정

파이프라인 시작 전에 변경 내용을 분류하여 불필요한 Phase를 건너뛴다.

```bash
git diff --name-only HEAD
git diff --stat HEAD
```

변경 파일의 확장자와 경로를 분석하여 아래 플래그를 설정:

| 플래그    | 조건                                                                   | 효과                                |
| --------- | ---------------------------------------------------------------------- | ----------------------------------- |
| `TRIVIAL` | 설정(.json/.yaml/.toml), 문서(.md), lock 파일, skill/agent 정의만 변경 | Phase 3 lint skip, Phase 4 skip     |
| `SMALL`   | 코드 변경 포함, 파일 ≤ 3개 & 50줄 미만                                 | Phase 4 → Lite 리뷰 (agent #1+#2만) |
| `MEDIUM`  | 코드 변경 포함, 파일 ≤ 5개 & 200줄 미만                                | Phase 4 → Standard 리뷰 (#1+#2+#3)  |
| `LARGE`   | 코드 변경 포함, 파일 > 5개 또는 200줄 이상                             | Phase 4 → Full 리뷰 (#1~#5)         |

> `--no-merge` 플래그 → Phase 5 항상 skip

---

## Phase 1: Branch Setup

### 현재 브랜치가 디폴트가 아닌 경우 → Phase 2로 직행

### 현재 브랜치가 디폴트인 경우:

**1-A: PR 분리 분석**

변경 사항의 관심사, 모듈, 변경 종류를 분석.

분리 제안 기준 (하나라도 해당):

- 서로 다른 관심사 혼재 (feature + bugfix, refactor + new feature)
- 독립 모듈/패키지 동시 수정 (`backend/` + `frontend/`)
- 20+ 파일, 500+ 줄이고 리뷰 단위로 나눌 수 있음

단일 PR 기준 (모두 해당):

- 한 가지 관심사
- 한 모듈/디렉토리에 집중
- 10파일 미만, 300줄 미만

분리 필요 시 AskUserQuestion:

- **분리 진행** — 제안대로 분리 (Phase 2~5를 PR별 반복)
- **단일 PR** — 분리 없이 진행
- **직접 조정** — 분리 방법 지정

분리 진행 시 stash로 파일 분리:

```bash
git stash push -- <PR2-files>   # PR1 작업 시
# PR1 완료 후
git stash pop
git checkout -b <branch-2>
```

**1-B: 브랜치 생성**

컨벤션이 `__USE_DEFAULT__`이면 Recent branches에서 추론 → `.claude/branch-convention.md` 작성.

```bash
git pull origin <default-branch>
git checkout -b <branch-name>
```

- $ARGUMENTS로 브랜치명/작업 내용 제공 → 컨벤션에 맞게 변환
- 미제공 → 변경 내용에서 자동 생성, AskUserQuestion으로 확인

---

## Phase 2: Commit

> 상세 규칙: `references/commit-rules.md`

1. 컨벤션 확인 (`__USE_DEFAULT__`이면 추론 → `.claude/commit-convention.md`)
2. 관심사별 분리 & 커밋 (의존성 순서, `git add -p` 활용)
3. 각 커밋 전 staged diff 리뷰 (버그/컨벤션/보안/설계, confidence 70+)

---

## Phase 3: Push & PR

> 상세 규칙: `references/pr-rules.md`

### 3-A: 정적 분석

- `TRIVIAL` → **skip**
- lintable 파일 없음 → **skip**
- 그 외 → lint/type check 병렬 실행, error만 보고

### 3-B: Push

```bash
git push -u origin <branch>
```

### 3-C: PR 생성/업데이트

```bash
gh pr view --json number,title,body,url,assignees,labels
```

- PR 없음 → 신규 생성 (제목, body, assignee, label)
- PR 있음 → 주요 변경이면 업데이트, 마이너면 push만

---

## Phase 4: Code Review

> 상세 규칙: `references/review-rules.md`

### Skip 판단

- `TRIVIAL` → **Phase 4 전체 skip** → Phase 5로
- `SMALL` → Lite 리뷰 (agent #1 CLAUDE.md + #2 버그)
- `MEDIUM` → Standard 리뷰 (#1 + #2 + #3 설계)
- `LARGE` → Full 리뷰 (#1 ~ #5)

### 실행

1. CLAUDE.md 규칙 수집 (Agent로 프로젝트 내 모든 CLAUDE.md 탐색)
2. PR diff 수집: `gh pr diff <number>`
3. 강도에 맞는 agent만 병렬 호출
4. 신뢰도 75+ 이슈만 필터링
5. 이슈별 AskUserQuestion: **수정** / **Skip**
6. 수정 시 추가 커밋 → push → 리뷰 재실행 (최대 2회)

---

## Phase 5: Merge

### Skip 판단

- `--no-merge` 플래그 → **skip**
- Phase 4에서 미해결 이슈 존재 → **skip**
- WIP PR → **skip**

### Mergeable 확인

```bash
gh pr view <number> --json mergeStateStatus,reviewDecision,statusCheckRollup -q '{state: .mergeStateStatus, review: .reviewDecision, checks: [.statusCheckRollup[]?.conclusion]}'
```

- `mergeStateStatus` 가 `BLOCKED` → **skip** (PR URL 출력 + 차단 사유 안내)
- `reviewDecision` 이 `CHANGES_REQUESTED` → **skip**
- status check 실패 → **skip**

### 실행

Mergeable 확인 통과 시 **Merge commit으로 즉시 머지** (AskUserQuestion 없이 진행):

```bash
gh pr merge <number> --merge --delete-branch
```

---

## 분리 PR 반복 처리

Phase 1에서 분리 선택 시, 각 PR에 대해 Phase 2~5를 순차 반복.

```
━━━ PR 1/N: <관심사 A> ━━━
  Phase 2 → 3 → 4 → 5

━━━ PR 2/N: <관심사 B> ━━━
  Phase 2 → 3 → 4 → 5
```
