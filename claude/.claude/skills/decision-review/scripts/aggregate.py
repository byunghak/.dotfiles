#!/usr/bin/env python3
"""sample_*.jsonl 과 subagent 가 쓴 labels_*.jsonl 을 합쳐 칸·유형별 권장안 채택률을 낸다.

usage: aggregate.py <out_dir>
결과는 표준 출력과 <out_dir>/summary.json 에 쓴다.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

OUTCOMES = ("recommended", "other option", "free text")
# json.loads 결과. transcript 구조가 Claude Code 버전마다 달라 필드 타입을 고정하지 않는다
JsonObject = dict


def main() -> None:
    out_dir = Path(sys.argv[1])
    samples = {row["id"]: row for row in read_rows(out_dir, "sample_")}
    labels = {row["id"]: row for row in read_rows(out_dir, "labels_")}
    missing = sorted(set(samples) - set(labels))
    if missing:
        raise SystemExit(
            f"labels missing for {len(missing)} sample ids, first: {missing[:10]}"
        )

    by_column: dict[str, Counter] = defaultdict(Counter)
    by_subtype: dict[str, Counter] = defaultdict(Counter)
    subtype_columns: dict[str, Counter] = defaultdict(Counter)
    for sample_id, sample in samples.items():
        label = labels[sample_id]
        for bucket in (by_column[label["column"]], by_subtype[label["subtype"]]):
            bucket["n"] += 1
            bucket[sample["outcome"]] += 1
            bucket["confused"] += bool(label["confused"])
        subtype_columns[label["subtype"]][label["column"]] += 1

    print(f"samples={len(samples)}")
    print_table("column", by_column)
    print_table("subtype", by_subtype, subtype_columns)
    summary = {
        "samples": len(samples),
        "by_column": {k: dict(v) for k, v in by_column.items()},
        "by_subtype": {
            k: {**v, "columns": dict(subtype_columns[k])} for k, v in by_subtype.items()
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1)
    )


def read_rows(out_dir: Path, prefix: str) -> list[JsonObject]:
    return [
        json.loads(line)
        for path in sorted(out_dir.glob(f"{prefix}*.jsonl"))
        for line in path.open()
        if line.strip()
    ]


def print_table(
    name: str, buckets: dict[str, Counter], columns: dict[str, Counter] | None = None
) -> None:
    print(
        f"\n| {name} | n | 권장안 | 다른 선택지 | 직접 입력 | 되묻기 |{' 칸 |' if columns else ''}"
    )
    print(f"|---|---|---|---|---|---|{'---|' if columns else ''}")
    for key, bucket in sorted(buckets.items(), key=lambda item: -item[1]["n"]):
        n = bucket["n"]
        rates = " | ".join(f"{100 * bucket[outcome] / n:.0f}%" for outcome in OUTCOMES)
        extra = f" {dict(columns[key])} |" if columns else ""
        print(f"| {key} | {n} | {rates} | {bucket['confused']} |{extra}")


if __name__ == "__main__":
    main()
