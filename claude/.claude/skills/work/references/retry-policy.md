# Retry Policy — Stage Fix 재시도 규칙

Stage Post 가 FAIL 일 때 Stage Fix 를 몇 번 시도할지, 언제 포기할지 결정한다.

---

## 기본값

| 항목                      | 값   |
| :------------------------ | :--- |
| 최대 재시도 횟수          | 3    |
| 동일 에러 연속 횟수 한계  | 2    |
| Fix 이후 Post 재실행 여부 | 필수 |

---

## 재시도 루프 구조

```
attempt = 0
loop:
  attempt += 1
  Stage Fix 수행 (verify-agent 1회 호출)
  Stage Post 재수행
  classify result:
    PASS              → break (성공)
    NEEDS ATTENTION   → break (warning only, Stage Clean 으로)
    FAIL:
      if attempt >= 3      → halt (실패 확정)
      if 같은 에러 2회 연속 → halt (정체 탐지)
      else                 → continue
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

1. Stage Post 재수행 필수 — fix 가 새 에러를 만들었을 수 있음
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

이 숫자는 오케스트레이터 수준에서 고정. 조정 필요 시 이 파일 수정.

---

## verify-agent 내부 재시도와의 관계

Stage Fix 는 verify-agent 를 호출할 때 **내부 재시도 1회**만 허용한다. 오케스트레이터(이 파일) 가 루프를 직접 관리해야 횟수/로그 추적이 정확해지기 때문이다.

중첩 재시도는 시도 횟수가 불투명해진다 (3×3=9 같은). 단일 책임 원칙: **재시도 관리는 오케스트레이터(retry-policy.md)에서만**.
