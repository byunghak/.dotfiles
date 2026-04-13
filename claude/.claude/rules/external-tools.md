# External Tools (외부 도구 및 명령어)

## CLI

- **GitHub**: `gh` CLI 사용 (`gh pr`, `gh api`, `gh repo` 등)
- **Jira**: `jira` CLI 사용 (`jira issue`, `jira sprint`, `jira board`, `jira epic` 등)
- **Notion**: `notion` CLI 사용 (`notion page`, `notion search`, `notion block`, `notion db` 등). MCP 대신 CLI를 우선 사용하여 토큰 절약. 출력 포맷은 `--format md` 로 markdown 우선

## Shell 명령어 제약

- **`rm -rf` 절대 금지**: `rm -r` 사용할 것. 삭제 전 대상 파일 확인 필수
- **`rm` 사용 시**: 와일드카드(`*`) 사용 최소화. 삭제 대상을 명시적으로 나열
- **`sudo` 금지**: 권한 상승이 필요하면 사용자에게 위임
- **파이프를 통한 스크립트 실행 금지**: `curl | sh`, `wget | sh` 패턴 사용 금지
