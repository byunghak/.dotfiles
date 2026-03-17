---
name: work-clean
model: opus
allowed-tools: Bash(npm:*), Bash(npx:*), Bash(pnpm:*), Bash(git:*), Bash(go:*), Bash(cargo:*), Bash(pip:*), Read, Edit, Write, Grep, Glob, Agent
description: dead code 제거, 미사용 import/변수/dependency 정리, 코드 중복 제거. Use when 구현 완료 후 코드 정리가 필요할 때.
---

# Work Clean — 코드 정리

> **참고**: 대규모 리팩토링(3파일 이상 변경 예상)은 `/work-pre`를 먼저 실행하세요.

## Step 1: 환경 수집

1. `git diff --name-only` — 변경 파일 목록
2. 프로젝트 타입 감지: `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`
3. CLAUDE.md 읽기 (있으면)

## Step 2: refactor-cleaner 에이전트 호출

Agent tool (subagent_type: general-purpose, model: sonnet)로 호출:

```
당신은 refactor-cleaner 에이전트입니다.

프로젝트 타입: [감지된 타입]
변경 파일: [git diff --name-only 결과]

다음 정리 작업을 수행하세요:

1. Dead code 탐지
   - 미사용 export, 함수, 클래스, 변수
   - 도구 활용: knip, depcheck, ts-prune (사용 가능한 것만)
   - 수동 탐지: Grep으로 참조 카운트 확인

2. 미사용 dependency 정리
   - Node.js: depcheck 또는 package.json 대조
   - Rust: cargo-udeps (설치되어 있으면)
   - Go: go mod tidy (dry-run)
   - Python: pip-autoremove 또는 import 대조

3. 코드 중복 제거
   - 변경 파일 내 반복 패턴 식별
   - 3회 이상 반복되는 패턴만 대상

분류 기준:
  - SAFE: 테스트 파일, 미사용 유틸리티, 미사용 dependency
  - CAUTION: API 라우트, 컴포넌트, 자주 import되는 모듈
  - DANGER: 설정 파일, 메인 엔트리포인트

핵심 원칙:
- SAFE만 자동 삭제. CAUTION은 보고만, DANGER는 건드리지 않음
- 한 번에 하나의 파일/export만 삭제
- 삭제 전 테스트 실행 → 삭제 → 재테스트 → 실패 시 롤백
- When in doubt, don't remove

출력 형식:
  ## 삭제 완료
  - [파일:라인] 설명 (N건)
  ## 보고만 (CAUTION)
  - [파일:라인] 설명 — 수동 확인 필요
  ## 미사용 dependency
  - [패키지명] — 제거 가능/확인 필요
```

## Step 3: 결과 출력

에이전트 결과를 사용자에게 전달:

```
## Work Clean — 정리 결과

### 삭제 완료
- [파일] 설명 (N건)

### 수동 확인 필요 (CAUTION)
- [파일] 설명

### 미사용 dependency
- [패키지명] — 상태

### 테스트: PASS / FAIL
```

---

## 다음 단계

| 정리 후   | 커맨드        |
| :-------- | :------------ |
| 검증      | `/work-fix`   |
| 종합 점검 | `/work-post`  |
| 커밋      | `/git-commit` |
