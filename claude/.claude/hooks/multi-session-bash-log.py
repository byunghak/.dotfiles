#!/usr/bin/env python3
"""PreToolUse·PostToolUse(Bash) hook: multi-session worker 의 Bash 호출과 실행 여부를 기록만 한다.

worker 명령이 막힐 때 막는 쪽이 모델 판단인지 auto mode classifier·권한 프롬프트인지 가르려는 관찰용이다.
Pre 만 있고 같은 tool_use_id 의 Post 가 없으면 실행되지 않은 호출이다. 어떤 결정도 내지 않는다.

`python3 multi-session-bash-log.py report` 로 실행되지 않은 호출을 출력한다.
"""

import json
import os
import pathlib
import subprocess
import sys
import time

LOG_PATH = pathlib.Path.home() / ".claude" / "logs" / "multi-session-bash.jsonl"
COMMAND_LIMIT = 300


def main() -> None:
    if sys.argv[1:] == ["report"]:
        report()
        return
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return
    title = pane_title(pane)
    if "-worker-" not in title:
        return
    event = json.load(sys.stdin)
    append_record(event, title)


def report() -> None:
    records = [json.loads(line) for line in LOG_PATH.read_text().splitlines() if line]
    finished = {r["tool_use_id"] for r in records if r["event"] == "PostToolUse"}
    for record in records:
        if record["event"] == "PreToolUse" and record["tool_use_id"] not in finished:
            print(
                f"{record['ts']}  {record['pane_title']}  {record['permission_mode']}  {record['command']}"
            )


def pane_title(pane: str) -> str:
    title = subprocess.run(
        ["tmux", "display", "-p", "-t", pane, "#{pane_title}"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    return title.split(" ", 1)[-1] if " " in title else title


def append_record(event: dict[str, object], title: str) -> None:
    tool_input = event.get("tool_input", {})
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "event": event.get("hook_event_name"),
        "pane_title": title,
        "session_id": event.get("session_id"),
        "tool_use_id": event.get("tool_use_id"),
        "permission_mode": event.get("permission_mode"),
        "command": command[:COMMAND_LIMIT],
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as log:
        log.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
