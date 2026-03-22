---
name: github-pr-respond
model: opus
allowed-tools: Bash(gh api:*), Bash(gh pr view:*), Bash(gh repo view:*), Bash(git log:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git push:*), Bash(git status:*), Bash(git branch:*), Read, Glob, Grep, Edit, AskUserQuestion
description: PR 리뷰 코멘트에 대해 순차적으로 반영 여부를 확인하고 답변을 게시
---

## Context

- Current branch: !`git branch --show-current`
- Repository: !`gh repo view --json nameWithOwner -q '.nameWithOwner' 2>/dev/null`
- Recent commits: !`git log --oneline -5`

## Your Task

현재 브랜치의 PR에 달린 리뷰 코멘트를 순차적으로 처리합니다.
Arguments가 PR 번호 또는 URL이면 해당 PR을 사용하세요.

### CRITICAL RULE: 사용자 승인 없이 실행 금지

**매 단계마다 AskUserQuestion으로 사용자 승인을 받은 후 다음 액션을 실행하세요.**

- 코드 수정 전 → 수정 플랜을 보여주고 AskUserQuestion으로 승인
- 커밋 전 → AskUserQuestion으로 커밋 여부 확인
- 답변 게시 전 → 초안을 보여주고 AskUserQuestion으로 승인

### Step 1: PR 리뷰 코멘트 수집

```bash
# PR 찾기
gh pr view --json number,url,title

# 리뷰 코멘트 (reply 제외, 원본만)
gh api repos/<owner>/<repo>/pulls/<number>/comments \
  --jq '.[] | select(.in_reply_to_id == null) | {id, path, line: (.line // .original_line), body}'
```

코멘트가 없으면 "리뷰 코멘트가 없습니다"를 출력하고 종료.

### Step 2: 코멘트별 순차 처리

**각 코멘트에 대해 아래 순서를 하나씩 진행합니다.**

#### 2a. 분석 및 수정 플랜 제시

1. 코멘트가 가리키는 코드를 Read로 읽기
2. 리뷰어 지적의 타당성을 분석 (관련 코드 흐름, 데이터 소스 등 확인)
3. 아래 형식으로 제시:

```
### 코멘트 N/M: [severity] <요약>

**리뷰어 지적:** <지적 내용 요약>
**분석:** <타당성 판단 + 근거>
**수정 플랜:** <구체적 수정 내용> 또는 "수정 불필요 (사유)"

```

AskUserQuestion으로 선택지를 제공하세요:

- **반영** — 수정 플랜대로 코드를 수정합니다
- **스킵** — 이 코멘트는 건너뜁니다

#### 2b. 코드 수정

사용자가 반영을 승인한 경우에만 코드 수정을 실행합니다.
사용자가 수정 방향을 변경한 경우 해당 방향으로 수정합니다.

#### 2c. 커밋

코드 수정 완료 후 AskUserQuestion으로 선택지를 제공하세요:

- **커밋** — `/commit` command의 규칙을 따라 커밋합니다
- **스킵** — 커밋하지 않고 다음으로 넘어갑니다

#### 2d. Push & 답변 게시

커밋 완료 후 답변 초안을 제시하고 AskUserQuestion으로 선택지를 제공하세요:

- **게시** — push 후 답변을 게시합니다
- **스킵** — 답변을 게시하지 않습니다

게시 승인 시:

```bash
git push origin <branch>
gh api repos/<owner>/<repo>/pulls/<number>/comments/<comment_id>/replies \
  -X POST -f body='<답변>'
```

### Step 3: 완료 요약

모든 코멘트 처리 후 요약 테이블을 출력:

```
| 코멘트 | 상태 | 커밋 |
|--------|------|------|
| <요약> | 반영/스킵 | <hash> |
```

## 답변 작성 규칙

- 짧고 간결하게 (1-2문장)
- 반영 시: "반영했습니다. <변경 요약> (<commit_hash>)"
- 스킵 시: "<사유 간단 설명>"
- 불필요한 부연 설명 금지
