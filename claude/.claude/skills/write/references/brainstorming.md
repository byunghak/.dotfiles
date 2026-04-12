# Write Brainstorming — 글쓰기 전 설계

글을 쓰기 **전에** 결정만 하고 멈춥니다. 드래프트는 Compose 경로에서 작성합니다.

> **원칙**: 초고 텍스트를 생성하지 않는다. 모든 결정은 A/B/C + 추천 포맷으로 제시한다. 중립 나열 금지.
> **진입점**: 메인 SKILL.md 라우터에서 Step 1 (신규) 또는 Step 7 (재진입)로 진입.

산출물은 Compose 경로가 바로 소비 가능한 디렉토리 구조입니다:

```
.claude/drafts/YYYY-MM-DD-<slug>/
  OVERVIEW.md                   ← 큰 기획 (왜/무엇을)
  _manifest.yaml                ← 글 목록 (단일이어도 엔트리 1개)
  01-<article-slug>.brainstorm.md   ← Compose 의 입력 (글 1개 단위)
  02-<article-slug>.brainstorm.md
  ...
.claude/write-style.md          ← 없으면 부트스트랩 (프로젝트당 1회)
```

각 `NN-<article>.brainstorm.md` 는 프론트매터에 `status: draft | ready | done` 를 가진다. **ready** 상태만 Compose 경로가 수용한다.

---

## Step 1: 프로젝트 컨텍스트 감지

1. **프로젝트 타입 감지**:
   - `hugo.toml` / `config.toml` / `config.yaml` → Hugo
   - `_config.yml` + `_posts/` → Jekyll
   - `next.config.js` + `pages/posts` 또는 `app/blog` → Next.js
   - `content/` 디렉토리 + 마크다운 → Generic MD
2. **글 저장 위치** 파악: `content/posts/`, `_posts/`, `src/content/blog/` 등
3. **최근 글 1-2개** 훑어서 톤·구조 참고 (Glob 로 최신 `.md` 찾고 Read)
4. **i18n 페어 패턴** 감지: `.ko.md` / `.en.md` suffix, 또는 `content/ko/` / `content/en/` 디렉토리 분리

## Step 2: write-style.md 로드 또는 부트스트랩

### 있는 경우

- 내용을 mental model 에 탑재. 이후 결정은 이 규칙을 따르되 override 가능
- 충돌 시 "이번 글만 override" vs "write-style.md 갱신" 중 선택 요청

### 없는 경우 — 최소 필드 인터뷰

다음 4개 필드만 먼저 채운다:

1. **blog_identity** (자유): "이 블로그/프로젝트의 한 줄 정체성은?"
2. **audience** (자유): "주 독자는 누구인가요? (언어 포함)"
3. **category_tree** (자동 추론 + 확인):
   - `content/posts/*/` 하위 디렉토리를 스캔
   - 감지된 구조를 표시하고 "이 구조가 맞나요?" 확인
4. **i18n_policy** (AskUserQuestion):
   - `ko_only` — 한국어만
   - `lockstep` — ko/en 모두, 같은 시점에 동기화 (감지되면 추천)
   - `async` — ko/en 모두, 비동기 번역 허용

`references/write-style-template.md` 기반으로 `.claude/write-style.md` 에 작성. 작성 전 diff 보여주고 승인 요청.

## Step 3: 초기 결정 (A/B/C + 추천)

각 항목을 **순차적으로** 결정. 각 결정은 AskUserQuestion 으로, 항상 **추천 옵션 1개 + 근거**를 포함.

### 3.1 Core Message

> "독자가 이 글을 읽고 가져갈 **한 가지**는 무엇인가요?"

자유 입력. 시드가 이미 메시지를 함축하면 Claude 가 한 줄로 정제해서 확인.

### 3.2 Audience + Platform

- 청중 1-3 옵션 (write-style.md 의 audience 기본값 + 대안)
- 플랫폼 (블로그 / 링크드인 / 트위터 / 기타) 선택
- 추천 1개 + 근거

