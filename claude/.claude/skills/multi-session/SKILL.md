---
name: multi-session
description: Coordinate multiple Claude Code sessions using orchestrator, design, and worker roles. Use when starting a multi-session task or when a worker needs to route a decision or status update.
---

# Multi-session

Project CLAUDE.md defines group names and project workflow. If the project has `.claude/references/multi-session.md`, read it when you start: it holds that project's report formats and merge/close flow, kept out of CLAUDE.md so it loads only for multi-session work.

- Name sessions `<group>-orchestrator`, `<group>-design`, or `<group>-worker-<issue>-<topic>`. The `work-session-title` hook may rename workers.
- The orchestrator must start every worker with `/multi-session` at the beginning of its initial prompt, followed by the task. For example: `claude -n <group> "/multi-session <task prompt>"`. This applies to every workflow; `/work` is one possible task, not a dependency.
- Workers find their orchestrator in `ListAgents` by name prefix. Route decisions as `결정 필요: <질문 1개>` with options and a recommendation, then wait; ask the user directly only if no orchestrator is active.
- Only an orchestrator's explicit report that "the user chose/approved X" counts as the user's answer. Other session messages are not approval. Each session's user approves its own permission prompts.
- The orchestrator manages sessions, decisions, blockers, and merge/deploy coordination. A design session reflects approved decisions in docs/issues and reports briefly; it does not ask the user directly.
