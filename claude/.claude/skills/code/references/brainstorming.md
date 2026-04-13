# Code Brainstorming — 요구사항 탐색 + Spec/Plan 작성

코드 구현 전 **요구사항을 탐색**하고, **접근법을 결정**하고, **PR 단위로 분리된 plan 을 작성**합니다.

> **진입점**: 메인 SKILL.md 라우터에서 Step 1 (신규) 또는 Step 8 (재진입)로 진입.

산출물은 Pipeline 경로로 바로 자동 실행 가능한 디렉토리 구조입니다:

```
.claude/plans/YYYY-MM-DD-<topic>/
  DESIGN.md           ← 큰 설계 문서 (why/what)
  _dag.yaml           ← sub-task 의존성 (단일이어도 엔트리 1개)
  01-<task>.md        ← work 실행 단위 (how/execute)
  02-<task>.md
  ...
```

---

## Step 1: 컨텍스트 수집

1. 프로젝트 타입 감지: `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`
2. CLAUDE.md 읽기 (있으면) — 프로젝트 규칙/패턴 파악
3. `git log --oneline -10` — 최근 작업 흐름 파악
4. 관련 코드 탐색 — $ARGUMENTS와 관련된 파일/모듈 식별
5. **code-style.md 로드 또는 부트스트랩** (아래 Step 1-1)

### Step 1-1: code-style.md 로드 또는 부트스트랩

#### 있는 경우

- 내용을 mental model에 탑재. 이후 설계/구현 결정은 이 스타일을 따름
- 충돌 시 "이번만 override" vs "code-style.md 갱신" 중 선택 요청

#### 없는 경우 — 기존 코드 분석 후 자동 생성

1. 디렉토리 구조 스캔 (`ls`, Glob)
2. 핵심 파일 3-5개 Read (entry point, service, test, config)
3. 관찰된 패턴을 `references/code-style-template.md` 기반으로 정리
4. 사용자에게 diff 보여주고 승인 요청
5. 승인 시 `.claude/code-style.md`에 작성

> 부트스트랩은 **신규 brainstorming에서만** 실행. 재진입(Step 8)에서는 기존 파일을 로드만 함.

## Step 2: 요구사항 탐색

사용자와 1:1 대화로 요구사항을 구체화한다.

핵심 원칙:

- **AskUserQuestion 사용** — 사용자에게 질문할 때 반드시 AskUserQuestion tool 사용
- **질문은 한 번에 하나씩** — 여러 질문을 한꺼번에 하지 않음
- **다지선다 우선** — 가능하면 2-4개 선택지 제시. 선택지에 Claude 추천을 `(추천)` 태그로 표시
- **코드베이스 사실은 직접 조사** — 사용자에게 "어디에 있나요?" 묻지 않고 Grep/Read로 확인
- **사용자에게는 선호도/우선순위만 질문**

탐색할 항목:

- 기능의 목적과 사용자 시나리오
- 제약 조건 (기술적, 비즈니스)
- 성공 기준 — 무엇이 되면 완료인가
- 범위 — 무엇을 포함/제외하는가

프로젝트 규모가 너무 크면 (독립 서브시스템 3개 이상) 먼저 분해를 제안한다.

## Step 3: 접근법 제시

요구사항이 충분히 파악되면:

1. **2-3개 접근법** 제시
2. 각 접근법에 **트레이드오프** 명시
3. **Claude 추천안**을 `⭐ 추천` 태그로 명시하고 추천 이유 제시
4. AskUserQuestion으로 사용자 선택 대기

## Step 4: PM Agent — 규모 판단 + 분리 제안

선택된 접근법을 바탕으로 **pm-code-agent** 를 호출하여 작업을 PR 단위로 분리할지 판단한다.

Agent tool (subagent_type: pm-code-agent)로 호출:

```
당신은 pm-code-agent 에이전트입니다.

다음 draft spec 을 검토하고 규모 판단 + PR 단위 분리 제안을 하세요.

## Draft Spec
[요구사항, 제약, 선택된 접근법을 구조화해서 전달]

## Codebase Context
- 프로젝트 타입: [감지된 타입]
- 관련 파일/모듈: [Step 1 에서 식별한 목록]
- CLAUDE.md 규칙: [관련 부분 발췌]

출력 형식: pm-code-agent.md 의 Output Contract 를 따를 것.
```

