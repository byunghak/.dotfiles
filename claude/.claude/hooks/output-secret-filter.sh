#!/bin/bash
# Output Secret Filter - PostToolUse Hook
# 도구 실행 결과에서 시크릿을 감지하여 마스킹
#
# Hook trigger: PostToolUse (모든 도구)
# Exit codes: 0 = 항상 허용 (출력만 수정)
#
# 동작 방식:
#   - stdin으로 도구 실행 결과 JSON 수신
#   - tool_response 안의 모든 문자열 값에서 시크릿 패턴 감지
#   - 감지 시 hookSpecificOutput.updatedToolOutput 으로 마스킹된 tool_response 를 돌려준다 (Claude가 마스킹된 값만 봄)
#     일반 stdout 은 도구 출력을 바꾸지 못하고, updatedToolOutput 은 도구 출력과 구조가 같아야 적용되므로
#     tool_response 구조는 그대로 두고 문자열 값만 바꾼다
#   - 마스킹 발생 시 security.log에 기록 (값 자체는 기록하지 않음)

# stdin에서 JSON 읽기
INPUT=$(cat)

# 환경변수로 전달하여 Python에서 처리
export _FILTER_INPUT="$INPUT"
export _SECURITY_LOG="$HOME/.claude/security.log"

python3 <<'FILTER_SCRIPT'
import os
import sys
import json
import re
from datetime import datetime

input_json = os.environ.get("_FILTER_INPUT", "")
security_log = os.environ.get("_SECURITY_LOG", "")

if not input_json:
    sys.exit(0)

try:
    data = json.loads(input_json)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)

# PostToolUse 입력의 도구 출력 필드는 tool_response 다 (예전 코드는 tool_result 를 읽어 실제로는 한 번도 동작하지 않았다)
tool_response = data.get("tool_response")
if tool_response is None:
    sys.exit(0)

