# Stage: Clean — 코드 정리

각 sub-task 파이프라인의 **마지막 단계**. refactor-cleaner 에이전트를 호출하여 dead code / 미사용 import / 중복을 정리한다.

## 입력

- Stage Impl / Fix 의 변경사항 (git working tree)

## Step 1: 환경 수집

1. `git diff --name-only` — 변경 파일 목록
2. 프로젝트 타입 감지
3. CLAUDE.md 읽기

## Step 2: refactor-cleaner 에이전트 호출

Agent tool (subagent_type: refactor-cleaner):

```
당신은 refactor-cleaner 에이전트입니다.

프로젝트 타입: [감지된 타입]
변경 파일: [git diff --name-only 결과]

다음 정리 작업을 수행하세요:

1. Dead code 탐지
   - 미사용 export, 함수, 클래스, 변수
   - 도구 활용: knip, depcheck, ts-prune (사용 가능한 것만)
   - 수동 탐지: Grep 으로 참조 카운트 확인

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
  - CAUTION: API 라우트, 컴포넌트, 자주 import 되는 모듈
  - DANGER: 설정 파일, 메인 엔트리포인트

핵심 원칙:
- SAFE 만 자동 삭제. CAUTION 은 보고만, DANGER 는 건드리지 않음
- 한 번에 하나의 파일/export 만 삭제
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

## Step 3: 결과 집계

```
## Clean — 정리 결과

### 삭제 완료
- [파일] 설명 (N건)

### 수동 확인 필요 (CAUTION)
- [파일] 설명

### 미사용 dependency
- [패키지명] — 상태

### 테스트: PASS / FAIL
```

## 실패 처리 (특수 케이스)

Clean 실패는 **critical 이 아니다**:

- clean 은 선택적 정리 단계
- 실패해도 코드 자체는 정상 동작
- 리포트에 `⚠️ clean failed: <reason>` 만 기록하고 다음 sub-task 진행

**예외**: clean 이 build 를 깨뜨린 경우 (예: import 잘못 삭제) → critical. 이 경우 Stage Post 재실행으로 탐지되어 Stage Fix 루프 진입.

## 자동 모드 제약

- 단독 재검증 안내 생략 (오케스트레이터가 Stage Post 재실행으로 검증)
- AskUserQuestion 없이 refactor-cleaner 의 분류 기준에만 의존
