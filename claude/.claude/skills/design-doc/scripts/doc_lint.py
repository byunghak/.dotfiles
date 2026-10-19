#!/usr/bin/env python3
"""설계 문서 규칙 검사기.

문서를 고칠 때마다 형식 위반을 숫자로 잡는다 — 날짜·경위·질문이 본문에 섞이는 것,
줄 길이, 컴포넌트 틀 누락. 읽기 쉬운지는 잡지 못한다 (../references/reading-check.md).
규칙 원문은 ../references/rules.md. decision-log.md 는 경위를 쓰는 곳이라 건너뛴다.
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

MAX_LINE = 90
MAX_SECTION_LINES = 150
# 컴포넌트·흐름 ### 하나의 줄 수 (그림 제외) — 넘으면 명세·근거를 문서 밖으로
MAX_VISIBLE_LINES = 20
SKIP_FILES = {"decision-log.md"}

DECISION_HEADING = "결정과 이유"
# 4장 이름: "질문" 또는 "결정·고민 사항"
QUESTION_SECTIONS = ("질문", "고민 사항", "결정 사항")
COMPONENT_SECTION = "컴포넌트"
TEMPLATE_HEADINGS = ("바뀌는 것", "동작", "결정과 이유", "미정")
NO_CHANGE_MARK = "바뀌는 것: 없음"

# 본문에 결정 날짜를 두지 않는다 — 2026-10-11, (10-07 확인), 10-04 의 ...
DATE_RE = re.compile(
    r"20\d\d-\d\d-\d\d"
    r"|(?<![\d~.-])(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])(?=[\s)]|$|\s*(?:의|에|결정|확인|재결정|기준))"
)
# 경위 문구는 "결정과 이유" 안에서만
HISTORY_RE = re.compile(r"기각|재결정|을 바꿈|를 바꿈|바꿨|되돌|처음에는|이전 안|정정|번복")
# 질문 표지는 질문 절 안에서만
QUESTION_RE = re.compile(r"확인 필요|확인 중|물을 것|미확인|문의 중|답 전에는")
NAV_RE = re.compile(r"맨 아래|맨 위|아래 절|위 절|다음 절|용어는 |아래를 참고|아래 참고|위 참고")
METAPHOR_RE = re.compile(
    r"(?<![가-힣])(?:축|노브|경계|층|조각)(?=[\s,.)이을를은는의에으도만]|$)"
    r"|\b(?:axis|knob|layer)\b",
    re.IGNORECASE,
)
LEADERSHIP_RE = re.compile(r"리더십")
LINK_TARGET_RE = re.compile(r"\]\(([^)]*)\)")
ANCHOR_LINK_RE = re.compile(r"\]\(#([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")

MAX_DOC_LINES = 500
MAX_DECISION_TABLE_ROWS = 3
WARNING_CHECKS = {"절 길이", "문서 길이"}
DETAILS_OPEN_RE = re.compile(r"^\s*<details")
DETAILS_CLOSE_RE = re.compile(r"</details>")


@dataclass
class Finding:
    line_no: int
    check: str
    text: str


@dataclass
class LintReport:
    path: Path
    findings: list[Finding] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.check not in WARNING_CHECKS)


@dataclass
class Scope:
    """줄마다 어느 절·소제목 안에 있는지."""

    titles: dict[int, str] = field(default_factory=dict)

    def enter(self, level: int, title: str) -> None:
        self.titles = {lv: t for lv, t in self.titles.items() if lv < level}
        self.titles[level] = title

    @property
    def in_decision(self) -> bool:
        return any(DECISION_HEADING in t for lv, t in self.titles.items() if lv >= 3)

    @property
    def in_questions(self) -> bool:
        return any(q in self.titles.get(2, "") for q in QUESTION_SECTIONS)


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: doc_lint.py <문서.md> [...]", file=sys.stderr)
        return 2
    total = 0
    for arg in argv:
        path = Path(arg)
        if path.name in SKIP_FILES:
            print(f"skip {path} (경위 문서)")
            continue
        report = lint_document(path)
        print_report(report)
        total += report.error_count
    return 1 if total else 0


def lint_document(path: Path) -> LintReport:
    lines = path.read_text(encoding="utf-8").split("\n")
    report = LintReport(path=path)
    anchors = collect_anchors(lines)
    scope = Scope()
    in_code = False
    for idx, raw in enumerate(lines, start=1):
        if raw.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        heading = HEADING_RE.match(raw)
        if heading:
            scope.enter(len(heading.group(1)), heading.group(2))
        report.findings.extend(check_line(idx, raw, scope))
        report.findings.extend(check_anchor_links(idx, raw, anchors))
    report.findings.extend(check_component_template(lines))
    report.findings.extend(check_toggles(path, lines))
    report.findings.extend(check_decision_tables(lines))
    shown = len(lines) - folded_line_count(lines)
    if shown > MAX_DOC_LINES:
        report.findings.append(Finding(0, "문서 길이", f"{shown}줄 (상한 {MAX_DOC_LINES}, 토글 안 제외)"))
    for start, title, visible in visible_sizes(lines):
        if visible > MAX_VISIBLE_LINES:
            report.findings.append(
                Finding(start, "컴포넌트 길이", f"{title}: {visible}줄 (상한 {MAX_VISIBLE_LINES})")
            )
    for title, size in section_sizes(lines):
        if size > MAX_SECTION_LINES:
            report.findings.append(Finding(0, "절 길이", f"{title}: {size}줄"))
    return report


def check_line(idx: int, raw: str, scope: Scope) -> list[Finding]:
    found: list[Finding] = []
    stripped = raw.strip()
    is_table = stripped.startswith("|")
    if not is_table and len(LINK_TARGET_RE.sub("]()", raw)) > MAX_LINE:
        found.append(Finding(idx, "90자 초과", stripped))
    if DATE_RE.search(raw):
        found.append(Finding(idx, "날짜", stripped))
    if not scope.in_decision and HISTORY_RE.search(raw):
        found.append(Finding(idx, "경위 문구", stripped))
    if not scope.in_questions and QUESTION_RE.search(raw):
        found.append(Finding(idx, "질문 표지", stripped))
    if NAV_RE.search(raw):
        found.append(Finding(idx, "길 안내", stripped))
    if METAPHOR_RE.search(raw):
        found.append(Finding(idx, "비유어", stripped))
    if LEADERSHIP_RE.search(raw):
        found.append(Finding(idx, "리더십", stripped))
    return found


def check_component_template(lines: list[str]) -> list[Finding]:
    """컴포넌트 절의 ### 마다 틀(바뀌는 것·동작·결정과 이유·미정)을 지켰는지."""
    found: list[Finding] = []
    for start, title, body in component_blocks(lines):
        subheadings = [
            (no, m.group(2))
            for no, raw in body
            if (m := HEADING_RE.match(raw)) and len(m.group(1)) == 4
        ]
        for no, sub in subheadings:
            if sub not in TEMPLATE_HEADINGS:
                found.append(Finding(no, "틀 밖 소제목", f"{title} > {sub}"))
        has_action = any(sub == "동작" for _, sub in subheadings)
        no_change = any(NO_CHANGE_MARK in raw for _, raw in body)
        if not has_action and not no_change:
            found.append(Finding(start, "틀 누락", f"{title}: `#### 동작` 없음"))
    return found


