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
ANSWER_ENDINGS = ('", "', '". ', '"')


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
    for path in PROJECTS.glob("*/*.jsonl"):
        if path.stat().st_mtime < since:
            continue
        pending: dict[str, tuple[str, list[JsonObject]]] = {}
        for line in path.open(errors="replace"):
            entry = parse(line)
            for block in content_blocks(entry):
                kind, name = block.get("type"), block.get("name")
                if kind == "tool_use" and name == "SendMessage":
                    message = str(block.get("input", {}).get("message", ""))
                    if "결정 필요" in message[:200]:
                        requests.append(
                            {
                                "project": path.parent.name,
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
                            path.parent.name,
                            ts,
                            questions,
                            result_text(block.get("content")),
                            len(pairs),
                        )
                    )
        for ts, questions in pending.values():
            pairs.extend(to_pairs(path.parent.name, ts, questions, None, len(pairs)))
    return requests, pairs


def to_pairs(
    project: str,
    ts: str,
    questions: list[JsonObject],
    result: str | None,
    start_id: int,
) -> list[QuestionAnswer]:
    found = []
    for offset, question in enumerate(questions):
        text = str(question.get("question") or "")
        options = [
            str(o.get("label"))
            for o in question.get("options", [])
            if isinstance(o, dict)
        ]
        answer = answer_for(text, result)
        found.append(
            QuestionAnswer(
                start_id + offset,
                project,
                ts,
                text[:400],
                options,
                (answer or "")[:300],
                outcome_of(answer, options, result),
            )
        )
    return found


def answer_for(question: str, result: str | None) -> str | None:
    """답 문자열은 `"<질문>"="<답>", "<질문>"="<답>"` 꼴이다. 질문 원문으로 찾아 질문 안의 따옴표에 흔들리지 않게 한다."""
    if not result:
        return None
    marker = f'"{question}"="'
    start = result.find(marker)
    if start < 0:
        return None
    rest = result[start + len(marker) :]
    ends = [rest.find(ending) for ending in ANSWER_ENDINGS if rest.find(ending) >= 0]
    return rest[: min(ends)] if ends else rest


def outcome_of(answer: str | None, options: list[str], result: str | None) -> str:
    if result and "doesn't want to proceed" in result:
        return "rejected"
    if answer is None:
        return "no answer"
    if answer in options:
        return "recommended" if RECOMMENDED in answer else "other option"
    return "free text"


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
