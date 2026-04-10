# Stage Pipeline — 각 sub-task 의 파이프라인 실행 계약

한 sub-task 를 `pre → work → post → (fix) → clean` 으로 흘리는 방법. 각 stage 는 기존 스킬(`/work-pre`, `/work`, 등)을 **Skill tool 로 호출**하여 재사용한다. 오케스트레이터는 재구현하지 않는다.

---

## 공통 호출 원칙

1. **자동 모드 전파**: 각 stage 호출 직전, 오케스트레이터 맥락에 "자동 모드: 사용자 질문 금지, 모호하면 실패로 간주" 지침을 명시적으로 포함시킨다
2. **반환값 파싱**: 하위 스킬은 자연어 리포트를 반환. `halt-policy.md` 의 키워드 매칭으로 결과 분류
3. **에러 격리**: 한 stage 의 실패는 해당 sub-task 파이프라인만 halt. 전체 halt 는 halt-policy 에 따름
4. **상태 추적**: 각 stage 시작/종료 시 TaskUpdate 로 진행 상황 기록

---

## Stage 1: `/work-pre`

**목적**: sub-task 문서를 기반으로 코드베이스 분석 + 구현 계획 수립

**호출**:

```
Skill tool
  skill: "work-pre"
  args: "<plan-dir>/<task.file>"
```

**입력 계약**:

- `<task.file>` 은 `_dag.yaml` 에 정의된 sub-task 문서 (`NN-*.md`)
- sub-task 문서는 상위 `DESIGN.md` 를 참조할 수 있음 (work-pre 가 링크 따라감)

**성공 판정**: 리포트에 "분석 완료" 또는 유사 signal. 실패 signal (파일 없음, 분석 불가) 없음.

**실패 시**: 즉시 halt. retry 하지 않음 (분석 실패는 입력 문제).

---

## Stage 2: `/work`

**목적**: 계획에 따라 실제 코드 구현 (병렬 에이전트 팀)

**호출**:

```
Skill tool
  skill: "work"
  args: ""  # work-pre 결과가 컨텍스트에 있다는 전제
```

**입력 계약**:

- 직전 `/work-pre` 의 결과가 대화 컨텍스트에 있어야 함
- work 는 `.claude/plans/*.md` 자동 탐색 (최신 우선)

**성공 판정**: 리포트에 "구현 완료" + 수정 파일 목록. `git status` 로 변경사항 확인 가능.

**실패 시**: halt. post/fix 로 자동 복구 불가한 영역.

**주의**: `work` 는 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 필요. 환경변수 없으면 work-pre 이후 사용자에게 설정 요청 후 halt.

---

## Stage 3: `/work-post`

**목적**: 구현 결과 검증 — 빌드/타입/린트/테스트 + 코드/보안/DB 리뷰 (병렬 agent)

**호출**:

```
Skill tool
  skill: "work-post"
  args: "<sub-task pr_scope>"
```

**출력 판정 키워드** (리포트에서 파싱):

| 키워드                       | 분류            |
| :--------------------------- | :-------------- |
| `종합 판정: PASS`            | PASS            |
| `종합 판정: NEEDS ATTENTION` | NEEDS ATTENTION |
| `종합 판정: FAIL`            | FAIL            |

분류 후 `halt-policy.md` 로 행동 결정.

---

## Stage 4: `/work-fix` (조건부)

**목적**: critical 이슈(빌드 실패, 테스트 실패, critical 리뷰 이슈) 자동 수정

**호출 조건**: Stage 3 이 FAIL 일 때만

**호출**:

```
Skill tool
  skill: "work-fix"
  args: "<pr_scope> --max-retries 1"
```

> `--max-retries 1` 로 호출하는 이유: 오케스트레이터 자체가 재시도 루프를 관리함. work-fix 내부 재시도와 이중화 방지.

**재시도 루프** (retry-policy.md 참조):

1. work-fix 실행
2. work-post 재실행
3. PASS 면 Stage 5 로, 여전히 FAIL 이면 재시도 카운트 증가
4. 최대 3회 소진 시 전체 halt

---

## Stage 5: `/work-clean`

**목적**: dead code / 미사용 import / 중복 정리

**호출**:

```
Skill tool
  skill: "work-clean"
  args: ""
```

**성공 판정**: 리포트 반환되면 성공으로 간주

**실패 시**: **halt 하지 않음**. warning 으로 리포트에 기록하고 다음 sub-task 진행. clean 은 선택적 정리 단계이며 블로킹 해서는 안 됨.

---

## Sub-task 완료 체크리스트

한 sub-task 가 다음 조건을 모두 만족하면 `completed`:

- [ ] Stage 1 (pre) 성공
- [ ] Stage 2 (work) 성공
- [ ] Stage 3 (post) 가 PASS 또는 NEEDS ATTENTION
- [ ] Stage 5 (clean) 시도됨 (성공/warning 무관)

다음 sub-task 로 진행하기 전에 `git status --short` 를 찍어 working tree 상태를 리포트에 기록한다.
