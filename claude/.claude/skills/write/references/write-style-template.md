# write-style.md Template

프로젝트별 `.claude/write-style.md`의 표준 스키마. 프로젝트 첫 글 작성 시 `/write-brainstorming`이 이 템플릿을 기반으로 부트스트랩합니다.

필드는 **필수 최소 4개** + **선택 확장**으로 나뉩니다. 처음에는 필수만 채우고, 글을 쓰면서 필요할 때 확장 필드를 추가합니다.

## 표준 템플릿

```markdown
---
name: <project name>
updated: YYYY-MM-DD
---

# 필수 필드

## Identity

<프로젝트/블로그의 한 줄 정체성 — 왜 존재하는가>

## Audience

<주 독자 + 언어 정책의 근거>

## Category Tree

<현재 카테고리 구조. 새 카테고리 추가 시 여기 먼저 등록>

- path/to/category: <용도>
  - ko label: <한글 라벨>
  - en label: <영문 라벨>

## i18n Policy

- languages: [ko, en]
- source_of_truth: ko
- sync_mode: lockstep # lockstep | async | ko_only
- required_pairs: true

# 선택 확장 필드 (필요 시 추가)

## Placement Rules

<카테고리 배치 규칙. 특수 케이스 명시>

- 커리어 관련 글 → career/<company>/
- 언어별 글 → tech/language/<lang>/

## Frontmatter Conventions

- title: <자유 수정 가능, slug와 분리>
- slug: <kebab-case, 한번 정하면 안정>
- date: <첫 발행 시점, 임의 수정 가능>
- categories: <형식>
- tags: <형식>

## Tone Defaults

<프로젝트 기본 톤. 개별 글에서 override 가능>

- <예: 개인 회고는 반말/다체, 기술 글은 해요체>

## Structural Conventions

<프로젝트 수준 구조 기본값>

- <예: 번호 목록보다 서사적 전개>
- <예: 소제목 최소 사용>

## Publishing Flow

1. 로컬 빌드 검증 (hugo server)
2. /git-commit → /github-pr-push → merge
3. 자동 배포

## Cross-posting

- LinkedIn: <정책>
- Twitter: <정책>

## Don'ts

<반전(reversal)에서 학습된 규칙 우선 기록>

- <예: 제목에 시리즈 접두사(N일차) 사용 금지>
- <예: 카테고리 타이틀 하드코딩 금지>
```

## 필드 설명

### Identity

한 줄로 끝. "이 블로그는 X를 위한 공간이다"처럼 목적을 선언. 이게 모든 결정의 기준점이 됨.

### Audience

누구를 향해 쓰는지. 언어 선택과 톤 결정의 근거. "개발자 동료", "나 자신의 미래", "잠재적 협업자" 등.

### Category Tree

실제 `content/` 구조를 반영. 새 카테고리가 필요하면 여기 먼저 등록하고 파일을 만듦. 파일부터 만들고 여기 누락되면 프로젝트 스타일과 실제가 어긋남.

### i18n Policy

- `lockstep`: ko/en 같은 턴에 함께 수정. Write skill이 단일 언어 수정을 거부.
- `async`: 같은 페어를 유지하되 비동기 수정 허용. Warning만.
- `ko_only`: 한국어만. en 페어 불필요.

### Placement Rules

category_tree만으로 부족한 특수 배치 규칙. "회사별로 하위 폴더" 같은 관례.

### Frontmatter Conventions

이 프로젝트의 frontmatter 스키마. title vs slug 분리 원칙은 default로 적용 권장.

### Tone Defaults

프로젝트 수준 톤. 필체 프로파일(전역)과는 다름 — 여기는 "이 프로젝트에서는 이런 톤으로 쓴다"는 결정.

### Structural Conventions

"번호 목록 금지", "소제목 최소" 같은 구조 규칙이 **이 프로젝트에서만** 적용되는 경우 여기. 전역 필체라면 style-profile.md로.

### Publishing Flow

글이 쓰여진 후 발행까지의 단계. Write skill이 Step 7 "다음 단계 안내"에서 참고.

### Cross-posting

LinkedIn, Twitter, Medium 등 크로스 포스팅 대상. 플랫폼별 변환 규칙이 있다면 여기.

### Don'ts

가장 중요한 섹션. 프로젝트에서 **하지 말 것**의 목록. 특히 반전 패턴(한번 해봤다가 되돌린 결정)에서 학습된 규칙을 여기 축적. Write skill의 Step 5(반전 감지)가 자동으로 append 제안.
