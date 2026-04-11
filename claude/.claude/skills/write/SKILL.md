---
name: write
model: opus
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(ls:*), Bash(cat:*), Bash(hugo:*), Bash(find:*), Bash(mkdir:*), AskUserQuestion
description: 글 작성/리비전/첨삭 통합. brainstorm artifact 또는 기존 파일 또는 텍스트 블록을 받아 자동으로 Compose/Revise/Edit 모드 판별. 수정마다 필체 프로파일 누적 + bilingual lockstep 강제.
argument-hint: <slug | 파일 경로 | 텍스트 블록>
---

## Context

- 필체 프로파일: !`cat ~/.claude/skills/write/references/style-profile.md 2>/dev/null || echo "__NO_PROFILE__"`
- 프로젝트 스타일: !`cat .claude/write-style.md 2>/dev/null || echo "__NO_PROJECT_STYLE__"`
- 입력: $ARGUMENTS

---

# Write — 글 작성/리비전/첨삭 통합

하나의 skill로 **세 가지 모드**를 자동 감지해서 처리합니다.

| 모드        | 입력                                                               | 동작                              |
| ----------- | ------------------------------------------------------------------ | --------------------------------- |
| **Compose** | slug 또는 `.claude/drafts/<slug>.brainstorm.md` (타깃 파일 미존재) | 초고 생성 (i18n 페어 포함)        |
| **Revise**  | 기존 글 파일 경로                                                  | 타깃 범위 리비전 ("N-M행만 교체") |
| **Edit**    | 텍스트 블록 (파일 경로 아님)                                       | 리라이팅 + 수정안 제시            |

세 모드 모두 공통:

- 레이어 병합 (`style-profile` < `write-style` < `brainstorm`)
- A/B/C + 추천 포맷
- Bilingual lockstep (i18n_policy 준수)
- 수정 후 **필체 프로파일 누적**
- **커밋 금지**

---

## Step 0: 입력 해석 + 모드 자동 감지

`$ARGUMENTS`를 분류:

```
IF $ARGUMENTS == "":
    AskUserQuestion: "무엇을 작성할까요? (draft 디렉토리 / 파일 경로 / 붙여넣을 글)"

ELIF $ARGUMENTS 가 .claude/drafts/<slug>/ 디렉토리:
    → brainstorm 디렉토리 모드
    → _manifest.yaml 로드 + 사용자에게 어떤 article 작업할지 선택 (status=ready 만 노출)
    → 선택된 NN-*.brainstorm.md 를 Step 0-1 로 전달

ELIF $ARGUMENTS 가 .claude/drafts/<slug>/NN-*.brainstorm.md 파일:
    → 해당 article 브레인스토밍 파일
    → Step 0-1 로

ELIF $ARGUMENTS 가 실존 글 파일 경로 (content/posts/... 등):
    → REVISE

ELSE ($ARGUMENTS 가 200자 이상 텍스트):
    → EDIT
```

### Step 0-1: brainstorm artifact status 게이트

Brainstorm 파일(`NN-*.brainstorm.md`) 로 진입한 경우:

1. 파일의 frontmatter `status` 를 확인
2. 판정:
   - **`status: ready`** → 진행 (Step 1 로)
   - **`status: draft`** → 거부:
     ```
     ❌ 이 article 은 아직 draft 상태입니다.
     /write-brainstorming <draft-dir> 로 편집을 완료하고 status 를 ready 로 승격해주세요.
     ```
   - **`status: done`** → 거부 (이미 완료됨):
     ```
     ⚠️ 이 article 은 이미 done 상태입니다. 수정하려면 기존 글 파일을 REVISE 모드로 여세요.
     ```
   - **status 없음**: 경고 + draft 로 취급하여 거부
3. 타깃 글 파일(`content/posts/<placement>/<slug>.<lang>.md`) 존재 여부 확인:
   - 파일 없음 → COMPOSE 모드
   - 파일 있음 → REVISE 모드 (+ brainstorm 을 참조 자료로)

모호하면 AskUserQuestion 으로 확인.

## Step 1: 레이어 병합

순서대로 읽고 병합. **뒤가 앞을 override.**

1. **필체 프로파일** (`~/.claude/skills/write/references/style-profile.md`) — 사용자 전역 필체
2. **프로젝트 스타일** (`.claude/write-style.md`) — 이 프로젝트의 방향성/규칙
3. **Brainstorm artifact** (있을 경우) — 이번 글의 override

충돌 발생 시:

- 프로젝트 스타일이 필체 프로파일을 부정 → 프로젝트 우선
- brainstorm이 프로젝트 스타일을 부정 → 이번 글만 override, 사용자에게 "write-style.md 갱신할지" 나중(Step 6)에 질문

레퍼런스 없음 처리:

- `__NO_PROFILE__`: 기본 원칙으로 진행 (`references/edit-rewriting-rules.md` 참조)
- `__NO_PROJECT_STYLE__` + Compose/Revise 모드: "먼저 `/write-brainstorming`을 실행하시겠어요?" 권유. Edit 모드는 그대로 진행.

## Step 2: 모드별 실행

### Step 2A: Compose Mode

1. **Brainstorm artifact 읽기**: slug, message, placement, title, scope, languages
2. **타깃 경로 확정**: placement + slug → `content/posts/<placement>/<slug>.<lang>.md`
3. **Frontmatter 조립**: 프로젝트 스타일의 frontmatter_conventions 따름
4. **초고 프레임 제시**:
   - **먼저 개요만** (도입 / 전개 / 결론 한 줄씩) 제시하고 AskUserQuestion으로 승인
   - 승인 후 초고 본문 생성
