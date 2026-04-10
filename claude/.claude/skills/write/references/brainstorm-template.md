# Brainstorm Artifact Template

`/write-brainstorming`이 생성하고 `/write`가 소비하는 artifact의 표준 형식.

위치: `.claude/drafts/<slug>.brainstorm.md`

발행 후 아카이브: `.claude/drafts/archive/<slug>.brainstorm.md`

---

## 템플릿

```markdown
---
slug: <kebab-case-slug>
created: YYYY-MM-DD
status: draft # draft | in-progress | published | archived
placement: <category path, e.g. career/dable>
languages: [ko, en]
---

# <한국어 제목>

## Message

<독자가 가져갈 한 가지 — 한 줄>

## Title Options

- ko: <최종 한국어 제목>
- en: <최종 영문 제목>
- alternates_considered:
  - <대안 1>
  - <대안 2>

## Placement

<전체 경로>

path: content/posts/<placement>/<slug>.<lang>.md

rationale: <왜 이 위치인가>

## Scope

### In (포함)

- <다룰 것 1>
- <다룰 것 2>

### Out (제외)

- <다루지 않을 것 1>
- <다루지 않을 것 2>

## Seed

<원본 시드 — 사용자가 제공한 한 줄 아이디어, URL, 또는 러프 초안>

## Structure Sketch (선택)

<아주 간단한 뼈대. 초고 X, 문단 1-2줄 요약 O>

- 도입: <무엇으로 시작>
- 전개: <어떤 흐름>
- 결론: <어떻게 끝>

## Language Coverage

- source_of_truth: ko
- sync_mode: lockstep
- ko path: content/posts/<placement>/<slug>.ko.md
- en path: content/posts/<placement>/<slug>.en.md

## References

- 필체 프로파일: ~/.claude/skills/write/references/style-profile.md
- 프로젝트 스타일: .claude/write-style.md
- 유사 글 (선택): <기존 글 경로 1-2개>

## Decisions Log

<brainstorming 과정에서 내린 결정과 근거. 나중에 돌아볼 수 있도록>

- YYYY-MM-DD HH:MM — <결정>: <근거>
```

---

## 필드 설명

### Frontmatter

- **slug**: 한 번 정하면 안정. 제목 수정과 무관.
- **status**: `draft` (brainstorming 완료, 아직 초고 없음) → `in-progress` (write로 작성 중) → `published` (발행됨) → `archived` (발행 후 보관)
- **placement**: category path. 실제 파일 경로를 유추할 수 있어야 함.
- **languages**: 이 글이 다룰 언어. i18n_policy의 override.

### Message

**한 줄**. 독자가 글을 읽고 기억할 한 가지. 이게 흐릿하면 brainstorming을 재수집해야 함. 초고 작성 중에도 이 한 줄을 북극성으로 씀.

### Title Options

최종 제목 + 고려했던 대안 기록. 나중에 제목 수정 유혹이 올 때 "왜 이 제목이었는지" 돌아볼 수 있음.

### Placement

경로 + 근거. 새 카테고리 생성이면 `write-style.md`의 category_tree도 함께 업데이트하도록 안내.

### Scope (In/Out)

확장 유혹 차단용. "이것도 넣을까?" 싶을 때 Out 목록을 보고 의식적으로 결정.

### Seed

원본 아이디어 기록. 이후 글이 시드에서 얼마나 벗어났는지 비교 가능.

### Structure Sketch

**선택 필드**. 너무 일찍 구조를 고정하면 초고의 유연성을 잃음. 뼈대가 뚜렷할 때만 적음.

### Language Coverage

각 언어 파일의 실제 경로. write가 이 경로를 따라 파일 생성.

### References

참조할 레이어들의 경로. write가 레이어 병합 시 이 목록을 사용.

### Decisions Log

brainstorming 과정에서 반복적으로 갈등했던 결정과 최종 근거. 나중에 같은 종류의 글을 쓸 때 패턴 학습 자료.
