import tempfile
import unittest
from pathlib import Path

import doc_lint


def lint_text(text: str) -> doc_lint.LintReport:
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(text)
    return doc_lint.lint_document(Path(fh.name))


def checks(report: doc_lint.LintReport) -> list[str]:
    return [f.check for f in report.findings]


class DocLintTest(unittest.TestCase):
    def test_date_in_body(self) -> None:
        report = lint_text("## 1. 흐름\n\n- 사이드카가 보낸다 (2026-10-11)\n- 10-07 확인\n")
        self.assertEqual(checks(report).count("날짜"), 2)

    def test_range_is_not_date(self) -> None:
        report = lint_text("## 1. 흐름\n\n- 약 12~15일, 샘플 21~30\n")
        self.assertNotIn("날짜", checks(report))

    def test_history_allowed_only_under_decision_heading(self) -> None:
        body = (
            "## 2. 컴포넌트\n\n### 2.1 TR API\n\n#### 동작\n\n- 대안 (기각)\n\n"
            "#### 결정과 이유\n\n- 기각 — 이유\n\n#### 미정\n\n- 재결정 필요\n"
        )
        report = lint_text(body)
        self.assertEqual([f.line_no for f in report.findings if f.check == "경위 문구"], [7, 15])

    def test_question_marker_only_in_question_section(self) -> None:
        body = "## 1. 흐름\n\n- floor 는 PO 확인 중\n\n## 4. 질문\n\n### 4.1 PO\n\n- 확인 필요: floor\n"
        report = lint_text(body)
        self.assertEqual([f.line_no for f in report.findings if f.check == "질문 표지"], [3])

    def test_component_template(self) -> None:
        body = (
            "## 2. 컴포넌트\n\n"
            "### 2.1 TR API\n\n#### 바뀌는 것\n\n- 🟩 새 경로\n\n#### 동작\n\n- 규칙\n\n"
            "### 2.2 budget-pool\n\n바뀌는 것: 없음\n\n"
            "### 2.3 사이드카\n\n#### 설계안\n\n- 무엇\n\n"
            "## 3. WBS\n\n### 3.1 항목\n"
        )
        report = lint_text(body)
        found = {(f.check, f.text) for f in report.findings if f.check.startswith("틀")}
        self.assertEqual(
            found,
            {("틀 밖 소제목", "2.3 사이드카 > 설계안"), ("틀 누락", "2.3 사이드카: `#### 동작` 없음")},
        )

    def test_long_line_ignores_table_and_code(self) -> None:
        long_text = "가" * 91
        body = f"## 1. 흐름\n\n- {long_text}\n| {long_text} |\n```\n{long_text}\n```\n"
        report = lint_text(body)
        self.assertEqual([f.line_no for f in report.findings if f.check == "90자 초과"], [3])

    def test_metaphor_word_boundary(self) -> None:
        report = lint_text("## 1. 흐름\n\n- 같은 축으로 본다\n- 압축은 나중에, HTTP 계층\n")
        self.assertEqual([f.line_no for f in report.findings if f.check == "비유어"], [3])

    def test_toc_anchor(self) -> None:
        body = (
            "## 목차\n\n- [ok](#12-init--v1trinit)\n- [bad](#13-없음)\n\n"
            "## 1.2 init — `/v1/tr/init`\n"
        )
        report = lint_text(body)
        self.assertEqual(
            [f.text for f in report.findings if f.check == "깨진 목차 링크"], ["#13-없음"]
        )

    def test_visible_lines_exclude_details(self) -> None:
        bullets = "".join(f"- 줄 {i}\n" for i in range(70))
        folded = f"<details>\n<summary>표</summary>\n\n{bullets}\n</details>\n"
        body = (
            "## 2. 컴포넌트\n\n### 2.1 접음\n\n#### 동작\n\n" + folded
            + "\n### 2.2 펼침\n\n#### 동작\n\n" + bullets
        )
        report = lint_text(body)
        long = [f.text for f in report.findings if f.check == "컴포넌트 길이"]
        self.assertEqual(len(long), 1)
        self.assertTrue(long[0].startswith("2.2 펼침"))

    def test_toggle_rules(self) -> None:
        body = "## 1. 흐름\n\n<details>\n<summary>a</summary>\n\n</details>\n\n- x\n\n  <details>\n  <summary>b</summary>\n\n  </details>\n"
        report = lint_text(body)
        self.assertEqual(sorted(f.check for f in report.findings if "토글" in f.check), ["들여쓴 토글", "토글"])

    def test_toggles_allowed_in_wbs(self) -> None:
        body = "## 3. WBS\n\n<details>\n<summary>#2</summary>\n\n- x\n\n</details>\n\n## 4. 질문\n\n<details>\n<summary>q</summary>\n\n</details>\n\n## 용어\n\n<details>\n<summary>t</summary>\n\n</details>\n"
        report = lint_text(body)
        self.assertEqual([f.line_no for f in report.findings if f.check == "토글"], [19])

    def test_doc_length_excludes_toggle_body(self) -> None:
        bullets = "".join(f"- 줄 {i}\n" for i in range(600))
        body = "## 3. WBS\n\n<details>\n<summary>#2</summary>\n\n" + bullets + "\n</details>\n"
        report = lint_text(body)
        self.assertEqual([f for f in report.findings if f.check == "문서 길이"], [])

    def test_decision_table_rows(self) -> None:
        rows = "".join(f"| 안{i} | 기각 |\n" for i in range(4))
        body = (
            "## 2. 컴포넌트\n\n### 2.1 A\n\n#### 동작\n\n- x\n\n#### 결정과 이유\n\n"
            "- 결론 — 이유\n\n| 안 | 판정 |\n| --- | --- |\n" + rows
        )
        report = lint_text(body)
        self.assertEqual([f.text for f in report.findings if f.check == "결정 표"], ["4행 (상한 3)"])


if __name__ == "__main__":
    unittest.main()