### 3.3 Rough Scope

이 글/시리즈가 **다룰 것 2-3개 / 다루지 않을 것 2-3개**. 나중에 PM 판정에서 분리 근거로 사용.

## Step 4: PM Agent — 규모 판단 + 분리 제안

Step 3 결정을 바탕으로 **pm-write-agent** 를 호출하여 글을 단일로 쓸지 시리즈로 분리할지 판단한다.

Agent tool (subagent_type: pm-write-agent) 로 호출:

```
당신은 pm-write-agent 에이전트입니다.

다음 draft topic 을 검토하고 규모 판단 + 글 1개 단위 분리 제안을 하세요.

## Draft Topic
[Step 3 에서 결정한 message, audience, platform, scope 를 구조화해서 전달]

## Project Context
- blog_identity: [write-style.md 에서]
- audience: [write-style.md 에서]
- category_tree: [write-style.md 에서]
- i18n_policy: [write-style.md 에서]

출력 형식: pm-write-agent.md 의 Output Contract 를 따를 것.
```

### PM Verdict 처리

**SINGLE 판정**:

- 글 1편으로 진행
- 사용자 승인 불필요 — 바로 Step 5

**SPLIT 판정**:

- PM 이 제안한 manifest 를 사용자에게 보여주고 AskUserQuestion 으로 승인 요청
- 선택지:
  - `승인 (⭐ 추천)` — 제안대로 진행
  - `수정` — 사용자가 조정사항 명시 → PM 재호출
  - `SINGLE 로 강제` — 분리하지 않고 1편으로
- 승인되면 Step 5 로 진행

**에스컬레이션 (5개 초과 article 필요)**:

- PM 이 범위 축소를 요청한 경우 → Step 3 로 돌아가 사용자와 범위 재협의

## Step 5: 글별 세부 결정 (A/B/C + 추천)

PM 판정된 각 article 마다 개별 결정:

### 5.1 Placement (배치)

- category_tree 기반으로 2-3 경로 옵션 제시
- 새 카테고리 필요하면 "새 카테고리 생성" 옵션 포함
- 추천 1개 + 근거

### 5.2 Title + Slug (분리 락)

- **Title**: 자유 입력 또는 Claude 의 2-3 제안 + 추천
- **Slug**: Claude 가 제안한 kebab-case 기본값 + 확인
- **규칙**: slug 는 이후 제목 수정과 **무관하게** 안정. 원칙 명시.

### 5.3 Scope Boundaries (세부)

- 이 article 이 **다룰 것 / 다루지 않을 것** 각 2-3개
- 시리즈 내 다른 article 과의 경계 확인

### 5.4 Language Coverage

- i18n_policy 기본값 제시 + "이번만 override?" 확인
- lockstep 이면 ko/en 둘 다 기본

## Step 6: 디렉토리 + 파일 작성

### 6.1 디렉토리 생성

`.claude/drafts/YYYY-MM-DD-<series-slug>/`

series-slug 는 PM SPLIT 이면 전체 시리즈 이름, SINGLE 이면 article slug 와 동일.

### 6.2 OVERVIEW.md (항상 작성)

전체 기획 문서 — 왜/무엇을 관점:

```markdown
# Overview: <시리즈 또는 글 제목>

## 배경

왜 이 글/시리즈가 필요한가

## 핵심 메시지

독자가 가져갈 것 (전체 기준)

## 청중

주 독자 + 플랫폼

## 범위

### 포함

- ...

### 제외

- ...

## 작업 분리 (PM 판정)

- **Verdict**: SINGLE | SPLIT
- **Rationale**: [PM 근거 요약]
- **Articles**: (SPLIT 인 경우 목록)
  1. 01-<slug> — <제목>
  2. 02-<slug> — <제목>

## 참고 자료

- URL / 원문 / 영감 소스
```

### 6.3 `_manifest.yaml` (항상 작성)

