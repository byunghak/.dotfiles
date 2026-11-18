## Step 4 — Plan

Plan 은 메인이 쓰지 않고 agent 에 맡긴다 — 작성 `<planner>`, 검토 `<plan-reviewer>`. 메인 세션 effort 와 따로 두려는 것. Task 표·판단 지점·lane·조건 표 규칙은 `<planner>` 정의와 `.claude/skills/work/references/plan-template.md` 에 있다.

1. DESIGN.md 에 메인 대화의 결정을 옮긴다 — planner 는 이 대화를 못 본다
   - `## 승인 ① 결정`: 사용자가 고른 접근법·말로 정한 제약 (`→ <결정> (날짜 사용자)`)
   - `## PR 분리`: pm-code-agent 분리안 (PR 마다 제목·범위·분리 근거·depends_on·PR base)
   - 빠른 경로면 `## 승인 ① 결정: 없음 (빠른 경로)`, `## PR 분리: PR 1개 — <수정 방향 한 줄>` 로 적는다
2. `<planner>` 호출 — 프롬프트: plan 경로, `<PR base>`, worktree 경로(있으면), `<규칙 파일>`(있으면)
   - `stopped` 면 못 채운 칸과 이유를 보고 코드를 더 읽어 DESIGN.md 를 보강한 뒤 재개(SendMessage). DESIGN 자체가 틀렸으면 멈추고 사용자에게 보고
3. `<plan-reviewer>` 호출 — 프롬프트: plan 경로, `<PR base>`, worktree 경로 (빠른 경로면 생략하고 4 로)
   - `NEEDS_FIX` 면 지적 목록 전문을 planner 에 SendMessage 로 넘겨 재개 → 반영 보고를 받아 reviewer 를 재리뷰로 다시 호출 (이전 지적 목록 + planner "리뷰 반영" 줄)
   - 재리뷰는 이전 지적의 반영 확인만 시키고 Agent 호출에 `effort: "medium"` 을 준다 (재리뷰 10회 모두 PASS·새 block 0, 회당 비용은 첫 리뷰보다 컸다)
   - 재리뷰는 2회까지. 그 뒤에도 남은 `block` 은 승인 ② 에 지적 원문과 함께 싣는다. `should` 만 남으면 `## 결정 대기` 에 한 줄씩 적고 진행
4. 진행을 막는 판단(planner "결정 필요")은 승인 ② 에서 추천과 함께 한 번에 묻는다. 답은 PLAN.md 해당 판단 지점 줄에 `→ <결정> (날짜 사용자)` 로 적는다

- 승인 ② — 아래 중 하나라도 있을 때만 Task 표·조건 표를 보이고 묻는다. 없으면 표만 보이고 묻지 않고 Step 5
  - 진행을 막는 판단 지점 · <계약> 변경 · PR 2개 이상
- 그 뒤 브랜치가 없으면 Step 0 의 worktree 방식으로 만든다
