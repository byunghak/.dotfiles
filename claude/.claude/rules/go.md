---
paths:
  - "**/*.go"
---

# Go Conventions

- **`Get` prefix 금지**: getter에 `Get` 접두사 사용하지 않음 (`GetName()` ❌ → `Name()` ✅)
- **에러 wrapping**: 패키지 경계를 넘거나 I/O·외부 호출 결과를 돌려줄 때 맥락을 추가한다. 같은 패키지 안의 helper 에서 받은 에러는 `return err`로 그대로 전파한다. 호출자가 원본을 `errors.Is/As`로 검사해야 할 때만 `%w`를 쓴다 (감싼 에러가 공개 API 가 되므로)
- **라이브러리에서 `panic` 회피**: 호출자가 처리할 수 있는 실패는 `error`로 반환한다. `panic`은 복구 불가능한 내부 불변식 위반이나 프로그래머 오류로 제한한다
- **interface는 소비자 측에 정의**: 생산자가 interface를 만들지 않음. 필요한 쪽에서 최소 interface 정의
- **`init()` 지양**: 암묵적 초기화 대신 명시적 생성자 함수 사용
- **구현체는 `New` 생성자로 만든다**: 동작을 가진 struct는 호출부에서 리터럴로 조립하지 말고 `New`/`new` 생성자를 둔다. 불변식 검증과 기본값을 거기서 한다. 필드가 많으면 `Config` struct를 받고 구현체가 그것을 embed 한다 (`newTerminator(terminatorConfig{...})`) — 필드 중복 없이 호출부에서 이름이 보인다
- **라이브러리는 동기, 정책은 main**: 막히는 호출을 goroutine+select 헬퍼로 감싸지 말고 `context.AfterFunc` 등 표준 원시로 동기 함수를 유지. 기한·'기다리지 않기' 정책은 main 한 곳에서 조립. 공용 API 추가는 사용처가 여럿일 때만
