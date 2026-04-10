# Halt Policy — 이슈 분류와 중단 규칙

work-auto 의 자동 실행 중 "언제 계속하고 언제 멈출지" 판단 기준. 이 파일을 교체/수정하면 오케스트레이터의 자동화 성향이 바뀐다.

---

## 핵심 정책 (요약)

1. **(a) critical 이슈만 자동 fix** — warning 은 리포트만
2. **(i) task 실패 시 전체 halt** — downstream sub-task 실행 금지
3. **자동 모드 위반 = 실패** — 하위 skill 이 사용자 질문을 시도하면 즉시 halt

---

## 이슈 severity 분류

`/work-post` 의 리포트는 `[severity] ...` 형식으로 이슈를 나열한다. 다음 규칙으로 분류:

### Critical (자동 fix 대상)

다음 중 하나:

- 빌드 실패 (compile error, type error)
- 테스트 실패 (unit/integration 어느 쪽이든)
- 린트 에러 (warning 이 아닌 error)
- `[critical]` 태그가 붙은 코드/보안 리뷰 이슈
- `[high]` 태그가 붙은 보안 리뷰 이슈
- DB 스키마 손상/migration 롤백 불가

### Warning (리포트만, 진행)

- `[major]`, `[minor]` 태그의 코드 리뷰 이슈
- `[medium]`, `[low]` 보안 이슈
- 테스트 커버리지 하락
- 린트 warning (unused import/var 등)
- 성능 퇴화 가능성 (측정 없는 추정)

### Unknown (안전하게 critical 취급)

severity 가 명시되지 않은 이슈는 **critical 로 분류**. 모호한 경우 보수적으로.

---

## Post 판정별 행동표

| `/work-post` 출력  | Critical 수 | Warning 수 | 행동                                |
| :----------------- | :---------- | :--------- | :---------------------------------- |
| `PASS`             | 0           | 0          | Stage 5 (clean) 진행                |
| `NEEDS ATTENTION`  | 0           | ≥1         | 리포트 기록 후 Stage 5 진행         |
| `FAIL`             | ≥1          | any        | Stage 4 (fix loop) 진입             |
| (파싱 실패)        | —           | —          | critical 취급 → Stage 4 진입        |
| (사용자 질문 감지) | —           | —          | **즉시 전체 halt** — 자동 모드 위반 |

---

## 자동 모드 위반 감지

다음 신호가 하위 skill 에서 감지되면 **자동 모드 위반**으로 판정:

- `AskUserQuestion` tool 호출
- "사용자에게 확인 필요", "어떻게 진행할까요" 등의 대화형 출력
- work-fix 의 "5회 초과 시 사용자에게 판단 요청" 상태

위반 시:

1. 현재 sub-task 파이프라인 즉시 halt
2. 위반 stage 와 사유를 리포트에 기록
3. **전체 파이프라인 halt** (정책 i 적용)
4. 사용자에게 에스컬레이션 (reporting.md 의 halt 포맷)

---

## Task 실패 전파 (정책 i)

한 sub-task 가 실패하면 downstream sub-task 는 실행하지 않는다. 이유:

- downstream 은 upstream 의 산출물에 의존 — 불완전한 상태에서 실행하면 2차 오염
- 부분 성공 상태는 수동 개입이 명확한 게 안전 (어디서 멈췄는지)
- 롤백 단위를 명확히 유지

**예외 없음**. "독립적인 sub-task 는 계속" 같은 optimistic 정책은 사용하지 않음. 정말 독립적이었다면 DAG 에서 depends_on 이 없었어야 하고, 그런 경우는 거의 없음.

---

## Clean 실패 특수 케이스

`/work-clean` 의 실패는 critical 이 아니다:

- clean 은 선택적 정리 단계
- 실패해도 코드 자체는 정상 동작
- 리포트에 `⚠️ clean failed: <reason>` 만 기록하고 다음 sub-task 진행

단, clean 이 **build 를 깨뜨린** 경우 (예: import 잘못 삭제) 는 critical — 이 경우 work-post 재실행으로 탐지되어 fix loop 진입.

---

## Halt 리포트 필수 포함 정보

중단 시 사용자에게 보여줄 정보:

```
❌ work-auto halted

기능: <feature>
중단된 sub-task: <id> (<pr_scope>)
중단 stage: pre / work / post / fix / clean
사유: <구체적 이유>

완료된 sub-task: [<id1>, <id2>, ...]
남은 sub-task: [<id3>, <id4>, ...]

git status:
  M: ...
  ?: ...

권장 조치:
  - <구체적 다음 액션>
  - 재개: <재개 방법>
```

이 정보가 있어야 사용자가 수동 복구 후 작업을 이어갈 수 있다.
