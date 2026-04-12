# PR Rules

## 정적 분석 (Push 전)

변경 파일 대상으로 정적 분석. 해당 도구가 프로젝트에 존재하는 경우에만, 병렬 실행.

| 조건                                 | 실행                  |
| ------------------------------------ | --------------------- |
| `package.json`의 `scripts.lint` 존재 | `npx eslint <files>`  |
| pyright 설정 존재                    | `npx pyright <files>` |

- warning 무시, error만 보고
- error 시 AskUserQuestion: **수정** / **그대로 진행**

## PR 생성

### 제목

`[JIRA-TICKET] <description>` — 브랜치명에서 티켓 패턴 추출 (예: `BE-1376`, `SUPPORT-3210`). 찾을 수 없으면 사용자에게 JIRA 번호 확인 요청.

WIP인 경우 `[WIP]` prefix 추가.

### Body

**PR template이 있는 경우** — template 구조를 유지하면서:

- **JIRA 섹션**: 브랜치명에서 추출, `https://teamdable.atlassian.net/browse/TICKET`. 없으면 `N/A`
- **Changes 섹션**: 커밋 목록과 변경 파일 분석, bullet point
- **Why 섹션**: 변경 이유/목적
- **체크리스트 섹션**: 변경 내용 기준으로 `[x]`/`[ ]` 체크

**PR template이 없는 경우**:

```markdown
## JIRA

https://teamdable.atlassian.net/browse/TICKET

## Changes

- <변경 내용>

## Why

- <변경 이유>
```

### Assignee & Label

- Assignee: `@me`
- Label: 브랜치 prefix에서 추론:

| 브랜치 prefix                | Label           |
| ---------------------------- | --------------- |
| `feature/`, `feat/`          | `enhancement`   |
| `fix/`, `bugfix/`, `hotfix/` | `bug`           |
| `refactor/`                  | `refactor`      |
| `docs/`                      | `documentation` |
| `chore/`                     | `chore`         |

매칭 실패 시 `gh label list`로 선택지 제공.

## PR 업데이트 (기존 PR)

기존 PR body에 반영되지 않은 커밋 분석:

- **주요 변경** (새 파일, 아키텍처, 동작, 기능) → title/body 재생성
- **마이너 변경** (bugfix 연장, typo, lint) → push만으로 충분, body 미갱신
