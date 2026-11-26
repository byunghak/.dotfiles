## Step 7 — Ship 판단

아래를 보여주고 **묻지 않고 Step 8** (PR 올리기는 질문 대상이 아니다). <확인 base> 머지는 끝: 결정 모음에서 확인받는다.

- PR 이 바꾼 줄에 남은 지적이 있으면 Step 6 으로 돌아가 고친다 (Ship 판단을 묻는 것으로 대신하지 않는다)
- 설계 결정이 필요한 지적·머지 후 수동 작업은 PR 본문(범위 밖·머지 후 수동 작업 절)에 적고 Ship 한다. 결정은 `## 결정 대기` 로

```
PR <n> — <제목> (분리 근거: <...>)
Task: T1 ✅ T2 ✅ (lane a <hash>) · T3 ✅ (lane b <hash>) ...
리뷰: <리뷰어> PASS · <리뷰어> NEEDS ATTENTION (<id> medium 1)
검증: <검사별 결과 — 줄 구성은 프로젝트 추가 파일>
머지 후 수동 작업: <배포·마이그레이션 순서 등 | 없음>
```

## Step 8 — Ship

- `/github-ship` 을 호출한다 (Skill tool). 인자에 다음을 넣는다
  - base `<PR base>`, `--no-merge`, `--no-review` (리뷰는 Step 6 에서 끝났다)
  - 일반(Ready) PR 로 올린다. `--draft` 는 통합 브랜치(`<통합 브랜치>`) → `<BASE>` 묶음 PR 에만 쓴다 — Draft 로 올리면 머지 때 Ready 전환이 한 단계 더 생긴다
  - 본문 재료는 **사실만**: 의도와 이유, 바뀐 파일, 실제로 돌린 검증 명령과 결과, 알고 남긴 것, 머지 후 수동 작업
  - milestone·label·assignee: 프로젝트 추가 파일이 정한 규칙으로 고른 값을 인자에 적는다
  - 인자 끝에 "본문에 Generated with 줄 금지" 를 적는다
  - Skill 대신 Agent(`github-ship`)를 직접 부르지 않는다. skill 틀이 `--no-review` 를 `옵션:` 줄로 넘긴다
  - github-ship 보고의 `Phase 4:` 줄에서 code-reviewer 가 `skip (--no-review)` 가 아니면 옵션이 빠진 것이다. 다음 ship 인자를 고친다
  - 보고에 codex 지적이 있으면 Step 6 반영 규칙대로 고친다 (리뷰어 하나의 지적으로 본다). 고친 커밋은 아래 "리뷰 지적 후속 — PR 이 아직 열려 있으면" 대로 push 한다. codex 가 실패·timeout 이면 PR 본문 "검증" 에 그 한 줄을 적고 진행한다
- 본문 형식은 `.claude/pr-convention.md` 가 정한다 (github-ship 에 이 경로를 넘긴다). 인자에 제목·절 구성을 따로 지시하지 않는다 (인자로 형식을 지시했다가 convention 과 어긋난 사고)
- 본문에 넣지 않는 것: Task 번호(T1·T2), Red→Green, 리뷰어 에이전트 이름 — PLAN 내부 용어다
- PR 이 열리면 `pr-convention.md` 의 "올리기 전 점검" 으로 본문과 milestone·label 을 대조한다. 어긋나면 `gh pr edit` 로 고치고 알린다
- PR 이 열리면 PLAN.md 의 판단 지점·결정마다 그 결정이 반영된 diff 줄에 인라인 리뷰 코멘트 (`pr-convention.md` "인라인 리뷰 코멘트" 형식)
  - `gh api repos/{owner}/{repo}/pulls/<n>/reviews` 로 한 번에 (`event: COMMENT`, `comments[]` 에 path·line·body)
- force-push 금지
- 끝나면 Step 9
- 리뷰 지적 후속
  - PR 이 아직 열려 있으면: 같은 브랜치에 새 커밋(implementer) → `/github-ship --no-review` 로 push 만(새 커밋 금지·force-push 금지 지시). 본문 `## 검증` 에 후속 한 줄
  - 이미 머지됐으면: 같은 worktree 에서 `origin/<PR base>` 기준 새 브랜치 → PLAN.md 에 "PR N" 블록을 더해 Step 4 부터 (같은 이슈 번호)
  - 머지 전에 `<PR base>` 가 많이 앞섰으면 임시 worktree 에서 `origin/<PR base>` 에 `merge --no-commit` 해 PR 마무리 명령을 다시 돌리고, 끝나면 `merge --abort` 와 worktree 제거
