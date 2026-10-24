#!/usr/bin/env python3
"""work-session-title - UserPromptSubmit Hook

`/work <이슈>` 로 시작하는 prompt 면 세션 이름을 `<묶음>-worker-<n>-<주제>` 로,
`/work <plan 디렉토리>` 면 `<묶음>-worker-<디렉토리에서 날짜를 뺀 이름>` 으로 바꾼다.
묶음이 없으면 `issue-<n>-<주제>` · `plan-<이름>`.

근거: 세션 간 협업은 "이슈 1개 = 세션 1개" 이고 orchestrator 가 세션 이름으로 SendMessage 한다.
  `/rename` 을 사람이 잊거나 잘못 붙여 두 세션 이름이 겹쳤다.
  `/rename` 은 내장 명령이라 skill 본문으로는 부를 수 없어 hook 의 `sessionTitle` 을 쓴다.
  번호만으로는 tmux 칸·ListAgents 에서 무슨 작업인지 안 보여 주제를 붙인다.

묶음 접두사 (`<묶음>-orchestrator` 가 이 접두사로 자기 세션을 찾는다):
  orchestrator 가 `claude -n <묶음> "/work #N"` 으로 띄우면 지금 이름(`<묶음>`)을 접두사로 쓴다.
  이미 `<묶음>-worker-…`·`<묶음>-orchestrator`·`<묶음>-design` 인 세션에서 `/work` 해도 접두사를 지킨다.

인식하는 입력:
  /work #1657 · /work 1657 · /work https://github.com/<owner>/<repo>/issues/1657 → issue-1657-<주제>
  /work .claude/plans/2026-10-21-1657-app-cat/ (재개) → plan-1657-app-cat
작업 설명만 있는 `/work` 는 붙일 이름이 없어 그대로 둔다.
  `#` 없는 숫자 뒤에 글이 더 있으면 설명으로 본다 — `/work 3 files need cleanup` 이 issue-3 이 되지 않게.
  그래서 번호 뒤 주제 단어는 `#N` 이나 URL 에서만 받는다.

주제 (앞에서 정해지면 끝):
  1. 번호 뒤 단어 — `/work #1234 e2e` → issue-1234-e2e. 영문 소문자·숫자·`-` 단어만, 최대 2개
     번호 뒤가 한글 설명이면 1 은 건너뛴다
  2. 이슈 제목 — 앞 `[태그]` 를 빼고 영문 단어 앞 2개 (`gh issue view`, 3초. repo 는 URL 또는 cwd)
  3. 둘 다 없으면 issue-<n>
  주제는 20자 안에서 단어 단위로 자른다 — 단어 중간에서 끊으면 읽히지 않는다

ENV: `WORK_TITLE_GH_ACCOUNT` 가 있으면 `GH_TOKEN` 이 없을 때 그 계정 토큰을 쓴다
  (dotfiles 가 public 이라 계정 이름은 settings.local.json 의 env 에 둔다)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

GH_TIMEOUT_S = 3
TOPIC_MAX_WORDS = 2
TOPIC_MAX_LEN = 20

WORK_PREFIX = re.compile(r"^\s*/work\b(?P<args>.*)", re.DOTALL)
PLAN_DIR = re.compile(r"\.claude/plans/(?:\d{4}-\d{2}-\d{2}-)?(?P<name>[^/\s]+)")
ISSUE_URL = re.compile(r"github\.com/(?P<repo>[\w.-]+/[\w.-]+)/issues/(?P<number>\d+)")
ISSUE_NUMBER = re.compile(r"^\s*(?P<hash>#)?(?P<number>\d+)\b")
BUNDLE_ONLY = re.compile(r"[a-z][a-z0-9]*")
BUNDLE_PREFIX = re.compile(r"(?P<bundle>[a-z][a-z0-9]*)-(?:worker-|orchestrator$|design$)")
TOPIC_ARG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
TITLE_TAGS = re.compile(r"^\s*(?:\[[^\]]*\]\s*)+")
TITLE_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*|\d+[A-Za-z][A-Za-z0-9]*")


def session_title(prompt: str, current_title: str) -> str | None:
    work_item = _work_item(prompt)
    if work_item is None:
        return None
    kind, name = work_item
    bundle = _bundle(current_title)
    return f"{bundle}-worker-{name}" if bundle else f"{kind}-{name}"


def _work_item(prompt: str) -> tuple[str, str] | None:
    """("issue", "<n>-<주제>") 또는 ("plan", "<plan 이름>")."""
    work = WORK_PREFIX.match(prompt)
    if work is None:
        return None
    args = work.group("args")
    plan = PLAN_DIR.search(args)
    if plan is not None:
        return "plan", plan.group("name")
    url = ISSUE_URL.search(args)
    found = url or ISSUE_NUMBER.search(args)
    if found is None:
        return None
    rest = args[found.end() :]
    if url is None and found.group("hash") is None and rest.strip():
        return None
    number = found.group("number")
    repo = url.group("repo") if url else None
    topic = _topic_from_args(rest) or _topic_from_title(number, repo)
    return "issue", f"{number}-{topic}" if topic else number


def _bundle(current_title: str) -> str:
    # 묶음 이름만 붙은 새 세션이거나, 이미 묶음 접두사가 있는 작업 세션
    if BUNDLE_ONLY.fullmatch(current_title):
        return current_title
    prefixed = BUNDLE_PREFIX.match(current_title)
    return prefixed.group("bundle") if prefixed else ""


def _topic_from_args(rest: str) -> str:
    words: list[str] = []
    for token in rest.split():
        if TOPIC_ARG.fullmatch(token) is None:
            break
        words.append(token)
        if len(words) == TOPIC_MAX_WORDS:
            break
    return _fit(words)


def _topic_from_title(number: str, repo: str | None) -> str:
    title = _issue_title(number, repo)
    if title is None:
        return ""
    words = TITLE_WORD.findall(TITLE_TAGS.sub("", title))[:TOPIC_MAX_WORDS]
    return _fit([w.lower() for w in words])


def _issue_title(number: str, repo: str | None) -> str | None:
    # 제목을 못 읽어도 세션 이름은 번호만으로 정해져야 한다 — 오류는 삼킨다
    env = dict(os.environ)
    command = ["gh", "issue", "view", number, "--json", "title", "--jq", ".title"]
    if repo:
        command += ["-R", repo]
    try:
        account = env.get("WORK_TITLE_GH_ACCOUNT")
        if "GH_TOKEN" not in env and account:
            token = subprocess.run(
                ["gh", "auth", "token", "-u", account],
                capture_output=True,
                text=True,
                timeout=GH_TIMEOUT_S,
                check=True,
            )
            env["GH_TOKEN"] = token.stdout.strip()
        view = subprocess.run(
            command, capture_output=True, text=True, timeout=GH_TIMEOUT_S, check=True, env=env
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return view.stdout.strip() or None


def _fit(words: list[str]) -> str:
    if not words:
        return ""
    topic = words[0][:TOPIC_MAX_LEN]
    for word in words[1:]:
        if len(topic) + 1 + len(word) > TOPIC_MAX_LEN:
            break
        topic = f"{topic}-{word}"
    return topic


def main() -> None:
    hook_input = json.load(sys.stdin)
    current = hook_input.get("session_title") or ""
    title = session_title(hook_input.get("prompt", ""), current)
    if title is None or title == current:
        return
    print(
        json.dumps(
            {
                "systemMessage": f"세션 이름 → {title}",
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "sessionTitle": title,
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
