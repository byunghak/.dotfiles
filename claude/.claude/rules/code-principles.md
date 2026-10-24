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
