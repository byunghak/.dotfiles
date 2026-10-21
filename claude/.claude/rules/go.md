# Go Conventions

- **`Get` prefix 금지**: getter에 `Get` 접두사 사용하지 않음 (`GetName()` ❌ → `Name()` ✅)
- **에러 wrapping**: `return err` 금지. `fmt.Errorf("context: %w", err)`로 컨텍스트 추가
- **`panic` 금지 (라이브러리)**: 라이브러리 코드에서 panic 대신 error 반환. main/테스트에서만 허용
- **interface는 소비자 측에 정의**: 생산자가 interface를 만들지 않음. 필요한 쪽에서 최소 interface 정의
- **`init()` 지양**: 암묵적 초기화 대신 명시적 생성자 함수 사용
- **구현체는 `New` 생성자로 만든다**: 동작을 가진 struct는 호출부에서 리터럴로 조립하지 말고 `New`/`new` 생성자를 둔다. 불변식 검증과 기본값을 거기서 한다. 필드가 많으면 `Config` struct를 받고 구현체가 그것을 embed 한다 (`newTerminator(terminatorConfig{...})`) — 필드 중복 없이 호출부에서 이름이 보인다
