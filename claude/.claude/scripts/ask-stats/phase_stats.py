"""timeline.jsonl 의 사용자 결정(AskUserQuestion 문항·사용자가 누른 권한 프롬프트)을 작업 단계로 분류해 집계한다.

사용: python3 -I phase_stats.py <timeline.jsonl> — 집계는 stdout, 문항별 행은 timeline 옆 rows.json

연결 규칙: orchestrator 문항 → 그 세션이 받은 worker `결정 필요` (같은 #이슈 번호, 없으면 같은 턴에 받은 것) → 그 worker 가 보낸 시점 직전에 읽은 step 파일.
"""

import json, os, re, sys, statistics
from collections import defaultdict, Counter

TL = sys.argv[1]
ROWS_OUT = os.path.join(os.path.dirname(os.path.abspath(TL)), "rows.json")
PHASES = ["brainstorm", "plan", "impl", "review", "ship", "wrapup", "unk"]
PHASE_KO = dict(
    brainstorm="brainstorm·설계 인터뷰(시작 전)",
    plan="계획(Plan)",
    impl="구현 중",
    review="리뷰",
    ship="PR·머지·배포",
    wrapup="마무리",
    unk="미분류",
)
STEP_PHASE = {
    "step0-prepare": "brainstorm",
    "step1-3-analyze": "brainstorm",
    "step4-plan": "plan",
    "step5-code": "impl",
    "step6-review": "review",
    "step7-8-ship": "ship",
    "step9-merge-end": "ship",
}
# 내용 규칙: 위에서부터 처음 맞는 것
CONTENT_RULES = [
    ("ship", r"머지|merge|배포|deploy|terraform apply|rollout|재기동|릴리스|release|publish|PR (을 )?(올|생성|만들)|gh pr create|ready for review|draft"),
    ("wrapup", r"정리|닫을|닫기|닫아|close|종료|/exit|남은 일|브랜치 삭제|worktree (remove|삭제)|회고|이슈로 남|별도 이슈|후속 이슈|memory"),
    ("review", r"리뷰 지적|리뷰어|review|지적|NEEDS|재리뷰"),
    ("plan", r"\bplan\b|PLAN|계획|Task|승인 ②|PR 분리|PR 을 나|나눌"),
    ("impl", r"실패|에러|error|재현|막혔|멈췄|못 찾|건너뛰|테스트|빌드|확인 못|결과가|측정|돌릴"),
    ("brainstorm", r"착수|worker|워커|띄울|새 (작업|세션)|목표|설계|방식|접근|범위|어디까지|구성|안 [A-D1-4]|[ABC] 안|옵션|요구|spec|이슈 (초안|생성|만들)|무엇을 진행|어느 쪽|어떻게 둘|어떻게 할|우선|순서|먼저"),
]
CONTENT_RE = [(p, re.compile(r, re.I)) for p, r in CONTENT_RULES]
TYPE_RULES = [
    ("머지", r"머지|merge"),
    ("배포", r"배포|deploy|apply|업로드|rollout|릴리스|release"),
    (
        "외부 게시",
        r"코멘트|comment|이슈 (생성|만들)|이슈로|Slack|슬랙|Notion|노션|게시|공지|답글|회신|메일|PR 본문",
    ),
    ("새 worker", r"worker|워커|착수|띄울|세션"),
    ("정리", r"정리|닫|close|종료|브랜치 삭제|worktree"),
    ("범위", r"범위|어디까지|포함|빼|제외|이번 PR|별도|후속|우선|순서|먼저|다음"),
    (
        "설계",
        r"방식|설계|구조|어떻게|안 ?[A-D1-4]|옵션|접근|값|기준|규칙|계약|스키마|API",
    ),
]
TYPE_RE = [(t, re.compile(r, re.I)) for t, r in TYPE_RULES]
ISSUE_RE = re.compile(r"#(\d{2,5})")
CLARIFY_RE = re.compile(r"(\?|？|무슨|뭐|뭔|뭘|어떤 ?거|말씀|이해|설명|차이|왜|보여)")


# 답 문구만 보고 고른 선택지 밖의 되묻기를 가린다
ANSWER_CLARIFY_RE = re.compile(r"(\?|무슨|뭐|뭔|어떤 ?거|말씀|이해|설명|차이|왜)")


