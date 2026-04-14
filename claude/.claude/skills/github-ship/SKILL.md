---
name: github-ship
model: opus
effort: medium
allowed-tools: Read, Agent, AskUserQuestion, Bash(git rev-parse:*)
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

## 실행

`github-ship` 에이전트를 spawn하여 전체 파이프라인을 실행한다:

```
github-ship 에이전트를 호출합니다.

작업 설명: [$ARGUMENTS]

ship 파이프라인을 실행하세요:
Phase 1 (Branch Setup) → Phase 2 (Commit) → Phase 3 (Push & PR) → Phase 4 (Code Review) → Phase 5 (Merge)
```

`--no-merge` 옵션이 있으면 github-ship에 전달하여 Phase 5를 skip한다.