# 마스킹 패턴 정의 (패턴, 설명)
SECRET_PATTERNS = [
    # API 키 패턴
    (r'\bsk-[a-zA-Z0-9_-]{20,}\b', "OpenAI API Key"),
    (r'\bsk-proj-[a-zA-Z0-9_-]{20,}\b', "OpenAI Project Key"),
    (r'\bAKIA[A-Z0-9]{16,}\b', "AWS Access Key"),
    (r'\bxoxb-[a-zA-Z0-9-]{20,}\b', "Slack Bot Token"),
    (r'\bxoxp-[a-zA-Z0-9-]{20,}\b', "Slack User Token"),
    (r'\bghp_[a-zA-Z0-9]{36,}\b', "GitHub PAT"),
    (r'\bghs_[a-zA-Z0-9]{36,}\b', "GitHub App Token"),
    (r'\bgho_[a-zA-Z0-9]{36,}\b', "GitHub OAuth Token"),
    (r'\bghu_[a-zA-Z0-9]{36,}\b', "GitHub User Token"),
    (r'\bglpat-[a-zA-Z0-9_-]{20,}\b', "GitLab PAT"),
    (r'\bnpm_[a-zA-Z0-9]{36,}\b', "NPM Token"),

    # Bearer/Auth 토큰
    (r'(?i)\bBearer\s+[a-zA-Z0-9_.-]{20,}\b', "Bearer Token"),
    (r'(?i)\btoken=[a-zA-Z0-9_.-]{20,}\b', "Token Parameter"),
    (r'(?i)\bauth=[a-zA-Z0-9_.-]{20,}\b', "Auth Parameter"),
    (r'(?i)\bapi[_-]?key=[a-zA-Z0-9_.-]{20,}\b', "API Key Parameter"),

    # 비밀번호/시크릿 패턴
    (r'(?i)\bpassword=[^\s&]{8,}\b', "Password Parameter"),
    (r'(?i)\bpasswd=[^\s&]{8,}\b', "Password Parameter"),
    (r'(?i)\bsecret=[^\s&]{20,}\b', "Secret Parameter"),

    # 환경변수 값 (KEY=VALUE 형식에서 값 부분)
    (r'(?i)\bAWS_SECRET_ACCESS_KEY=[^\s]{20,}\b', "AWS Secret Key"),
    (r'(?i)\bOPENAI_API_KEY=[^\s]{20,}\b', "OpenAI Key Value"),
    (r'(?i)\bANTHROPIC_API_KEY=[^\s]{20,}\b', "Anthropic Key Value"),
    (r'(?i)\bTELEGRAM_BOT_TOKEN=[^\s]{20,}\b', "Telegram Token Value"),
    (r'(?i)\bGITHUB_TOKEN=[^\s]{20,}\b', "GitHub Token Value"),
    (r'(?i)\bSUPABASE_SERVICE_ROLE_KEY=[^\s]{20,}\b', "Supabase Key Value"),
    (r'(?i)\bDATABASE_URL=[^\s]{20,}\b', "Database URL Value"),

    # Private Key 블록
    (r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', "Private Key"),

    # 긴 Base64 같은 문자열 (컨텍스트 의존)
    (r'(?i)(?:key|secret|token|password|credential|auth)[\s=:]+["\']?[a-zA-Z0-9+/]{40,}={0,2}["\']?', "Potential Base64 Secret"),
]

import base64
import urllib.parse

def decode_layers(text):
    """base64, URL 인코딩을 디코딩하여 숨겨진 시크릿을 탐지"""
    decoded_variants = []
    b64_pattern = re.compile(r'[A-Za-z0-9+/]{20,}={0,2}')
    for m in b64_pattern.finditer(text):
        try:
            decoded = base64.b64decode(m.group(0), validate=True).decode("utf-8", errors="ignore")
            if decoded and len(decoded) >= 10:
                decoded_variants.append(decoded)
        except Exception:
            pass
    try:
        url_decoded = urllib.parse.unquote(text)
        if url_decoded != text:
            decoded_variants.append(url_decoded)
    except Exception:
        pass
    return decoded_variants

def mask_match(original):
    """매칭된 문자열을 마스킹"""
    if len(original) > 16:
        return original[:8] + "***MASKED***" + original[-4:]
    return original[:4] + "***MASKED***"

masked_count = 0
masked_types = []


def mask_text(text):
    """문자열 하나에서 시크릿을 찾아 마스킹한다. 찾은 수와 종류는 전역 집계에 더한다."""
    global masked_count
    masked_output = text

    # 1단계: 원본 텍스트에서 직접 매칭
    for pattern, desc in SECRET_PATTERNS:
        matches = list(re.finditer(pattern, masked_output))
        if matches:
            for match in reversed(matches):
                original = match.group(0)
                masked_output = masked_output[:match.start()] + mask_match(original) + masked_output[match.end():]
                masked_count += 1
            if desc not in masked_types:
                masked_types.append(desc)

    # 2단계: 인코딩 우회 탐지
    decoded_variants = decode_layers(text)
    for decoded_text in decoded_variants:
        for pattern, desc in SECRET_PATTERNS:
            if re.search(pattern, decoded_text):
                b64_pattern = re.compile(r'[A-Za-z0-9+/]{20,}={0,2}')
                for m in b64_pattern.finditer(masked_output):
                    try:
                        d = base64.b64decode(m.group(0), validate=True).decode("utf-8", errors="ignore")
                        if re.search(pattern, d):
                            chunk = m.group(0)
                            masked_output = masked_output[:m.start()] + mask_match(chunk) + masked_output[m.end():]
                            masked_count += 1
                            if desc not in masked_types:
                                masked_types.append(desc)
                            break
                    except Exception:
                        pass
                try:
                    url_decoded = urllib.parse.unquote(masked_output)
                    if url_decoded != masked_output and re.search(pattern, url_decoded):
                        pct_pattern = re.compile(r'(?:%[0-9A-Fa-f]{2}[A-Za-z0-9_.~-]*){5,}')
                        for pm in reversed(list(pct_pattern.finditer(masked_output))):
                            decoded_chunk = urllib.parse.unquote(pm.group(0))
                            if re.search(pattern, decoded_chunk):
                                masked_output = masked_output[:pm.start()] + mask_match(pm.group(0)) + masked_output[pm.end():]
                                masked_count += 1
                                if desc not in masked_types:
                                    masked_types.append(desc)
                except Exception:
                    pass
    return masked_output


def mask_value(value):
    """구조(dict·list)는 그대로 두고 문자열 값만 마스킹한다. updatedToolOutput 은 도구 출력과 구조가 같아야 적용된다."""
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, dict):
        return {key: mask_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [mask_value(item) for item in value]
    return value


masked_response = mask_value(tool_response)

if masked_count > 0:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedToolOutput": masked_response,
        }
    }, ensure_ascii=False))

    # 보안 로그 기록 (마스킹된 값 자체는 기록하지 않음)
    if security_log:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            tool_name = data.get("tool_name", "unknown")
            session_id = data.get("session_id", "unknown")
            log_entry = (
                f"{timestamp} | SECRET_MASKED | tool={tool_name} | "
                f"count={masked_count} | types={','.join(masked_types)} | "
                f"session={session_id}\n"
            )
            with open(security_log, "a") as f:
                f.write(log_entry)
        except (IOError, OSError):
            pass

# 항상 허용 (exit 0)
sys.exit(0)
FILTER_SCRIPT
