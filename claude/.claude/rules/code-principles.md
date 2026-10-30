# Code Principles (언어 공통)

- **fail-fast**: validation 실패 시 skip/warn 금지, 즉시 `raise`/`throw`. 불필요한 try-catch 래핑 금지
- **불필요한 Optional 분기 금지**: 런타임에 항상 존재하는 값은 필수 타입으로 선언. 진입점에서 검증 후 이후 로직은 분기 없이 단순하게
- **접근 제어 엄격 적용**: private/protected/public 구분을 언어 관례에 맞게 엄격히 적용. 내부 전용을 최소 접근 수준으로 퉁치지 말 것
- **Stepdown Rule**: public 메소드를 먼저 선언하고, 호출되는 private 메소드를 아래에 배치. 호출 순서대로 위→아래로 읽히도록 구성
- **파라미터 3개 이상 → 객체/구조체 형태**: 공개 API 타입은 별도 정의
- **조기 반환 (Guard Clause)**: 중첩 if 대신 실패 조건을 먼저 걸러내고 early return. 정상 흐름은 indent 없이 flat하게
- **불변성 우선**: 불변 선언을 기본으로 사용. mutation이 필요하면 명시적 범위 한정 (예: builder pattern, 지역 변수 내)
- **순수 함수 우선**: side effect(I/O, 상태 변경)는 호출 경계로 밀어내고, 핵심 로직은 입력→출력만으로 구성
- **Any 타입 금지**: 언어별 any/Any 계열 타입 사용 금지. 제네릭, union, 구체 타입으로 해결. 외부 라이브러리 한계로 불가피한 경우만 inline suppress와 함께 허용
- **단순화 우선**: 타입 에러는 cast()/wrapper보다 inline suppress(`// @ts-ignore`, `# pyright: ignore`) 우선. 복잡한 diff parsing/multi-step workaround보다 직접 편집 우선
- **Boolean 파라미터 금지**: `process(data, true, false)` 금지. enum, 별도 메소드, 또는 옵션 객체로 대체하여 호출부 가독성 확보
- **에러에 컨텍스트 포함**: 제네릭 에러 메시지 금지. 디버깅에 필요한 식별자, 상태, 입력값을 포함
- **네이밍 구체성**: `data`, `result`, `info`, `item`, `temp` 같은 모호한 이름 금지. 도메인 용어로 의미를 드러낼 것
- **테스트는 실제 외부로 나가지 않는다**: 테스트가 Slack·메일·결제·프로덕션 API·클라우드 리소스(Secret Manager 등)에 닿으면 안 된다. 로컬엔 ADC·토큰이 살아 있어 "설정이 없으면 실제 값을 조회" 하는 fallback 이 그대로 성공한다. 개별 테스트의 stub 에만 기대지 말고, 테스트 공통 설정(conftest·setup 파일)에 외부 호출을 막고 호출되면 실패시키는 가드를 둔다. 가드 없는 코드베이스에 전송 경로 테스트를 더할 때는 가드부터 넣는다 (2026-10-27: airflow 실패 알림 테스트가 실제 알림 채널로 반복 전송)
