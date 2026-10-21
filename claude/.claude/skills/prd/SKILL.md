---
name: prd
model: opus
effort: high
description: PRD 를 엔지니어 관점에서 분석하고 설계 문서로 풀어낸다. 단계 메뉴 — understand(이해) · verify(코드 대조) · design(설계 Brainstorm) · diagram · wbs(작업 분해·이슈 생성) · diff(PRD 갱신 영향) · publish(Notion 게시). PRD 원문은 수정하지 않는다.
argument-hint: "<Notion PRD URL | page id> [understand|verify|design|diagram|wbs|diff|publish]"
disable-model-invocation: true
---

# prd

PRD 를 읽고, 코드와 대조하고, 엔지니어 설계 문서와 WBS 로 풀어낸다.
**PRD 원문은 고치지 않는다.** 결과는 별도 설계 문서이고, 로컬에서 쓴 뒤 확정되면 Notion 에 게시한다.

```
understand → verify → design → diagram → wbs ──(이슈 생성)──▶ /work 같은 구현 skill
                        ▲                         │
                        └──── diff (PRD 갱신 시) ◀─┘
```

## 협상 대상 아닌 규칙

- PRD 원문 수정·댓글 금지
- 외부 공개 작업은 둘뿐 — GitHub 이슈 생성, Notion 게시·갱신. 매번 대상과 위치를 보여주고 승인 후 실행. 승인은 그 실행에만 유효
- 공수 숫자를 먼저 제시하지 않는다. 요인만 정리하고 값은 사용자가 정한다
- 기존 설계 문서는 참고만 한다. 수정하지 않는다
- 코드에 대한 결론은 `file:line` 근거로. PRD·문서의 서술은 출발점이지 근거가 아니다
- 한 턴에 질문 1개. 결론 먼저, 쉬운 말. 터미널은 ASCII, 문서는 mermaid
- **임의 번호를 만들지 않는다.** 항목은 PRD 절 번호 + 주장·항목 내용으로 가리킨다 (예: "§5.1 `nobidBackoffSec` 주장"). PRD 가 직접 붙인 번호(open decision D1 등)만 그대로 쓴다
- **터미널에는 한 번에 3~5개까지만.** 포인트가 많으면 중요한 것부터 나눠 보여주고 사용자 반응을 받은 뒤 다음 묶음으로 간다. 파일에는 전부 저장하되, 터미널은 핑퐁 단위로

## Step 0 — 입력과 상태

1. 인자에서 PRD id 와 단계 이름을 분리한다
2. PRD 읽기
   - `command -v notion` 이 있으면 `notion page get <id> --format md` (서브커맨드는 `notion page --help` 로 확인)
   - 없으면 Notion MCP `notion-fetch` (스키마가 없으면 ToolSearch `select:mcp__claude_ai_Notion__notion-fetch`)
   - 제목, 상위 페이지 경로, `page_last_edited_at` 을 기록
   - `truncated`·`unknown_block_ids` 가 있으면 누락 블록을 추가로 읽는다
3. 작업 폴더 결정
   - 기본: `<repo>/docs/design/<prd-주제>/` (주제는 PRD 제목에서 짧은 kebab-case)
   - 이미 이 PRD URL 을 담은 `README.md` 가 있는 폴더가 있으면 그것을 쓴다 (`grep -rl "<page id>" docs/design/*/README.md`)
   - `docs/` 가 git 추적 대상이면 커밋해도 되는지 사용자에게 한 번 묻는다
4. 기준 브랜치
   - repo 의 project skill 이 기준 브랜치를 선언했으면 그 값 (예: `.claude/skills/work/SKILL.md` 의 `BASE`)
   - 없으면 `git for-each-ref --sort=-committerdate refs/remotes/origin | head` 로 활성 브랜치를 보고 사용자 확인
   - `git fetch origin <브랜치>` 후 `git rev-parse --short origin/<브랜치>` 를 코드 기준 리비전으로
5. 상태 파일 `README.md` 를 읽거나 새로 만든다 (`references/state-template.md`)
6. 스냅샷
   - `prd-snapshot.md` 가 있고 새 원문과 다르면 → diff 를 먼저 수행한 뒤 덮어쓴다
   - 없으면 새로 저장
7. 단계 선택
   - 인자로 지정됐으면 그 단계
   - 아니면 제안: 작업 폴더 새로 만듦 → understand / PRD 가 바뀜 → diff / 그 외 → 상태가 `미실행`·`재실행 필요` 인 첫 단계
   - 제안은 한 줄로 하고 사용자 확인 후 진행

## Step 1 — understand

`references/understand.md` 형식. 결과를 터미널에 요약하고 `00-understand.md` 에 저장.

- 한 문단 요약 → 핵심 흐름 ASCII → 용어 → 컴포넌트 표 → 엔지니어 위임 목록 → 미결정 목록
- PRD 가 정의 없이 쓴 용어도 한 줄 정의를 붙인다
- 미결정은 PRD 의 open decision + 읽다가 발견한 암묵적 미결정(“~필요하다”, “결정 사항이다”)
- 이후 사용자가 묻는 절을 더 깊이 설명. 개념이 코드에 없으면 GitHub 이슈 검색 (`gh issue list --search`)

## Step 2 — verify

`references/verify.md` 규칙. 결과를 `01-verify.md` 에 저장.

