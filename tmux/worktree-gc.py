#!/usr/bin/env python3
"""저장소들의 git worktree 를 분류해 표로 보여주고, `--apply` 면 안전한 것만 지운다.

안전한 것: prunable(디렉터리 없음), 또는 미커밋 변경 없음 + 살아 있는 worker pane 이 기록하지 않음 +
  (PR MERGED 이고 HEAD 가 PR head) 또는 (PR 없고 HEAD 가 원격 브랜치에 있음 — 리뷰·검증 scratch).
나머지(미커밋 변경·원격에 없는 커밋·열린 PR·사용 중)는 표에만 낸다. 로컬 브랜치는 지우지 않는다.

사용: worktree-gc.py <repo> [<repo> ...] [--apply]
"""

from __future__ import annotations

import enum
import json
import os
import subprocess
import sys
from dataclasses import dataclass


class Verdict(enum.Enum):
    PRUNABLE = "prunable"
    SAFE = "지워도 됨"
    IN_USE = "사용 중"
    DIRTY = "미커밋 변경"
    UNPUSHED = "원격에 없는 커밋"
    OPEN_PR = "열린 PR"


@dataclass(frozen=True)
class Worktree:
    repo: str
    path: str
    branch: str | None
    head: str
    prunable: bool


@dataclass(frozen=True)
class Classified:
    worktree: Worktree
    verdict: Verdict
    note: str


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    repos = [
        os.path.realpath(os.path.expanduser(arg)) for arg in args if arg != "--apply"
    ]
    if not repos:
        sys.exit("usage: worktree-gc.py <repo> [<repo> ...] [--apply]")
    in_use = live_worker_worktrees()
    rows = [
        classify(worktree, in_use)
        for repo in repos
        for worktree in list_worktrees(repo)
    ]
    for row in rows:
        print(
            f"{row.verdict.value}\t{row.worktree.path}\t{row.worktree.branch or 'detached'}\t{row.note}"
        )
    if apply:
        remove_safe(rows)


def list_worktrees(repo: str) -> list[Worktree]:
    porcelain = git(repo, "worktree", "list", "--porcelain")
    worktrees = []
    for block in porcelain.strip().split("\n\n")[1:]:  # 첫 블록은 메인 checkout
        fields: dict[str, str] = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        branch = fields.get("branch", "").removeprefix("refs/heads/") or None
        worktrees.append(
            Worktree(
                repo, fields["worktree"], branch, fields["HEAD"], "prunable" in fields
            )
        )
    return worktrees


def classify(worktree: Worktree, in_use: set[str]) -> Classified:
    if worktree.prunable:
        return Classified(worktree, Verdict.PRUNABLE, "")
    if os.path.realpath(worktree.path) in in_use:
        return Classified(
            worktree, Verdict.IN_USE, "살아 있는 worker pane 의 @claude_worktrees"
        )
    dirty = git(worktree.path, "status", "--porcelain").splitlines()
    if dirty:
        return Classified(worktree, Verdict.DIRTY, f"{len(dirty)}개")
    pull_request = pull_request_of(worktree)
    if pull_request and pull_request["state"] == "OPEN":
        return Classified(
            worktree,
            Verdict.OPEN_PR,
            f"#{pull_request['number']} {pull_request['title']}",
        )
    if (
        pull_request
        and pull_request["state"] == "MERGED"
        and pull_request["headRefOid"] == worktree.head
    ):
        return Classified(worktree, Verdict.SAFE, f"#{pull_request['number']} MERGED")
    if git(worktree.repo, "branch", "-r", "--contains", worktree.head).strip():
        return Classified(worktree, Verdict.SAFE, "HEAD 가 원격 브랜치에 있음")
    return Classified(worktree, Verdict.UNPUSHED, "HEAD 를 담은 원격 브랜치 없음")


def pull_request_of(worktree: Worktree) -> dict[str, str] | None:
    if not worktree.branch:
        return None
    output = subprocess.run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            worktree.branch,
            "--state",
            "all",
            "--json",
            "number,state,title,headRefOid",
        ],
        cwd=worktree.repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    pull_requests = json.loads(output)
    return pull_requests[0] if pull_requests else None


def live_worker_worktrees() -> set[str]:
    listing = subprocess.run(
        ["tmux", "list-panes", "-a", "-F", "#{@claude_worktrees}"],
        capture_output=True,
        text=True,
    ).stdout
    return {
        os.path.realpath(path)
        for line in listing.splitlines()
        for path in line.split("|")
        if path
    }


def remove_safe(rows: list[Classified]) -> None:
    for repo in sorted(
        {row.worktree.repo for row in rows if row.verdict is Verdict.PRUNABLE}
    ):
        git(repo, "worktree", "prune")
        print(f"pruned\t{repo}")
    for row in rows:
        if row.verdict is not Verdict.SAFE:
            continue
        # 미커밋 변경이 생겼으면 --force 없는 remove 가 거부해 멈춘다
        git(row.worktree.repo, "worktree", "remove", row.worktree.path)
        print(f"removed\t{row.worktree.path}")


def git(directory: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", directory, *args], capture_output=True, text=True, check=True
    ).stdout


if __name__ == "__main__":
    main()
