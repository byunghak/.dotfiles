---
name: work-debug
model: opus
allowed-tools: Read, Grep, Glob, Bash(git log:*), Bash(git diff:*), Bash(git blame:*), Bash(git status:*), Bash(npm test:*), Bash(npx:*), Bash(go test:*), Bash(cargo test:*), Bash(python -m pytest:*), Bash(make:*), Agent, Edit, AskUserQuestion
description: 버그/테스트 실패의 root cause를 체계적으로 추적하고 수정. Use when 버그, 테스트 실패, 예상치 못한 동작, 빌드 실패가 발생했을 때.
argument-hint: <에러 메시지, 증상, 또는 재현 방법>
---

# Work Debug — 체계적 디버깅

버그의 **root cause를 먼저 찾고**, 증거 기반으로 수정합니다.

> **Iron Rule**: root cause 파악 없이 수정 시도 금지. 증상 수정은 실패다.

---

## Step 1: 증거 수집

$ARGUMENTS에서 증상을 파악한 후, 다음을 **병렬로** 수집한다:

### Agent A: 에러 분석 (Explore)

Agent tool (subagent_type: Explore):

```
다음 에러/증상을 분석하세요:
[에러 메시지 또는 증상]

수행:
1. 에러 메시지/스택트레이스 전문 읽기 — 파일, 라인, 에러 코드 추출
2. 해당 파일:라인의 코드 읽기
3. 호출 체인 역추적 — 에러 발생 지점에서 호출자를 따라 올라가기
4. 관련 타입/인터페이스 확인

출력:
  ## 에러 위치: [file:line]
  ## 호출 체인: [caller → callee → error]
  ## 관련 코드 스니펫
  ## 초기 소견
```

### Agent B: 변경 추적 (Explore)

Agent tool (subagent_type: Explore):

```
최근 변경사항과 버그의 연관성을 분석하세요:

수행:
1. git log --oneline -20 — 최근 커밋 확인
2. git diff HEAD~5 --name-only — 최근 변경 파일
3. 변경 파일 중 에러 관련 파일 식별
4. git blame [에러 파일] — 문제 라인의 최근 변경자/시점

출력:
  ## 최근 변경 파일
  ## 에러 관련 변경 이력
  ## 의심 커밋: [hash] [message]
```

## Step 2: 증거 공유 + 재현 확인

수집된 증거를 사용자에게 요약하고, AskUserQuestion으로 확인:

```
⭐ 추천: [가장 유력한 원인 영역]

확인이 필요합니다:
1. 이 증상을 일관되게 재현할 수 있나요?
2. 언제부터 발생했나요? (특정 커밋/배포 이후?)
3. 추가 컨텍스트가 있나요?
```

재현 불가능하면 → 추가 로깅/계측 코드 제안 후 대기.

## Step 3: 패턴 비교

에러 영역이 확인되면, 동작하는 코드와 비교한다:

1. **유사 동작 코드 탐색** — Grep으로 같은 패턴/API를 사용하는 다른 코드 찾기
2. **차이점 식별** — 동작하는 코드와 깨진 코드의 차이 목록화
3. **의존성 확인** — 설정, 환경, 외부 시스템 계약

## Step 4: 가설 제시

AskUserQuestion으로 가설을 제시한다:

```
## 가설

**원인**: [구체적 root cause] (file:line)
**근거**: [증거 1], [증거 2]
**영향 범위**: [이 원인이 영향을 미치는 다른 곳]

⭐ 추천 수정 방향: [최소 변경 제안]

진행할까요?
```

사용자 승인 후 Step 5로 진행.

## Step 5: 최소 수정

핵심 원칙:

- **한 번에 하나만 변경** — 여러 수정을 묶지 않음
- **root cause 수정** — 증상이 아닌 원인을 고침
- **최소 변경** — "ついでに" 개선 금지

수정 후 관련 테스트/빌드를 실행하여 검증한다.

## Step 6: 검증 + 결과

```
## Work Debug — 결과

### Root Cause
[file:line] — [원인 설명]

### 수정 내역
- [file:line] [변경 내용]

### 검증
- 재현 테스트: ✅/❌
- 기존 테스트: ✅/❌

### 다음 단계: /work-fix (추가 검증) 또는 /git-commit
```

---

## 3회 실패 규칙

수정 시도가 **3회 실패**하면:

1. **즉시 중단** — 추가 수정 시도 금지
2. AskUserQuestion으로 아키텍처 재검토 제안:

```
⚠️ 3회 수정 실패 — 아키텍처 문제 가능성

패턴:
- [1차 시도]: [결과]
- [2차 시도]: [결과]
- [3차 시도]: [결과]

⭐ 추천: /work-pre로 구조 분석 후 접근법 재설계
```

---

## 다음 단계

| 결과에 따라    | 커맨드        |
| :------------- | :------------ |
| 추가 검증      | `/work-fix`   |
| 구조 문제 발견 | `/work-pre`   |
| 수정 완료      | `/git-commit` |