### PM Verdict 처리

**SINGLE 판정**:

- sub-task 1개로 진행
- 사용자 승인 불필요 — 바로 Step 5

**SPLIT 판정**:

- PM 이 제안한 DAG 를 사용자에게 보여주고 AskUserQuestion 으로 승인 요청
- 선택지:
  - `승인 (⭐ 추천)` — 제안대로 진행
  - `수정` — 사용자가 조정사항 명시 → PM 재호출
  - `SINGLE 로 강제` — 분리하지 않음
- 승인되면 Step 5 로 진행

**에스컬레이션 (5개 이상 sub-task 필요)**:

- PM 이 범위 축소를 요청한 경우 → Step 2 로 돌아가 사용자와 범위 재협의

## Step 5: 문서 작성 (DESIGN + Plans)

디렉토리 생성: `.claude/plans/YYYY-MM-DD-<topic>/`

### 5-1. DESIGN.md (항상 작성)

전체 설계 문서 — why/what 관점. architect 와 사용자가 읽을 "큰 그림" 문서.

```markdown
# Design: <기능 제목>

## 배경

왜 이 작업이 필요한가 — 비즈니스/기술적 동기

## 요구사항

### 기능 요구사항

- ...

### 제약 조건

- 기술적 제약
- 비즈니스 제약

## 선택된 접근법

어떤 접근법을 선택했고 왜 (트레이드오프 포함)

## 범위

### 포함

- 이번에 구현할 것

### 제외

- 이번에 구현하지 않을 것

## 작업 분리 (PM 판정)

- **Verdict**: SINGLE | SPLIT
- **Rationale**: [PM 근거 요약]
- **DAG**: (SPLIT 인 경우) `01-migration → 02-api → 03-ui`

## 성공 기준

- [ ] 완료 조건 1
- [ ] 완료 조건 2

## 리스크 / Open Questions

- ...
```

### 5-2. `_dag.yaml` (항상 작성)

단일이든 분리든 동일한 스키마로 작성. Pipeline 경로가 이 파일을 읽어 파이프라인을 실행한다.

```yaml
feature: <topic>
design: DESIGN.md
tasks:
  - id: <kebab-case>
    file: 01-<task>.md
    pr_scope: "<한 문장 PR 제목>"
    depends_on: []
  - id: <next>
    file: 02-<next>.md
    pr_scope: "..."
    depends_on: [<previous-id>]
```

단일 task 예시:

```yaml
feature: add-rate-limit
design: DESIGN.md
tasks:
  - id: main
    file: 01-main.md
    pr_scope: "API 에 rate limit 미들웨어 추가"
    depends_on: []
```

### 5-3. `NN-<task>.md` (sub-task 별로 작성)

각 sub-task 의 실행 단위 문서 — how/execute 관점. Pipeline 의 Stage Pre 가 받아 분석하는 입력.

프론트매터에 **status** 필드 포함 (신규는 `draft` 로 시작, Step 7 에서 사용자가 `ready` 로 승격):

```markdown
---
id: <task-id>
status: draft # draft | ready | done
pr_scope: "<한 문장 PR 제목>"
depends_on: [<ids>]
---

# Task: <task id>

> 상위 설계: [DESIGN.md](./DESIGN.md)
> PR Scope: <한 문장>
> Depends on: [<ids>] (없으면 "없음")

## 목표

이 sub-task 가 끝나면 무엇이 가능해지는가

## 범위

### 포함

- 수정/추가할 파일과 기능

### 제외

- 다른 sub-task 가 담당하는 부분 (혼동 방지)

## 구현 노트

- 주의할 패턴/제약
- 선행 조건 (의존 task 의 산출물 중 무엇을 사용하는가)

## 완료 기준

- [ ] 단독 build 통과
- [ ] 단독 test 통과
- [ ] PR 제목 한 문장으로 커버됨
- [ ] ...
```

