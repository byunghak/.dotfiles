# Commit Rules

## 컨벤션 확인

Commit convention이 `__USE_DEFAULT__`이면 `git log --oneline -50`으로 패턴을 추론하여 `.claude/commit-convention.md`를 작성한다.

## Default Convention

> 프로젝트 commit convention이 존재하면 아래 대신 해당 규칙을 따른다.

### Format

```
<type>: <description>
```

### Allowed Types

| type       | 사용 상황                                       |
| ---------- | ----------------------------------------------- |
| `feature`  | 새로운 기능 추가                                |
| `fix`      | 버그 수정                                       |
| `chore`    | 빌드, 설정, 리팩토링, 이름 변경 등 기능 외 변경 |
| `refactor` | 기능 변경 없이 코드 구조 개선                   |
| `test`     | 테스트 추가/수정                                |
| `docs`     | 문서 수정                                       |

### Rules

1. type은 소문자
2. description은 영어 소문자로 시작, 마침표 없이
3. 한 커밋 = 한 가지 관심사 — 섞이면 커밋 분리
4. description은 무엇을(what)이 아닌 왜(why)/어떤 행위를 표현

## 관심사별 분리

변경 사항을 관심사별로 그룹핑하여 **항상 별도 커밋으로 처리**. 분리 여부를 사용자에게 묻지 않는다.

- 관심사 하나 → 단일 커밋
- 관심사 여러 개 → 의존성 순서:
  ```
  기반 타입/에러 정의 → 하위 레이어 → 상위 레이어 → 테스트
  ```
- 파일 내 일부만 스테이징 필요 시 `git add -p` 사용

## Staged Diff 리뷰

각 관심사 그룹 스테이징 후, 커밋 전에 리뷰:

1. staged diff + 관련 컨텍스트를 Read로 확인
2. 4관점(버그, 컨벤션, 보안, 설계) 리뷰, confidence 70+ 이슈만 보고
3. false positive 제외 (linter가 잡을 이슈, pre-existing, nitpick)
4. 이슈 발견 시 AskUserQuestion:
   - **수정** — 이슈 수정 후 커밋
   - **그대로 커밋** — 무시하고 커밋
5. 이슈 없으면 바로 커밋