def outcome(q, ans):
    """rec 권장안 · nonrec 다른 선택지 · first 권장 표시 없이 첫 칸 · clarify 되묻기 · other 직접 입력 · none 답 없음."""
    opts = [o.get("label", "") for o in q.get("options") or []]
    if ans is None:
        return "none"
    rec = next(
        (i for i, l in enumerate(opts) if "Recommended" in l or "권장" in l), None
    )
    picked = (
        [a.strip() for a in ans.split(", ")] if q.get("multiSelect") else [ans.strip()]
    )
    idx = [opts.index(p) for p in picked if p in opts]
    if not idx:
        return "clarify" if ANSWER_CLARIFY_RE.search(ans) and len(ans) < 200 else "other"
    if rec is not None:
        return (
            "rec"
            if rec in idx and len(idx) == (1 if not q.get("multiSelect") else len(idx))
            else "nonrec"
        )
    return "first" if idx == [0] else "nonrec"


def content_phase(text):
    for p, r in CONTENT_RE:
        if r.search(text):
            return p
    return "unk"


def qtype(text):
    for t, r in TYPE_RE:
        if r.search(text):
            return t
    return "기타"


def last_before(events, ts, kind):
    out = None
    for e in events:
        if e["ts"] > ts:
            break
        if e["k"] == kind:
            out = e
    return out


def load():
    sessions = [json.loads(l) for l in open(TL)]
    return [s for s in sessions if not s["sub"]]


def build_worker_sends(sessions):
    """worker 가 보낸 결정 필요: 본문 앞부분 → (worker 세션, 보낸 시각, step, 그 뒤 첫 수신, 막힘 여부)."""
    sends = {}
    for s in sessions:
        ev = sorted(s["events"], key=lambda e: e["ts"])
        calls = sorted(s["calls"])
        for e in ev:
            if e["k"] != "send" or "-worker" not in (s["name"] or ""):
                continue
            st = last_before(ev, e["ts"], "step")
            relay = next(
                (x for x in ev if x["k"] == "peer_in" and x["ts"] > e["ts"] + 5), None
            )
            relay_ts = relay["ts"] if relay else None
            busy = relay_ts is not None and any(
                e["ts"] + 90 < c < relay_ts - 5 for c in calls
            )
            sends[norm(e["msg"])] = dict(
                sid=s["sid"],
                name=s["name"],
                ts=e["ts"],
                msg=e["msg"],
                step=st["step"] if st else None,
                step_ts=st["ts"] if st else None,
                relay_ts=relay_ts,
                blocked=(relay_ts is not None and not busy),
            )
    return sends


def norm(t):
    return re.sub(r"\s+", " ", t)[:120]


def link_question(q_text, ask_ts, inbox, turn_start):
    """inbox: 이 orchestrator 가 받은 worker 메시지 (ts 오름차순). 같은 #이슈 번호의 최근 것(3일 안) → 번호가 없으면 같은 턴(직전 사람 프롬프트 뒤)에 받은 마지막 결정 필요."""
    nums = set(ISSUE_RE.findall(q_text))
    cands = [m for m in inbox if m["ts"] <= ask_ts and ask_ts - m["ts"] < 3 * 86400]
    if nums:
        hit = [m for m in cands if nums & set(ISSUE_RE.findall(m["body"][:600]))]
        if hit:
            return hit[-1], "issue"
        return None, None
    same_turn = [m for m in cands if m["ts"] >= turn_start and "결정 필요" in m["body"][:200]]
    if same_turn:
        return same_turn[-1], "same-turn"
    return None, None


