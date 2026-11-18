---
name: multi-session
description: 옛 이름. orchestrator 는 orchestrator skill, worker·design 은 session-worker skill 을 쓴다. `/multi-session <이름>` 으로 시작한 세션은 이름을 보고 둘 중 하나를 불러라.
---

# Multi-session (옛 이름)

이 skill 은 둘로 나뉘었다. 세션 이름(시작 prompt 의 이름, 없으면 `ListAgents` 첫 줄 "This session is <name>")을 보고 Skill 도구로 맞는 skill 을 불러 그 지시를 따른다.

- `<group>-orchestrator` → `orchestrator`
- `<group>-worker-…`, `<group>-design…` → `session-worker`