5. **언어별 초고**: i18n_policy에 따라 ko/en 동시 생성. source_of_truth 먼저, 번역본 나중.
6. **파일 쓰기**: 승인 후 `Write`로 파일 생성

> **중요**: 초고 작성 시 스타일 프로파일의 리듬·구조 패턴을 참고. 예: "단문 우세, 대시 부연, 오프닝 회수 마무리"가 프로파일에 있으면 초고도 그 리듬으로.

### Step 2B: Revise Mode

1. **타깃 파일 읽기** (ko/en 페어 모두)
2. **수정 범위 파악**: 사용자 요청을 문단/문장/제목 중 어느 레벨인지 분류
3. **수정 범위 명시**:
   ```
   기존 본문 X-Y행은 그대로 유지하고, Z-W행을 교체합니다.
   ```
   주변 보존을 명시적으로 선언.
4. **A/B/C 수정안 제시** (+ 추천 + 근거)
5. **사용자 승인** 후 `Edit` tool로 적용. **ko/en 같은 턴에 적용** (i18n_policy 준수).
6. **Before/After 테이블** 출력 + intent 한 줄

### Step 2C: Edit Mode

`references/edit-rewriting-rules.md`를 로드해서 상세 원칙 적용.

1. **글 파악**: 언어 감지, 플랫폼 추정(블로그/링크드인/기타), 핵심 메시지 추출
2. **리라이팅**: rewriting-rules.md의 언어·플랫폼별 원칙 적용. 단, **필체 프로파일이 기본 원칙과 충돌 시 프로파일 우선**.
3. **출력 포맷**:

   ```
   ## 수정본
   [리라이팅된 전체 글]

   ## 주요 변경 사항
   | 항목 | 원본 | 수정 | 이유 |
   |---|---|---|---|

   ## 추가 제안 (선택)
   [적용하지 않은 고려사항 1-3]
   ```

4. **피드백 반영**: AskUserQuestion으로 "다르게 고쳤으면 하는 부분?". 있으면 재수정.

## Step 3: Bilingual Lockstep 검증

`write-style.md`의 `i18n_policy.sync_mode`가 `lockstep`이면:

- 한 언어만 수정 시도를 **거부**하고 다른 언어도 같은 턴에 수정.
- Revise/Compose 모드에서 페어 중 한쪽만 수정하면 에러.
- Edit 모드는 단일 텍스트 블록이면 해당 없음.

sync_mode가 `async`면 경고만 출력하고 진행.

## Step 4: 빌드 검증 (선택적)

프로젝트 타입별 검증 명령:

| 타입    | 명령                                 |
| ------- | ------------------------------------ |
| Hugo    | `hugo --cleanDestinationDir --quiet` |
| Jekyll  | `bundle exec jekyll build`           |
| Next.js | `next build` (느리면 skip)           |
| Generic | skip                                 |

에러 발생 시 내용 보고. 파일 지정 없는 Edit 모드는 skip.

## Step 5: 반전 감지 → 규칙 승격 제안

**같은 세션 내**에서 패턴 반전 감지:

- 예: 사용자가 "휴직 1일차:" 접두사를 추가했다가 다음 턴에 제거
- 예: A/B/C 중 이전에 선택한 옵션과 반대 방향으로 재선택

감지 시 AskUserQuestion:

> "방금 전과 반대 방향으로 결정하셨네요. 이걸 `.claude/write-style.md`의 규칙으로 추가해서 앞으로 같은 실수를 피할까요?"

승인 시 write-style.md의 `Don'ts` 또는 `Structural Conventions` 섹션에 append.

## Step 6: 필체 프로파일 누적 업데이트

모든 모드에서 수정이 완료된 후:

1. **관찰 기록**: 사용자가 승인한 표현/구조 = 선호, 수정 요청한 부분 = 비선호
2. **`~/.claude/skills/write/references/style-profile.md` 업데이트**:
   - 빈도 기반 병합 (덮어쓰지 않고 카운트 증가)
   - 충돌 시 빈도 높은 쪽 우세
3. 업데이트 내용은 출력에 간단히 요약 ("선호 추가: X, 비선호 추가: Y")

포맷은 `references/style-profile-schema.md` 참조.

## Step 7: Brainstorm status 전환 (Done hook)

Compose 모드에서 **성공적으로** 초고가 생성된 경우에만:

1. 원본 `NN-*.brainstorm.md` 파일의 frontmatter `status` 를 `ready` → `done` 으로 업데이트 (Edit tool 사용)
2. 실패/중단/REVISE/EDIT 모드는 상태 변경하지 않음
3. 출력에 명시:

   ```
   📦 Brainstorm status 전환: ready → done
   파일: .claude/drafts/<slug>/NN-<article>.brainstorm.md
   ```

> **주의**: 같은 세션에서 동일 브레인스토밍을 재사용하고 싶다면 수동으로 status 를 ready 로 되돌려야 한다.

## Step 8: 다음 단계 안내

- 수정 사항 검증 원하시면 로컬 빌드 띄우세요 (Hugo면 `hugo server`)
- 커밋은 `/git-commit`, PR은 `/github-pr-push`
- **자동 커밋 금지**

---

## 금지 사항

- **자동 커밋 금지** — 명시적 요청 전까지 `git commit` 실행 안 함
- **Bilingual lockstep 위반 금지** — sync_mode=lockstep에서 단일 언어 수정 거부
- **A/B/C 없이 바로 수정 적용 금지** — 수정안은 항상 옵션 + 추천, 사용자 승인 후 적용
- **Brainstorm artifact 없이 Compose 금지** — Compose 모드는 반드시 artifact 필요 (없으면 `/write-brainstorming` 안내)
- **write-style.md 자동 수정 금지** — 반전 감지 후에도 사용자 승인 거쳐서만 갱신