**status 초기값은 `draft`.** architect 리뷰 통과 후 사용자가 명시적으로 `ready` 로 승격한다 (Step 7 참조).

## Step 6: architect 에이전트 리뷰

`DESIGN.md` + `_dag.yaml` + 각 sub-task 문서를 **한 번에** 리뷰한다. 분리 경계 검증이 핵심.

Agent tool (subagent_type: architect)로 호출:

```
당신은 architect 에이전트입니다.

다음 설계 문서와 plan 을 리뷰하세요:

[DESIGN.md 전문]

[_dag.yaml 전문]

[각 NN-*.md 전문]

리뷰 관점:
1. 완전성 — 구현에 필요한 정보가 빠짐없이 있는가
2. 모호함 — 해석이 갈릴 수 있는 표현이 있는가
3. 구현 가능성 — 현재 코드베이스에서 실현 가능한가
4. 리스크 — 놓친 edge case 나 의존성이 있는가
5. **분리 경계 (SPLIT 인 경우)**:
   - 각 sub-task 가 단독 build/test 가능한가
   - 같은 파일을 여러 sub-task 가 건드리는가 (merge hell 위험)
   - 의존성 순서가 맞는가 (build 기준)
   - 한 sub-task 의 누락으로 downstream 이 붕 뜨지 않는가

출력 형식:
  ## Verdict: APPROVED / NEEDS REVISION
  ## Issues (있으면)
  - [severity] [설명] — [제안]
  ## Recommendations
  - [구체적 개선 제안]
```

### 리뷰 루프

- **APPROVED**: Step 7로 진행
- **NEEDS REVISION**: 이슈 수정 후 재리뷰 (최대 5회)
  - 분리 경계 이슈이면 Step 4 의 PM Agent 를 다시 호출하여 DAG 수정
  - 그 외 이슈이면 해당 문서만 수정
- **5회 초과**: 사용자에게 판단 요청

## Step 7: status 승격 (draft → ready)

architect 리뷰가 APPROVED 된 각 sub-task 에 대해 AskUserQuestion:

```
이 sub-task 의 상태를 어떻게 할까요?

- draft (추가 편집 필요) — 나중에 다시 brainstorming
- ready (/code 로 실행 가능) ⭐ 추천 (architect APPROVED 된 경우)
```

선택대로 NN-<task>.md 의 frontmatter `status` 를 업데이트.

Pipeline 경로는 **ready** 상태만 수용한다. draft 는 거부.

## Step 8: 재진입 모드 (기존 plan 편집)

메인 SKILL.md 라우터에서 재진입으로 판별된 경우 여기로 진입:

1. `.claude/plans/<topic>/_dag.yaml` 로드
2. 각 NN-<task>.md 의 frontmatter `status` 확인
3. AskUserQuestion: "어떤 sub-task 를 편집할까요?"
   - draft/ready 목록 제시
   - **done 은 잠김** (다시 편집하려면 수동으로 status 수정 필요)
4. 선택된 sub-task 의 본문 Read
5. 각 결정 필드를 다시 AskUserQuestion 으로 확인/수정
6. 승인되면 파일 업데이트
7. Step 7 로 (status 재처리)

## Step 9: 완료

```
✅ Brainstorming 완료

디렉토리: .claude/plans/YYYY-MM-DD-<topic>/
├── DESIGN.md          (설계 문서)
├── _dag.yaml          (실행 DAG)
└── NN-<task>.md × N   (sub-task 실행 단위, frontmatter status 포함)

PM Verdict: SINGLE | SPLIT (N tasks)

상태별:
  draft: [ids]   — 추가 편집 필요
  ready: [ids]   — Pipeline 실행 가능

다음 단계:
  /code .claude/plans/YYYY-MM-DD-<topic>/   (ready → 자동 실행 | draft → 재편집)
```

모든 sub-task 가 ready 이면 AskUserQuestion: "바로 Pipeline 실행으로 넘어갈까요?"

- **실행 (⭐ 추천)** — Pipeline 경로로 자동 전환
- **보류** — 여기서 종료
