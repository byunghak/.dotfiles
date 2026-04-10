---
name: write-brainstorming
model: opus
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(ls:*), Bash(mkdir:*), Bash(find:*), Bash(cat:*), AskUserQuestion
description: 글 작성 전 메시지/배치/제목/범위/언어를 결정하고 brainstorm artifact를 생성. 프로젝트 write-style.md 없으면 부트스트랩. 초고는 생성하지 않음.
argument-hint: <글감 한 줄, URL, 또는 러프한 초안>
---

## Context

- 프로젝트 스타일: !`cat .claude/write-style.md 2>/dev/null || echo "__NO_PROJECT_STYLE__"`
- 입력: $ARGUMENTS

---

# Write Brainstorming — 글쓰기 전 설계

글을 쓰기 **전에** 결정만 하고 멈춥니다. 드래프트는 `/write`에서 작성합니다.

> **원칙**: 초고 텍스트를 생성하지 않는다. 모든 결정은 A/B/C + 추천 포맷으로 제시한다. 중립 나열 금지.

산출물은 `/write`가 바로 소비 가능한 구조입니다:

```
.claude/drafts/<slug>.brainstorm.md   ← /write의 입력
.claude/write-style.md                 ← 없으면 부트스트랩 (프로젝트당 1회)
```

---

## Step 0: 입력 확인

`$ARGUMENTS`가 비어 있으면 AskUserQuestion:

> "어떤 글을 쓸지 시드를 알려주세요. 한 줄 아이디어, 러프한 초안, 또는 참고할 URL 모두 가능합니다."

## Step 1: 프로젝트 컨텍스트 감지

1. **프로젝트 타입 감지**:
   - `hugo.toml`/`config.toml`/`config.yaml` → Hugo
   - `_config.yml` + `_posts/` → Jekyll
   - `next.config.js` + `pages/posts` 또는 `app/blog` → Next.js
   - `content/` 디렉토리 + 마크다운 → Generic MD
2. **글 저장 위치** 파악: `content/posts/`, `_posts/`, `src/content/blog/` 등
3. **최근 글 1-2개** 훑어서 톤·구조 참고 (`Glob`로 최신 .md 찾고 `Read`)
4. **i18n 페어 패턴** 감지: `.ko.md`/`.en.md` 같은 suffix, 또는 `content/ko/`/`content/en/` 같은 디렉토리 분리

## Step 2: write-style.md 로드 또는 부트스트랩

### 있는 경우

- 내용을 mental model에 탑재. 이후 결정은 이 규칙을 따르되 override 가능.
- 충돌 시 사용자에게 "이번 글만 override" vs "write-style.md 갱신" 중 선택 요청.

### 없는 경우 — 최소 필드 인터뷰

다음 4개 필드만 먼저 채웁니다. 나머지는 처음 사용 시점에 자연스럽게 추가.

1. **blog_identity** (자유 입력): "이 블로그/프로젝트의 한 줄 정체성은? 왜 존재하나요?"
2. **audience** (자유 입력): "주 독자는 누구인가요? (언어 포함)"
3. **category_tree** (자동 추론 + 확인):
   - `content/posts/*/` 하위 디렉토리를 스캔
   - 감지된 구조를 표시하고 "이 구조가 맞나요?" 확인
4. **i18n_policy** (AskUserQuestion 2-3 옵션):
   - `ko_only` — 한국어만
   - `lockstep` — ko/en 모두, 같은 시점에 같이 수정 (감지되면 추천)
   - `async` — ko/en 모두, 비동기 번역 허용

채워진 값을 `references/write-style-template.md` 기반으로 `.claude/write-style.md`에 작성. 작성 전 사용자에게 diff 보여주고 승인 요청.

## Step 3: 결정 단계 (A/B/C + 추천)

각 항목을 **순차적으로** 결정. 각 결정은 AskUserQuestion으로, 항상 **추천 옵션 1개 + 근거**를 포함.

### 3.1 Message (핵심 메시지)

> "독자가 이 글을 읽고 가져갈 **한 가지**는 무엇인가요?"

자유 입력. 시드가 이미 메시지를 함축하면 Claude가 한 줄로 정제해서 확인.

### 3.2 Placement (배치)

- category_tree 기반으로 2-3 경로 옵션 제시
- 새 카테고리가 필요해 보이면 "새 카테고리 생성" 옵션도 포함
- 추천 1개 + 근거 명시

### 3.3 Title + Slug (분리 락)

- **Title**: 자유 입력 또는 Claude의 2-3 제안 + 추천
- **Slug**: Claude가 제안한 kebab-case 기본값 + 확인
- **규칙**: slug는 이후 제목 수정과 **무관하게** 안정. 이 원칙을 사용자에게 명시.

### 3.4 Scope Boundaries

- 이 글이 **다룰 것 / 다루지 않을 것** 각 2-3개
- 확장 유혹을 미리 차단

### 3.5 Language Coverage

- i18n_policy 기본값 제시 + "이번만 override?" 확인
- lockstep이면 ko/en 둘 다 기본

## Step 4: Brainstorm Artifact 작성

`.claude/drafts/<slug>.brainstorm.md` 파일 생성. `references/brainstorm-template.md` 형식 사용.

파일 생성 전 사용자에게 내용을 보여주고 승인 요청.

## Step 5: 다음 단계 안내

```
다음 단계:
  /write <slug>

또는 직접 경로 지정:
  /write .claude/drafts/<slug>.brainstorm.md
```

---

## 금지 사항

- **초고 텍스트 생성 금지** — 아이디어/메시지 요약은 OK, 문단 작성은 금지
- **중립 나열 금지** — 모든 선택지에 추천 1개 + 근거
- **질문 폭격 금지** — 한 번에 하나씩 (AskUserQuestion은 상관없음, 다지선다 OK)
- **write-style.md 자동 수정 금지** — 변경 전 항상 diff 보여주고 승인