def component_blocks(lines: list[str]) -> list[tuple[int, str, list[tuple[int, str]]]]:
    blocks: list[tuple[int, str, list[tuple[int, str]]]] = []
    in_components = False
    in_code = False
    current: tuple[int, str, list[tuple[int, str]]] | None = None
    for idx, raw in enumerate(lines, start=1):
        if raw.strip().startswith("```"):
            in_code = not in_code
        heading = None if in_code else HEADING_RE.match(raw)
        level = len(heading.group(1)) if heading else 0
        if heading and level <= 3 and current is not None:
            blocks.append(current)
            current = None
        if heading and level == 2:
            in_components = COMPONENT_SECTION in heading.group(2)
            continue
        if heading and level == 3 and in_components:
            current = (idx, heading.group(2), [])
            continue
        if current is not None:
            current[2].append((idx, raw))
    if current is not None:
        blocks.append(current)
    return blocks


def check_toggles(path: Path, lines: list[str]) -> list[Finding]:
    """토글은 WBS 항목 상세와 질문 절에만 둔다. 들여쓴 토글은 어느 문서든 Notion 에서 깨진다."""
    found: list[Finding] = []
    details_doc = "details" in path.name or "상세" in path.name
    in_code = False
    in_foldable = False
    for idx, raw in enumerate(lines, start=1):
        if raw.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if raw.startswith("## "):
            in_foldable = "WBS" in raw or any(q in raw for q in QUESTION_SECTIONS)
        if "<details" not in raw:
            continue
        if raw.startswith((" ", "\t")):
            found.append(Finding(idx, "들여쓴 토글", raw.strip()))
        elif not (details_doc or in_foldable):
            found.append(Finding(idx, "토글", raw.strip()))
    return found


def folded_line_count(lines: list[str]) -> int:
    """<details> 안쪽 줄 수 (summary 줄 제외). 접혀 있어 읽을 때 길이에 넣지 않는다."""
    folded = 0
    inside = False
    for raw in lines:
        if DETAILS_OPEN_RE.match(raw):
            inside = True
            continue
        if DETAILS_CLOSE_RE.search(raw):
            inside = False
            continue
        if inside and not raw.lstrip().startswith("<summary>"):
            folded += 1
    return folded


