## Step 9 — 머지·정리 (PR 마다)

base 가 `<통합 브랜치>` 면 묻지 않고 머지한다 (통합 브랜치는 배포·릴리스되지 않는다). `<확인 base>` 는 DESIGN.md `## 사전 승인` 조건을 모두 채우면 묻지 않고, 아니면 확인을 받는다. 정리는 머지를 검사로 확인한 뒤 묻지 않고 한다.

사전 승인 검사 (`<확인 base>` 머지 전, 하나라도 아니면 사전 승인 없음):

- 이 PR 이 `## 사전 승인` 머지 줄에 있고 base 가 같다
- 리뷰 PASS · 이 head 의 마무리 검증 exit 0 (head 가 바뀌었으면 다시 검증)
- <계약>·DESIGN 범위 밖 파일 변경 없음 · 승인 뒤 범위 변경 없음
- 채우면 머지하고 끝 보고에 `사전 승인 머지: #<n> (<하는 일>) <merge commit>` 한 줄. hook·권한 창이 뜨는 base(보호 base 등)는 그 창은 그대로 둔다 — 사전 승인은 대화상자를 없애는 것이고 권한 확인을 우회하지 않는다
  - controller 아래에서 hook 이 이 머지를 deny 하면(확인 창을 띄울 수 없는 pane) 명령과 `사전 승인: DESIGN.md <줄>` 을 controller 에 보낸다. controller 는 사용자에게 다시 묻지 않고 자기 pane 에서 실행한다
- 배포가 사전 승인돼 있으면 같은 방식으로 시점 조건을 보고 진행한다

머지 확인 (`<확인 base>` 만):

- 사전 승인이 없는 PR 은 PR 마다 묻지 않는다. PLAN.md PR 블록에 `- 머지 대기` 를 적고 다음 PR 이 있으면 Step 5 로 → 끝: 결정 모음에서 한 번에 묻는다
  - 다음 PR 이 이 PR 에 의존하면 이 PR 브랜치 위에 쌓는다 (Step 5 "다른 PR 위에 쌓을 때"). 머지 뒤 그 브랜치를 갱신한다
  - 사용자가 진행 중에 머지를 말하면 그때 이 Step 으로 온다
- 누가 머지하나
  - 이 세션이 머지한다 (base 가 `<확인 base>` 면 확인 뒤, `<통합 브랜치>` 면 리뷰 통과 뒤 바로)
  - 컨트롤러가 먼저 머지했다는 통보를 받으면 머지는 건너뛰고 정리로 간다
- 머지 명령: `gh pr merge <n> --merge --match-head-commit <확인받은 시점의 head>`
  - merge commit 만 쓴다. squash·rebase 는 커밋을 새로 만들어 정리의 조상 검사가 실패하고, autoMode 가 브랜치 삭제를 막는다
  - `--delete-branch` 는 쓰지 않는다. 삭제는 아래 정리 명령에서 검사와 함께 한다

정리 (머지 직후, 또는 컨트롤러 머지 통보를 받은 직후):

- 이 브랜치를 base 로 쓰는 열린 PR 이 있으면(`gh pr list --base <b> --state open`) 지우지 않고 보고한다
- 검사와 삭제를 한 명령으로 — 검사 하나라도 실패하면 아무것도 지우지 않는다

  ```
  git fetch origin --prune -q && \
  git merge-base --is-ancestor origin/<b> origin/<PR base> && \
  [ -z "$(git -C <worktree> status --porcelain)" ] && \
  git worktree remove <worktree> && git branch -D <b> && git push origin --delete <b>
  ```

  - `<worktree>` 는 PLAN.md 의 `- worktree:` 줄. Step 5 의 lane worktree 가 남아 있으면 같은 방식으로

- 다른 사람이 squash 로 머지해 조상 검사가 실패하면, 조상 검사 대신 PR 상태로 확인하고 지운다 — `gh pr view` 가 MERGED 이고 headRefOid = 로컬 끝 = 원격 끝 (patch-id 비교는 base 커밋을 손으로 찾아야 하고 base 를 merge 로 받은 브랜치면 어긋난다)

  ```
  git fetch origin --prune -q && \
  [ "$(gh pr view <n> --json state,headRefOid -q '.state+" "+.headRefOid')" = "MERGED $(git rev-parse <b>)" ] && \
  [ "$(git rev-parse <b>)" = "$(git rev-parse origin/<b>)" ] && \
  [ -z "$(git -C <worktree> status --porcelain)" ] && \
  git worktree remove <worktree> && git branch -D <b> && git push origin --delete <b>
  ```

- 그래도 실패하면 지우지 않고 보고: 실패한 검사, worktree 변경 수
- autoMode 가 막으면 막힌 명령을 보이고 멈춘다. 다른 방법으로 다시 시도하지 않는다
- 이 세션이 리뷰·검증용으로 만든 detached worktree 도 결과를 worktree 밖에 남긴 뒤 `git worktree remove --force <worktree>` 로 지운다. 남기면 `session-worker` 의 보존 표시를 한다
- 정리 결과 한 줄: `정리: worktree <경로> · 로컬 <b> · 원격 <b> 삭제` 또는 `정리 보류: <이유>`
- 이 세션이 직접 머지했고 PLAN.md `- controller:` 가 `없음` 이 아니면, 정리 뒤 컨트롤러에 `PR #N 머지됨 <merge commit> · 정리 <완료|보류: 이유>` 를 보낸다

## 끝 — 결정 모음

이슈의 모든 PR 이 Ship 되면 쌓인 결정을 한 번에 처리한다 ("끝난 뒤 마지막에 한 번에").

1. 보고 (결론부터): Ship 된 PR 표(PR | 하는 일 | 검증 수치 | 상태) → PLAN.md 의 stopped·리뷰 FAIL 지점 한 줄씩 (회고 재료)
2. 결정 표 — PLAN.md `## 결정 대기` 전부 + 아래를 모은다
   - `<확인 base>` `- 머지 대기` PR (머지 / 나중에) — 사전 승인이 깨진 PR 은 깨진 조건을 함께
   - 사전 승인으로 실행한 것·위임 원칙으로 정한 자체 결정 (유지 / 변경)
   - 이슈 생성 (작업 설명만으로 시작했을 때 — 리마인드)
   - 권장안으로 진행한 판단 지점 (유지 / 변경 — 변경 시 고칠 곳)
   - 충돌 해결 merge (확인 권장 — 충돌 파일·해결 방식)
   - 머지 후 수동 작업 (배포·마이그레이션 순서 등)
   - 열: 결정 | 지금 값(권장안) | 근거 | 바꾸면 고칠 곳
3. 질문: AskUserQuestion 한 번에 최대 4개(이 단계만 "한 턴에 질문 1개" 예외). 4개를 넘으면 되돌리기 어려운 순(머지 → <계약>·계약 → 나머지)으로 나눠 이어 묻는다
4. 답을 받으면 그대로 실행한다: 머지 → Step 9 정리, 변경 → 해당 PR 에 후속 커밋(Step 8 리뷰 지적 후속과 같은 방식), 이슈 생성 → `/github-issue`
5. 끝에 남은 것: 머지 대기·정리 보류로 남은 PR·브랜치·worktree
