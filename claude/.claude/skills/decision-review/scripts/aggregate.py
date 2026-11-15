#!/usr/bin/env python3
"""sample_*.jsonl 과 subagent 가 쓴 labels_*.jsonl 을 합쳐 칸·유형별 권장안 채택률을 낸다.

usage: aggregate.py <out_dir>
결과는 표준 출력과 <out_dir>/summary.json 에 쓴다.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path

OUTCOMES = ("recommended", "other option", "free text")
# SKILL.md 분류 프롬프트의 목록과 같아야 한다. 목록 밖 값은 표를 조용히 쪼개므로 실패시킨다
COLUMNS = ("worker", "orchestrator", "user")
SUBTYPES = [
    "impl_approach",
    "verify_next_step",
    "test_add",
    "test_env",
    "doc_edit",
    "plan_approval",
    "review_feedback",
    "pr_split",
    "order_dependency",
    "scope_interpret",
    "session_mgmt",
    "start_worker",
    "merge_pr",
    "deploy",
    "cleanup",
    "close_issue",
    "create_issue",
    "post_comment",
    "publish",
    "design_contract",
    "permission",
    "credential",
    "spend_cost",
    "product_decision",
    "other",
]
CHUNK_FILE = re.compile(r"(sample|labels)_\d+\.jsonl")
# json.loads 결과. 파일 단위로 검증한 뒤에만 키를 꺼낸다
JsonObject = dict


def main() -> None:
    out_dir = Path(sys.argv[1])
    samples = read_by_id(out_dir, "sample", check_sample)
    labels = read_by_id(out_dir, "labels", check_label)
    if not samples:
        raise SystemExit(f"no sample_N.jsonl rows in {out_dir}")
    missing, extra = (
        sorted(set(samples) - set(labels)),
        sorted(set(labels) - set(samples)),
    )
    if missing or extra:
        raise SystemExit(
            f"label ids differ from sample ids: missing {len(missing)} {missing[:10]}, extra {len(extra)} {extra[:10]}"
        )

    by_column: dict[str, Counter] = defaultdict(Counter)
    by_subtype: dict[str, Counter] = defaultdict(Counter)
    subtype_columns: dict[str, Counter] = defaultdict(Counter)
    for sample_id, sample in samples.items():
        label = labels[sample_id]
        for bucket in (by_column[label["column"]], by_subtype[label["subtype"]]):
            bucket["n"] += 1
            bucket[sample["outcome"]] += 1
            bucket["confused"] += label["confused"]
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


def read_by_id(
    out_dir: Path, prefix: str, check: Callable[[str, JsonObject], None]
) -> dict[int, JsonObject]:
    """`<prefix>_N.jsonl` 만 읽는다. `.bak`·`_old` 같은 사본이 섞이면 id 가 겹쳐 덮어쓰인다."""
    rows: dict[int, JsonObject] = {}
    for path in sorted(out_dir.glob(f"{prefix}_*")):
        if not CHUNK_FILE.fullmatch(path.name):
            raise SystemExit(
                f"{path}: unexpected file; keep only {prefix}_N.jsonl in {out_dir}"
            )
        for lineno, line in enumerate(path.open(), 1):
            if not line.strip():
                continue
            where = f"{path}:{lineno}"
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise SystemExit(
                    f"{where}: not JSON ({error.msg}): {line[:80]!r}"
                ) from error
            if not isinstance(row, dict) or type(row.get("id")) is not int:
                raise SystemExit(
                    f"{where}: expected an object with int id: {line[:80]!r}"
                )
            check(where, row)
            if row["id"] in rows:
                raise SystemExit(f"{where}: duplicate id {row['id']}")
            rows[row["id"]] = row
    return rows


def check_sample(where: str, row: JsonObject) -> None:
    if row.get("outcome") not in OUTCOMES:
        raise SystemExit(f"{where}: outcome {row.get('outcome')!r} not in {OUTCOMES}")


def check_label(where: str, row: JsonObject) -> None:
    if row.get("column") not in COLUMNS:
        raise SystemExit(f"{where}: column {row.get('column')!r} not in {COLUMNS}")
    if row.get("subtype") not in SUBTYPES:
        raise SystemExit(
            f"{where}: subtype {row.get('subtype')!r} not in the SKILL.md list"
        )
    if type(row.get("confused")) is not bool:
        raise SystemExit(
            f"{where}: confused must be true/false, got {row.get('confused')!r}"
        )


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
