## Step 0 — 입력 판별과 준비

입력 판별:

- 이슈 URL·`#<n>`·숫자 → `<repo>` 에서 이슈 번호 `<n>` 를 찾는다 → Step 1
- `.claude/plans/<dir>/` → 재개
  - `PLAN.md` 상태 칸을 읽어 첫 미완료 지점부터 시작
  - `stopped` Task 가 있으면 그 이유부터 사용자와 본다
- 이슈 번호로 들어왔는데 같은 이슈의 `.claude/plans/*-<n>-*/` 가 있으면 묻지 않고 그 plan 을 재개한다 (새로 시작은 사용자가 말할 때만)
- 작업 설명만 → Step 1 을 건너뛰고 Step 2. 이슈 생성 여부는 묻지 않는다 — 로컬에 두고 `## 결정 대기` 에 `- 이슈 생성 (없음)` 을 적어 끝: 결정 모음에서 리마인드한다

빠른 경로 — 문제·원인·수정이 이미 명확할 때:

- 해당: 같은 대화의 조사(troubleshoot·debugging)로 원인이 `file:line` 과 재현 로그로 확정됐고 수정 방향이 하나뿐인 경우
- Step 1·1.5·2·3 (분석 요약·작업 그림·Brainstorm·PR 분리) 과 승인 ① 을 건너뛴다. 이슈 생성 여부도 묻지 않는다
- DESIGN.md 에는 문제·원인(`file:line`·에러 원문)·수정 방향만 적고 Step 4 Plan 으로. 승인 ② 는 Step 4 의 묻는 조건에 해당할 때만
- Step 4 는 `<planner>` 만 호출하고 `<plan-reviewer>` 는 생략한다 — 한두 파일 수정이라 lane 충돌·어휘·계약 고정 테스트 지적이 드물다. 조건 표는 planner 가 그대로 쓴다
- 작은 수정이라는 이유로 /work 밖에서 직접 고치지 않는다 — 리뷰(Step 6)가 빠지면 테스트 사각을 못 본다 (추가한 테스트가 경계 변이 4개 중 1개만 잡았는데 사용자가 물은 뒤에야 발견)

`<PR base>` 최신화 (`<PR base>` 는 `<BASE>`, 이슈가 통합 브랜치 묶음이면 그 `<통합 브랜치>` — PLAN.md PR 블록 `- base:` 에 적는다):

- `git fetch origin <PR base>`
- `git status --short` — 추적 파일에 변경이 있으면 먼저 알린다 (<커밋 제외> 는 무시)
- 현재 브랜치 `git branch --show-current`
  - 이 이슈의 브랜치(`issue-<n>-*`)면 `git rev-list --count HEAD..origin/<PR base>` 로 뒤처진 수를 보고
    - 묻지 않고 `git merge origin/<PR base>` 로 따라잡는다 (rebase·force-push 금지)
    - 충돌이 나면 직접 해결한다: 양쪽 의도를 커밋 메시지·PR 로 읽고 합친 뒤, 바뀐 모듈의 테스트를 돌려 통과를 확인하고 merge 커밋. 결과(충돌 파일·해결 방식·테스트 결과)는 진행 보고에 한 줄, 끝: 결정 모음에 "확인 권장" 으로
    - 양쪽 의도가 서로 배타적이라 하나를 버려야 하면(같은 칸을 다른 뜻으로 씀 등) 그때만 멈추고 묻는다
  - 다른 브랜치·`<BASE>`·`<통합 브랜치>`·main 이면 브랜치는 Plan 승인 후 `origin/<PR base>` 에서 **worktree 로** 만든다 — 메인 체크아웃의 브랜치는 바꾸지 않는다
    - 이름: `issue-<n>-<짧은-주제>`, 위치: `<worktree 루트>/<n>-<짧은-주제>`
    - `git worktree add -b issue-<n>-<주제> <worktree 루트>/<n>-<주제> origin/<PR base>` 뒤 `git -C <worktree> branch --unset-upstream` (origin/<PR base> 추적 방지)
    - `.claude/` 가 git 미추적이면 이어서 `ln -s <메인 체크아웃>/.claude <worktree>/.claude`. 없으면 worktree 에서 연 세션이 CLAUDE.md·agents·skills 를 못 읽는다. exclude 는 worktree 가 공유해 커밋되지 않고 `git worktree remove` 도 막지 않는다
    - `.claude/plans/` 는 메인 체크아웃에 두고 PLAN.md 에 `- worktree: <경로>` 를 적는다. implementer·리뷰어·github-ship 프롬프트에 그 경로를 넘기고 "worktree 에서만 편집·커밋, worktree 의 `.claude` 는 메인 체크아웃 symlink 이니 실제 디렉토리로 바꾸거나 따로 만들지 말 것" 을 적는다
- PLAN.md 에 `- controller: <이름|없음>` 도 적는다 — `<controller>` 규칙대로 `ListAgents` 에서 찾고, 없으면 `없음`
  - 이후 머지·막힘·결정 필요는 이 줄의 컨트롤러에 보낸다
