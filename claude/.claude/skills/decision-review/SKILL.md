---
name: decision-review
description: 지난 대화 히스토리에서 사용자에게 올라온 결정(AskUserQuestion·worker `결정 필요`)을 모아 multi-session 결정 규칙표의 칸(worker·orchestrator·사용자)별 권장안 채택률을 잰다. 규칙표를 넓힐지 좁힐지 정할 때, 지난번 측정과 비교할 때 쓴다.
disable-model-invocation: true
---

# Decision review

결정 규칙표(multi-session SKILL.md)가 맞는지 히스토리로 잰다. 권장안 채택률이 높은 유형은 더 아래 칸(worker 쪽)으로, 낮거나 되묻기가 많은 유형은 사용자 칸으로 옮길 근거가 된다.

## 흐름

```
extract.py ──▶ pairs.jsonl · worker_requests.jsonl · sample_N.jsonl (200건씩)
                                   │
                    sample 하나당 sonnet subagent 1개 (병렬) ──▶ labels_N.jsonl
                                   │
aggregate.py ──▶ 칸·유형별 표 + summary.json ──▶ 지난 summary.json 과 비교해 보고
```

## 실행

1. 결과 폴더는 `~/.claude/decision-review/<YYYY-MM-DD>/` 로 한다. 같은 날 다시 재면 `-2` 를 붙인 새 폴더를 쓴다 — 지난 sample·labels 가 있으면 `extract.py` 가 멈춘다.
2. `python3 -I ~/.claude/skills/decision-review/scripts/extract.py <폴더> --days 30 --sample 400`
3. `sample_N.jsonl` 마다 Agent(`model: "sonnet"`) 를 한 메시지에서 병렬로 띄운다. 프롬프트는 아래 "분류 프롬프트" 를 그대로 쓰고 입력·출력 경로만 바꾼다.
4. subagent 보고를 믿지 말고 `labels_N.jsonl` 줄 수를 직접 센다. `aggregate.py` 는 id 가 sample 과 다르거나 겹치면, column·subtype 이 아래 목록 밖이면, confused 가 bool 이 아니면 파일:줄과 함께 실패한다. 그 줄만 subagent 에 다시 맡긴다.
5. `python3 -I ~/.claude/skills/decision-review/scripts/aggregate.py <폴더>`
6. 권장안과 다르게 고른 worker 칸 질문을 직접 10건 이상 읽고 분류가 맞는지 본다 (subagent 분류는 검증 전 추정이다).
7. 보고: 칸별 표, 변화가 큰 유형, 칸을 옮길 후보(채택률 90% 이상 → 아래 칸 후보, 70% 미만이거나 되묻기 많음 → 사용자 칸 후보). 지난 폴더의 `summary.json` 이 있으면 같은 표로 비교한다. 규칙표 수정은 사용자가 고른 뒤 한다.

## 분류 프롬프트

```
Classify past decision questions that Claude Code sessions asked a human user.
Input (JSONL): <sample_N.jsonl>. Each line: id, project, question, options ("(Recommended)" marks the asker's recommendation), answer, outcome.
For EVERY line assign, by reading it (no keyword heuristics):
1. column:
   - "worker": inside one task/issue — implementation approach, code structure, tests and test env, next verification/measurement step, behavior-preserving review fixes, branches/worktrees, docs inside the repo, Plan approval without contract/behavior change, read-only investigation.
   - "orchestrator": affects other parallel workers — PR split, issue order/dependency, files shared by several issues, issue scope interpretation, session/subagent management, same-repo result-report comments.
   - "user": hard to reverse or externally visible — merge, deploy/apply/rollout, delete/close, creating issues, other comments/Slack, API/schema/wire contract, changing what a feature does, starting work the user didn't ask for, credentials, cost, product judgment.
2. subtype: one of impl_approach, verify_next_step, test_add, test_env, doc_edit, plan_approval, review_feedback, pr_split, order_dependency, scope_interpret, session_mgmt, start_worker, merge_pr, deploy, cleanup, close_issue, create_issue, post_comment, publish, design_contract, permission, credential, spend_cost, product_decision, other.
3. confused: true if the answer asks a question back or asks for an explanation.
Write JSONL to <labels_N.jsonl>: {"id":..., "column":..., "subtype":..., "confused":...}, one line per input id. Do not modify the input.
Report only the number of lines written.
```

## 기준값 (11-15, 30일)

| 칸           | 비율 | 권장안 채택 |
| ------------ | ---- | ----------- |
| worker       | 38%  | 88%         |
| orchestrator | 15%  | 79%         |
| 사용자       | 47%  | 76%         |

- 질문 약 1,314건, worker `결정 필요` 652건 (그중 머지 약 240건), 표본 400건
- 처음 집계는 사본 entry(`api-request-blob`)까지 세어 `결정 필요` 를 1,312건으로 두 배 셌다. 위 값은 사본을 뺀 값이고, 표본 400건의 칸별 비율은 사본을 빼지 않은 채 잰 값이다
- 이 기준은 결정 규칙표를 적용하기 전 값이다. 적용 뒤에는 worker 칸 질문 수 자체가 줄어야 한다
