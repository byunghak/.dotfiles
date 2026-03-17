---
name: dable-jira-summary
model: opus
disable-model-invocation: true
allowed-tools: Bash(git log:*), Bash(git diff:*), Bash(git branch:*), Bash(gh repo view:*), Bash(jira issue view:*), Bash(jira issue comment add:*), Read, Glob, Grep, AskUserQuestion
description: 브랜치 작업 내용을 요약하여 JIRA 카드 댓글로 작성
---

## Context

- Current branch: !`git branch --show-current`
- Recent commits on this branch: !`BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@.*/@@' || echo main) && git log $BASE..HEAD --oneline`
- Changed files summary: !`BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@.*/@@' || echo main) && git diff $BASE...HEAD --stat`
- Project name: !`gh repo view --json name -q '.name' 2>/dev/null || basename $(git rev-parse --show-toplevel)`

## Your Task

현재 브랜치의 작업 내용을 요약하여 JIRA 카드에 댓글로 작성하세요.

### Step 1: JIRA 이슈 키 추출

브랜치 이름에서 JIRA 이슈 키를 추출하세요 (예: `feature/BE-1320/...` → `BE-1320`).

Arguments가 있으면 해당 값을 JIRA 이슈 키로 사용하세요.

추출 실패 시 사용자에게 이슈 키를 물어보세요.

### Step 2: 변경 내용 분석

base 브랜치 기준으로 현재 브랜치의 전체 변경 내용을 분석하세요.

먼저 base 브랜치를 감지하세요:

```bash
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@.*/@@' || echo main)
```

그 후 병렬로 실행:

```bash
git log $BASE..HEAD --oneline
git diff $BASE...HEAD --stat
git diff $BASE...HEAD
```

### Step 3: 작업 단위 요약 작성

파일 단위가 아닌 **작업 단위**로 요약하세요. 메인 변경점과 부수적 변경점을 분리합니다.

요약 형식:

```markdown
## 브랜치 작업 요약 — `<project-name>` (`<branch-name>`)

### 메인: <핵심 작업 한 줄 요약>

<핵심 작업 설명 — 무엇을 왜 했는지>

1. **<작업 단위 1>** — <설명>
2. **<작업 단위 2>** — <설명>
   ...

---

### 부수: <부제목>

- **<변경 1>** — <설명>
- **<변경 2>** — <설명>
  ...
```

### Step 4: 사용자 확인

작성할 요약을 보여준 후 AskUserQuestion 도구로 선택지를 제공하세요:

- **댓글 작성** — `<ISSUE-KEY>`에 바로 댓글을 게시합니다
- **수정 후 작성** — 요약 내용을 수정한 뒤 댓글을 게시합니다

### Step 5: JIRA 댓글 작성

사용자가 "댓글 작성"을 선택한 경우 `jira-cli`로 댓글을 작성하세요:

```bash
cat <<'EOF' | jira issue comment add <ISSUE-KEY> --template -
<요약 내용>
EOF
```

완료 후 JIRA 카드 링크를 제공하세요.
