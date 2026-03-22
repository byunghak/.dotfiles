---
name: dable-encrypt
model: opus
effort: low
disable-model-invocation: true
allowed-tools: Bash(jira issue view:*), Bash(jira issue edit:*), Bash(jira issue comment add:*), Bash(gh search code:*), Bash(gh repo view:*), Bash(gh api:*), Bash(gh repo clone:*), Bash(git checkout:*), Bash(git branch:*), Bash(git log:*), Bash(git diff:*), Bash(git push:*), Bash(git remote:*), Bash(git status:*), Bash(git rev-parse:*), Bash(git pull:*), Bash(gh pr create:*), Bash(gh pr view:*), Bash(gh pr edit:*), Bash(gh label list:*), Bash(npm install:*), Bash(npm ls:*), Bash(node:*), Bash(npx:*), Bash(mysql:*), Bash(find:*), Bash(cat:*), Bash(ls:*), Bash(cd:*), Bash(jq:*), Bash(grep:*), Read, Write, Edit, Glob, Grep, Agent, AskUserQuestion
description: DB 컬럼 암호화 마이그레이션 — Step 문서 기반 진행 (Step 1 준비 → Step 2 마이그레이션 → Step 3 정리 → Step 4 컬럼 제거)
---

## Arguments

- `$ARGUMENTS`: `<TICKET>`

## Context

- JIRA 티켓: $ARGUMENTS에서 추출
- GitHub 조직: teamdable
- db-cipher repo: teamdable/db-cipher
- data-schema repo: teamdable/data-schema

---

## 코드 수정 시 주의사항

Agent에게 작업을 위임할 때 반드시 아래 주의사항을 prompt에 포함하세요.

### 1. SELECT \_ 와 encrypted\_\_ 컬럼

`SELECT *` 사용 시 encrypted\_\* 컬럼이 결과에 자동 포함됩니다.

- 별도로 SELECT 목록에 추가할 필요 없음
- **복호화 로직만 추가**하면 됨 (결과 행에서 encrypted\_\* 읽고 delete)
- 특정 컬럼만 SELECT하는 경우에만 encrypted\_\* 컬럼을 명시적으로 추가

### 2. 동기 → 비동기 전환

기존 코드의 직렬화/역직렬화 함수(`deserialize`, `serialize` 등)가 **동기 함수**인 경우가 많습니다.
decrypt는 비동기이므로:

- 기존 동기 함수는 그대로 유지
- **별도의 async 복호화 헬퍼**를 만들어 SELECT 결과에 적용
- `.then(rows => rows.map(deserialize))` → `Promise.all(rows.map(decryptAndDeserialize))` 패턴 사용
- 함수 시그니처가 `function` → `async function`으로 변경될 수 있으므로, 호출부 영향도 확인

### 3. MySQL `SET ?` (객체 기반 UPDATE) 패턴

MySQL의 `UPDATE table SET ?` 패턴에서 `?`에 객체를 전달하는 경우:

- 객체에 encrypted\_\* 프로퍼티를 추가하거나
- `SET ?, encrypted_xxx = ?` 형태로 추가 파라미터를 별도 전달
- 기존 객체 구조를 변경하지 않도록 주의

### 4. 에러 핸들링 정책 유지

기존 코드에 에러 핸들링 패턴(try-catch + logger + fallback 등)이 있으면, 암호화/복호화 코드에도 **동일한 정책**을 적용해야 합니다. 기존 패턴을 반드시 확인하고 일관성을 유지하세요.

### 5. LIKE 검색 대상 컬럼 전환

원본 컬럼에 대한 `LIKE` 검색이 있는 경우:

- 비민감 필드(예: `known_route`, `biz_name`)는 암호화 컬럼에서도 평문이므로 `LIKE` 검색 대상을 암호화 컬럼으로 전환 가능
- 민감 필드(예: `email`, `phone`)에 대한 `LIKE` 검색은 암호화 후 불가 — TODO 주석 추가

### 6. body NOT NULL + mediumtext DEFAULT 불가 대응

원본 컬럼이 `NOT NULL`이고 `mediumtext`/`longtext` 타입이면 DEFAULT를 지정할 수 없음 (MySQL 5.x 제약).
이 경우 INSERT/UPDATE에서 원본 컬럼에 `'{}'` (빈 JSON) placeholder를 명시적으로 써야 합니다.

---

## 진입점: Step 문서 확인

`$ARGUMENTS`가 없으면 AskUserQuestion으로 JIRA 티켓 키를 요청하세요.

현재 작업 디렉토리에서 Step 문서를 찾습니다:

```
encrypt-plan-<TICKET>.md
```

