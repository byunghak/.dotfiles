---
name: git-branch
model: opus
effort: low
disable-model-invocation: true
allowed-tools: Bash(git branch:*), Bash(git checkout:*), Bash(git log:*), Bash(git remote:*), Bash(mkdir:*), AskUserQuestion
description: 프로젝트 컨벤션에 맞춰 git branch 생성. 기존 브랜치 패턴 자동 감지.
---

## Context

- Current branch: !`git branch --show-current`
- Recent branches: !`git branch --sort=-committerdate --all --format='%(refname:short)' --no-contains=HEAD | head -20`
- Default remote branch: !`git remote show origin 2>/dev/null | grep 'HEAD branch'`
- Project branch convention: !`cat .claude/branch-convention.md 2>/dev/null || grep -A 40 -m 1 "## Branch" CLAUDE.md 2>/dev/null || echo "__USE_DEFAULT__"`

## Your Task

### Step 1: 브랜치 컨벤션 확인

"Project branch convention"이 `__USE_DEFAULT__`인 경우:

1. 위 "Recent branches" 목록을 분석하여 네이밍 패턴을 파악
2. `.claude/` 디렉토리 생성 후 `.claude/branch-convention.md` 파일을 작성
3. 이후 브랜치 생성에 해당 컨벤션 적용

### Step 2: 브랜치명 결정

사용자가 브랜치명 또는 작업 내용을 제공한 경우 → 컨벤션에 맞게 변환하여 생성
사용자가 아무것도 제공하지 않은 경우 → AskUserQuestion으로 어떤 작업을 위한 브랜치인지 물어보세요

**기본 separator**: 컨벤션이 없고 히스토리에서도 판단할 수 없는 경우, 단어 구분자로 underscore(`_`)를 사용

### Step 3: 브랜치 생성

```bash
git checkout -b <branch-name>
```
