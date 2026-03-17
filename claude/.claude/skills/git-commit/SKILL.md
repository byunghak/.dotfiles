---
name: git-commit
model: opus
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git commit:*), Bash(mkdir:*), AskUserQuestion
description: 프로젝트 컨벤션에 맞춰 git commit 생성. 관심사별 분리, staged diff 리뷰 포함.
---

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`
- Project commit convention: !`cat .claude/commit-convention.md 2>/dev/null || grep -A 60 -m 1 "## Commit" CLAUDE.md 2>/dev/null || echo "__USE_DEFAULT__"`

## Commit Rules

> **프로젝트 우선**: 위 "Project commit convention"이 `__USE_DEFAULT__`가 아닌 경우, 아래 기본 규칙 대신 해당 내용을 따르세요.

### Default Message Format

```
<type>: <description>
```

### Allowed Types

| type       | 사용 상황                                       |
| ---------- | ----------------------------------------------- |
| `feature`  | 새로운 기능 추가                                |
| `fix`      | 버그 수정                                       |
| `chore`    | 빌드, 설정, 리팩토링, 이름 변경 등 기능 외 변경 |
| `refactor` | 기능 변경 없이 코드 구조 개선                   |
| `test`     | 테스트 추가/수정                                |
| `docs`     | 문서 수정                                       |

### Rules

1. **type은 소문자**로 작성 (`Feature` ❌ → `feature` ✅)
2. **description은 영어 소문자**로 시작, 마침표 없이
3. **한 커밋 = 한 가지 관심사** — 섞이면 커밋 분리
4. description은 **무엇을(what)이 아닌 왜(why)/어떤 행위**를 표현

### Good Examples

```
feature: add DekAlreadyExistsError for duplicate secret detection
fix: handle race condition in fetchOrCreateDek by re-fetching on conflict
chore: rename tablePath to tableConfig for consistency
refactor: extract dek generation to private method
```

### Bad Examples

```
FEATURE: Update code            ← 대문자, 모호한 설명
fix: fixed bug                  ← 중복 표현
chore: update                   ← 너무 모호
feature: add feature and fix bug  ← 두 가지 관심사 혼재
```

## Your Task

**한 번의 응답에서 모든 스테이징과 커밋을 처리하세요.**

### Step 1: 커밋 컨벤션 확인

"Project commit convention"이 `__USE_DEFAULT__`인 경우:

1. `git log --oneline -50`으로 기존 커밋 히스토리를 분석하여 컨벤션 패턴을 파악
2. `.claude/` 디렉토리 생성 후 `.claude/commit-convention.md` 파일을 작성
3. 이후 커밋부터 해당 컨벤션을 적용

### Step 2: 관심사별 리뷰 & 커밋

변경 사항을 관심사별로 그룹핑하여 **항상 별도 커밋으로 처리**하세요. 분리 여부를 사용자에게 묻지 않습니다.

- 관심사가 하나인 경우 → 단일 커밋
- 관심사가 여러 개인 경우 → 의존성 순서대로 별도 커밋:

  ```
  기반 타입/에러 정의 → 하위 레이어 구현 → 상위 레이어 핸들링 → 테스트
  ```

**파일 내 일부 변경만 스테이징이 필요한 경우** `git add -p`를 사용하세요:

```bash
git add -p <파일>   # hunk 단위로 선택적 스테이징
```

**각 관심사 그룹 커밋 전 코드 리뷰:**

스테이징 완료 후 커밋 전에 `/review-staged`와 동일한 리뷰를 수행하세요:

1. staged diff + 관련 컨텍스트를 Read tool로 읽고 4관점(버그, 컨벤션, 보안, 설계) 리뷰
2. confidence 70+ 이슈만 보고, false positive 제외 (linter가 잡을 이슈, pre-existing, nitpick)
3. 이슈 발견 시 결과를 보여주고 AskUserQuestion으로 선택지 제공:
   - **수정** — 이슈를 수정한 뒤 커밋합니다
   - **그대로 커밋** — 이슈를 무시하고 커밋합니다
4. 이슈 없으면 바로 커밋 진행
