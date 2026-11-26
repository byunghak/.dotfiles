---
name: github-ship
model: opus
effort: medium
allowed-tools: Read, Agent, AskUserQuestion, Bash(git rev-parse:*)
description: branch → commit → push/PR → review → merge 전체 파이프라인. 디폴트 브랜치면 생성, PR 분리 필요 시 제안, 리뷰 후 머지까지.
argument-hint: <작업 설명 또는 브랜치명> [--no-merge] [--no-review]
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

`github-ship` 에이전트를 spawn 하여 전체 파이프라인을 실행한다. prompt 는 아래 틀을 그대로 쓰고, `<옵션>` 칸만 채운다:

```
github-ship 에이전트를 호출합니다.

옵션: <$ARGUMENTS 의 --no-merge·--no-review·--draft 등 `--` 옵션을 빠짐없이 그대로. 없으면 "없음">

작업 설명: [$ARGUMENTS]

ship 파이프라인을 실행하세요. 옵션 줄의 옵션이 정한 단계는 건너뜁니다.
```

- prompt 를 새로 쓰거나 줄여 쓰지 않는다. `Phase 1 → … → Phase 5` 목록을 prompt 에 적지 않는다 — 목록을 베끼면 Phase 이름이 붙은 `--no-merge` 만 옮겨지고 `--no-review` 가 빠져, 이미 리뷰한 PR 에 Phase 4 code-reviewer 가 다시 돈다
- `--no-merge` 는 Phase 5 를 skip 한다. `--no-review` 는 커밋 전 staged diff 리뷰와 Phase 4 code-reviewer 를 skip 하고 codex 리뷰만 돌린다 (자세한 범위는 agent 정의)
- agent 최종 보고의 `Phase 4:` 줄이 `--no-review` 와 맞지 않으면(옵션을 줬는데 code-reviewer `실행`) 호출한 쪽에 그대로 알린다

## Agent spawn 실패 시

github-ship 에이전트 spawn 이 실패(rate limit, 에러 등)하면 git/gh 명령을 직접 실행하지 않는다. 브랜치 확인·PR 분리·리뷰는 agent 절차 안에 있어, 직접 실행하면 그 검사를 건너뛴다.

1. 사용자에게 실패 사유를 보고하고 대기한다
2. 사용자가 재시도를 요청하면 다시 Agent tool 로 spawn 을 시도한다
