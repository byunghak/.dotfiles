"""세션 jsonl 에서 세션별 타임라인(step 읽기·Skill·AskUserQuestion·사용자 권한 응답·세션 간 메시지·사람 프롬프트·호출 시각)을 뽑아 jsonl 로 쓴다.

사용: python3 -I extract_timeline.py --since 2026-11-15 --out <경로>/timeline.jsonl [--root ~/.claude/projects]
다음 단계: phase_stats.py <timeline.jsonl>
"""

import argparse, json, glob, os, re, sys
from datetime import datetime

STEP_RE = re.compile(r"references/steps/(step[0-9a-z_-]+)\.md")
USER_SOURCES = ("user_temporary", "user_reject", "user_permanent")


def ts_of(o):
    t = o.get("timestamp")
    if not t:
        return None
    return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        return " ".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return None


def process(path, root, since_ts):
    sid = os.path.basename(path)[:-6]
    proj = path[len(root) + 1 :].split("/")[0]
    name = None
    uses = {}
    events = []
    calls = []
    seen = set()
    for line in open(path, errors="ignore"):
        try:
            o = json.loads(line)
        except Exception:
            continue
        t = o.get("type")
        if t == "custom-title":
            name = o.get("customTitle") or name
            continue
        if t == "agent-name":
            name = o.get("agentName") or name
            continue
        if t not in ("assistant", "user"):
            continue
        ts = ts_of(o)
        if ts is None or ts < since_ts:
            continue
        msg = o.get("message") or {}
        if t == "assistant":
            mid = msg.get("id")
            if mid and mid not in seen:
                seen.add(mid)
                calls.append(ts)
            for b in msg.get("content") or []:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                nm, inp = b.get("name"), b.get("input") or {}
                uses[b["id"]] = (nm, inp, ts)
                blob = (
                    inp.get("file_path", "")
                    if nm == "Read"
                    else (inp.get("command", "") if nm == "Bash" else "")
                )
                m = STEP_RE.search(blob or "")
                if m:
                    events.append(dict(k="step", ts=ts, step=m.group(1)))
                if nm == "Skill":
                    events.append(
                        dict(
                            k="skill",
                            ts=ts,
                            skill=inp.get("skill"),
                            args=str(inp.get("args", ""))[:300],
                        )
                    )
                if nm == "SendMessage":
                    events.append(
                        dict(
                            k="send",
                            ts=ts,
                            to=str(inp.get("to", "")),
                            msg=str(inp.get("message", ""))[:3000],
                        )
                    )
            continue
        content = msg.get("content")
        pd = (
            o.get("permissionDecision")
            if isinstance(o.get("permissionDecision"), dict)
            else {}
        )
        if isinstance(content, list):
            for b in content:
                if not (isinstance(b, dict) and b.get("type") == "tool_result"):
                    continue
                tu = uses.get(b.get("tool_use_id"))
                if not tu:
                    continue
                nm, inp, uts = tu
                if nm == "AskUserQuestion":
                    tur = o.get("toolUseResult")
                    events.append(
                        dict(
                            k="ask",
                            ts=uts,
                            ans_ts=ts,
                            questions=inp.get("questions"),
                            answers=tur.get("answers")
                            if isinstance(tur, dict)
                            else None,
                            annotations=tur.get("annotations")
                            if isinstance(tur, dict)
                            else None,
                            result=(
                                b.get("content")
                                if isinstance(b.get("content"), str)
                                else json.dumps(b.get("content"), ensure_ascii=False)
                            )[:800],
                        )
                    )
                    continue
                src = pd.get("source")
                # rule 로 자동 허용된 user_permanent 는 사용자가 누른 것이 아니다
                if src in USER_SOURCES and not (
                    src == "user_permanent" and pd.get("reasonType") == "rule"
                ):
                    cmd = (
                        inp.get("command")
                        or inp.get("file_path")
                        or json.dumps(inp, ensure_ascii=False)
                    )
                    events.append(
                        dict(
                            k="perm",
                            ts=uts,
                            ans_ts=ts,
                            tool=nm,
                            src=src,
                            cmd=str(cmd)[:600],
                        )
                    )
        if o.get("isMeta") and (o.get("origin") or {}).get("kind") != "peer":
            continue
        txt = text_of(content)
        if txt is None:
            continue
        origin = (o.get("origin") or {}).get("kind") or "human"
        body = (o.get("origin") or {}).get("body") or txt
        if txt.startswith("Another Claude session sent a message") or origin == "peer":
            events.append(dict(k="peer_in", ts=ts, body=body[:3000]))
        elif txt.startswith("<task-notification") or origin != "human":
            continue
        else:
            events.append(dict(k="human", ts=ts, text=body[:600]))
    return dict(
        sid=sid,
        proj=proj,
        name=name,
        sub="/subagents/" in path,
        calls=calls,
        events=events,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", required=True, help="YYYY-MM-DD, 이 날짜 0시(로컬) 뒤 이벤트만")
    parser.add_argument("--out", required=True)
    parser.add_argument("--root", default=os.path.expanduser("~/.claude/projects"))
    args = parser.parse_args()
    since_ts = datetime.strptime(args.since, "%Y-%m-%d").timestamp()
    root = os.path.abspath(args.root)
    files = [
        f
        for f in glob.glob(root + "/**/*.jsonl", recursive=True)
        if os.path.getmtime(f) >= since_ts
    ]
    with open(args.out, "w") as out:
        for f in files:
            s = process(f, root, since_ts)
            if s["events"] or s["calls"]:
                out.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(len(files), "files", file=sys.stderr)


if __name__ == "__main__":
    main()
