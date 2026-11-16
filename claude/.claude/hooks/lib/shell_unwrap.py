"""guard hook 공용: 문자열로 감싼 명령과 절대 경로 명령을 검사 가능한 꼴로 편다.

`/bin/sh -c 'git push --force'` 처럼 감싸면 명령 이름이 따옴표 안 한 토큰이 되어,
명령 이름을 토큰으로 찾는 guard 가 안쪽 명령을 보지 못했다 (11-14 재현: force push·secret 조회 통과).
`/usr/bin/curl … | /bin/bash` 는 명령 이름 앞의 경로 때문에 이름 패턴이 맞지 않았다.
"""

from __future__ import annotations

import re
import shlex

SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}
MAX_DEPTH = 5

# 실행 파일 디렉터리만 벗긴다. /etc/passwd 같은 데이터 경로는 경로 패턴이 그대로 봐야 한다
BIN_DIR = re.compile(
    r"(?<![\w./~-])(?:/usr/local|/opt/homebrew|/usr)?/s?bin/(?=[\w.+-]+(?=\s|$|[;&|)'\"`]))"
)


def strip_bin_dirs(command: str) -> str:
    """`/usr/bin/curl` → `curl`. 이름 패턴이 명령 위치에서 맞게 한다."""
    return BIN_DIR.sub("", command)


def nested_commands(command: str) -> list[str]:
    """command 자신과, 그 안에서 셸 `-c`·`eval` 로 실행되는 문자열을 모두 돌려준다 (중첩 포함)."""
    found = [command]
    frontier = [command]
    for _ in range(MAX_DEPTH):
        inner = [nested for text in frontier for nested in _direct_inner(text)]
        if not inner:
            break
        found.extend(inner)
        frontier = inner
    return found


def _direct_inner(command: str) -> list[str]:
    tokens = _tokens(command)
    inner: list[str] = []
    for index, token in enumerate(tokens):
        name = token.rsplit("/", 1)[-1]
        if name in SHELLS:
            script = _shell_c_argument(tokens[index + 1 :])
            if script is not None:
                inner.append(script)
        elif name == "eval":
            inner.append(" ".join(_until_operator(tokens[index + 1 :])))
    return inner


def _shell_c_argument(rest: list[str]) -> str | None:
    """`-c`(또는 -lc·-ec 같은 묶음) 뒤 첫 인자. -c 가 없으면 None."""
    has_c = False
    for token in rest:
        if token.startswith("-") and not token.startswith("--"):
            has_c = has_c or "c" in token[1:]
            continue
        if token.startswith("--"):
            continue
        return token if has_c else None
    return None


def _until_operator(rest: list[str]) -> list[str]:
    words = []
    for token in rest:
        if token and all(char in "|&;()" for char in token):
            break
        words.append(token)
    return words


def _tokens(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        # 따옴표가 안 닫힌 명령은 공백으로만 쪼갠다 — 안쪽 명령은 못 펴도 바깥 검사는 그대로 돈다
        return command.split()