def main():
    sessions = load()
    sends = build_worker_sends(sessions)
    rows = []
    perms = []
    for s in sessions:
        ev = sorted(s["events"], key=lambda e: e["ts"])
        inbox = []
        turn_start = 0
        for e in ev:
            if e["k"] == "human":
                turn_start = e["ts"]
            if e["k"] == "peer_in":
                body = e["body"]
                w = sends.get(norm(body[body.find("결정 필요") :])) or sends.get(
                    norm(body)
                )
                if w:
                    inbox.append(dict(ts=e["ts"], body=body, worker=w))
            if e["k"] == "perm":
                perms.append(dict(sess=s["name"], sid=s["sid"], **e))
            if e["k"] != "ask":
                continue
            answers = e.get("answers") or {}
            for qi, q in enumerate(e.get("questions") or []):
                text = (
                    q.get("question", "")
                    + " "
                    + q.get("header", "")
                    + " "
                    + " ".join(o.get("label", "") for o in q.get("options") or [])
                )
                src, how = link_question(text, e["ts"], inbox, turn_start)
                w = src["worker"] if src else None
                if w and w["step"]:
                    base = STEP_PHASE.get(w["step"], "impl")
                    if base == "ship":
                        cp = content_phase(text)
                        phase = "wrapup" if cp == "wrapup" else "ship"
                    else:
                        phase = base
                    rule = "step:" + w["step"]
                elif src:
                    phase = content_phase(text)
                    rule = "worker-msg"
                else:
                    phase = content_phase(text)
                    rule = "question"
                ans = answers.get(q.get("question"))
                oc = "declined" if not answers else outcome(q, ans)
                if (
                    oc in ("other", "clarify")
                    and ans
                    and CLARIFY_RE.search(ans)
                    and len(ans) < 250
                ):
                    oc = "clarify"
                rows.append(
                    dict(
                        sess=s["name"],
                        sid=s["sid"],
                        ask_ts=e["ts"],
                        wait=e["ans_ts"] - e["ts"],
                        dialog=(s["sid"], e["ts"]),
                        q=q.get("question", ""),
                        opts=[o.get("label") for o in q.get("options") or []],
                        ans=ans,
                        oc=oc,
                        phase=phase,
                        rule=rule,
                        link=how,
                        type=qtype(text),
                        worker=(w["name"] if w else None),
                        worker_sid=(w["sid"] if w else None),
                        worker_wait=(
                            (w["relay_ts"] - w["ts"]) if w and w["relay_ts"] else None
                        ),
                        blocked=(w["blocked"] if w else True),
                        wmsg=(src["body"][:1500] if src else None),
                    )
                )
    json.dump(rows, open(ROWS_OUT, "w"), ensure_ascii=False)
    report(rows, perms)


def report(rows, perms):
    n = len(rows)
    print(
        f"문항 {n} · 대화상자 {len(set(r['dialog'] for r in rows))} · 사용자 누른 권한 프롬프트 {len(perms)}"
    )
    print(
        "분류 근거:",
        Counter(r["rule"].split(":")[0] for r in rows),
        "링크:",
        Counter(r["link"] for r in rows),
    )
    print(
        "\n단계 | 문항 | 비율 | 권장안 채택% | 되묻기% | 직접입력% | 대기 중앙값(분) | worker 대기 중앙값(분) | worker 막힘% | 주요 유형"
    )
    for p in PHASES:
        rs = [r for r in rows if r["phase"] == p]
        if not rs:
            continue
        oc = Counter(r["oc"] for r in rs)
        k = len(rs)
        acc = 100 * (oc["rec"] + oc["first"]) / k
        ww = [r["worker_wait"] / 60 for r in rs if r["worker_wait"]]
        wb = [r for r in rs if r["worker"]]
        types = ", ".join(
            f"{t} {c}" for t, c in Counter(r["type"] for r in rs).most_common(4)
        )
        print(
            f"{PHASE_KO[p]} | {k} | {100 * k / n:.0f}% | {acc:.0f} | {100 * oc['clarify'] / k:.0f} | {100 * oc['other'] / k:.0f} | {statistics.median(r['wait'] for r in rs) / 60:.1f} | "
            f"{(statistics.median(ww) if ww else float('nan')):.0f} | {(100 * sum(r['blocked'] for r in wb) / len(wb)) if wb else float('nan'):.0f} (n={len(wb)}) | {types}"
        )
    after = [r for r in rows if r["phase"] in ("impl", "review", "ship", "wrapup")]
    after_nomerge = [r for r in rows if r["phase"] in ("impl", "review", "wrapup")]
    print(
        f"\n시작(구현 착수) 뒤 문항: {len(after)}/{n} = {100 * len(after) / n:.0f}% · 머지·배포 제외 {len(after_nomerge)}/{n} = {100 * len(after_nomerge) / n:.0f}%"
    )
    # 끊김: worker(작업) 마다 그 작업 문항이 든 대화상자 수
    per_task = defaultdict(set)
    for r in rows:
        if r["worker_sid"]:
            per_task[r["worker_sid"]].add(r["dialog"])
    if per_task:
        v = [len(x) for x in per_task.values()]
        print(
            f"worker 작업 {len(v)}개: 작업당 대화상자 중앙값 {statistics.median(v)} 평균 {statistics.mean(v):.1f} 최대 {max(v)}"
        )
    per_orch = defaultdict(set)
    for r in rows:
        per_orch[r["sess"]].add(r["dialog"])
    print("세션별 대화상자:", {k: len(v) for k, v in per_orch.items()})
    print(
        "권한 프롬프트 세션:",
        Counter(p["sess"] for p in perms).most_common(),
        "대기 중앙값(분)",
        statistics.median(p["ans_ts"] - p["ts"] for p in perms) / 60,
    )


if __name__ == "__main__":
    main()
