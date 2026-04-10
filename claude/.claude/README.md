# Claude Code Configuration

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) 글로벌 설정입니다. 모든 프로젝트에 공통 적용됩니다.

## Setup

```sh
cd ~/.dotfiles
stow claude   # ~/.claude → symlink
```

## Directory Structure

```
.claude/
├── CLAUDE.md                  # 글로벌 행동 규칙 (Claude가 항상 읽음)
├── settings.json              # 권한, hooks, 모델 설정
├── agents/                    # 서브에이전트 정의 (.md)
├── skills/                    # Workflow 레시피 (SKILL.md)
├── hooks/                     # Pre/PostToolUse hook 스크립트
└── rules/                     # 언어/도메인별 코딩 규칙
```

## Quick Start

```sh
# 1. symlink 생성
cd ~/.dotfiles && stow claude

# 2. 아무 프로젝트에서 Claude Code 실행
cd ~/my-project && claude

# 3. 슬래시 커맨드 사용
/git-commit          # 변경 사항 커밋
/git-branch feat/xxx # 브랜치 생성
/github-pr-push      # PR 생성
```

## Skills (18개)

`.claude/skills/<name>/SKILL.md`에 정의합니다. `/skill-name`으로 호출하거나, auto-trigger 설정 시 모델이 자동 호출합니다.

### Git Workflow

| Skill      | 호출          | 모델   | 용도                                      |
| ---------- | ------------- | ------ | ----------------------------------------- |
| git-branch | `/git-branch` | sonnet | 프로젝트 컨벤션에 맞는 브랜치 생성        |
| git-commit | `/git-commit` | sonnet | 관심사별 분리, staged diff 리뷰 포함 커밋 |

### PR Workflow

| Skill             | 호출                         | 모델   | 용도                                                     |
| ----------------- | ---------------------------- | ------ | -------------------------------------------------------- |
| github-pr-push    | `/github-pr-push`            | sonnet | 브랜치 리뷰 → push → PR 생성/업데이트                    |
| github-pr-analyze | `/github-pr-analyze`         | opus   | PR 변경 구조 분석 (purpose, core changes, data flow)     |
| github-pr-review  | `/github-pr-review <PR번호>` | opus   | 5개 관점 병렬 PR 리뷰 (버그, 컨벤션, 설계, 보안, 테스트) |
| github-pr-respond | `/github-pr-respond`         | opus   | PR 리뷰 코멘트 순차 반영 + 답변 게시                     |

### 구현 파이프라인 (code-\*)

| Skill              | 호출                         | 모델 | 용도                                                                 | 단계   |
| ------------------ | ---------------------------- | ---- | -------------------------------------------------------------------- | ------ |
| code-brainstorming | `/code-brainstorming "설명"` | opus | 요구사항 탐색 + PM 분리 판단 + DESIGN/plan 작성                      | 기획   |
| code               | `/code <plan-dir>`           | opus | pre→impl→post→fix→clean 파이프라인을 DAG 순서로 자체 실행 (자체완결) | 실행   |
| code-debug         | `/code-debug`                | opus | 버그/테스트 실패의 root cause 추적 + 수정                            | 디버깅 |

### 사내 도구 연동 (dable-\*)

| Skill               | 호출                   | 모델   | 용도                                         |
| ------------------- | ---------------------- | ------ | -------------------------------------------- |
| dable-encrypt       | `/dable-encrypt`       | opus   | DB 컬럼 암호화 마이그레이션 3단계 워크플로우 |
| dable-jira-create   | `/dable-jira-create`   | sonnet | JIRA 이슈 생성                               |
| dable-jira-summary  | `/dable-jira-summary`  | sonnet | 브랜치 작업 내용을 JIRA 코멘트로 요약        |
| dable-sprint-report | `/dable-sprint-report` | sonnet | 스프린트 리포트 생성                         |

### 개인용

| Skill        | 호출            | 모델   | 용도                                                     |
| ------------ | --------------- | ------ | -------------------------------------------------------- |
| obsidian     | `/obsidian`     | sonnet | Obsidian vault 통합 — 노트 생성, 정리, 리서치, 학습 관리 |
| session-wrap | `/session-wrap` | sonnet | 세션 종료 시 4개 병렬 subagent로 문서화/학습/후속 작업   |

### 호출 방식

