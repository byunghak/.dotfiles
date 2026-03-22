---
name: work-brainstorming
model: opus
allowed-tools: Read, Grep, Glob, Bash(git log:*), Bash(git diff:*), Bash(git status:*), Bash(ls:*), Agent, Write, Edit, AskUserQuestion
description: 코드 구현 전 요구사항 탐색 + spec 문서 작성 + architect 리뷰. Use when 구현할 기능의 요구사항이 불명확하거나, 접근법을 결정해야 할 때.
argument-hint: <구현할 기능/변경에 대한 아이디어>
---

# Work Brainstorming — 요구사항 탐색 + Spec 작성

코드 구현 전 **요구사항을 탐색**하고, **접근법을 결정**하고, **spec 문서를 작성**합니다.

> **코드 작업 전용**입니다. 비코드 작업(문서 작성, 설계 논의 등)에는 사용하지 마세요.

---

## Step 1: 컨텍스트 수집

1. 프로젝트 타입 감지: `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`
2. CLAUDE.md 읽기 (있으면) — 프로젝트 규칙/패턴 파악
3. `git log --oneline -10` — 최근 작업 흐름 파악
4. 관련 코드 탐색 — $ARGUMENTS와 관련된 파일/모듈 식별

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

## Step 4: Spec 문서 작성

사용자가 접근법을 선택하면 spec 문서를 작성한다.

파일 경로: `.claude/plans/YYYY-MM-DD-<topic>.md`

```markdown
# Spec: <기능 제목>

## 배경

왜 이 작업이 필요한가

## 요구사항

- 기능 요구사항 목록
- 제약 조건

## 선택된 접근법

어떤 접근법을 선택했고 왜

## 범위

### 포함

- 이번에 구현할 것

### 제외

- 이번에 구현하지 않을 것

## 성공 기준

- [ ] 완료 조건 1
- [ ] 완료 조건 2
```

## Step 5: architect 에이전트 리뷰

spec 문서의 완전성과 구현 가능성을 검증한다.

Agent tool (subagent_type: architect)로 호출:

```
당신은 architect 에이전트입니다.

다음 spec 문서를 리뷰하세요:
[spec 문서 전문]

리뷰 관점:
1. 완전성 — 구현에 필요한 정보가 빠짐없이 있는가
2. 모호함 — 해석이 갈릴 수 있는 표현이 있는가
3. 구현 가능성 — 현재 코드베이스에서 실현 가능한가
4. 리스크 — 놓친 edge case나 의존성이 있는가

출력 형식:
  ## Verdict: APPROVED / NEEDS REVISION
  ## Issues (있으면)
  - [severity] [설명] — [제안]
  ## Recommendations
  - [구체적 개선 제안]
```

### 리뷰 루프

- **APPROVED**: Step 6으로 진행
- **NEEDS REVISION**: 이슈를 수정하고 재리뷰 (최대 5회)
- **5회 초과**: 사용자에게 판단 요청

## Step 6: 완료

```
✅ Spec 작성 완료

파일: .claude/plans/YYYY-MM-DD-<topic>.md

다음 단계: /work-pre .claude/plans/YYYY-MM-DD-<topic>.md
```

---

## 다음 단계

| Spec 승인 후         | 커맨드                                          |
| :------------------- | :---------------------------------------------- |
| 분석 + 계획          | `/work-pre .claude/plans/YYYY-MM-DD-<topic>.md` |
| 단순 작업 (1-2 파일) | 직접 구현                                       |