```yaml
series: <series-slug>
overview: OVERVIEW.md
articles:
  - id: <kebab-case>
    file: 01-<article-slug>.brainstorm.md
    title_draft: "<제목>"
    audience: "<청중>"
```

단일 글 예시:

```yaml
series: 2026-04-11-my-thoughts
overview: OVERVIEW.md
articles:
  - id: main
    file: 01-main.brainstorm.md
    title_draft: "오늘의 생각"
    audience: "개발자"
```

### 6.4 `NN-<article-slug>.brainstorm.md` (article 별로)

각 글의 브레인스토밍 결과. 프론트매터에 **status** 필드 포함:

```markdown
---
id: <kebab-case>
slug: <article-slug>
status: draft # draft | ready | done (신규는 draft 로 시작)
title: "<제목 초안>"
placement: <category path>
message: "<핵심 메시지 한 줄>"
audience: "<청중>"
platform: "<플랫폼>"
languages: [ko, en]
---

# <제목>

## 배경 / Hook

## 핵심 메시지

## 구조 (개요)

- 도입
- 전개
- 결론

## 포함 / 제외

### 포함

- ...

### 제외

- ...

## 참고 자료

- ...
```

**status 초기값은 `draft`.** 사용자가 이 단계에서 "완성" 을 명시적으로 선택하면 `ready` 로 승격 (다음 Step 8).

## Step 7: 재진입 모드 (기존 draft 편집)

메인 SKILL.md 라우터에서 재진입으로 판별된 경우 여기로 진입:

1. `.claude/drafts/<slug>/_manifest.yaml` 로드
2. 각 article 의 `status` 확인
3. AskUserQuestion: "어떤 article 을 편집할까요?"
   - draft/ready article 목록 제시
   - **done 은 잠김** (다시 편집하려면 수동으로 status 수정 필요)
4. 선택된 article 의 본문/프론트매터 Read
5. 각 결정 필드를 다시 AskUserQuestion 으로 확인/수정
6. 승인되면 파일 업데이트
7. Step 8 로 (status 처리)

## Step 8: status 처리 (신규 + 재진입 공통)

각 편집한 article 에 대해 AskUserQuestion:

```
이 article 의 상태를 어떻게 할까요?

- draft (추가 브레인스토밍 필요) — 나중에 다시 편집
- ready (완성본, Compose 로 진행 가능) ⭐ 추천 (내용이 충분히 결정되었을 때)
```

선택대로 frontmatter `status` 업데이트.

## Step 9: 완료 안내

```
✅ Brainstorming 완료

디렉토리: .claude/drafts/YYYY-MM-DD-<slug>/
├── OVERVIEW.md          (전체 기획)
├── _manifest.yaml       (글 목록)
└── NN-<article>.brainstorm.md × N

PM Verdict: SINGLE | SPLIT (N articles)

상태별:
  draft: [ids]   — 추가 편집 필요
  ready: [ids]   — Compose 로 진행 가능

다음 단계:
  /write .claude/drafts/<slug>/                          (ready → Compose | draft → 재편집)
  /write .claude/drafts/<slug>/NN-xxx.brainstorm.md      (개별 Compose)
```

모든 article 이 ready 이면 AskUserQuestion: "바로 Compose 로 넘어갈까요?"

- **진행 (⭐ 추천)** — Compose 경로로 자동 전환
- **보류** — 여기서 종료

---

## 금지 사항

- **초고 텍스트 생성 금지** — 아이디어/메시지 요약은 OK, 문단 작성은 금지
- **중립 나열 금지** — 모든 선택지에 추천 1개 + 근거
- **질문 폭격 금지** — 한 번에 하나씩 (AskUserQuestion 다지선다는 OK)
- **write-style.md 자동 수정 금지** — 변경 전 항상 diff 보여주고 승인
- **done 상태 article 재편집 금지** — 실수로 완료된 글을 덮어쓰지 않도록
- **5개 초과 분리 금지** — PM 에스컬레이션으로 범위 축소
