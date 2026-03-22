---
name: obsidian
model: opus
effort: low
disable-model-invocation: true
allowed-tools: Bash(obsidian-cli *), WebSearch, WebFetch, AskUserQuestion
description: Obsidian vault 통합 워크플로우 — 노트 생성, 정리, 리서치, 학습 관리
---

## Context

- Vault 폴더: !`obsidian-cli list 2>/dev/null || echo "obsidian-cli 미설치"`
- 사용자 입력: $ARGUMENTS

## Your Task

$ARGUMENTS의 의도를 파악하고 적절한 vault 작업을 수행하세요.

### 의도 판단 기준

| 의도               | 트리거 예시                                            |
| ------------------ | ------------------------------------------------------ |
| **노트 생성/추가** | "React hooks 정리", "회의 메모", 특정 주제/내용 언급   |
| **정리**           | "inbox 정리", "노트 정리", "태그 정리", 인자 없이 실행 |
| **리서치**         | "조사해줘", "찾아봐", "알아봐", 학습/조사 의도 표현    |
| **학습 관리**      | "학습 큐", "queue", "공부할 것", 학습 계획 관련        |

### 공통 규칙

- 작업 전 `obsidian-cli search-content`로 기존 관련 노트 확인
- 새 노트: frontmatter 필수 (`date`, `tags`)
- 내부 링크: `[[note-name]]` wikilink 형식
- 파괴적 작업(delete, move)은 AskUserQuestion으로 확인 후 실행

---

### 노트 생성/추가

1. 키워드로 기존 노트 검색 (`search-content`)
2. 관련 노트 존재 시 AskUserQuestion: **기존에 추가** vs **새로 생성**
3. 노트 생성 시 관련 노트에 `[[wikilink]]` 포함

### 정리 (인자 없거나 "정리" 요청)

1. `obsidian-cli list "00-inbox"`로 inbox 스캔
2. 각 노트 내용 확인 (`print`, `frontmatter --print`)
3. 이동할 폴더를 제안하고 AskUserQuestion으로 확인
4. 누락된 frontmatter/태그 보완

### 리서치

1. vault 내 기존 노트 확인
2. WebSearch + WebFetch로 조사
3. 구조화된 노트 생성 (요약, 상세, 출처)
4. 관련 기존 노트에 링크 추가

### 학습 관리

1. `obsidian-cli print "02-learning/queue.md"`로 큐 확인
2. 인자에 따라: 큐 현황 보기 / 항목 추가 / 학습 노트 생성
3. 학습 노트 생성 시 큐에서 `- [x]`로 체크