def check_decision_tables(lines: list[str]) -> list[Finding]:
    """결정과 이유 안의 표는 3행 이하."""
    found: list[Finding] = []
    scope = Scope()
    rows = 0
    start = 0
    in_code = False
    for idx, raw in enumerate(lines + [""], start=1):
        if raw.strip().startswith("```"):
            in_code = not in_code
        heading = None if in_code else HEADING_RE.match(raw)
        if heading:
            scope.enter(len(heading.group(1)), heading.group(2))
        is_separator = bool(re.match(r"^\s*\|[\s:|-]+\|\s*$", raw))
        if scope.in_decision and is_separator:
            continue
        is_row = raw.strip().startswith("|")
        if scope.in_decision and is_row:
            if rows == 0:
                start = idx
            rows += 1
            continue
        if rows:
            if rows - 1 > MAX_DECISION_TABLE_ROWS:
                found.append(Finding(start, "결정 표", f"{rows - 1}행 (상한 {MAX_DECISION_TABLE_ROWS})"))
            rows = 0
    return found


def visible_sizes(lines: list[str]) -> list[tuple[int, str, int]]:
    """## 1·2 절의 ### 마다 <details> 밖에 보이는 비어 있지 않은 줄 수."""
    sizes: list[tuple[int, str, int]] = []
    current: tuple[int, str] | None = None
    visible = 0
    depth = 0
    in_scope = False
    in_code = False
    for idx, raw in enumerate(lines, start=1):
        # 코드 블록(그림·JSON)은 세지 않는다 — 그림은 렌더되면 줄 수와 상관없다
        if raw.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        heading = HEADING_RE.match(raw)
        level = len(heading.group(1)) if heading else 0
        if heading and level <= 3:
            if current is not None:
                sizes.append((current[0], current[1], visible))
                current = None
            if level == 2:
                in_scope = COMPONENT_SECTION in heading.group(2) or "흐름" in heading.group(2)
            elif in_scope:
                current, visible = (idx, heading.group(2)), 0
            continue
        if DETAILS_OPEN_RE.match(raw):
            depth += 1
        if current is not None and depth == 0 and raw.strip() and raw.strip() != "<!-- -->":
            visible += 1
        if DETAILS_CLOSE_RE.search(raw):
            depth = max(0, depth - 1)
    if current is not None:
        sizes.append((current[0], current[1], visible))
    return sizes


def check_anchor_links(idx: int, raw: str, anchors: set[str]) -> list[Finding]:
    return [
        Finding(idx, "깨진 목차 링크", f"#{target}")
        for target in ANCHOR_LINK_RE.findall(raw)
        if target not in anchors
    ]


def collect_anchors(lines: list[str]) -> set[str]:
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    in_code = False
    for raw in lines:
        if raw.strip().startswith("```"):
            in_code = not in_code
            continue
        heading = HEADING_RE.match(raw)
        if in_code or not heading:
            continue
        slug = gfm_slug(heading.group(2))
        count = seen.get(slug, 0)
        anchors.add(slug if count == 0 else f"{slug}-{count}")
        seen[slug] = count + 1
    return anchors


def gfm_slug(title: str) -> str:
    text = title.lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def section_sizes(lines: list[str]) -> list[tuple[str, int]]:
    """## 절의 줄 수. 컴포넌트 절은 ### 단위로 잰다 — 컴포넌트 수만큼 길어지는 게 정상이라."""
    sizes: list[tuple[str, int]] = []
    current: str | None = None
    count = 0
    in_components = False
    for raw in lines:
        heading = HEADING_RE.match(raw)
        level = len(heading.group(1)) if heading else 0
        starts = level == 2 or (level == 3 and in_components)
        if heading and starts:
            if current is not None:
                sizes.append((current, count))
            if level == 2:
                in_components = COMPONENT_SECTION in heading.group(2)
            current, count = heading.group(2), 0
        count += 1
    if current is not None:
        sizes.append((current, count))
    return sizes


def print_report(report: LintReport) -> None:
    print(f"== {report.path}")
    by_check: dict[str, list[Finding]] = {}
    for finding in report.findings:
        by_check.setdefault(finding.check, []).append(finding)
    for check, items in by_check.items():
        print(f"-- {check}: {len(items)}")
        for finding in items:
            where = f"{finding.line_no}: " if finding.line_no else ""
            print(f"   {where}{finding.text[:120]}")
    print(f"합계 {report.error_count} (절 길이 경고 제외)")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