| 방식          | 설정                              | 해당 Skills                                                                         |
| ------------- | --------------------------------- | ----------------------------------------------------------------------------------- |
| auto-trigger  | `disable-model-invocation` 미설정 | git-commit, github-pr-push, github-pr-respond, github-pr-review, work-\* 전체 (6개) |
| 명시적 호출만 | `disable-model-invocation: true`  | git-branch, github-pr-analyze, dable-\* 전체 (4개), obsidian, session-wrap          |

## Agents (7개)

`.claude/agents/<name>.md`에 정의합니다. Skill에서 dispatch하거나 `Agent` tool의 `subagent_type`으로 직접 호출합니다.

### 분석/설계

| Agent       | 모델 | 용도                                 | dispatch하는 Skill                         |
| ----------- | ---- | ------------------------------------ | ------------------------------------------ |
| `architect` | opus | 아키텍처 분석, 디버깅 근본 원인 진단 | `/code-brainstorming`, `/code` (Stage Pre) |
| `planner`   | opus | 작업 분해, step-by-step 계획 수립    | `/code` (Stage Pre)                        |

### 리뷰

| Agent               | 모델 | 용도                                 | dispatch하는 Skill                        |
| ------------------- | ---- | ------------------------------------ | ----------------------------------------- |
| `code-reviewer`     | opus | 2단계 리뷰 (스펙 준수 → 코드 품질)   | `/code` (Stage Post), `/github-pr-review` |
| `security-reviewer` | opus | OWASP Top 10 기반 보안 취약점 분석   | `/code` (Stage Post)                      |
| `database-reviewer` | opus | 스키마, 쿼리, RLS, 마이그레이션 리뷰 | `/code` (Stage Post, DB 변경 시)          |

### 실행/검증

| Agent              | 모델   | 용도                                       | dispatch하는 Skill       |
| ------------------ | ------ | ------------------------------------------ | ------------------------ |
| `refactor-cleaner` | sonnet | dead code 제거, 코드 정리                  | `/code` (Stage Clean)    |
| `verify-agent`     | sonnet | 빌드 → 타입체크 → 린트 → 테스트 파이프라인 | `/code` (Stage Post/Fix) |

## Hooks (6개)

도구 실행 전후에 자동으로 동작합니다. 별도 호출이 필요 없습니다.

### 동작 흐름

```
[사용자 요청]
  → Claude가 도구 실행 결정
  → PreToolUse hook 검사 (Bash인 경우)
    → remote-command-guard: 위험 명령 차단 (exit 2)
    → rtk-rewrite: 명령어를 RTK proxy로 rewrite
  → 도구 실행 완료
  → PostToolUse hooks 순차 실행:
    1. output-secret-filter (모든 도구) → 시크릿 마스킹
    2. format-file (Edit/Write) → 포매터 실행
    3. security-auto-trigger (Edit/Write) → 보안 파일 수정 감지
    4. code-quality-reminder (Edit/Write) → 품질 체크 리마인더
```

### Hook 목록

| Hook                    | 트리거            | 동작                                     |
| ----------------------- | ----------------- | ---------------------------------------- |
| `remote-command-guard`  | Bash 실행 전      | 위험 명령 7개 카테고리 차단              |
| `rtk-rewrite`           | Bash 실행 전      | 명령어를 RTK proxy로 rewrite (토큰 절감) |
| `output-secret-filter`  | 모든 도구 실행 후 | API 키, 토큰 등 시크릿 자동 마스킹       |
| `format-file`           | 파일 수정 후      | 프로젝트 포매터 자동 실행                |
| `security-auto-trigger` | 파일 수정 후      | 보안 관련 파일 수정 감지 시 리뷰 권고    |
| `code-quality-reminder` | 코드 파일 수정 후 | 에러 핸들링, 불변성, 입력 검증 리마인더  |

### remote-command-guard 차단 카테고리

1. **파괴적 삭제** — `rm -rf`, `mkfs`, `dd`
2. **시크릿 유출** — `env`, `printenv`, `echo $SECRET_*`, `cat .env`
3. **경로 순회** — `/etc/passwd`, `/proc/self/`, `../../etc/`
4. **외부 통신** — `curl`, `wget`, `nc`, `ssh`, `scp` (localhost 제외)
5. **권한 변경** — `chmod 777`, `chown`, `sudo`, `mount`
6. **프로세스 종료** — `kill -9`, `pkill`, `shutdown`, `reboot`
7. **명령 주입** — `eval`, `exec`, `| sh`, `base64 -d | bash`

## Permission 모델

