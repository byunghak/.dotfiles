---
paths:
  - "**/*.swift"
  - "**/*.mm"
---

# Swift Conventions

- **라이브러리는 호스트 앱을 죽이지 않는다**: 공개 API 입구에서 검증하고, 실패는 실패 콜백·`throws`·에러 결과로 알린다. `try!`·`fatalError`·`precondition`·강제 언래핑(`!`)으로 실패를 처리하지 않는다 (`init?(coder:)` 의 `fatalError()` 관용구만 예외). 테스트 코드는 해당 없음
- **앱에 넘기는 콜백은 메인 스레드**: delegate·completion 을 메인에서 부른다. 호출 스레드에서 그대로 부르는 공개 API 는 문서에 그렇게 적는다
- **메인 스레드에서 I/O 금지**: 디스크·네트워크·DB 는 전용 serial queue 에서. 메인을 막으면 터치·렌더가 멈춘다
- **delegate 는 `weak`**: 클로저가 `self` 를 오래 잡으면 `[weak self]`. 참조 카운트라 순환 참조는 누수가 된다
- **`Timer.scheduledTimer` 는 메인에서만**: 호출 스레드 RunLoop 에 걸려 동시성 풀·백그라운드 큐에선 울리지 않는다. 그 밖에서는 `DispatchSourceTimer`
- **ObjC optional delegate 는 테스트로 확인**: WebKit·UIKit·외부 SDK 의 optional 메서드는 시그니처(`@MainActor`·`@escaping` 등)가 틀려도 컴파일되고 호출만 안 된다. 구현하면 `responds(to:)` 테스트를 붙인다
- **시간은 주입**: 벽시계·monotonic 시계를 주입받아 테스트에서 경계값을 바로 만든다. 테스트에서 `sleep` 금지. `@MainActor` 테스트에서 동기 `wait` 대신 `await fulfillment`
- **동시성 변경은 TSan**: 스레드·큐·락을 바꾸면 `-enableThreadSanitizer YES` 로 테스트한다 (ASan 과 동시 불가). 통과여도 실행된 테스트 개수를 확인한다 — sanitizer 가 프로세스를 죽이면 일부만 돌고 초록으로 보인다