- PRD 에서 코드 주장을 뽑는다 — 경로·심볼·필드·엔드포인트 인용, "없다/있다/부분" 상태 단정
- 판정: 맞음 / 낡음 / 틀림 / 확인 불가. 근거 `file:line`, 낡음이면 바꾼 커밋
- 코드 추적은 `tracing-system-internals` skill 규칙을 따른다
- repo 의 project skill 목록을 보고 해당 영역에 맞는 것을 쓴다 (예: 데이터 원천 → `data-map`, 운영 관측 → `troubleshoot`)
- 주장이 10개를 넘으면 영역별로 Explore agent 를 병렬로 띄운다. 각 agent 에 주장 목록과 판정 기준을 넘기고 `file:line` 을 요구한다
- 결과 요약을 터미널에: 낡음·틀림만 먼저, 맞음은 개수만

## Step 3 — design

`references/design-doc.md` 형식.

1. 입력 정리: understand 의 위임 목록, verify 의 낡음·틀림(전제 교정), 기존 설계 문서(참고)
   - 기존 설계 문서 찾기: `docs/design/` 에서 PRD URL·제목 키워드 grep. 사용자에게 목록 확인
2. 문서 나누기 제안 — 독자와 수명이 다르면 나눈다 (예: 서버 설계 / 외부 연동 스펙 / 로그 설계 / 클라이언트 설계). 승인
3. 위임 항목마다 하나씩
   - 현재 동작 (`file:line`)
   - 접근법 2~3개 + 트레이드오프 + 권장안
   - 기존 설계 문서의 결론이 있으면 같이 보여주고, 권장안과 다르면 이유
   - 승인 → 설계 문서 해당 절 작성. 결론 → 근거 → 기각한 대안
   - PRD 권장과 다른 결정은 `PRD 와 다름:` 으로 표시
   - 기존 설계 문서와 다른 결정은 `기존 설계와 다름:` 으로 표시
4. README 결정 기록과 문서-PRD 절 대응표 갱신

## Step 4 — diagram

- 설계 문서마다 필요한 그림을 제안하고 승인된 것만 그린다
  - 전체 구조: 🟩 새로 생김 / 🟨 입력·형태가 바뀜 / ⬜ 그대로
  - 시퀀스: 서비스 간 호출 순서와 시간 예산
  - 데이터 흐름: 이벤트·로그가 어디서 나와 어디에 쌓이는지
- 문서에는 mermaid, 터미널 미리보기는 ASCII
- 노드 이름은 실제 서비스·모듈·엔드포인트 이름. 추상어 금지
- 그림의 모든 노드가 본문이나 `file:line` 에 근거가 있는지 확인

## Step 5 — wbs

`references/wbs.md` 형식. `wbs.md` 에 저장.

1. 설계 문서에서 이슈 단위 항목을 뽑는다
   - 이슈 = 독립적으로 설계·검증할 수 있는 기능 하나. PR 로 쪼개지 않는다
   - 항목마다: 설계 문서 절, 선행 항목, 걸친 repo, 공수 요인
2. 공수
   - 처음 실행 시 단위를 묻는다 (인일 / 범위 / 상대 크기 / 기타). README 에 기록
   - 항목을 몇 개씩 묶어 요인을 보여주고 사용자가 값을 정한다. 내가 먼저 숫자를 내지 않는다
3. 이슈 생성 승인 — AskUserQuestion: 전부 생성 / 일부 생성 / 보류
   - 일부면 어떤 항목인지 묻는다
   - 생성 전 repo·라벨·상위 이슈를 보여준다
   - 상위 이슈가 있으면 sub-issue 로 연결: `gh api repos/<o>/<r>/issues/<parent>/sub_issues -F sub_issue_id=<child 의 id>` (number 가 아니라 `gh api repos/<o>/<r>/issues/<n> --jq .id`)
   - 생성된 항목은 `생성됨 #n`, 나머지는 `보류`
4. 다시 실행하면 `보류` 항목부터 보여준다

## Step 6 — diff

- 새 원문과 `prd-snapshot.md` 를 절(헤딩) 단위로 비교 → 바뀐 절 목록 (추가·삭제·수정)
- 바뀐 절마다
  - 영향받는 설계 문서 절 (README 대응표)
  - 영향받는 WBS 항목·생성된 이슈
  - 설계 결정과 충돌하는지 — 특히 `PRD 와 다름:` 표시가 붙은 결정
- README 의 해당 단계를 `재실행 필요` 로
- 결과를 터미널에 보여주고, 다음에 다시 돌릴 단계를 제안
- 비교가 끝나면 스냅샷을 새 원문으로 덮어쓴다

## Step 7 — publish

- 대상: README 에서 `확정` 상태인 설계 문서. 초안이면 확정할지 먼저 묻는다
- 위치 제안: PRD 의 하위 페이지. 사용자가 다른 위치를 지정할 수 있다
- 변환
  - mermaid 코드블록 유지
  - 로컬 상대 링크 → Notion 페이지 또는 GitHub 링크
  - `file:line` → GitHub permalink (`https://github.com/<o>/<r>/blob/<기준 리비전>/<path>#L<n>`)
- 이미 `게시됨 <URL>` 이면 그 페이지를 갱신한다. 새 페이지를 또 만들지 않는다
- 승인 후 Notion MCP 로 생성·갱신 (`notion-create-pages` / `notion-update-page`, 스키마는 ToolSearch 로 로드)
- README 에 Notion URL 과 게시 시각 기록

## 끝

단계가 끝날 때마다:

- README 상태 갱신 (단계 완료 날짜, 코드 기준 리비전)
- 바꾼 파일과 다음 단계 제안 한 줄. 품질 판정("좋아 보인다")은 하지 않는다
