# Retry Policy — work-fix 재시도 규칙

`/work-post` 가 FAIL 일 때 `/work-fix` 를 몇 번 시도할지, 언제 포기할지 결정한다.

---

## 기본값

| 항목                      | 값   |
| :------------------------ | :--- |
| 최대 재시도 횟수          | 3    |
| 동일 에러 연속 횟수 한계  | 2    |
| fix 이후 post 재실행 여부 | 필수 |

---

## 재시도 루프 구조

```
attempt = 0
loop:
  attempt += 1
  run /work-fix (오케스트레이터가 최대 1회만 내부 재시도 지시)
  run /work-post
  classify result:
    PASS              → break (성공)
    NEEDS ATTENTION   → break (warning only, clean 으로 진행)
    FAIL:
      if attempt >= 3 → halt (실패 확정)
      else:           continue
```

---

## 정체(stuck) 탐지

동일한 에러가 연속 N회 나오면 재시도해도 소용없을 가능성이 높다.

- **같은 에러 2회 연속**: 재시도 포기 + halt
- **새 에러 등장**: counter reset, 남은 재시도 계속

"같은 에러"의 판정:

- 파일 경로 + 에러 메시지 핵심(첫 줄) 일치
- 파싱 어려우면 보수적으로 "다른 에러"로 간주 (재시도 계속)

---

## 재시도 중 동작 규칙

### 매 시도 전

1. `git status --short` 로 dirty state 확인
2. 이전 fix 시도의 diff 기록 (다음 시도 판단용)

### 매 시도 후

1. `/work-post` 재실행 필수 — fix 가 새 에러를 만들었을 수 있음
2. 결과를 halt-policy.md 로 재분류

### 재시도 소진 시

halt-policy.md 의 halt 리포트 포맷에 다음 정보 추가:

```
재시도 횟수: <N>/3
마지막 에러: <요약>
시도별 diff 크기:
  attempt 1: +N -M
  attempt 2: +N -M
  attempt 3: +N -M
```

---

## 왜 최대 3회인가

- **1회**: 단순 빌드/타입 에러 복구율 높음
- **2회**: 1회 시도가 새 에러를 만든 경우 복구
- **3회**: 1회/2회 사이 진동(oscillation) 마지막 기회
- **4회 이상**: 경험적으로 자동 복구 확률 급감, 사람이 개입하는 게 빠름

이 숫자는 오케스트레이터 수준에서 고정. 사용자 조정 필요 시 이 파일 수정.

---

## work-fix 내부 재시도와의 관계

`/work-fix` 는 자체 `--max-retries` 옵션을 가진다. 오케스트레이터는 이를 **1 로 고정**하여 호출한다:

```
work-fix <pr_scope> --max-retries 1
```

이유:

- 오케스트레이터가 fix 와 post 사이클을 직접 관리해야 정확한 횟수/로그 추적 가능
- 중첩 재시도는 시도 횟수가 불투명해짐 (3×3=9 같은)
- fix 내부 재시도와 우리의 재시도가 서로 다른 정체 판정을 가질 수 있음

단일 책임 원칙: **재시도는 오케스트레이터에서만**.
