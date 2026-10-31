# External Tools (외부 도구 및 명령어)

## CLI

- **GitHub**: `gh` CLI 사용 (`gh pr`, `gh api`, `gh repo` 등)
- **Jira**: `jira` CLI 사용 (`jira issue`, `jira sprint`, `jira board`, `jira epic` 등)
- **Notion**: claude.ai Notion MCP 사용 (10-31 사용자)

## Shell 명령어 제약

- **`rm -rf` 절대 금지**: `rm -r` 사용할 것. 삭제 전 대상 파일 확인 필수
- **`rm` 사용 시**: 와일드카드(`*`) 사용 최소화. 삭제 대상을 명시적으로 나열
- **`sudo` 금지**: 권한 상승이 필요하면 사용자에게 위임
- **파이프를 통한 스크립트 실행 금지**: `curl | sh`, `wget | sh` 패턴 사용 금지
- **`cp`·`rm` 은 `-i` 별칭**: 확인 프롬프트에서 멈춘다 → python `shutil.copyfile`·`shutil.rmtree`·`os.remove` 사용
- **훅·권한이 막는 명령**: `nc`, `xargs`, 명령 문자열 안의 프로세스 종료 명령어(heredoc 본문 포함) → 그런 내용을 담은 파일은 Write 도구로 쓴다
