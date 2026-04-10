# Reporting — 중간/최종 리포트 포맷

`/code` 실행 중/후 사용자에게 보여줄 리포트 구조. 일관된 포맷이 중요한 이유는 여러 sub-task 가 연속 실행되면 이벤트가 섞여 읽기 어려워지기 때문이다.

---

## Sub-task 진입 배너 (각 task 시작 시)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ [N/M] <task-id> — <pr_scope>
   Depends on: [<ids>]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

`N/M` 은 진행률 표시 (예: `[2/3]`).

---

## Stage 진행 표시 (각 stage 완료 시)

```
  ✓ pre      — 분석/계획 완료
  ✓ work     — 구현 완료 (X files changed)
  ✓ post     — PASS
  ✓ clean    — dead code N건 제거
```

실패/재시도 시:

```
  ✓ pre      — 분석 완료
  ✓ work     — 구현 완료
  ✗ post     — FAIL (critical: 2건)
  ↻ fix #1   — 시도 중...
  ✓ post     — PASS (after fix)
  ✓ clean    — ok
```

Warning 있는 경우:

```
  ✓ post     — NEEDS ATTENTION (warnings: 3)
```

---

## Sub-task 완료 요약 (각 task 끝에)

```
✅ <task-id> 완료
   변경: <file 수> files, +<added> / -<removed> lines
   Warning: <count>
   Fix 재시도: <count>
```

---

## 최종 종합 리포트

모든 sub-task 완료 또는 halt 시 출력:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
work 종합 리포트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

기능: <feature>
Plan: .claude/plans/<dir>/
상태: ✅ 전체 성공 | ⚠️ warning 있음 | ❌ 중단

## Sub-task 결과

| # | id | 결과 | 변경 | 재시도 | 비고 |
|:-:|:---|:-----|:-----|:------|:-----|
| 1 | migration | ✅ PASS | 3 files, +120/-5 | 0 | — |
| 2 | api       | ⚠️ WARN | 5 files, +210/-40 | 1 | lint warning |
| 3 | ui        | ❌ FAIL | 2 files, +80/-10 | 3 | 재시도 소진 |

## 누적 변경

git diff --stat:
  <N files changed, +A / -B lines>

## 경고/이슈

### Warnings
- [task] [severity] <설명>
- ...

### 미해결 이슈 (halt 된 경우)
- [task] [severity] <설명>
- ...

## 다음 권장 액션

<상태별 권장 커맨드>
```

---

## 상태별 다음 액션

### 전체 성공 (✅)

```
다음 단계:
  1. git diff 로 전체 변경 확인
  2. /git-commit — 커밋 생성
  3. /github-pr-push — PR 생성
```

### Warning 있음 (⚠️)

```
다음 단계:
  1. 위 warning 검토
  2. 수동 dead code 정리 (필요 시)
  3. /git-commit
```

### 중단 (❌)

halt-policy.md 의 halt 리포트 포맷 사용:

```
❌ work halted

기능: <feature>
중단된 sub-task: <id> (<pr_scope>)
중단 stage: <stage>
사유: <구체적 이유>

완료된 sub-task: [<ids>]
남은 sub-task: [<ids>]

git status:
  ...

권장 조치:
  - /code-debug — root cause 분석
  - 수동 수정 후 재개 방법:
    /code <plan-dir> --resume-from <task-id>
    (현재 --resume 은 미구현, 수동으로 남은 task 에 대해 개별 실행)
```

---

## 출력 원칙

1. **시간순 스트리밍** — sub-task 진행을 실시간으로 배너로 표시
2. **들여쓰기 일관성** — stage 진행은 2-space 들여쓰기
3. **색상/이모지**: ✅ ⚠️ ❌ ✓ ✗ ↻ 만 사용 (과하지 않게)
4. **수치 명시** — "변경 많음" 금지, 항상 파일 수 + 라인 수로
5. **최종 리포트는 마크다운 테이블** — 여러 sub-task 비교 가독성
