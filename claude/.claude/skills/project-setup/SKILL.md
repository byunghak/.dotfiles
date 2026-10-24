---
name: project-setup
description: Use when 새 프로젝트(또는 아직 정리되지 않은 프로젝트)에서 Claude Code 를 쓰기 전에 프로젝트 설정(CLAUDE.md·.claude/ rules·agents·skills·hooks·settings)을 전역 설정과 대조해 무엇을 유지·줄이기·추가할지 정해야 할 때. 사용자가 /project-setup <경로> 로 부른다.
argument-hint: <프로젝트 경로>
disable-model-invocation: true
---

# project-setup

전역 설정은 공통 기반이고, 프로젝트 설정은 그 위에 **이 저장소에만 필요한 것**만 더한다.
이 Skill 은 두 범위를 읽고 대조해 **분류표 + diff 초안**을 낸다. 파일은 바꾸지 않는다.

## 읽는 것

| 범위     | 파일                                                                                                                                                                                                        |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 전역     | `~/.claude/CLAUDE.md`, `~/.claude/rules/*.md`(frontmatter `paths:` 포함), `agents/*.md` frontmatter, `skills/*/SKILL.md` frontmatter, `settings.json` 의 hooks·permissions, `~/.claude/settings.local.json` |
| 프로젝트 | `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/{rules,agents,skills,hooks}/`, `.claude/settings*.json`, README, 빌드 설정(Makefile·package.json·go.work·Cargo.toml·pyproject.toml 등 있는 것)                   |
| git      | `git check-ignore -q .claude`(개인용인지), `git log -1`, 활성 브랜치                                                                                                                                        |

- 각 파일의 크기(`wc -w`)를 함께 적는다. 상시 로드(CLAUDE.md, `paths:` 없는 rules)와 호출 시 로드(Skill 본문, agent)를 나눈다.
- 파일을 열어 보지 않은 명령·경로·언어를 결과에 쓰지 않는다. 확인하지 못한 것은 `확인 필요` 로 분류한다.

## 출력 계약

마지막 메시지는 아래 네 절, 이 순서로만 쓴다.

1. **요약** — 3줄. 프로젝트 설정 규모, 가장 큰 축소 후보, 가장 큰 위험(충돌).
2. **분류표** — 한 행에 한 항목.

   | 분류 | 항목 | 위치(file:line) | 근거 | 전역과의 관계 |
   | ---- | ---- | --------------- | ---- | ------------- |
   - 분류는 `유지` · `축소·이동` · `추가` · `충돌` · `확인 필요` 다섯 가지만 쓴다.
   - `전역과의 관계` 는 `중복`(같은 규칙이 전역에 있음) · `예외`(전역과 다르게 정한 것) · `프로젝트 전용` 중 하나.
   - `충돌` 은 실제로 동작이 어긋나는 것만(예: 전역 deny 가 프로젝트 allow 를 무력화, 전역 hook 이 프로젝트 도구와 다르게 포맷).

3. **diff 초안** — `축소·이동`·`추가`·`충돌` 행마다 바뀌는 줄만 unified diff 로. 파일 전체를 다시 쓰지 않는다. 전역 파일을 바꾸는 diff 는 맨 아래에 따로 모으고 "다른 프로젝트에도 영향" 이라고 적는다.
   - diff 안에서 원문을 "(이하 상세)" 처럼 줄이지 않는다. 블록을 통째로 옮기면 diff 대신 `L35-57 → <새 파일>` 처럼 줄 범위와 목적지로 적는다.
4. **확인하지 못한 것** — 추정으로 남긴 판단과, 그것을 확인할 명령.

적용 순서·다음 작업 제안은 이 보고에 넣지 않는다. 사용자가 고를 항목을 물으면 그때 낸다.

## 지키는 것

- 사용자 검토 전에는 파일을 만들거나 고치지 않는다. 권한·hook·plugin·MCP 를 켜지 않는다.
- 전역 규칙을 프로젝트 파일에 복사하는 diff 를 내지 않는다. 같은 내용이 있으면 `축소·이동`(중복) 으로 분류한다.
- 안전 기준(deny·보안 hook)을 프로젝트에서 낮추는 diff 는 `충돌` 로 올리고 이유를 적는다.
- secret·토큰 값은 출력하지 않는다. 회사 정보(org·내부 도메인·버킷)는 공개 dotfiles 가 아니라 `~/.claude/settings.local.json` 이나 프로젝트 개인 설정에 둔다.
