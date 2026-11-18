## Step 5 — Code (PR 마다, lane 은 병렬 · lane 하나 = implementer 1회)

PR 시작 시 base 커밋을 기록: `git rev-parse HEAD` → PLAN.md PR 블록에 `- base: <hash>`.

PR 시작 전에 열린 PR 과 파일이 겹치는지 본다 (Ship 직전에 한 번 더):

- `gh pr list --state open --json number,headRefName,files` 의 파일과 이 PR 의 `파일` 칸 교집합
- 겹치면 그 PR 의 diff 를 읽고, 같은 코드를 쓰는 중이면 멈추고 보고 (다른 PR 과 같은 코드를 Ship 직전에야 발견한 일이 있다)
  - 같은 함수를 고치는 열린 PR 이 있으면 순서는 묻지 않는다: 그 PR 머지 뒤 시작으로 정하고 `## 결정 대기` 에 한 줄, 그동안 다른 PR·lane 을 진행

다른 PR 위에 쌓을 때(base 가 머지 전 브랜치)는 Code 전에 임시 worktree 에서 `origin/<PR base>` 를 `merge --no-commit` 해 PR 마무리 명령을 1회 돌린 뒤 `merge --abort`·worktree 제거. 실패하면 두 base 의 차이(스키마 번호·<계약> 칸 등)부터 본다

lane 마다:

- 첫 lane 은 PR worktree, 나머지 lane 은 같은 base 에서 별도 worktree
  (`git worktree add -b <PR 브랜치>-<lane> <worktree 루트>/<n>-<주제>-<lane> <base>` 뒤 Step 0 과 같은 `.claude` symlink)
- lane 들을 **동시에** 시작한다. lane 마다 `<implementer>` 를 1번 호출
  - 프롬프트: plan 경로, PR 번호, lane id, Task id 목록, 이전 커밋 hash, worktree 경로, Task 별 판단 지점 결정, `<규칙 파일>`(있으면)
  - implementer 가 lane 안에서 실행 명령이 같은 Task 끼리 묶어 stub → Red 1회 → Green 1회 를 돌리고, lane 끝에 커밋 1개
- 모든 lane 이 끝나면 다른 lane 커밋을 PR 브랜치로 `git cherry-pick` (push 전이라 이력 문제 없음) → lane worktree 제거
  - 충돌하면 lane 나누기가 틀린 것 → 멈추고 보고
- 판단 지점은 Plan 때 정해져 있다. 새로 생기면:
  - DESIGN.md `## 위임 원칙` 이 있으면 그 순서로 정하고 PR "자체 결정" 절에 `<선택> — <원칙·근거 한 줄>` 로 적는다
  - repo 선례가 있으면 선례대로 정하고 결정 표(결정 | 선례 파일)만 보인 뒤 진행한다
  - 선례가 없어도 진행을 막지 않으면 권장안으로 진행하고 `## 결정 대기` 에 쌓는다. 그때 묻는 건 다른 이슈 계약에 영향·<계약> 호환·규칙 예외·`## 사용자에게 남김` 에 해당할 때만
  - 물어야 하면 그 lane 만 멈추고 `## 결정 대기` 에 쌓는다. 다른 lane·PR 은 계속하고, 모든 lane 이 멈췄을 때만 그때 묻는다
  - 물을 때는 흐름 그림(ASCII)을 먼저 보인다: 호출 방향, 오가는 값, 그 값을 쓰는 쪽. 질문 칸은 그림 안에 `← 이 칸`. 경우가 갈리면 경우별 값을 나란히. 선택지 표는 그 아래
- 사용자에게 코드 작성을 요청하지 않는다 (학습은 별도 learn skill 몫)
- lane 을 기다리는 동안 다른 lane·이 대화의 다른 작업을 진행한다. 보고는 lane 이 끝날 때 짧게

implementer 보고를 받으면 사용자에게 짧게 보여준다:

```
lane a ✅ T1 Red: <메시지> · T2 Red: <메시지>
   Green: <파일 +N/-M> · 판단 지점: <한 줄> · <hash>
```

- `stopped` → 그 lane 은 멈춘다 (다른 lane 은 계속). 원인을 본다. 이미 Green 인 묶음은 커밋 전이라 worktree 에 남아 있다
  - 내가 정해도 되는 경우 — PLAN.md 에 한 줄 적고 implementer 를 재개(SendMessage):
    - 범위 밖 파일이 **테스트만**이고, 이미 승인된 결정이 기대값을 바꾼 것 (예: 개수·바이트 고정 테스트)
    - 근거를 직접 확인한다 (읽는 쪽 코드·선례). 확인 못 하면 묻는다
  - 묻는 경우: 실제 코드의 범위 밖 수정, <계약> 호환 판단이 필요한 것, 기대와 다른 실패 원인이 설계와 관련된 것

## Step 5.5 — 마무리 검증 (PR 마다, 1회)

- 모든 lane 을 합친 뒤 `.claude/skills/work/references/test-commands.md` 의 "PR 마무리" 명령을 **에이전트 없이** Bash `run_in_background` 로 돌린다
  - 검사마다 `.claude/skills/work/scripts/runlog.sh <plan>/logs/<pr>-final-<검사>.txt <명령>` 으로 (첫 줄 명령·끝 줄 exit). `&&` 로 검사를 잇지 않는다 — 앞 실패가 뒤 검사를 가린다
  - 무거운 명령은 runlog.sh 가 머신 전체 잠금으로 하나씩, `nice -n 10` 으로 돌린다. 동시에 띄워도 줄을 선다 — 대기 중이면 stderr 에 실행 중인 명령이 찍힌다. 무거운 도구를 직접 부르지 말고 runlog 를 거친다 (잠금 대상은 runlog.sh 머리 주석)
  - 리뷰 전 점검 `python3 -I <메인 체크아웃>/.claude/skills/work/scripts/review_precheck.py <base>` (PR worktree 에서) → `<pr>-final-precheck.txt`. error 가 있으면 Step 6 전에 고친다
  - `test-commands.md` "알려진 기존 실패" 표에 있는 실패는 base 를 다시 돌리지 않고 기존 실패로 적는다
  - 무거운 명령 횟수는 묻지 않는다: Red·Green·마무리에 필요한 만큼 돌린다. DESIGN.md `## 사전 승인` 에 검증 예산이 있으면 그 상한 안에서, 넘어야 하면 그 PR 만 멈추고 `## 결정 대기`
  - 전체 CI 스크립트는 기본으로 돌리지 않는다 (리소스 과다·fail-fast 라 앞 실패가 뒤 게이트를 가린다). 대신 `test-commands.md` "PR 마무리 범위" 표대로 바뀐 단위 + 그 단위에 의존하는 단위의 PR 마무리 명령과 정적 검사를 각각 runlog 로 돌린다. 고른 단위와 이유(바뀐 경로 → 의존 단위)를 `<pr>-final-scope.txt` 에 적는다. 전체 CI 스크립트는 사용자가 요청하거나 범위 판정이 안 될 때만
  - 이 로그들이 없으면 Ship·머지(통합 브랜치 직접 머지 포함)로 가지 않는다. PR 본문 "검증" 에 실행 명령과 결과(exit·실행 테스트 수·기존 실패)를 적는다
- 실패하면 원인 Task 를 찾아 그 Task 만 implementer 로 고친다 (실패 테스트가 곧 Red) → 실패한 명령만 다시
- 통과하면 바로 Step 6. 결과 표는 Step 7 보고에 쓴다