- **문서가 없으면** → [초기 설정: JIRA 파싱 + Step 문서 생성](#초기-설정-jira-파싱--step-문서-생성)으로 이동
- **문서가 있으면** → 문서를 읽고 첫 번째 미완료 항목(`- [ ]`)을 찾아 해당 Step 절차를 진행

---

## 초기 설정: JIRA 파싱 + Step 문서 생성

### JIRA 카드 파싱

```bash
jira issue view <TICKET> --raw
```

description에서 아래 정보를 추출하세요. **표준 형식이 아니더라도 유연하게 파싱**합니다:

**테이블 레벨 정보** (스칼라):

| #   | 항목         | 예시            | 파싱 힌트                                   |
| --- | ------------ | --------------- | ------------------------------------------- |
| 1   | 서버         | AD, RECO, DMP   | db-cipher의 SENSITIVE_TABLE_CONFIG_BY_DB 키 |
| 2   | 데이터베이스 | AD_ADMIN, DABLE | `{서버}_{...}` 형태 또는 DDL 경로에서 추론  |
| 3   | 테이블명     | ACCOUNT_REQUEST | 대문자 + 언더스코어 패턴                    |

**컬럼 레벨 정보** (배열 — 복수 행 가능):

| #   | 항목      | 예시                     | 비고                                            |
| --- | --------- | ------------------------ | ----------------------------------------------- |
| 4   | 컬럼명    | body, email, phone       | 암호화 대상 원본 컬럼. 복수 가능                |
| 5   | 타입      | mediumtext, varchar(255) | DDL에서 확인 가능                               |
| 6   | 민감 필드 | email, phone, name       | JSON 내 부분 암호화 대상 키. 전체 암호화면 빈칸 |

**표준 테이블 형식** (권장 — 복수 행 지원):

```
| 서버 | 데이터베이스 | 테이블 | 컬럼명 | 타입 | 민감 필드 |
```

- 행이 1개면 단일 컬럼
- 행이 N개면 복수 컬럼 (서버/DB/테이블이 빈 행은 직전 행 값 상속)

**비표준 형식 대응**: description이 표준 형식이 아닌 경우:

1. description 내용에서 테이블명, 컬럼명 등을 최대한 추출
2. 추출한 정보를 사용자에게 보여주고 확인 요청
3. 누락된 항목은 개별적으로 AskUserQuestion으로 요청

**정보 누락 시 자동 해결 + 개별 질문** (한 번에 모든 것을 묻지 말고, 단계적으로):

1. 서버명 자동 해결 (GitHub에서 constants.ts 조회):

   ```bash
   gh api repos/teamdable/db-cipher/contents/src/common/constants.ts -H "Accept: application/vnd.github.raw+json" | grep -B 10 "<TABLE>"
   ```

   - `SENSITIVE_TABLE_CONFIG_BY_DB.<SERVER>.<DB>.<TABLE>` 경로에서 서버키 추출
   - 찾으면 자동 사용, 못 찾으면 AskUserQuestion: "이 테이블의 서버명을 알려주세요"

2. 컬럼 타입 확인 (GitHub에서 DDL 조회 + 불일치 검증):

   ```bash
   gh api repos/teamdable/data-schema/contents/rds/<db(소문자)>/<TABLE>.sql -H "Accept: application/vnd.github.raw+json"
   ```

   - DDL에서 각 컬럼의 타입을 추출
   - **DDL 불일치 검증**: JIRA에 있지만 DDL에 없는 컬럼이 있으면 AskUserQuestion:
     "JIRA에 `<컬럼명>`이 있지만 DDL에는 없습니다. 이 컬럼을 암호화 대상에 포함할까요?"
   - DDL에서도 전혀 확인 불가하면 AskUserQuestion으로 타입 요청

3. 민감 필드를 알 수 없으면:
   - AskUserQuestion: "이 컬럼은 JSON Object인가요? JSON이라면 암호화할 필드명을 알려주세요 (예: email, phone, name)"
   - 참고 링크 제공: [데이터베이스 개인정보 관리 시트](https://docs.google.com/spreadsheets/d/10Nx_Thi2cfblUegiXAHXzUyANt2FaUPV/edit?gid=2055106771#gid=2055106771)

**암호화 패턴 자동 판별** (컬럼별 민감 필드 유무로 결정):

| 패턴                                  | 조건           | 신규 컬럼 접두사       | db-cipher API                   |
| ------------------------------------- | -------------- | ---------------------- | ------------------------------- |
| **Pattern A** (JSON 부분 암호화)      | 민감 필드 있음 | `partially_encrypted_` | `encryptFields`/`decryptFields` |
| **Pattern B** (개별 컬럼 전체 암호화) | 민감 필드 없음 | `encrypted_`           | `encrypt`/`decrypt`             |

**PK 컬럼명 확인**:

```bash
gh api repos/teamdable/data-schema/contents/rds/<db(소문자)>/<TABLE>.sql -H "Accept: application/vnd.github.raw+json" | grep -i "PRIMARY KEY"
```

- DDL에서 PK를 확인할 수 없으면 AskUserQuestion: "이 테이블의 Primary Key 컬럼명을 알려주세요 (예: pkid, id, idx)"

**최종 확인**: 모든 정보를 수집한 후 AskUserQuestion으로 요약을 보여주고 확인받으세요.

### 의존 Repository 탐색

```bash
gh search code "<테이블명>" --owner teamdable --json repository,path,textMatches -L 100
```

결과에서:

- node_modules, test, spec, mock, fixture, migration 경로는 제외
- data-schema 레포는 제외
- 실제 SQL 쿼리나 모델에서 테이블을 참조하는 코드만 필터링

**결과 분류**: 각 의존 repo의 코드를 분석하여 카테고리 분류

| 카테고리 | 키워드 패턴                                       |
| -------- | ------------------------------------------------- |
| INSERT   | `INSERT INTO`, `insert into`                      |
| UPDATE   | `UPDATE ...SET`, `update ...set`                  |
| SELECT   | `SELECT`, `select`, `findAll`, `findOne`, `fetch` |

AskUserQuestion으로 탐색 결과를 보여주고 확인을 받으세요.

### Step 문서 생성

현재 작업 디렉토리에 `encrypt-plan-<TICKET>.md` 파일을 생성합니다.
Step 문서 템플릿은 아래와 같습니다 (Pattern A/B에 따라 대상 정보 섹션만 다름):

```markdown
# 암호화 마이그레이션: <TICKET>

## 대상 정보

(Pattern/컬럼 정보를 테이블로 정리)

## 의존 Repository

(repo, 카테고리, 주요 파일을 테이블로 정리)

## Step 1: 준비 (DDL + db-cipher 적용)

- [ ] JIRA 작업 범위 댓글 작성
- [ ] data-schema DDL PR:
- [ ] <repo별> db-cipher 적용 PR:

## Step 2: 데이터 마이그레이션

- [ ] Step 1 PR 전체 머지 확인
- [ ] 마이그레이션 스크립트 생성
- [ ] dev dry-run 실행
- [ ] dev 실제 마이그레이션 실행
- [ ] prod dry-run 실행
- [ ] prod 실제 마이그레이션 실행
- [ ] 복호화 검증
  - 결과:

## Step 3: 정리 (fallback 제거 + DDL 제약 변경)

- [ ] 마이그레이션 데이터 검증 (NULL/빈값 없음)
- [ ] <repo별> fallback 제거 PR:
- [ ] data-schema DDL 제약 변경 PR:
- [ ] JIRA 완료 처리

## Step 4: 원본 컬럼 제거 (별도 진행)

- [ ] Step 3 PR 전체 머지 및 배포 확인
- [ ] <repo별> 원본 컬럼 참조 완전 제거 PR:
- [ ] data-schema DDL 원본 컬럼 DROP PR:
- [ ] JIRA 최종 완료 처리
```

### JIRA 설명란 업데이트

Step 문서 생성 후, JIRA 티켓 description에 진행 상황 체크리스트를 추가합니다.

**jira CLI 제약사항**: `jira issue edit --body`는 마크다운을 ADF로 변환하지만, `- [x]` / `- [ ]`를 네이티브 JIRA taskList가 아닌 일반 bulletList로 변환합니다. 체크박스 UI는 제공되지 않지만 텍스트로 상태가 표시됩니다.

**업데이트 방법**: 기존 description 원본을 마크다운으로 재구성한 후, 체크리스트를 하단에 추가하여 `--body`로 전체 교체합니다.

```bash
jira issue edit <TICKET> --no-input --body "$(cat <<'MDEOF'
<기존 description 내용을 마크다운으로 재구성>

---

## 암호화 마이그레이션 진행 상황

### Step 1: 준비 (DDL + db-cipher 적용)
- [ ] JIRA 작업 범위 댓글 작성
- [ ] data-schema DDL PR
- [ ] <repo별> db-cipher 적용 PR

### Step 2: 데이터 마이그레이션
- [ ] Step 1 PR 전체 머지 확인
- [ ] 마이그레이션 스크립트 생성 및 실행 (dev + prod)

### Step 3: 정리 (fallback 제거 + DDL 제약 변경)
- [ ] fallback 제거 PR
- [ ] data-schema DDL 제약 변경 PR
- [ ] 완료 처리

### Step 4: 원본 컬럼 제거
- [ ] 원본 컬럼 참조 완전 제거 PR
- [ ] data-schema DDL 컬럼 DROP PR
MDEOF
)"
```

**Step 문서 생성 완료 후**, 첫 번째 미완료 항목(Step 1)부터 진행합니다.

---

## Step 진행 규칙

1. Step 문서에서 첫 번째 `- [ ]` 항목을 찾아 해당 절차를 실행
2. 항목 완료 시 → Step 문서의 `- [ ]`를 `- [x]`로 업데이트 + PR URL 등 결과 기록
3. 각 Step의 마지막 항목 완료 시 → JIRA 설명란의 해당 Step 체크리스트도 업데이트
   - **JIRA 싱크 방법**: 로컬 Step 문서의 `[x]`/`[ ]` 상태를 기준으로 JIRA description 전체를 `jira issue edit --no-input --body`로 재작성
   - description 원본 내용(테이블 정보 등) + 체크리스트를 마크다운으로 구성하여 전달
   - 완료된 Step 제목에 ✅ 표시 추가 (예: `### Step 1: 준비 ✅`)
4. Step 간 전환 시 사용자에게 안내하고 확인을 받은 후 진행

---

## Step 1: 준비 (DDL + db-cipher 적용)

### JIRA 작업 범위 댓글 작성

아래 형식으로 댓글을 작성하세요:

```bash
cat <<'EOF' | jira issue comment add <TICKET> --template -
> 마이그레이션 진행 순서(예상)

1. DB 암호화 컬럼 생성
   1. 암호화 컬럼은 암호화 여부를 확인할 수 있도록 접두사 추가
      - 일반 컬럼: `encrypted_` + 컬럼명
      - JSON 컬럼: `partially_encrypted_` + 컬럼명
   2. 초기 컬럼 세팅은 nullable로 세팅
2. 암호화 모듈 적용
   1. INSERT, UPDATE 작업이 있는 부분 우선적으로 마이그레이션
   2. 스크립트를 통해 마이그레이션 대상 컬럼 데이터와 암호화 컬럼 데이터 싱크
   3. SELECT 작업이 있는 부분 마이그레이션
3. 기능 이상 여부 확인 및 기존 컬럼 제거

> 테이블 의존성 파악

- INSERT
  - <repo-name> (<파일 경로 링크>)
- UPDATE
  - <repo-name> (<파일 경로 링크>)
- SELECT
  - <repo-name> (<파일 경로 링크>)
EOF
```

GitHub 파일 링크 형식: `https://github.com/teamdable/<repo>/blob/<default-branch>/<path>#L<line>`

완료 후 → Step 문서에서 `- [ ] JIRA 작업 범위 댓글 작성`을 `- [x]`로 업데이트

---

### data-schema DDL PR 생성 (Agent 위임)

**Agent를 사용하여 DDL PR을 생성합니다.**

Agent prompt에 포함할 정보:

- Step 문서의 **대상 정보** 전체 (서버, DB, 테이블, 패턴, 컬럼 목록)
- data-schema 로컬 경로 (없으면 clone 지시)
- DDL 수정 규칙:
  - Pattern A: `` `partially_encrypted_<컬럼명>` <타입> CHARACTER SET utf8 COMMENT '<설명>' ``
  - Pattern B: `` `encrypted_<컬럼명>` text CHARACTER SET utf8 COMMENT '<설명>' ``
  - mediumtext/longtext에 DEFAULT 사용 불가 (MySQL 5.x 제약)
  - nullable로 설정
  - TODO 주석 추가: `-- TODO: 애플리케이션 배포 및 마이그레이션 완료 후 NOT NULL 제약 추가`
- 브랜치: `feature/<TICKET>/add_encrypted_column`
- 커밋 메시지: `feature: add encrypted column(s) for <테이블명>`
- PR 제목: `WIP: [<TICKET>] add encrypted column(s) for <테이블명>`
- `--assignee @me` 옵션 포함

Agent 완료 후 → Step 문서에서 `- [ ] data-schema DDL PR:`을 `- [x] data-schema DDL PR: <PR URL>`로 업데이트

---

### 의존 Repository별 db-cipher 적용 (Agent 위임)

**각 의존 repo에 대해 Agent를 사용하여 db-cipher 적용 + PR을 생성합니다.**
독립적인 repo는 **병렬로 Agent를 실행**할 수 있습니다.

#### Agent prompt 템플릿

각 Agent에게 아래 정보를 모두 전달하세요:

````
## 작업 개요
<TICKET> 암호화 마이그레이션 — <repo-name>에 db-cipher 적용

## 대상 정보
(Step 문서의 대상 정보 전체를 복사)

## 코드 수정 주의사항
(본 Skill 상단의 "코드 수정 시 주의사항" 6개 항목을 복사)

## 작업 범위
- repo 경로: <repo-path>
- 카테고리: <INSERT/UPDATE/SELECT 등>
- 대상 파일: <파일 목록>

## 작업 절차

### 1. 브랜치 생성
cd <repo-path>
git checkout <default-branch> && git pull
git checkout -b feature/<TICKET>/apply_db_cipher

### 2. 모듈 시스템 감지
- package.json의 "type": "module" 여부
- 기존 .js 파일의 import/require 사용 패턴

### 3. @teamdable/db-cipher 의존성 확인 및 설치
npm ls @teamdable/db-cipher 2>/dev/null
없으면: npm install @teamdable/db-cipher

### 4. 보일러플레이트 코드 생성

**lib/cipher/db_cipher.js** (이미 존재하면 skip):
인스턴스 기반 singleton 패턴 사용. static 메서드 금지.

CJS 버전:
```js
const { DbCipherImpl } = require('@teamdable/db-cipher');

class DbCipherWrapper {
  #instance;

  async init() {
    this.#instance = await DbCipherImpl.init(process.env.NODE_ENV === 'production');
  }

  getInstance() {
    if (!this.#instance) {
      throw new Error('DbCipher not initialized. Call dbCipherWrapper.init() first.');
    }
    return this.#instance;
  }
}

const dbCipherWrapper = new DbCipherWrapper();

module.exports = { dbCipherWrapper };
````

ESM/TypeScript 버전:

```ts
import { DbCipherImpl } from "@teamdable/db-cipher";

class DbCipherWrapper {
  private _instance: Awaited<ReturnType<typeof DbCipherImpl.init>>;

  async init(): Promise<void> {
    this._instance = await DbCipherImpl.init(
      process.env.NODE_ENV === "production",
    );
  }

  getInstance() {
    if (!this._instance) {
      throw new Error(
        "DbCipher not initialized. Call dbCipherWrapper.init() first.",
      );
    }
    return this._instance;
  }
}

export const dbCipherWrapper = new DbCipherWrapper();
```

**앱 진입점에서 init() 호출 필수**:

- 서버: listen() 전 또는 기존 Promise.all 초기화 배열에 추가
- 배치/cron job: run() 함수 최상단에서 `await dbCipherWrapper.init()`
- Lambda: handler 함수 최상단에서 호출

**lib/cipher/<테이블명\_소문자>\_table_cipher.js**:
`dbCipherWrapper.getInstance()`를 통해 cipher 인스턴스를 동기적으로 획득.
(Pattern A/B에 맞는 템플릿 제공)

### 5. 쿼리 코드 수정

**Pattern B INSERT/UPDATE 수정:**

- 암호화 대상 컬럼 값을 encrypt 후 encrypted\_\* 컬럼에 이중 쓰기
- INSERT: encrypted\_\* 컬럼 및 값 추가
- UPDATE SET: encrypted\_\* = ? 추가
- 함수가 동기이면 async로 전환

**Pattern B SELECT 수정:**

- SELECT \_: encrypted\_\_ 자동 포함되므로 복호화 로직만 추가
- 특정 컬럼 SELECT: encrypted\_\* 컬럼 명시적 추가
- 기존 동기 직렬화 함수가 있으면:
  → 별도 async 복호화 헬퍼 생성
  → decryptUserRow(row): encrypted\_\_ 존재 시 복호화, delete encrypted\_\_
  → decryptAndDeserialize(row): decryptUserRow + 기존 deserialize 조합
- .then(rows.map(deserialize)) → Promise.all(rows.map(decryptAndDeserialize))

**Pattern A INSERT/UPDATE 수정:**

- encryptBody() 호출 후 partially_encrypted\_\* 컬럼에 JSON.stringify 값 추가

**Pattern A SELECT 수정:**

- partially_encrypted\_\* 존재 시 JSON.parse → decryptPartiallyEncryptedBody
- 없으면 기존 컬럼 값 사용 (fallback)

### 6. 단위 테스트 생성

기존 테스트 디렉토리/패턴을 확인하여 TableCipher 테스트 작성

### 7. 커밋 및 PR

- git add 및 커밋
- git push -u origin feature/<TICKET>/apply_db_cipher
- gh pr create --title "WIP: [<TICKET>] apply db-cipher to <테이블명>" --assignee @me
- **PR URL을 반드시 결과에 포함**

```

#### Agent 실행 및 결과 처리

1. 독립적인 repo는 **병렬로 Agent 실행** (run_in_background=true)
2. 각 Agent 완료 시 → Step 문서에서 해당 repo의 `- [ ]`를 `- [x] <repo> db-cipher 적용 PR: <PR URL>`로 업데이트
3. 모든 Agent 완료 후 → 사용자에게 결과 요약 제공

---

### Step 1 완료 처리

모든 항목이 `[x]`가 되면:

1. Step 문서에 완료 표시
2. JIRA 설명란의 Step 1 체크리스트를 모두 체크로 업데이트
3. 사용자에게 안내:
```

Step 1 완료. PR 머지 후 Step 2를 진행하려면: /dable-encrypt <TICKET>

````

---

## Step 2: 데이터 마이그레이션

### Step 1 PR 머지 확인

AskUserQuestion으로 확인:

- **Step 1 PR 전체 머지 완료** — 진행합니다
- **아직 미완료** — Step 1 PR 머지 후 다시 실행하세요

미완료 시 중단.

완료 확인 후 → Step 문서에서 `- [ ] Step 1 PR 전체 머지 확인`을 `- [x]`로 업데이트

### 마이그레이션 환경 확인

**db-cipher 로컬 경로 확인**:

```bash
DB_CIPHER_PATH=$(find ~/dev -maxdepth 3 -type d -name "db-cipher" 2>/dev/null | head -1)
if [ -z "$DB_CIPHER_PATH" ]; then
gh repo clone teamdable/db-cipher /tmp/db-cipher
DB_CIPHER_PATH="/tmp/db-cipher"
fi
````

**mysql2 의존성 확인**:

```bash
cd $DB_CIPHER_PATH && npm ls mysql2 2>/dev/null
```

없으면 사용자에게 설치 안내: `npm install mysql2`

**.env 파일 안내**:

사용자에게 `.env` 파일 템플릿을 제공하고 직접 생성하도록 안내:

```
DB_HOST=
DB_USER=
DB_PASSWORD=
DB_PORT=3306
BATCH_SIZE=1000
NODE_ENV=production
```

실행 시 `node --env-file=.env <script>` 형태로 사용 (Node.js 20.6+).

AskUserQuestion으로 확인 (하나씩 질문):

1. **DB 접속 방식**: .env 파일 / SSH 터널 / 직접 접속
2. **실행 환경**: dev → prod 순차 실행 (기본)
3. **batch size**: 기본값 1000
4. **dry-run 먼저 실행 여부**: 기본 Yes

### 마이그레이션 스크립트 생성 (Agent 위임)

**Agent를 사용하여 마이그레이션 스크립트를 생성합니다.**

Agent prompt에 포함할 정보:

- Step 문서의 **대상 정보** 전체
- db-cipher 경로
- Pattern A/B에 따른 스크립트 템플릿:

**Pattern A**: encryptFields로 JSON 부분 암호화, 단일 신규 컬럼에 JSON.stringify
**Pattern B**: encrypt로 각 컬럼 개별 암호화, COLUMN_PAIRS 배열 기반

공통 구조:

- mysql2/promise로 DB 연결
- BATCH_SIZE 환경변수 (기본 1000)
- DRY_RUN 환경변수 지원
- 진행률 로깅
- 에러 카운트 및 개별 에러 로깅
- PK 기반 WHERE 절
- **LIMIT에 prepared statement 파라미터(`?`) 사용 금지** — mysql2에서 `Incorrect arguments to mysqld_stmt_execute` 에러 발생. `LIMIT ${BATCH_SIZE}`로 직접 삽입

스크립트 경로: `migrate-<테이블명_소문자>.js` (현재 작업 디렉토리)

Agent 완료 후 → Step 문서에서 `- [ ] 마이그레이션 스크립트 생성`을 `- [x]`로 업데이트

### dev/prod 순차 실행

**dev DB 먼저 실행 → 검증 → prod DB 실행** 순서로 진행합니다.

1. **dev dry-run**: `DRY_RUN=true node --env-file=.env migrate-<테이블명>.js`
2. dry-run 결과 확인 (대상 건수, 에러 건수)
3. **dev 실제 실행**: `node --env-file=.env migrate-<테이블명>.js`
4. dev 복호화 검증 (샘플 조회)
5. 사용자에게 prod 호스트 변경 안내
6. **prod dry-run** → **prod 실제 실행** → **prod 복호화 검증**

각 단계 완료 시 Step 문서 업데이트.

### 손상 데이터 처리

dry-run에서 에러가 발생한 경우 (예: JSON.parse 실패):

1. 에러 행의 원본 데이터를 조회하여 사용자에게 보여줌
2. AskUserQuestion으로 처리 방안 선택:
   - **skip** — 해당 행은 건너뛰고 나머지 실행 (NULL 유지)
   - **regex 추출 후 암호화** — 손상된 JSON에서 민감 필드를 regex로 추출하여 암호화
   - **빈 값으로 채우기** — 암호화 컬럼을 `'{}'`으로 채워 NULL이 아니게 만듦
3. skip한 경우, 실제 마이그레이션 완료 후 별도 보조 스크립트로 처리

**regex 추출 패턴** (JSON이 잘린 경우에도 앞부분 필드는 추출 가능):

```js
function extractFields(raw) {
  const obj = {};
  const regex = /"(\w+)":"([^"]*)"/g;
  let match;
  while ((match = regex.exec(raw)) !== null) {
    obj[match[1]] = match[2];
  }
  return obj;
}
```

### Step 2 완료 처리

1. Step 문서 업데이트 완료 (dev + prod 결과 기록)
2. JIRA 설명란의 Step 2 체크리스트 업데이트
3. JIRA 댓글에 마이그레이션 결과 작성 (대상 건수, 성공/실패, 검증 결과)
4. 안내: `Step 2 완료. Step 3를 진행하려면: /dable-encrypt <TICKET>`

---

## Step 3: 정리 (fallback 제거 + DDL 제약 변경)

### 사전 확인

AskUserQuestion으로 체크리스트 확인:

- **마이그레이션 데이터 검증 완료** — 신규 컬럼에 NULL/빈값이 없는지 확인했습니까?

미완료 시 중단하고 Step 2 검증을 먼저 완료하도록 안내.

완료 확인 후 → Step 문서에서 `- [ ] 마이그레이션 데이터 검증`을 `- [x]`로 업데이트

### 의존 Repository 코드 정리 (Agent 위임)

**각 의존 repo에 대해 Agent를 사용하여 fallback 제거 + PR을 생성합니다.**
독립적인 repo는 **병렬로 Agent를 실행**할 수 있습니다.

#### Agent prompt 템플릿

```
## 작업 개요
<TICKET> 암호화 마이그레이션 Phase 3 — <repo-name>에서 평문 컬럼 fallback 제거

## 대상 정보
(Step 문서의 대상 정보 전체를 복사)

## 코드 수정 주의사항
(본 Skill 상단의 "코드 수정 시 주의사항" 6개 항목을 모두 복사 — 특히 4, 5, 6번 중요)

## 작업 범위
- repo 경로: <repo-path>
- 대상 파일: <파일 목록>

## 작업 절차

### 1. 브랜치 생성
cd <repo-path>
git checkout <default-branch> && git pull
git checkout -b feature/<TICKET>/remove_plaintext_column

### 2. fallback 로직 제거

**Pattern B:**
- INSERT 이중 쓰기 제거: 원본 컬럼이 NOT NULL이면 `'{}'` 또는 빈 문자열 placeholder 쓰기. nullable이면 NULL.
- UPDATE 이중 쓰기 제거: 동일하게 placeholder 또는 NULL.
- SELECT fallback 제거:
  Before: if (row.encrypted_xxx) { decrypt } else { use plaintext } (fallback)
  After: row.xxx = await decrypt(row.encrypted_xxx); delete row.encrypted_xxx;

**Pattern A:**
- INSERT 이중 쓰기 제거: 원본 컬럼이 NOT NULL이면 `'{}'` placeholder 쓰기. 실제 데이터는 partially_encrypted_* 에만 저장.
- SELECT fallback 제거: if 분기 없이 항상 partially_encrypted 에서 복호화

### 3. 에러 핸들링 정책 유지
- 기존 코드의 에러 핸들링 패턴(try-catch, logger, fallback 등)을 확인
- 복호화 코드에도 **동일한 패턴** 적용
- 예: 기존에 JSON.parse 실패 시 빈 객체 fallback이 있었다면, decrypt 실패 시에도 동일하게 처리

### 4. LIKE 검색 대상 전환
- 원본 컬럼에 대한 LIKE 검색이 있는지 확인
- 비민감 필드 LIKE 검색: 암호화 컬럼으로 전환 (비민감 필드는 평문 유지)
- 민감 필드 LIKE 검색: 암호화 후 불가 — TODO 주석 유지/추가

### 5. 테스트 업데이트
- fallback 테스트 케이스 제거, 암호화 컬럼 직접 사용 테스트로 교체
- 테스트 mock 데이터의 원본 컬럼 값을 실제 운영 값('{}' 등)으로 통일

### 6. 커밋 및 PR
- git push -u origin feature/<TICKET>/remove_plaintext_column
- gh pr create --title "WIP: [<TICKET>] remove plaintext column fallback from <테이블명>" --assignee @me
- **PR URL을 반드시 결과에 포함**
```

#### Agent 실행 및 결과 처리

1. 독립적인 repo는 **병렬로 Agent 실행** (run_in_background=true)
2. 각 Agent 완료 시 → Step 문서 업데이트
3. 모든 Agent 완료 후 → 사용자에게 결과 요약 제공

---

### data-schema DDL 제약 변경 (Agent 위임)

**이 단계는 코드 정리 PR과 동시에 진행 가능하나, 배포는 반드시 앱 PR 배포 후에 적용해야 합니다.**

Agent에게 위임:

- DDL 파일에서 두 가지 변경:
  1. **원본 컬럼**: `NOT NULL` 제거 → nullable로 변경
  2. **암호화 컬럼**: `NOT NULL` 제약 추가 + TODO 주석 제거
- 브랜치: `feature/<TICKET>/update_ddl_constraints`
- 커밋 메시지: `feature: update <테이블명> DDL — <원본컬럼> nullable, <암호화컬럼> NOT NULL`
- PR 제목: `WIP: [<TICKET>] update <테이블명> DDL constraints`
- `--assignee @me` 옵션 포함
- **PR description에 배포 순서 명시**: "이 DDL 변경은 앱 코드 PR 배포 완료 후에 적용해야 합니다."

---

### Step 3 완료 처리

1. Step 문서의 모든 항목을 `[x]`로 확인
2. JIRA 설명란의 Step 3 체크리스트 업데이트 (전체 완료)
3. JIRA 댓글에 완료 보고
4. Step 문서에서 `- [ ] JIRA 완료 처리`를 `- [x]`로 업데이트
5. 사용자에게 안내:

   ```
   Step 3 완료. 앱 PR 배포 후 DDL PR을 적용하세요.
   배포 순서: 앱 PR 배포 → DDL PR 적용
   Step 4 (원본 컬럼 제거)를 진행하려면: /dable-encrypt <TICKET>
   ```

---

## Step 4: 원본 컬럼 제거

### 사전 확인

AskUserQuestion으로 확인:

- **Step 3 PR 전체 머지 및 배포 완료** — DDL 제약 변경까지 적용되었습니까?

미완료 시 중단.

### 의존 Repository 원본 컬럼 참조 제거 (Agent 위임)

**각 의존 repo에서 원본 컬럼에 대한 모든 참조를 제거합니다.**
독립적인 repo는 **병렬로 Agent를 실행**할 수 있습니다.

#### Agent prompt 템플릿

```
## 작업 개요
<TICKET> 암호화 마이그레이션 Phase 4 — <repo-name>에서 원본 컬럼 참조 완전 제거

## 대상 정보
(Step 문서의 대상 정보 전체를 복사)

## 작업 범위
- repo 경로: <repo-path>
- 대상 파일: <파일 목록>

## 작업 절차

### 1. 브랜치 생성
cd <repo-path>
git checkout <default-branch> && git pull
git checkout -b feature/<TICKET>/drop_plaintext_column

### 2. 원본 컬럼 참조 제거
- SELECT 쿼리에서 원본 컬럼 제거 (FIELDS 배열, 명시적 SELECT 목록 등)
- INSERT/UPDATE에서 원본 컬럼 placeholder(`'{}'`) 쓰기 제거
- INSERT SQL에서 원본 컬럼명 및 해당 `?` 제거
- UPDATE SQL에서 원본 컬럼 SET 절 제거
- 관련 import/변수가 unused가 되면 함께 제거
- lint 실행하여 unused 경고 확인 및 정리

### 3. 테스트 업데이트
- 테스트에서 원본 컬럼 참조 제거
- mock 데이터에서 원본 컬럼 제거

### 4. 커밋 및 PR
- git add 및 커밋
- 커밋 메시지: `feature: remove <원본컬럼> column references from <테이블명>`
- git push -u origin feature/<TICKET>/drop_plaintext_column
- gh pr create --title "WIP: [<TICKET>] remove <원본컬럼> column references from <테이블명>" --assignee @me
- **PR URL을 반드시 결과에 포함**
```

#### Agent 실행 및 결과 처리

1. 독립적인 repo는 **병렬로 Agent 실행** (run_in_background=true)
2. 각 Agent 완료 시 → Step 문서 업데이트
3. 모든 Agent 완료 후 → 사용자에게 결과 요약 제공

---

### data-schema DDL 원본 컬럼 DROP (Agent 위임)

**⚠️ 위 코드 PR이 모두 배포된 후에만 진행합니다.**

AskUserQuestion으로 확인:

- **코드 PR 전체 배포 완료** — 진행합니다
- **나중에 수동 진행** — 이 단계를 건너뜁니다

Agent에게 위임:

- DDL 파일에서 원본 컬럼 정의 제거
- 브랜치: `feature/<TICKET>/drop_plaintext_column`
- 커밋 메시지: `feature: drop <원본컬럼> column from <테이블명>`
- PR 제목: `WIP: [<TICKET>] drop <원본컬럼> column from <테이블명>`
- `--assignee @me` 옵션 포함

### Step 4 완료 처리

1. Step 문서의 모든 항목을 `[x]`로 확인
2. JIRA 설명란 전체 완료 업데이트
3. JIRA 댓글에 최종 완료 보고
4. 최종 요약 출력:

   ```
   ## 암호화 마이그레이션 전체 완료

   Step 문서: encrypt-plan-<TICKET>.md
   모든 Step이 완료되었습니다.
   ```
