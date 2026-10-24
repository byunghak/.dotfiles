---
paths:
  - "**/*.{py,pyi}"
---

# Python Conventions

- Namespace Packages 우선: `__init__.py`는 regular package가 필요하거나 프로젝트·도구가 요구할 때만 추가
- 비공개 속성은 이름 앞의 `_`로 표시한다. `@property`는 계산·검증·호환성 등 접근 시 동작이 필요한 경우에 쓴다
- **`__` name mangling은 클래스 내부 전용**: module-level private 함수/변수는 `_single_underscore` 사용 (`__`는 클래스 밖에서 mangling이 작동하지 않음)
- **타입 힌트 필수**: 함수 시그니처에 파라미터 타입과 반환 타입 항상 명시
- **`dataclass`/`NamedTuple` 우선**: 구조화된 데이터에 plain dict/tuple 대신 사용
- **f-string 우선**: `format()`, `%` 대신 f-string 사용
