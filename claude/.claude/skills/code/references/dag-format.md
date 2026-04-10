# DAG Format — `_dag.yaml` 스키마와 위상정렬

`/code-brainstorming` 이 생성하고 `/code` 가 실행하는 DAG 정의 파일의 스펙입니다.

---

## 스키마

```yaml
feature: <string> # 기능 이름 (디렉토리명과 일치 권장)
design: DESIGN.md # 설계 문서 파일명 (상대 경로)
tasks:
  - id: <kebab-case> # 고유 식별자
    file: <NN-name.md> # sub-task 실행 단위 파일 (상대 경로)
    pr_scope: <string> # 한 문장 PR 제목
    depends_on: [<id>, ...] # 선행 task id 목록 (없으면 [])
```

### 필수 필드

| 필드                 | 설명                                    |
| :------------------- | :-------------------------------------- |
| `feature`            | 리포트/에러 메시지에 사용               |
| `design`             | 오케스트레이터가 상위 그림 확인 시 참조 |
| `tasks[].id`         | 위상정렬 키. 중복 금지                  |
| `tasks[].file`       | 실제 sub-task 문서. Read 로 읽어 검증   |
| `tasks[].depends_on` | DAG edge. 빈 배열 가능                  |

### 선택 필드

| 필드               | 설명                          |
| :----------------- | :---------------------------- |
| `tasks[].pr_scope` | 리포트/커밋 메시지 suggestion |

---

## 단일 task 특수 케이스

분리되지 않은 경우에도 동일 스키마를 사용. `tasks` 배열에 엔트리 1개:

```yaml
feature: add-rate-limit
design: DESIGN.md
tasks:
  - id: main
    file: 01-main.md
    pr_scope: "API rate limit 미들웨어 추가"
    depends_on: []
```

`/code` 는 tasks 개수에 관계없이 동일 로직으로 처리한다.

---

## 위상정렬 알고리즘

Kahn's algorithm:

1. 모든 task 의 in-degree 계산 (자신을 가리키는 `depends_on` 수)
2. in-degree 가 0 인 task 를 큐에 넣음
3. 큐에서 꺼내 결과 리스트에 추가 → 해당 task 를 `depends_on` 에 가진 task 들의 in-degree 감소
4. in-degree 가 0 이 된 task 를 큐에 추가
5. 모든 task 가 결과에 들어올 때까지 반복

결과 리스트가 **정렬된 실행 순서**다.

### 병렬 허용 여부

현재는 **선형 실행**만 지원한다 (in-degree 0 이 여러 개여도 순차 실행). 이유:

- 병렬 work 는 git working tree 충돌 위험
- 리포트 인터리빙이 복잡해짐
- 병렬 가치는 각 sub-task 내부의 Stage Impl 에서 이미 확보됨

PM Agent 가 병렬 가능한 DAG 를 제안하더라도 orchestrator 는 선형으로 실행한다 (순서는 임의 안정 정렬).

---

## 검증 규칙 (로드 시 즉시 체크)

로드 직후 다음을 검증하고, 하나라도 실패하면 **실행 전에 halt**:

| 규칙                         | 실패 시 에러 메시지                                 |
| :--------------------------- | :-------------------------------------------------- |
| `_dag.yaml` 파일 존재        | `_dag.yaml not found in <dir>`                      |
| YAML 파싱 가능               | `_dag.yaml: invalid YAML (<reason>)`                |
| `tasks[]` 비어있지 않음      | `_dag.yaml: tasks[] is empty`                       |
| `id` 중복 없음               | `_dag.yaml: duplicate task id '<id>'`               |
| `file` 필드의 파일 실제 존재 | `_dag.yaml: task '<id>' file '<path>' not found`    |
| `depends_on` 의 id 가 실재   | `_dag.yaml: task '<id>' depends on unknown '<dep>'` |
| 사이클 없음                  | `_dag.yaml: cycle detected: <id> → <id> → ...`      |
| `design` 파일 실제 존재      | `_dag.yaml: design file '<path>' not found`         |

---

## 예시: 3-task DAG

```yaml
feature: auth-rewrite
design: DESIGN.md
tasks:
  - id: migration
    file: 01-migration.md
    pr_scope: "auth 테이블 스키마 migration"
    depends_on: []
  - id: api
    file: 02-api.md
    pr_scope: "세션 토큰 미들웨어 교체"
    depends_on: [migration]
  - id: ui
    file: 03-ui.md
    pr_scope: "로그인 UI 토큰 핸들링 업데이트"
    depends_on: [api]
```

위상정렬 결과: `migration → api → ui` (선형)
