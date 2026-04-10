# Stage: Fix — 빌드/테스트 에러 자동 수정

각 sub-task 파이프라인의 **조건부 단계**. Stage Post 가 FAIL 일 때만 진입. verify-agent 를 호출하여 fixable 에러를 자동 수정한다.

## 진입 조건

- Stage Post 의 종합 판정 = FAIL
- 재시도 카운트 < 최대값 (기본 3, `retry-policy.md` 참조)

## Step 1: 환경 수집

1. `git status --short` — 변경사항 확인
2. `git diff --name-only` — 변경 파일 목록
3. 프로젝트 타입 + 패키지 매니저 감지:
   - `package.json` → Node.js (npm/pnpm/yarn)
   - `Cargo.toml` → Rust
   - `go.mod` → Go
   - `pyproject.toml` → Python

## Step 2: verify-agent 호출 (1회)

Agent tool (subagent_type: verify-agent):

```
당신은 verify-agent 입니다.

프로젝트 타입: [감지된 타입]
패키지 매니저: [감지된 PM]
변경 파일: [git diff --name-only 결과]
의도: [sub-task pr_scope]

검증 모드: loop (내부 재시도 1회로 제한 — 오케스트레이터가 루프 관리)
검증 범위: all

순서: TypeCheck → Lint → Build → Test
- Fixable 에러는 자동 수정 후 재검증
- Non-fixable 에러는 목록으로 보고
- 최대 수정 파일 10개/라운드
- 수정 후 반드시 빌드 재실행으로 검증

Fixable 에러 기준:
| 유형            | 감지 패턴                | 수정 방법                   |
| --------------- | ------------------------ | --------------------------- |
| Missing Import  | Cannot find module       | import 문 추가              |
| Unused Import   | defined but never used   | import 행 제거              |
| Lint (auto-fix) | eslint fixable           | eslint --fix                |
| Type Mismatch   | not assignable           | 타입 캐스팅/인터페이스 수정 |
| Formatting      | prettier/gofmt           | 포매터 실행                 |

Non-fixable (로직 오류, 아키텍처 이슈)는 보고만 하고 수정하지 않음.

최종 결과 형식:
  ├── TypeCheck: ✅/❌
  ├── Lint: ✅/❌
  ├── Build: ✅/❌
  └── Test: ✅/❌
  상태: PASS/FAIL
  수정 내역: [파일:변경 요약]
  미해결: [에러 목록]
  lint warning: [N건]
```

## Step 3: 재검증

Fix 시도 후 **반드시 Stage Post 를 재실행** 하여 상태를 갱신한다:

1. Stage Post 의 verify-agent + code-reviewer + security-reviewer 를 다시 돌린다
2. 새 판정을 얻는다

## Step 4: 결과 처리

Stage Post 재실행 결과에 따라:

- **PASS / NEEDS ATTENTION** → Stage Clean 으로 진행
- **FAIL (재시도 여유 있음)** → Stage Fix 재진입 (retry 카운트 +1)
- **FAIL (재시도 소진)** → 전체 halt + 에스컬레이션

## 정체(stuck) 탐지

- 동일한 에러가 2회 연속 나오면 재시도해도 소용없음 → 즉시 halt
- "같은 에러" 판정: 파일 경로 + 에러 메시지 핵심(첫 줄) 일치

자세한 재시도 규칙은 `retry-policy.md`.

## Non-fixable 에러 처리

verify-agent 가 "미해결" 목록에 남긴 에러가 있으면:

- 로직 오류/아키텍처 이슈 → halt (자동 복구 불가)
- halt 리포트에 미해결 에러 목록 포함

## 옵션 (기본 비활성)

`/code` 호출 시 `--security` / `--coverage` 플래그가 넘어오면 활성화:

### --security

보안 검증 포함. verify-agent 와 security-pipeline 연동.

### --coverage

verify-agent 에 추가 지시: "테스트 커버리지를 측정하고 80% 미만 파일을 보고하세요."