```
허용 (Bash(*), Read(*), Edit(*), ...)
  ↓ deny 규칙으로 위험 명령 차단
  ↓ PreToolUse hook으로 2차 검증
  = 안전한 명령만 실행
```

### 자동 차단되는 명령 (deny 규칙)

| 카테고리                 | 예시                                         |
| ------------------------ | -------------------------------------------- |
| 파괴적 삭제              | `rm -rf /`, `rm -rf ~`, `rm -rf .`           |
| 권한 상승                | `sudo`, `chmod 777`, `chown`, `mount`        |
| 외부 스크립트 실행       | `curl \| sh`, `wget \| sh`                   |
| Force push (main/master) | `git push --force main`                      |
| 패키지 배포              | `npm publish`, `pnpm publish`                |
| 코드 실행 주입           | `eval`, `bash -c`, `node -e`, `osascript`    |
| 시스템 설정 변경         | `crontab`, `launchctl`, `~/.zshrc` 덮어쓰기  |
| 시크릿/환경변수 유출     | `printenv`, `export -p`                      |
| 민감 경로 접근           | `/etc/passwd`, `/etc/shadow`, `/etc/sudoers` |
| 프로세스 종료            | `kill -9`, `killall`, `pkill`, `shutdown`    |

## Rules (5개)

Claude가 코드를 작성/수정할 때 자동 적용되는 규칙입니다.

| 파일                 | 내용                                                          |
| -------------------- | ------------------------------------------------------------- |
| `code-principles.md` | fail-fast, 불필요한 Optional 금지, 접근 제어, Stepdown Rule   |
| `typescript.md`      | destructuring 우선, 중괄호 필수, `type` 우선, `enum` 사용     |
| `python.md`          | namespace packages, `@property` 접근 제어, 타입 힌트 필수     |
| `go.md`              | `Get` prefix 금지, 에러 wrapping, `panic` 금지, `init()` 지양 |
| `rust.md`            | `unwrap()` 금지, `&str` 우선, 불필요한 `.clone()` 금지        |

## Plugins (14개)

`claude plugin install`로 설치합니다. 새 환경 설정 시 참고용 목록입니다.

### Core

| 플러그인               | 용도                                              |
| ---------------------- | ------------------------------------------------- |
| `superpowers`          | brainstorming, TDD, parallel agents 등 워크플로우 |
| `claude-md-management` | CLAUDE.md 관리 및 개선                            |
| `claude-hud`           | statusline HUD 표시                               |

### Integrations

| 플러그인     | 용도                      |
| ------------ | ------------------------- |
| `Notion`     | Notion 페이지/DB 연동     |
| `context7`   | 라이브러리 최신 문서 조회 |
| `serena`     | 시맨틱 코드 분석/편집     |
| `playwright` | 브라우저 자동화/테스트    |

### Code Quality

| 플러그인            | 용도                      |
| ------------------- | ------------------------- |
| `security-guidance` | 보안 가이드               |
| `frontend-design`   | 프론트엔드 UI 디자인 생성 |

### LSP

| 플러그인            | 언어       |
| ------------------- | ---------- |
| `pyright-lsp`       | Python     |
| `typescript-lsp`    | TypeScript |
| `rust-analyzer-lsp` | Rust       |
| `gopls-lsp`         | Go         |

### Output Styles

| 플러그인                | 설명           |
| ----------------------- | -------------- |
| `learning-output-style` | 학습+설명 모드 |

## 커스터마이징

### Skill 추가

`skills/<name>/SKILL.md` 파일을 생성하면 `/skill-name`으로 호출할 수 있습니다.

```yaml
---
name: my-skill
model: sonnet
disable-model-invocation: true
allowed-tools: Read, Bash(git diff:*)
description: 스킬 설명
---
프롬프트 내용을 여기에 작성합니다.
```

### Agent 추가

`agents/<name>.md` 파일을 생성하면 `subagent_type`으로 호출할 수 있습니다.

```yaml
---
name: my-agent
description: 에이전트 역할 설명
tools: ["Read", "Grep", "Glob", "Bash"]
model: sonnet
---
에이전트 프롬프트를 여기에 작성합니다.
```

### 규칙 추가

`rules/` 디렉토리에 `.md` 파일을 추가하면 Claude가 자동으로 읽고 적용합니다.

### 권한 수정

`settings.json`의 `permissions.allow`/`permissions.deny` 배열을 수정합니다. deny 규칙이 allow보다 우선합니다.
