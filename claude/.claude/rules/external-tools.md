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
- **훅·권한이 막는 명령**: `nc`, 명령 위치의 프로세스 종료 명령어(`pkill`·`kill -9`), 따옴표 없는 heredoc 본문 → 그런 내용을 담은 파일은 Write 도구로 쓴다. 따옴표 heredoc(`<<'EOF'`) 본문은 검사하지 않는다
- **막히면 처음부터 대안으로** (차단 1건마다 재시도 3~5회, 10일 약 700회 — 11-05): 프로세스 종료 → `pgrep -f <패턴>` 으로 PID 확인 뒤 `kill <PID>` · 기다리기 → `sleep` 대신 `run_in_background` 완료 알림이나 Monitor · 외부 HTTP → `curl` 대신 WebFetch · `$(`·`bash -c`·`xargs` 가 든 긴 명령 → 스크립트 파일로 쓰고 실행
