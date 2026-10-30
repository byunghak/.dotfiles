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
- **요청마다 도는 경로는 할당을 센다**: hot path(요청·메시지마다 실행)에서
  - method value(`req.SetX`, `src.X`)를 slice·map·struct 에 담아 넘기지 않는다 — 칸마다 heap closure 가 된다. setter 를 직접 부르고 에러만 이름과 묶는다 (`check("bidId", req.SetBidId(v))`)
  - 검증만 하는 읽기는 `string` 복사 대신 `*Bytes()`·길이로 본다
  - goroutine·pool 작업 closure 는 필요한 칸만 캡처한다. 요청 객체 전체를 잡으면 큐 대기 동안 live heap 이 된다
  - 크기를 아는 slice 는 `make(..., 0, n)`. 원소가 한 자리 수면 map 대신 slice 선형 탐색
  - 요청 객체가 응답 뒤까지 살아남는 곳(비동기 발행·통보)에 `sync.Pool` 금지 — 돌려준 뒤 쓰는 버그가 된다
- **할당 주장은 측정으로**: "줄었다/늘었다" 는 `go build -gcflags=-m` 의 escape 줄과 `go test -bench -benchmem` 의 ns/op·B/op·allocs/op 전후 수치로 말한다. 측정 안 한 것은 "추정"
- **GC 런타임은 배포 설정에 둔다**: 컨테이너 메모리 limit 이 있는 Go 서비스는 `GOMEMLIMIT` 을 limit 의 ~85% 로 env 에 둔다 (없으면 GC 가 limit 을 모르고 버스트에서 OOMKill). `GOGC` 는 측정 근거 없이 바꾸지 않는다. Go 1.25+ 는 GOMAXPROCS 가 cgroup CPU limit 을 따르니 automaxprocs 를 넣지 않는다
- **라이브러리는 동기, 정책은 main**: 막히는 호출을 goroutine+select 헬퍼로 감싸지 말고 `context.AfterFunc` 등 표준 원시로 동기 함수를 유지. 기한·'기다리지 않기' 정책은 main 한 곳에서 조립. 공용 API 추가는 사용처가 여럿일 때만
