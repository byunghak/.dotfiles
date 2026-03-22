---
name: dable-sprint-report
model: opus
effort: low
disable-model-invocation: true
description: Sprint Report 자동 작성
---

# Sprint Report 자동 작성

> **JIRA CLI 전용**: REST API 직접 호출 금지. CLI 실패 시 에러를 보고하고 사용자에게 확인할 것.

BE 스프린트 회고 Notion 페이지에 Sprint Report를 JIRA CLI 기반으로 자동 작성한다.

## 입력

- 회고 Notion 페이지 URL (사용자 블록 링크 포함): $ARGUMENT_1
- Sprint Report 템플릿 Notion 페이지 URL: $ARGUMENT_2

## 실행 절차

### 1단계: 템플릿 확인

Notion MCP `notion-fetch`로 Sprint Report 템플릿 페이지($ARGUMENT_2)를 가져와서 작성 포맷을 파악한다.

- 템플릿의 Notion Markdown 구조를 그대로 준수한다.
- 제목(heading), 불릿(bullet), 볼드 등 서식을 임의로 추가하지 않는다.
- 템플릿에 있는 서식만 사용한다.

### 2단계: 회고 페이지 확인

Notion MCP `notion-fetch`로 회고 페이지($ARGUMENT_1)를 가져와서:

- 사용자 블록(toggle section)의 위치와 현재 내용을 확인한다.
- URL fragment(#)로 사용자 블록을 식별한다.

### 3단계: JIRA 현재 스프린트 티켓 수집

```bash
# 현재 사용자 확인
jira me

# BE 프로젝트 활성 스프린트 ID 확인
jira sprint list -p BE --state active --table --plain --columns id,name,start,end,state

# 스프린트 전체 이슈 목록 (assignee 필터링용)
jira sprint list <SPRINT_ID> -p BE --plain --columns type,key,summary,status,assignee --no-truncate
```

- `jira me`로 확인한 사용자 이름과 assignee를 매칭하여 본인 티켓만 필터링한다.
- 상태별 분류: 완료 → Done, 진행 중/리뷰중 → Progress, 해야 할 일 → Progress (할당된 경우)

### 4단계: 티켓 상세 정보 수집

필터링된 각 티켓에 대해 상세 정보를 가져온다:

```bash
jira issue view <TICKET_KEY> --plain
```

- Description과 Comments에서 요약, 주요 내용, 성과 정보를 추출한다.
- 병렬로 최대 6개씩 호출하여 속도를 높인다.

### 5단계: 프로젝트별 그룹핑

티켓들을 프로젝트/에픽 단위로 그룹핑한다:

- 티켓의 parent item, label, 제목 패턴으로 프로젝트를 추론한다.
- 관련 없는 독립 작업은 "기타" 프로젝트로 분류한다.

### 6단계: Sprint Report 작성

Notion MCP `notion-update-page`의 `replace_content_range`로 사용자 toggle 섹션 내용을 업데이트한다.

**중요: 1단계에서 파악한 템플릿 포맷을 그대로 따른다. 임의로 heading, bold, bullet 등 서식을 추가/변경하지 않는다.**

### 7단계: 결과 확인

작성 완료 후 사용자에게 결과 요약을 보여준다:

- Done/Progress 티켓 수
- 프로젝트별 그룹핑 결과
- Notion 페이지 링크

## 주의사항

- JIRA CLI(`jira`)를 사용한다. curl/API 직접 호출 금지.
- Notion Markdown 특수문자(`[`, `]`, `\`, `~` 등)는 반드시 escape 처리한다.
- 티켓 Description이 비어있으면 Comments에서 정보를 추출한다.
- Comments도 없으면 티켓 제목만으로 요약을 작성한다.
- 사용자에게 작성 전 내용을 확인받는다.
- **템플릿 포맷을 절대 임의 변경하지 않는다.** 템플릿 Notion 페이지의 Markdown 구조를 그대로 복제한다.
