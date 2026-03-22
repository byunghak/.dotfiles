---
name: work-post
model: opus
allowed-tools: Bash(npm:*), Bash(npx:*), Bash(pnpm:*), Bash(git:*), Bash(go:*), Bash(cargo:*), Bash(make:*), Read, Grep, Glob, Agent
description: 구현 완료 후 코드 품질, 빌드/테스트, 보안, DB 병렬 검증. Use when 기능 구현이 끝나고 커밋 전 종합 점검이 필요할 때.
argument-hint: [의도 설명 - 생략 시 git diff 기반 추론]
---

# Work Post — 구현 후 종합 검증

구현 완료 후 **에이전트를 병렬로** 실행하여 품질을 종합 검증합니다.

## Step 1: 환경 수집

1. `git diff --name-only` — 변경 파일 목록 (없으면 중단)
2. `git diff --stat` — 변경 규모 파악
3. 프로젝트 타입 감지: `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`
4. CLAUDE.md 읽기 (있으면)
5. DB 변경 감지: 변경 파일 중 `.sql`, `migration`, `schema`, `prisma`, `drizzle`, `knex`, `sqlalchemy` 관련 파일 존재 여부 확인

## Step 2: 서브에이전트 병렬 호출

다음 Agent tool 호출을 **동시에** 실행 (DB 변경이 없으면 3개, 있으면 4개):

### Agent A: code-reviewer (코드 품질)

Agent tool (subagent_type: code-reviewer):

```
당신은 code-reviewer 에이전트입니다.

변경 파일: [git diff --name-only 결과]
CLAUDE.md 규칙: [CLAUDE.md 내용]

변경된 코드를 리뷰하세요:
- CLAUDE.md 규칙 준수 여부
- 로직 오류, edge case, null/undefined
- 설계 적합성, 레이어 위반
- 에러 핸들링 누락, 리소스 해제

발견한 이슈를 severity(critical/major/minor)와 file:line으로 보고
```

### Agent B: verify-agent (빌드/테스트)

Agent tool (subagent_type: verify-agent):

```
당신은 verify-agent입니다.

프로젝트 타입: [감지된 타입]
변경 파일: [git diff --name-only 결과]
의도: $ARGUMENTS

검증 모드: single-pass (재시도 없음, 상태만 보고)
순서: TypeCheck → Lint → Build → Test

최종 결과를 다음 형식으로 보고:
  ├── TypeCheck: ✅/❌
  ├── Lint: ✅/❌
  ├── Build: ✅/❌
  └── Test: ✅/❌
  상태: PASS/FAIL
  lint warning: [N건] (unused import, unused variable 등)
```

### Agent C: security-reviewer (보안)

Agent tool (subagent_type: security-reviewer):

```
당신은 security-reviewer 에이전트입니다.

변경 파일: [git diff --name-only 결과]

변경된 파일만 대상으로 빠른 보안 스캔:
- 하드코딩된 secrets
- Injection 취약점 (SQL, XSS, Command)
- 인증/인가 우회 가능성
- 민감 데이터 로깅/노출

CRITICAL/HIGH 이슈만 보고 (MEDIUM 이하 생략)
```

### Agent D: database-reviewer (DB 변경 시에만)

DB 관련 파일이 변경된 경우에만 실행:

Agent tool (subagent_type: database-reviewer):

```
당신은 database-reviewer 에이전트입니다.

변경 파일: [DB 관련 변경 파일만]

변경된 DB 코드를 리뷰하세요:
- 마이그레이션 안전성 (데이터 손실, 롤백 가능 여부)
- 쿼리 성능 (N+1, 인덱스 누락, full table scan)
- 스키마 설계 (정규화, 제약 조건)
- RLS/권한 정책 누락

CRITICAL/HIGH 이슈만 보고
```

## Step 3: 결과 종합

모든 에이전트 결과를 합산하여 출력:

```
## Work Post — 종합 검증

### 빌드/테스트
├── TypeCheck: ✅/❌
├── Lint: ✅/❌
├── Build: ✅/❌
└── Test: ✅/❌

### 코드 리뷰
- [severity] 이슈 N건

### 보안
- [severity] 이슈 N건

### DB (해당 시)
- [severity] 이슈 N건

### 종합 판정: PASS / NEEDS ATTENTION / FAIL
```

| 판정            | 조건                                  |
| :-------------- | :------------------------------------ |
| PASS            | 빌드 통과 + critical 이슈 0건         |
| NEEDS ATTENTION | 빌드 통과 + major/minor 이슈 있음     |
| FAIL            | 빌드 실패 또는 critical 이슈 1건 이상 |

verify-agent 결과에 lint warning(unused import, unused variable 등)이 있으면
`/work-clean`에 `⭐ 추천` 태그를 붙여 안내한다.

### Agent 실패 처리

개별 agent가 실패(타임아웃, 에러)한 경우:

1. 실패한 agent를 결과에 `⚠️ 실패 (사유)` 로 표시
2. 나머지 agent 결과만으로 종합 판정 진행
3. 판정 시 실패한 agent 영역은 **미검증**으로 명시

---

## 다음 단계

| 결과에 따라         | 커맨드           |
| :------------------ | :--------------- |
| lint warning 있으면 | `⭐ /work-clean` |
| 이슈 수정 후        | `/work-fix`      |
| 모두 통과           | `/git-commit`    |
