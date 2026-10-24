---
paths:
  - "**/*.rs"
---

# Rust Conventions

- **오류 처리**: production의 fallible operation은 `Result`와 `?`로 전파한다. `unwrap()`은 테스트에만 쓰고, `expect()`는 프로그래머 불변식과 실패 이유를 명확히 설명할 수 있을 때만 허용. `expect` 메시지에는 실패하지 않는 이유(불변식)를 쓴다
- **`&str` 우선**: 함수 파라미터에 `String` 대신 `&str`. 소유권이 필요한 경우만 `String`
- **불필요한 `.clone()` 금지**: 소유권/참조로 해결 가능하면 clone 하지 않음
- **Rust 설명은 Go 와 짝지어**: 메모리 레이아웃 그림 + 레포 실제 코드 + `~/.cargo/registry/src` crate 소스를 함께, Go 대응 개념과 짝지을 것 (사용자는 Go 배경, Rust 초보)
- **`clippy` 준수**: `#[allow(clippy::...)]` 남발 금지. 정당한 사유 있을 때만 주석과 함께 허용
