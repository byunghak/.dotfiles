---
paths:
  - "**/*.kt"
  - "**/*.kts"
---

# Kotlin Conventions

- **라이브러리는 호스트 앱을 죽이지 않는다**: 공개 API 입구에서 검증하고, 실패는 실패 콜백·`Result` 로 알린다. `!!`·`error()`·`require()` 로 호스트에 예외를 던지지 않는다. 테스트 코드는 해당 없음
- **앱에 넘기는 콜백은 메인 스레드**: listener 를 `Dispatchers.Main`·메인 `Handler` 에서 부른다. 호출 스레드에서 그대로 부르는 공개 API 는 KDoc 에 적는다
- **메인 스레드에서 I/O 금지**: 디스크·네트워크·DB 는 전용 실행기에서. 메인을 막으면 ANR
- **실행기 작업의 예외를 삼키지 않는다**: `ScheduledThreadPoolExecutor` 에 넘긴 작업이 던진 예외는 버려지는 `Future` 에 묻혀 신호 없이 멈춘다. 작업 본문에서 잡아 카운터·로그로 남긴다
- **라이브러리 의존성 최소**: 서드파티(Room 등)를 더하지 않고 플랫폼 API(시스템 SQLite 등)를 쓴다. 호스트 앱과 버전 충돌하면 빌드가 깨진다. R8 로 지워지면 안 되는 공개 클래스는 `consumer-rules.pro` 에 등록
- **Activity 재생성에 대비**: 회전·화면 크기 변경으로 Activity 가 다시 만들어지면 상태가 사라진다. `configChanges` 로 막거나 상태를 보존하고, 재생성 회귀 테스트를 둔다
- **시간은 주입**: 시계를 주입받아 테스트에서 경계값을 바로 만든다. 경과 시간은 `elapsedRealtimeNanos`(잠든 시간 포함). 테스트에서 `Thread.sleep` 금지
