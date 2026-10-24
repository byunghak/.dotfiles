#!/bin/bash
# Remote Command Guard - PreToolUse Hook
# Bash 실행 전 위험 명령 7개 카테고리를 검사하여 차단
#
# Hook trigger: PreToolUse, matcher: Bash
# Exit codes: 0 = 허용, 2 = 차단
#
# 차단 범주:
#   1. 파괴적 삭제 (rm -rf /, rm -rf ~, rm -rf *)
#   2. 환경변수/시크릿 유출 (env, printenv, echo $SECRET 등)
#   3. 경로 순회 (/etc/passwd, /etc/shadow 등)
#   4. 외부 통신 (curl, wget, nc, ncat 등)
#   5. 권한 변경 (chmod 777, chown, mount 등)
#   6. 프로세스 종료 (kill -9, pkill 등)
#   7. 명령 주입 (eval, exec 등)

# stdin에서 JSON 읽기
INPUT=$(cat)

# 명령어 추출. 파싱 실패·python3 없음은 막는다 (fail-closed): 검사하지 못한 명령을 통과시키지 않는다
if ! command -v python3 &>/dev/null; then
	echo "BLOCKED: remote-command-guard cannot inspect the command (python3 not found)" >&2
	exit 2
fi
if ! COMMAND=$(printf '%s' "$INPUT" | python3 -c '
import sys, json
data = json.load(sys.stdin)
print(data.get("tool_input", {}).get("command", ""))
' 2>/dev/null); then
	echo "BLOCKED: remote-command-guard cannot parse the hook input JSON" >&2
	exit 2
fi

if [[ -z "$COMMAND" ]]; then
	exit 0
fi

# 환경변수로 명령어 전달 → Python 검사 로직
export _GUARD_CMD="$COMMAND"
python3 <<'GUARD_SCRIPT'
import os
import sys
import re

command = os.environ.get("_GUARD_CMD", "")
if not command:
    sys.exit(0)

# 명령어 정규화 (여러 공백 → 단일 공백)
cmd = re.sub(r'\s+', ' ', command.strip())
cmd_lower = cmd.lower()


def command_segments(text):
    """명령 위치(맨 앞, ; & | ( ) 뒤, 줄바꿈 뒤, $( 와 ` 안)에서 시작하는 조각을 돌려준다.

    명령 이름 패턴은 이 조각의 맨 앞에서만 맞춘다. 문자열 어디든 맞추면 커밋 메시지·PR 제목·따옴표 안의
    단어(nc, env, reboot 등)에도 막힌다. 따옴표 안의 ; | & 는 경계로 보지 않지만, $( 와 ` 는 따옴표 안에서도
    실행되므로 경계로 본다. heredoc 본문의 각 줄도 조각이 되므로 본문 줄이 명령 이름으로 시작하면 여전히 걸린다.
    """
    segments, current, quote, index = [], [], None, 0
    while index < len(text):
        char = text[index]
        if quote == "'":
            if char == "'":
                quote = None
            current.append(char)
            index += 1
            continue
        if char == "\\" and index + 1 < len(text):
            current.append(text[index:index + 2])
            index += 2
            continue
        if text.startswith("$(", index) or char == "`":
            segments.append("".join(current))
            current = []
            index += 2 if char == "$" else 1
            continue
        if quote == '"':
            if char == '"':
                quote = None
            current.append(char)
            index += 1
            continue
        if char in "'\"":
            quote = char
            current.append(char)
            index += 1
            continue
        if char in ";&|()\n":
            segments.append("".join(current))
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    segments.append("".join(current))
    # 명령 앞에 붙는 환경변수 대입·감싸는 명령은 건너뛰고 실제 명령 이름부터 보게 한다 (sudo 는 그 자체가 차단 대상이라 두지 않음)
    wrapper = re.compile(
        r'^\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+|rtk\s+|command\s+|nohup\s+|time\s+|doas\s+'
        # 뒤에 실제 명령이 올 때만 감싸는 env 로 본다. 단독 env(환경변수 덤프)는 지우지 않아야 secret 패턴이 잡는다
        r'|env\s+(?:-\S+\s+)*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*(?=\S)'
        r'|timeout\s+(?:-\S+\s+)*\S+\s+|nice\s+(?:-n\s+\S+\s+|-\S+\s+)*|xargs\s+(?:-\S+\s+)*)*'
    )
    return [re.sub(r'\s+', ' ', wrapper.sub('', seg)).strip() for seg in segments if seg.strip()]


segments = command_segments(command)

# 다른 명령을 문자열로 받아 실행하는 구조가 있으면 조각 맨 앞만 봐서는 안쪽 명령을 놓친다
# (bash -c "curl …", find -exec rm …, eval, parallel, watch, su -c). 이때는 예전처럼 문자열 전체에서 맞춘다 — 오탐보다 우회가 더 나쁘다
launches_nested_command = bool(re.search(
    r'\b(?:ba|z|da|k|fi)?sh\s+(?:-\S+\s+)*-\S*c\b|\s-exec(?:dir)?\s|\beval\b|\bparallel\b|\bwatch\b|\bsu\b.*\s-c\b|\bxargs\b',
    command, re.IGNORECASE,
))


def runs_at_command(patterns):
    """패턴이 어느 조각의 맨 앞에서 맞으면 True. 안쪽 명령을 실행하는 구조가 있으면 문자열 전체에서 맞춘다"""
    if launches_nested_command:
        return any(re.search(pat, cmd, re.IGNORECASE) for pat in patterns)
    return any(re.match(pat, seg, re.IGNORECASE) for seg in segments for pat in patterns)


blocked_reason = None

# === 1. 파괴적 삭제 ===
destructive_patterns = [
    r'\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s',
    r'\brm\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s',
    r'\brm\b.*\s+/$',
    r'\brm\b.*\s+/\s',
    r'\brm\b.*\s+~/?(\s|$)',
    r'\brm\b.*\s+\*(\s|$)',
    r'\bmkfs\b',
    r'\bdd\s+.*of=/dev/',
]
# fork bomb 은 ( ) | & 로 쪼개면 모양이 사라지므로 문자열 전체에서 본다
# ':' 는 단어 문자가 아니라 앞에 \b 를 두면 맨 앞의 ':' 에서 절대 맞지 않는다 (예전 패턴이 막지 못하던 이유)
fork_bomb_pattern = r':\s*\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;'
if runs_at_command(destructive_patterns) or re.search(fork_bomb_pattern, cmd_lower):
    blocked_reason = "파괴적 삭제 명령 감지"

# === 2. 환경변수/시크릿 유출 ===
if not blocked_reason:
    secret_patterns = [
        r'\b(env|printenv|set)\s*$',
        r'\b(env|printenv|set)\s*\|',
        r'\becho\s+.*\$[A-Z_]*KEY\b',
        r'\becho\s+.*\$[A-Z_]*SECRET\b',
        r'\becho\s+.*\$[A-Z_]*TOKEN\b',
        r'\becho\s+.*\$[A-Z_]*PASSWORD\b',
        r'\becho\s+.*\$[A-Z_]*PASSWD\b',
        r'\becho\s+.*\$[A-Z_]*API\b',
        r'\becho\s+.*\$[A-Z_]*CREDENTIAL\b',
        r'\becho\s+.*\$(AWS_|OPENAI_|ANTHROPIC_|TELEGRAM_|GITHUB_|SUPABASE_)',
        r'\bcat\s+.*\.env\b',
        r'\bcat\s+.*\.netrc\b',
        r'\bcat\s+.*credentials\b',
        r'\bcat\s+.*/\.ssh/',
        r'\bexport\s+-p\s*$',
        r'\bexport\s+-p\s*\|',
    ]
    # 조각은 | 에서 끊기므로 "env | …" 는 조각 "env" 로 남는다 → \s*$ 패턴이 잡는다
    if runs_at_command(secret_patterns):
        blocked_reason = "시크릿/환경변수 유출 시도 감지"

# === 3. 경로 순회 ===
if not blocked_reason:
    path_traversal_patterns = [
        r'/etc/passwd',
        r'/etc/shadow',
        r'/etc/sudoers',
        r'/etc/master\.passwd',
        r'\.\./(\.\./)*(etc|proc|sys|dev)/',
        r'/proc/self/',
        r'/proc/\d+/',
        r'/sys/class/',
    ]
    for pat in path_traversal_patterns:
        if re.search(pat, cmd_lower):
            blocked_reason = "민감 시스템 경로 접근 감지"
            break

# === 4. 외부 통신 ===
if not blocked_reason:
    network_patterns = [
        r'\bcurl(\s|$)',
        r'\bwget(\s|$)',
        r'\bnc(\s|$)',
        r'\bncat(\s|$)',
        r'\bnetcat(\s|$)',
        r'\btelnet(\s|$)',
        r'\bssh(\s|$)',
        r'\bscp(\s|$)',
        r'\brsync\s.*:',
        r'\bftp(\s|$)',
        r'\bsftp(\s|$)',
        r'\bsocat(\s|$)',
        r'\bpython3?\s+-m\s+http\.server',
        r'\bphp\s+-S\s',
        r'\bnpm\s+publish\b',
        r'\bnpx\s.*ngrok',
    ]
    local_hosts = {"localhost", "127.0.0.1", "0.0.0.0"}

    def is_local_curl(seg):
        """curl 이 가리키는 호스트가 전부 로컬일 때만 True (개발용 예외).

        문자열 어딘가에 localhost 가 있기만 하면 통과시키면 `curl https://evil/?x=localhost` 가 빠져나간다.
        scheme URL 의 호스트, scheme 없는 host[:port] 인자를 모두 모아 하나라도 로컬이 아니면 False.
        """
        if not re.match(r'curl(\s|$)', seg, re.IGNORECASE):
            return False
        url_hosts = re.findall(r'\b[a-z][a-z0-9+.-]*://(?:[^\s/@]*@)?([^\s/:?#]+)', seg, re.IGNORECASE)
        bare_hosts = [
            m.group(1)
            for m in re.finditer(r'(?:^|\s)([A-Za-z0-9.-]+\.[A-Za-z0-9-]+|localhost)(?::\d+)?(?:/\S*)?(?=\s|$)', seg)
            if not m.group(0).strip().startswith('-')
        ]
        hosts = [h.lower() for h in url_hosts + bare_hosts]
        return bool(hosts) and all(h in local_hosts for h in hosts)

    # 안쪽 명령을 실행하는 구조면 문자열 전체에서 맞추고 localhost 예외를 두지 않는다 (bash -c "curl localhost; curl evil")
    if launches_nested_command:
        if any(re.search(pat, cmd, re.IGNORECASE) for pat in network_patterns):
            blocked_reason = "외부 네트워크 통신 시도 감지"
    for seg in ([] if launches_nested_command else segments):
        if is_local_curl(seg):
            continue
        if any(re.match(pat, seg, re.IGNORECASE) for pat in network_patterns):
            blocked_reason = "외부 네트워크 통신 시도 감지"
            break

# === 5. 권한 변경 ===
if not blocked_reason:
    permission_patterns = [
        r'\bchmod\s+777\b',
        r'\bchmod\s+666\b',
        r'\bchmod\s+[0-7]*[67][0-7]{2}\b.*/(etc|usr|var|sys)',
        r'\bchown\s',
        r'\bmount\s',
        r'\bumount\s',
        r'\bsudo\s',
        r'\bsu\s+-?\s',
        r'\bdscl\s',
    ]
    if runs_at_command(permission_patterns):
        blocked_reason = "권한 변경 명령 감지"

# === 6. 프로세스 종료 ===
if not blocked_reason:
    process_patterns = [
        r'\bkill\s+-9\b',
        r'\bkill\s+-KILL\b',
        r'\bkill\s+-SIGKILL\b',
        r'\bkillall\s',
        r'\bpkill\s',
        r'\bxkill\b',
        r'\bshutdown\b',
        r'\breboot\b',
        r'\bhalt\b',
        r'\binit\s+[06]\b',
    ]
    if runs_at_command(process_patterns):
        blocked_reason = "프로세스 종료/시스템 제어 명령 감지"

# === 7. 명령 주입 ===
if not blocked_reason:
    # 명령 이름(eval·exec·source)은 명령 위치에서만, 나머지는 파이프·치환 구조라 문자열 전체에서 본다
    injection_commands = [
        r'\beval\s',
        r'\bexec\s',
        r'\bsource\s+/dev/',
    ]
    if runs_at_command(injection_commands):
        blocked_reason = "명령 주입 패턴 감지"
if not blocked_reason:
    injection_patterns = [
        r'\bbash\s+-c\s.*\$\(',
        r'\bsh\s+-c\s.*\$\(',
        r'`[^`]*\$\([^)]+\)[^`]*`',
        r'\|\s*sh\b',
        r'\|\s*bash\b',
        r'\|\s*zsh\b',
        r'>\s*/dev/sd[a-z]',
        r'>\s*/dev/nvme',
        r'\bbase64\s+-d\s*\|\s*(sh|bash|zsh)',
    ]
    for pat in injection_patterns:
        if re.search(pat, cmd_lower):
            blocked_reason = "명령 주입 패턴 감지"
            break

if blocked_reason:
    safe_cmd = cmd[:200]
    print(f"BLOCKED: {blocked_reason}", file=sys.stderr)
    print(f"Command: {safe_cmd}", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
GUARD_SCRIPT
