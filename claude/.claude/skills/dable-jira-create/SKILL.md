---
name: dable-jira-create
model: opus
disable-model-invocation: true
allowed-tools: Bash(jira issue create:*), Bash(jira me:*), Bash(jira project list:*), Bash(cat > /tmp/jira-*), AskUserQuestion, Read, Glob, Grep
description: 세션 대화 내용을 요약하여 JIRA 카드 생성
---

## Your Task

현재 세션의 대화 내용을 기반으로 JIRA 카드를 생성하세요.

### Step 1: 세션 내용 분석

세션에서 논의된 내용을 분석하세요. 다음 정보가 충분한지 판단합니다:

- **무엇을**: 작업/공유/논의 대상
- **왜**: 목적 또는 배경
- **핵심 내용**: 세부 사항

정보가 부족하면 AskUserQuestion으로 부족한 항목을 물어보세요. 추측하지 마세요.

### Step 2: 카드 메타데이터 결정

Arguments가 있으면 프로젝트 키로 사용하세요. 없으면 AskUserQuestion으로 프로젝트를 물어보세요.

다음 항목을 결정하세요:

- **프로젝트**: arguments 또는 사용자 입력
- **제목**: 세션 내용에서 추출 (간결하게)
- **이슈 타입**: 기본값 `작업`
- **라벨**: 세션 맥락에서 추론 (없으면 생략)
- **담당자**: `jira me` 결과 사용 (email 형태이므로 `-a` 플래그에 그대로 전달)

### Step 3: 요약 작성

세션 내용을 JIRA wiki markup으로 요약하세요.

작성 원칙:

- 세션의 논의 흐름이 아닌, **결론과 핵심 내용** 중심으로 정리
- 제목(h2, h3)과 목록(\*, --)으로 구조화
- 코드/설정이 포함된 경우 `{code}` 또는 `{noformat}` 블록 사용
- 불필요한 대화 맥락은 제거

### Step 4: 사용자 확인

제목과 요약 내용을 보여준 후 AskUserQuestion으로 선택지를 제공하세요:

- **카드 생성** — 바로 JIRA 카드를 생성합니다
- **수정 후 생성** — 수정할 부분을 자유 입력받아 반영 후 다시 미리보기를 제공합니다

### Step 5: JIRA 카드 생성

`-T` 옵션으로 body를 파일에서 읽어야 interactive prompt를 우회할 수 있습니다.

```bash
# body를 임시 파일에 저장
cat > /tmp/jira-create-body.md <<'EOF'
<요약 내용 — wiki markup>
EOF

# 카드 생성 (--no-input 필수)
jira issue create -p<PROJECT> -t"작업" \
  -s"<제목>" \
  -a"<담당자>" \
  -l"<라벨>" \
  --no-input \
  -T /tmp/jira-create-body.md
```

완료 후 생성된 JIRA 카드 링크를 제공하세요.

### 주의사항

- 스프린트 할당은 하지 마세요
- 사용자가 명시하지 않은 필드(priority, component 등)는 기본값을 사용하세요
