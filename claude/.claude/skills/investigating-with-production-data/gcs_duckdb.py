"""GCS parquet 을 내려받지 않고 DuckDB httpfs 로 직접 집계한다.

필요한 컬럼·행 그룹만 range 요청으로 읽으므로, 하루 수백 MB 원천도 집계는 수 초다.
gcloud storage cp 로 받으면 같은 집계에 수 분이 든다.

사용:
  uvx --with duckdb python gcs_duckdb.py \
    'gs://<bucket>/<prefix>/dt=2026-11-0[1-3]/*.parquet' \
    "SELECT dt, count(*) FROM src GROUP BY 1 ORDER BY 1"

- 첫 인자: gs:// 경로 (glob 허용). `src` 뷰로 노출된다
- hive 파티션(dt=, h=)은 컬럼으로 붙는다
- 토큰: gcloud 사용자 인증이 만료됐으면 GCS_TOKEN_CMD 로 바꾼다
  (예: GCS_TOKEN_CMD="gcloud auth application-default print-access-token")
"""

import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.parse
import urllib.request

import duckdb

GLOB_CHARS = re.compile(r"[*?\[]")


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: gcs_duckdb.py <gs://bucket/path-or-glob> <SQL over src>")
    gs_path, sql = sys.argv[1], sys.argv[2]
    token = fetch_token()
    urls = expand(gs_path, token)
    con = connect_gcs(token)
    con.read_parquet(urls, hive_partitioning=True).create_view("src")
    print(f"files: {len(urls)}", file=sys.stderr)
    print(con.sql(sql))


def fetch_token() -> str:
    token_cmd = os.environ.get("GCS_TOKEN_CMD", "gcloud auth print-access-token")
    return subprocess.run(
        shlex.split(token_cmd), check=True, capture_output=True, text=True
    ).stdout.strip()


def expand(gs_path: str, token: str) -> list[str]:
    """HTTP 경로엔 glob 이 없다. 객체 목록은 GCS JSON API 로 받아 fnmatch 로 거른다."""
    if not gs_path.startswith("gs://"):
        raise ValueError(f"expected gs:// path, got {gs_path!r}")
    bucket, _, pattern = gs_path.removeprefix("gs://").partition("/")
    if not GLOB_CHARS.search(pattern):
        return [f"https://storage.googleapis.com/{bucket}/{pattern}"]
    prefix = GLOB_CHARS.split(pattern, maxsplit=1)[0]
    names = [n for n in list_objects(bucket, prefix, token) if fnmatch.fnmatchcase(n, pattern)]
    if not names:
        raise FileNotFoundError(f"no object matches {gs_path}")
    return [f"https://storage.googleapis.com/{bucket}/{n}" for n in names]


def list_objects(bucket: str, prefix: str, token: str) -> list[str]:
    names: list[str] = []
    page_token = ""
    while True:
        query = urllib.parse.urlencode(
            {"prefix": prefix, "fields": "items(name),nextPageToken", "pageToken": page_token}
        )
        req = urllib.request.Request(
            f"https://storage.googleapis.com/storage/v1/b/{bucket}/o?{query}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req) as resp:
            page = json.load(resp)
        names += [item["name"] for item in page.get("items", [])]
        page_token = page.get("nextPageToken", "")
        if not page_token:
            return names


def connect_gcs(token: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    # gs:// 는 HMAC 키가 필요하다. https 경로 + bearer 토큰이면 ADC 만으로 읽힌다
    con.execute(f"CREATE SECRET gcs (TYPE http, BEARER_TOKEN '{token}')")
    return con


if __name__ == "__main__":
    main()
