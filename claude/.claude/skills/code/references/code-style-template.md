# Code Style Template

> 이 템플릿을 기반으로 `.claude/code-style.md`를 생성합니다.
> 기존 코드를 분석하여 각 섹션을 채웁니다.

```markdown
# Code Style: <프로젝트명>

## Architecture

- **패턴**: <layered / hexagonal / clean / MVC / monolith / microservice / etc.>
- **레이어 구조**: <예: controller → service → repository → entity>
- **의존성 방향**: <외부 → 내부, 상위 → 하위 등>

## Directory Structure
```

<프로젝트의 실제 디렉토리 구조 요약>

```

- **기능 배치 규칙**: <기능별 / 레이어별 / 도메인별>
- **새 파일 위치 판단 기준**: <어디에 무엇을 놓는가>

## Naming Conventions

- **파일명**: <camelCase / kebab-case / snake_case / PascalCase>
- **클래스/타입**: <PascalCase 등>
- **함수/메서드**: <camelCase / snake_case>
- **상수**: <UPPER_SNAKE_CASE>
- **도메인 용어**: <프로젝트 특유의 용어 매핑 — 예: "캠페인" = Campaign entity>

## Import / Module Organization

- **정렬 규칙**: <stdlib → 외부 → 내부, 알파벳 등>
- **그룹핑**: <빈 줄로 구분하는 기준>
- **경로 스타일**: <절대 / 상대 / alias>

## Error Handling Pattern

- **전략**: <Result 타입 / exceptions / error codes>
- **에러 전파 방식**: <wrapping / re-throw / transform>
- **로깅 위치**: <경계 레이어 / 발생 지점 / 둘 다>

## Test Conventions

- **프레임워크**: <jest / pytest / go test / etc.>
- **파일 배치**: <__tests__/ / *.test.ts / *_test.go / tests/ 등>
- **구조 패턴**: <given-when-then / arrange-act-assert / describe-it>
- **fixture 방식**: <factory / builder / fixture file / inline>
- **mock 정책**: <외부 의존성만 mock / repository mock / 전부 mock>

## Patterns in Use

- **DI 방식**: <constructor injection / module DI / global / none>
- **상태 관리**: <해당 시 — Redux, Zustand, Context 등>
- **API 스타일**: <REST / GraphQL / gRPC>
- **비동기 패턴**: <async/await / channels / callbacks>

## Don'ts (프로젝트 안티패턴)

- <기존 코드에서 관찰된 "하지 않는 것" 목록>
```
