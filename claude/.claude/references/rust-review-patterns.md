# Rust 리뷰 패턴 (반복 발견)

`code-reviewer`·`security-reviewer` 가 diff 에 `.rs` 파일이 있을 때 읽는다. 누적 PR 학습에서 반복 표면화된 항목이다.

## 품질 관점 (code-reviewer)


다음 패턴은 누적 PR 학습에서 반복 표면화된 항목. 코드 리뷰 시 우선 검토.

### Rust 멀티바이트 안전성 (UTF-8 boundary)

```rust
// BAD: &str[..N] 은 byte index — 멀티바이트 char 중간 → panic
let preview = &message[..50];

// BAD: b as char 은 ASCII 만 안전 — 멀티바이트 UTF-8 시퀀스 byte 변환 시 invalid char
let c = bytes[0] as char;

// GOOD: char boundary 안전한 슬라이싱
let preview: String = message.chars().take(50).collect();
```

### 다중 패턴 sanitize anchor min

```rust
// BAD: 첫 anchor 만 처리 — 앞쪽 secret 노출
for pattern in ["BEGIN PRIVATE KEY", "BEGIN RSA"] {
    if let Some(idx) = text.find(pattern) {
        return text[..idx].to_string();
        // break — 다른 패턴은 skip
    }
}

// GOOD: 모든 패턴의 min idx 찾기 — 앞쪽 secret 보호
// `-----BEGIN` 단일 anchor 가 모든 PEM 변종 흡수 + `eyJ` 가 JWT.
let min_idx = ["-----BEGIN", "eyJ"]
    .iter()
    .filter_map(|p| text.find(p))
    .min();
if let Some(idx) = min_idx {
    return text[..idx].to_string();
}
```

### ZeroizeOnDrop secrecy

```rust
// BAD: secret 이 Drop 후 메모리 잔류
struct ApiCredential {
    secret: String,
}

// GOOD: ZeroizeOnDrop derive 로 Drop 시 메모리 zeroize
use zeroize::ZeroizeOnDrop;
use secrecy::SecretString;

#[derive(ZeroizeOnDrop)]
struct ApiCredential {
    secret: SecretString,
}
```

### axum extractor 컴파일 타임 강제

```rust
// BAD: inline 가드 — 신규 라우트에서 누락 시 컴파일 통과
async fn admin_handler(headers: HeaderMap) -> Response {
    if !is_admin(&headers) {
        return StatusCode::FORBIDDEN.into_response();
    }
    // ...
}

// GOOD: FromRequestParts 구현으로 시그니처 자체가 강제
struct AdminAuthorized { user_id: Uuid }

impl<S> FromRequestParts<S> for AdminAuthorized {
    async fn from_request_parts(parts: &mut Parts, state: &S) -> Result<Self, Self::Rejection> {
        // 추출 + 검증 — 실패 시 라우트 진입 불가
    }
}

async fn admin_handler(auth: AdminAuthorized) -> Response {
    // 자동 검증 통과 후 진입 — 누락 시 컴파일 mismatch
}
```

### Saturating arithmetic bypass

```rust
// BAD: silent overflow — 음수 → u32 cast 시 wrap
let count = (n - m) as u32;  // n < m 이면 거대한 값

// GOOD: 명시적 검증
let count: u32 = (n - m).try_into().map_err(|_| Error::Underflow)?;
let count = n.checked_sub(m).ok_or(Error::Underflow)?;
```

## 보안 관점 (security-reviewer)


다음 패턴은 누적 PR 학습에서 반복 표면화된 항목. OWASP Top 10 외 추가 검토 대상.

### Rust 멀티바이트 안전성 — DoS/Memory Safety

```rust
// 위협: 사용자 입력 멀티바이트 char 중간 byte index 접근 → panic → DoS
// (Sentry/log preview, error message truncation 등에서 빈발)

// BAD
let preview = &user_input[..50];      // byte slice panic
let c = bytes[0] as char;             // non-ASCII byte → invalid char

// GOOD
let preview: String = user_input.chars().take(50).collect();
```

### 다중 패턴 sanitize anchor min — Credential Leak

```rust
// 위협: PEM/JWT/private key 등 다중 secret 형식 — 첫 anchor 만 처리 시 다른 형식 secret 누출
// (CLI stderr scrub, error message redaction 등)

// BAD: 첫 패턴만 처리 — 다른 secret 누출
for pattern in ["BEGIN PRIVATE KEY", "BEGIN RSA"] {
    if let Some(idx) = text.find(pattern) {
        return text[..idx].to_string();
    }
}

// GOOD: 모든 패턴 anchor 의 min idx — 앞쪽 secret 보호
// `-----BEGIN` 단일 anchor 가 모든 PEM 변종 (PRIVATE KEY / RSA / CERTIFICATE) 흡수 + `eyJ` 가 JWT.
let min_idx = ["-----BEGIN", "eyJ"]
    .iter()
    .filter_map(|p| text.find(p))
    .min();
if let Some(idx) = min_idx {
    return text[..idx].to_string();
}
```

### ZeroizeOnDrop secrecy — Memory Residue

```rust
// 위협: secret 이 Drop 후 메모리 잔류 → core dump/swap/heap inspection 시 노출

// BAD
struct ApiCredential { secret: String }  // Drop 후 메모리에 남음

// GOOD
use zeroize::ZeroizeOnDrop;
use secrecy::SecretString;

#[derive(ZeroizeOnDrop)]
struct ApiCredential { secret: SecretString }
```

### axum extractor 컴파일 타임 강제 — Authentication Bypass

```rust
// 위협: 신규 보호 라우트 추가 시 inline 가드 누락 → 인증 우회

// BAD: inline 가드 — 누락 시 컴파일 통과
async fn admin_handler(headers: HeaderMap) -> Response {
    if !is_admin(&headers) { return StatusCode::FORBIDDEN.into_response(); }
}

// GOOD: FromRequestParts — 시그니처 자체가 강제, 누락 시 컴파일 실패
async fn admin_handler(auth: AdminAuthorized) -> Response { /* ... */ }
```

### Saturating arithmetic bypass — Silent Overflow

```rust
// 위협: as cast 의 silent overflow — 음수 → u32 wrap 시 거대한 값 (DoS/limit bypass)

// BAD
let count = (n - m) as u32;  // n < m 이면 wrap

// GOOD
let count: u32 = (n - m).try_into().map_err(|_| Error::Underflow)?;
let count = n.checked_sub(m).ok_or(Error::Underflow)?;
```
