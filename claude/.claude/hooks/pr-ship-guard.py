#!/usr/bin/env python3
"""pr-ship-guard - PreToolUse Hook (matcher: Bash)

`gh pr create`·`gh pr merge` 직전에 두 가지를 본다.
  1. 검증 증거 (create·merge): PR 브랜치의 worktree 를 가리키는 runlog 로그 중 HEAD 커밋 이후 것이 있고,
     같은 명령의 최신 실행이 모두 exit=0 인가.
     worktree 가 없는 브랜치·`.claude/plans` 가 없는 repo 는 /work 산출물이 아니라 보지 않는다.
     create 는 막지 않고 문제 목록을 모델에 알려 PR 본문 "검증" 에 적게 한다 (11-17 사용자).
     merge 도 증거 문제는 막지 않고 모델에 알린 뒤 분류기에 맡긴다.
  2. 머지 base (merge): ask 는 main 머지와 infra/terraform/ 을 바꾸는 PR 뿐이다.
     develop·phasex/* 이고 증거가 맞으면 allow (develop 은 검증 로그를 실제로 본 경우만),
     그 밖·PR 조회 실패(셸 변수 지정자 등)는 분류기에 맡긴다. 변경 파일이 100개 이상이면 ask.
     allow 는 명령 전체가 `cd <dir> && …` 와 `gh pr merge …` 하나뿐일 때만 낸다.
     다른 명령·치환·리다이렉션이 섞이면 allow 가 그 명령까지 분류기 없이 통과시키므로 분류기에 맡긴다.
  3. multi-session worker pane(제목에 `-worker-`)에서는 ask 를 deny 로 바꾼다. 확인 창이 worker pane 에 뜨면
     사용자는 그 pane 을 보지 않아 worker 가 멈춘다 (11-15: geo-ui·41-geo-pr2·sdk-worker 3건).
     deny 사유를 본 worker 가 orchestrator 에 `결정 필요` 를 보내고, 사용자가 승인한 예외는 orchestrator 가
     같은 명령을 직접 실행해 orchestrator pane 의 확인 창으로 받는다. 승인 표식(파일·환경변수)은 모델이
     스스로 쓸 수 있어 두지 않는다 (11-15 사용자).

근거 (11-14):
  - 전역 allow `Bash(gh pr merge:*)` 가 base 와 무관하게 main 머지까지 분류기 없이 통과시켰다.
    allow 규칙과 hook ask 가 겹칠 때의 우선순위는 문서에 없어 allow 규칙을 지우고 이 hook 이 allow·ask 를 모두 낸다.
  - "로그가 없으면 Ship·머지로 가지 않는다"(/work step5-code.md) 는 문장뿐이었다.
    Stop hook 은 백그라운드 implementer 를 기다리는 정상 턴까지 막아 쓰지 않는다 (사용자 결정).
  - 기존 실패(test-commands.md "알려진 기존 실패")도 exit≠0 이라, 막지 않고 모델에 알려 PR 본문에 적게 한다.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))
from shell_unwrap import nested_commands, strip_bin_dirs  # noqa: E402  # pyright: ignore[reportMissingImports]

AUTO_MERGE_PREFIX = "phasex/"
AUTO_MERGE_BASES = {"develop"}
# 이 base 로의 머지는 증거와 무관하게 사용자 확인
CONFIRM_MERGE_BASES = {"main", "master"}
# 이 경로를 바꾸는 PR 은 base 와 무관하게 사용자 확인 — apply 가 리뷰를 전제로 한다
CONFIRM_PATH_PREFIXES = ("infra/terraform/",)
# gh pr view --json files 가 돌려주는 최대 개수. 이만큼이면 뒤쪽 파일을 못 봤을 수 있어 사용자 확인
PR_FILES_LIMIT = 100
# runlog 대신 PR 검증 코멘트를 증거로 받는 repo — 시뮬레이터 검증을 코멘트로 남기는 절차라서 (11-17 사용자)
# dotfiles 가 public 이라 repo·계정 이름은 비공개 settings(claude wrapper 의 --settings) env 에 둔다. 없으면 코멘트 증거를 보지 않는다
VERIFIED_COMMENT_REPO = os.environ.get("PR_SHIP_VERIFIED_COMMENT_REPO", "")
VERIFIER_LOGIN = os.environ.get("PR_SHIP_VERIFIER_LOGIN", "")
WORKER_DENY_HINT = (
    "worker 는 이 확인 창을 사용자에게 보일 수 없다. 검증이 문제면 runlog 로 다시 돌리고, "
    "그래도 올려야 하면 orchestrator 에 `결정 필요` 로 보낸다 (승인되면 orchestrator 가 직접 실행)"
)
# 값을 따로 받는 gh pr 플래그 — 값을 PR 지정자로 오인하지 않게 함께 건너뛴다
FLAGS_WITH_VALUE = {
    "-R",
    "--repo",
    "-b",
    "--body",
    "-F",
    "--body-file",
    "-t",
    "--title",
    "--subject",
    "--match-head-commit",
    "-A",
    "--author-email",
    "-B",
    "--base",
    "-H",
    "--head",
    "-l",
    "--label",
    "-a",
    "--assignee",
    "-r",
    "--reviewer",
    "-m",
    "--milestone",
    "-p",
    "--project",
}
SHELL_OPERATORS = {"|", "||", "&&", ";", "&"}
# allow 를 낼 수 있는 명령 모양: 앞의 `cd <dir> &&` 들과 셸 구문 없는 `gh pr merge` 하나
CD_SEGMENT = re.compile(r"cd [^\s;&|<>$`'\"\\(){}]+")
PLAIN_MERGE = re.compile(r"gh pr merge(?: [^;&|<>$`\n\\(){}]*)?")
COMMAND_TIMEOUT_SECONDS = 10
# 검증 코멘트의 통과 표시 — "미통과"·"불통과" 는 통과가 아니다
PASSED = re.compile(r"(?<![미불])통과")


class Verdict(Enum):
    ALLOW = "allow"
    ASK = "ask"
    # hook 은 결정을 내지 않고 일반 권한 흐름(auto mode 분류기)에 맡긴다
    DEFER = "defer"
    # 결정은 맡기고 문제만 모델 문맥에 알린다
    WARN = "warn"


@dataclass(frozen=True)
class PrInvocation:
    action: str  # "create" | "merge"
    args: list[str]
    # 같은 명령 안의 `cd <dir>` 를 따른다 — PR 번호·브랜치는 그 디렉터리의 repo 기준이다
    directory: str


@dataclass
class Evidence:
    """검증 증거 판정. problems 가 비면 통과, skipped 면 /work 산출물이 아니라 보지 않은 것."""

    skipped: bool = False
    problems: list[str] = field(default_factory=list)


def main() -> None:
    hook_input = json.load(sys.stdin)
    command = hook_input.get("tool_input", {}).get("command", "")
    if "gh" not in command or ("merge" not in command and "create" not in command):
        return
    cwd = hook_input.get("cwd") or os.getcwd()
    invocations = [
        invocation
        for text in nested_commands(strip_bin_dirs(command))
        for invocation in _pr_invocations(text, cwd)
    ]
    if not invocations:
        return
    judged = [_judge(invocation) for invocation in invocations]
    ask_reasons = [reason for verdict, reason in judged if verdict is Verdict.ASK]
    warn_reasons = [reason for verdict, reason in judged if verdict is Verdict.WARN]
    allow_reasons = [reason for verdict, reason in judged if verdict is Verdict.ALLOW]
    if ask_reasons:
        _decide("ask", " / ".join(ask_reasons))
    elif allow_reasons and len(allow_reasons) == len(judged):
        if not _is_plain_merge(command):
            _warn(f"gh pr merge 외 명령·셸 구문이 섞여 자동 허용하지 않고 분류기에 맡긴다: {command[:200]}")
            return
        _decide("allow", " / ".join(allow_reasons))
    elif warn_reasons:
        _warn(" / ".join(warn_reasons))


def _is_plain_merge(command: str) -> bool:
    *cd_segments, last = strip_bin_dirs(command).strip().split("&&")
    return (
        all(CD_SEGMENT.fullmatch(segment.strip()) for segment in cd_segments)
        and PLAIN_MERGE.fullmatch(last.strip()) is not None
    )


def _judge(invocation: PrInvocation) -> tuple[Verdict, str]:
    """(판정, 사유). create 는 증거만, merge 는 base 와 증거를 함께 본다."""
    selector, repo, head_flag = _parse_args(invocation.args)
    if invocation.action == "create":
        branch = head_flag or _git(invocation.directory, "branch", "--show-current")
        head_time = (
            _git(invocation.directory, "log", "-1", "--format=%ct", branch)
            if branch
            else None
        )
        evidence = _evidence(invocation.directory, branch, head_time)
        if evidence.problems:
            return (
                Verdict.WARN,
                f"gh pr create ({branch}): {'; '.join(evidence.problems)} → PR 본문 검증에 실패 사유(기존 실패 등)를 적는다",
            )
        return Verdict.DEFER, f"gh pr create ({branch}): 검증 로그 확인"
    pr = _pr_view(selector, repo, invocation.directory)
    if pr is None:
        return (
            Verdict.WARN,
            f"gh pr merge {selector or ''}: PR 조회 실패 — base·검증을 확인하지 못해 분류기에 맡긴다",
        )
    base, branch, head_oid = pr["baseRefName"], pr["headRefName"], pr["headRefOid"]
    confirm_paths = [
        path for path in pr["files"] if path.startswith(CONFIRM_PATH_PREFIXES)
    ]
    head_time = _git(invocation.directory, "show", "-s", "--format=%ct", head_oid)
    evidence = _evidence(invocation.directory, branch, head_time)
    label = f"gh pr merge {selector or branch} ({branch} → {base})"
    if evidence.problems and _verified_by_comment(pr):
        evidence = Evidence()
        label += " 검증 코멘트 확인"
    if confirm_paths:
        return (
            Verdict.ASK,
            f"{label}: {', '.join(confirm_paths[:5])} 를 바꿔 사용자 확인이 필요하다",
        )
    if len(pr["files"]) >= PR_FILES_LIMIT:
        return (
            Verdict.ASK,
            f"{label}: 변경 파일이 {PR_FILES_LIMIT}개 이상이라 {CONFIRM_PATH_PREFIXES} 변경 여부를 다 확인하지 못했다",
        )
    if base in CONFIRM_MERGE_BASES:
        return Verdict.ASK, f"{label}: base={base} 머지는 사용자 확인이 필요하다"
    if evidence.problems:
        return Verdict.WARN, f"{label}: {'; '.join(evidence.problems)}"
    if base not in AUTO_MERGE_BASES and not base.startswith(AUTO_MERGE_PREFIX):
        return Verdict.WARN, f"{label}: base={base} 는 develop·phasex/* 가 아니라 분류기에 맡긴다"
    if base in AUTO_MERGE_BASES and evidence.skipped:
        return Verdict.WARN, f"{label}: /work worktree 가 아니라 검증 로그를 보지 못해 분류기에 맡긴다"
    return (
        Verdict.ALLOW,
        f"{label}: {'검증 로그 확인' if not evidence.skipped else '/work worktree 아님'}",
    )


def _pr_invocations(text: str, cwd: str) -> list[PrInvocation]:
    """`gh pr create|merge …` 마다 인자와 그 시점의 디렉터리. 따옴표가 안 닫히면 공백으로 쪼갠다."""
    try:
        tokens = shlex.split(text, posix=True)
    except ValueError:
        tokens = text.split()
    found = []
    directory = cwd
    for index, token in enumerate(tokens):
        if token == "cd" and index + 1 < len(tokens):
            directory = os.path.join(
                directory, os.path.expanduser(tokens[index + 1].rstrip(";&|"))
            )
        if token.rsplit("/", 1)[-1] != "gh" or tokens[index + 1 : index + 2] != ["pr"]:
            continue
        action = tokens[index + 2] if index + 2 < len(tokens) else ""
        if action in ("create", "merge"):
            found.append(
                PrInvocation(action, _until_operator(tokens[index + 3 :]), directory)
            )
    return found


def _until_operator(rest: list[str]) -> list[str]:
    args = []
    for token in rest:
        if token in SHELL_OPERATORS:
            break
        args.append(token.rstrip(";&|"))
    return args


def _parse_args(args: list[str]) -> tuple[str | None, str | None, str | None]:
    """(PR 지정자, --repo, --head)."""
    selector, repo, head = None, None, None
    index = 0
    while index < len(args):
        token = args[index]
        value = args[index + 1] if index + 1 < len(args) else None
        if token.startswith("--repo="):
            repo = token.split("=", 1)[1]
        if token.startswith("--head="):
            head = token.split("=", 1)[1]
        if token in ("-R", "--repo"):
            repo = value
        if token in ("-H", "--head"):
            head = value
        if token in FLAGS_WITH_VALUE:
            index += 2
            continue
        if token and not token.startswith("-") and selector is None:
            selector = token
        index += 1
    return selector, repo, head


def _pr_view(
    selector: str | None, repo: str | None, directory: str
) -> dict[str, str | list[str]] | None:
    view = [
        "gh",
        "pr",
        "view",
        *([selector] if selector else []),
        "--json",
        "baseRefName,headRefName,headRefOid,files,url,comments",
    ]
    if repo:
        view += ["--repo", repo]
    output = _run(view, directory)
    if output is None:
        return None
    pr = json.loads(output)
    if not all(pr.get(key) for key in ("baseRefName", "headRefName", "headRefOid")):
        return None
    return {  # pyright: ignore[reportReturnType]
        **pr,
        "files": [file["path"] for file in pr.get("files") or []],
        "comments": [
            (comment["author"]["login"], comment["body"])
            for comment in pr.get("comments") or []
        ],
    }


def _verified_by_comment(pr: dict) -> bool:
    """SDK 는 시뮬레이터 검증을 PR 코멘트로 남긴다 — 첫 3줄에 '통과', 본문에 head SHA(8자리 이상) 가 있으면 증거로 본다."""
    if (
        not VERIFIED_COMMENT_REPO
        or not VERIFIER_LOGIN
        or VERIFIED_COMMENT_REPO not in str(pr.get("url", ""))
    ):
        return False
    # 짧은 SHA·전체 SHA, 백틱 유무와 무관하게 head 앞 8자리로 시작하는 hex 를 찾는다
    head = re.compile(r"(?<![0-9a-f])" + str(pr["headRefOid"])[:8])
    return any(
        author == VERIFIER_LOGIN
        and head.search(body) is not None
        and PASSED.search("\n".join(body.splitlines()[:3])) is not None
        for author, body in pr["comments"]
    )


def _evidence(directory: str, branch: str | None, head_time: str | None) -> Evidence:
    common_dir = _git(
        directory, "rev-parse", "--path-format=absolute", "--git-common-dir"
    )
    if common_dir is None or branch is None:
        return Evidence(skipped=True)
    plans_root = Path(common_dir).parent / ".claude" / "plans"
    worktree = _worktree_of(directory, branch)
    if not plans_root.is_dir() or worktree is None:
        return Evidence(skipped=True)
    if head_time is None:
        return Evidence(
            problems=["HEAD 커밋 시각을 몰라 검증 로그가 그 뒤인지 확인하지 못했다"]
        )
    latest = _latest_runs(plans_root, worktree, int(head_time))
    if not latest:
        return Evidence(
            problems=[f"HEAD 커밋 이후 {worktree} 를 가리키는 runlog 로그가 없다"]
        )
    failed = [f"{log.name}(exit={code})" for log, code in latest.values() if code != 0]
    if failed:
        return Evidence(
            problems=[f"최신 실행이 실패한 검사: {', '.join(sorted(failed))}"]
        )
    return Evidence()


def _latest_runs(
    plans_root: Path, worktree: str, since: int
) -> dict[str, tuple[Path, int]]:
    """명령(첫 줄)마다 since 이후 가장 최근 runlog 실행의 (로그, exit)."""
    mentions = re.compile(re.escape(worktree) + r"(?![\w.-])")
    latest: dict[str, tuple[Path, int, float]] = {}
    for log in plans_root.glob("*/logs/*.txt"):
        mtime = log.stat().st_mtime
        if mtime < since:
            continue
        lines = log.read_text(errors="replace").splitlines()
        if (
            len(lines) < 2
            or not lines[0].startswith("+ ")
            or not mentions.search(lines[0] + lines[1])
        ):
            continue
        exit_line = re.match(r"exit=(\d+)", lines[-1])
        if exit_line is None:
            continue
        if lines[0] not in latest or latest[lines[0]][2] < mtime:
            latest[lines[0]] = (log, int(exit_line.group(1)), mtime)
    return {command: (log, code) for command, (log, code, _) in latest.items()}


def _worktree_of(directory: str, branch: str) -> str | None:
    listing = _git(directory, "worktree", "list", "--porcelain")
    if listing is None:
        return None
    path = None
    for line in listing.splitlines():
        if line.startswith("worktree "):
            path = line.split(" ", 1)[1]
        if line == f"branch refs/heads/{branch}":
            return path
    return None


def _git(directory: str, *args: str) -> str | None:
    return _run(["git", "-C", directory, *args], directory)


def _run(argv: list[str], directory: str) -> str | None:
    try:
        completed = subprocess.run(
            argv,
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = completed.stdout.strip()
    return output if completed.returncode == 0 and output else None


def _decide(decision: str, reason: str) -> None:
    if decision == "ask" and _in_worker_pane():
        decision = "deny"
        reason += f" → {WORKER_DENY_HINT}"
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            },
            ensure_ascii=False,
        )
    )


def _warn(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": f"pr-ship-guard 경고: {reason}",
                }
            },
            ensure_ascii=False,
        )
    )


def _in_worker_pane() -> bool:
    """pane 제목은 `<상태 아이콘> <세션 이름>` 꼴이다. tmux 밖이거나 조회가 실패하면 worker 가 아니라 보고 ask 를 유지한다."""
    pane = os.environ.get("TMUX_PANE")
    if not pane:
        return False
    title = _run(["tmux", "display", "-p", "-t", pane, "#{pane_title}"], os.getcwd())
    return title is not None and "-worker-" in title


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # 판정 실패는 통과가 아니라 사용자 확인으로 보낸다
        _decide("ask", f"pr-ship-guard 판정 실패 ({type(error).__name__}: {error})")
