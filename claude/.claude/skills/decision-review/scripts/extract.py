#!/usr/bin/env python3
"""최근 transcript 에서 worker `결정 필요` 와 AskUserQuestion 질문·답을 뽑고, 분류용 표본을 나눈다.

usage: extract.py <out_dir> [--days 30] [--sample 400] [--chunk 200]
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
RECOMMENDED = "(Recommended)"
# json.loads 결과. transcript 구조가 Claude Code 버전마다 달라 필드 타입을 고정하지 않는다
JsonObject = dict
REJECTED_PREFIX = "The user doesn't want to proceed"


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    tool_use_result: object  # 답이 담긴 `toolUseResult` (answers: 질문 → 답)


@dataclass(frozen=True)
class QuestionAnswer:
    id: int
    project: str
    ts: str
    question: str
    options: list[str]
    answer: str
    outcome: str  # recommended | other option | free text | rejected | no answer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--sample", type=int, default=400)
    parser.add_argument("--chunk", type=int, default=200)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    # 지난 실행의 sample·labels 가 남으면 aggregate 가 섞어 집계한다
    leftovers = sorted(
        p.name
        for p in args.out_dir.glob("*_*.jsonl")
        if p.name.startswith(("sample_", "labels_"))
    )
    if leftovers:
        raise SystemExit(
            f"{args.out_dir} already has {leftovers[:5]}; use a new folder"
        )

    requests, pairs = collect(time.time() - args.days * 86400)
    write_jsonl(args.out_dir / "worker_requests.jsonl", requests)
    write_jsonl(args.out_dir / "pairs.jsonl", [asdict(pair) for pair in pairs])

    # 권장안이 있고 답이 확인된 질문만 분류 대상으로 쓴다 — 채택률을 잴 수 있는 것만
    eligible = [
        p
        for p in pairs
        if p.outcome in ("recommended", "other option", "free text")
        and any(RECOMMENDED in o for o in p.options)
    ]
    random.Random(7).shuffle(eligible)
    sample = eligible[: args.sample]
    for index in range(0, len(sample), args.chunk):
        write_jsonl(
            args.out_dir / f"sample_{index // args.chunk}.jsonl",
            [asdict(p) for p in sample[index : index + args.chunk]],
        )

    print(
        f"days={args.days} worker_requests={len(requests)} questions={len(pairs)} eligible={len(eligible)} sampled={len(sample)}"
    )
    print("outcomes:", dict(Counter(p.outcome for p in pairs)))


def collect(since: float) -> tuple[list[JsonObject], list[QuestionAnswer]]:
    requests: list[JsonObject] = []
    pairs: list[QuestionAnswer] = []
    # 파일 mtime 은 최근이어도 그 안의 질문은 오래됐을 수 있어 질문 시각으로도 거른다
    since_ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(since))
    for path in PROJECTS.glob("*/*.jsonl"):
        if path.stat().st_mtime < since:
            continue
        pending: dict[str, tuple[str, list[JsonObject]]] = {}
        for lineno, line in enumerate(path.open(errors="replace"), 1):
            entry = parse(line)
            try:
                collect_entry(entry, pending, requests, pairs, path.parent.name)
            except (AttributeError, KeyError, TypeError) as error:
                raise SystemExit(
                    f"{path}:{lineno}: unexpected transcript shape: {error!r}"
                ) from error
        for ts, questions in pending.values():
            pairs.extend(to_pairs(path.parent.name, ts, questions, None, len(pairs)))
    return (
        [r for r in requests if r["ts"] >= since_ts],
        [pair for pair in pairs if pair.ts >= since_ts],
    )


def collect_entry(
    entry: JsonObject,
    pending: dict[str, tuple[str, list[JsonObject]]],
    requests: list[JsonObject],
    pairs: list[QuestionAnswer],
    project: str,
) -> None:
    # api-request-blob 은 같은 메시지의 사본이라 세면 두 번 센다 (11-15: worker `결정 필요` 1,312건 중 660건)
    if entry.get("type") == "api-request-blob":
        return
    for block in content_blocks(entry):
        kind, name = block.get("type"), block.get("name")
        if kind == "tool_use" and name == "SendMessage":
            message = str(block.get("input", {}).get("message", ""))
            if "결정 필요" in message[:200]:
                requests.append(
                    {
                        "project": project,
                        "ts": entry.get("timestamp", ""),
                        "text": message[:1500],
                    }
                )
        if kind == "tool_use" and name == "AskUserQuestion":
            pending[block["id"]] = (
                entry.get("timestamp", ""),
                block.get("input", {}).get("questions", []),
            )
        if kind == "tool_result" and block.get("tool_use_id") in pending:
            ts, questions = pending.pop(block["tool_use_id"])
            pairs.extend(
                to_pairs(
                    project,
                    ts,
                    questions,
                    TranscriptResult(
                        result_text(block.get("content")), entry.get("toolUseResult")
                    ),
                    len(pairs),
                )
            )


def to_pairs(
    project: str,
    ts: str,
    questions: list[JsonObject],
    result: TranscriptResult | None,
    start_id: int,
) -> list[QuestionAnswer]:
    found = []
    for offset, question in enumerate(questions):
        text = str(question.get("question") or "")
        options = [str(o["label"]) for o in question["options"]]
        answer = answer_for(text, result)
        found.append(
            QuestionAnswer(
                start_id + offset,
                project,
                ts,
                text[:400],
                options,
                (answer or "")[:300],
                outcome_of(answer, options, bool(question.get("multiSelect")), result),
            )
        )
    return found


def answer_for(question: str, result: TranscriptResult | None) -> str | None:
    """답은 `toolUseResult.answers` 에서 질문 원문으로 찾는다. 결과 문자열 파싱은 답 안의 따옴표·다른 질문 문자열에 깨진다."""
    if result is None or not isinstance(result.tool_use_result, dict):
        return None
    answers = result.tool_use_result.get("answers")
    return answers.get(question) if isinstance(answers, dict) else None


def outcome_of(
    answer: str | None,
    options: list[str],
    multi_select: bool,
    result: TranscriptResult | None,
) -> str:
    if result and result.text.startswith(REJECTED_PREFIX):
        return "rejected"
    if answer is None:
        return "no answer"
    # multiSelect 답은 고른 label 을 ", " 로 이은 문자열이다
    chosen = answer.split(", ") if multi_select else [answer]
    if not all(label in options for label in chosen):
        return "free text"
    return (
        "recommended"
        if any(RECOMMENDED in label for label in chosen)
        else "other option"
    )


def parse(line: str) -> JsonObject:
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        return {}
    return entry if isinstance(entry, dict) else {}


def content_blocks(entry: JsonObject) -> list[JsonObject]:
    message = entry.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    return (
        [block for block in content if isinstance(block, dict)]
        if isinstance(content, list)
        else []
    )


def result_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            str(part.get("text", "")) for part in content if isinstance(part, dict)
        )
    return ""


def write_jsonl(path: Path, rows: list[JsonObject]) -> None:
    with path.open("w") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
