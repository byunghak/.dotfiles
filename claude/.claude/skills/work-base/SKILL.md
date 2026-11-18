---
name: work-base
description: 프로젝트 /work skill 이 주입해 쓰는 공통 개발 흐름(이슈 분석 → Brainstorm → PR 분리 → Plan → TDD Code → 리뷰 → Ship → 머지·정리). 직접 호출용이 아니다.
disable-model-invocation: true
---

# work-base

프로젝트 `/work` 의 공통 본문이다. 직접 호출하면 진행하지 않고, 아래 연결 방법을 안내한 뒤 멈춘다.

## 구성

- `core.md` — 흐름·원칙·협상 대상 아닌 규칙·단계 표. 프로젝트 SKILL.md 가 셸 주입(`config-template.md` 의 `cat` 줄)으로 본문에 넣는다
  - 프로젝트 밖 경로라 권한 확인 없이 실행되지 않으면, 그 줄은 실행 안내(`run this first`)로 바뀌고 세션이 `cat` 을 실행해 읽는다
- `references/steps/*.md` — 단계별 공통 절차. 단계에 들어갈 때 읽는다
- `config-template.md` — 프로젝트 SKILL.md 틀과 `## 설정` 칸 정의

## 프로젝트에 연결

1. `config-template.md` 를 `<repo>/.claude/skills/work/SKILL.md` 로 옮겨 `## 설정` 값과 추가 규칙을 채운다
2. 단계별 프로젝트 고유 규칙은 `<repo>/.claude/skills/work/references/addenda/<step 파일>` 에 둔다 (공통 파일과 같은 이름, 없으면 건너뜀)
3. 프로젝트 쪽에 둔다: `references/test-commands.md`·`references/plan-template.md`·`scripts/runlog.sh`·`scripts/review_precheck.py`, planner·plan-reviewer·implementer·리뷰어 agent

- 프로젝트 skill 이름은 `work` 로 둔다. global 에 같은 이름 skill 이 있으면 global 이 project 를 가리므로, 공통 본문은 이름이 다른 이 skill 에 둔다
