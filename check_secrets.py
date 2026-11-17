#!/usr/bin/env python3
"""公開される public/ と、リポジトリに保存される data/ に
楽天のアプリケーションID・アクセスキーが含まれていないか調べる。
見つかったら失敗（終了コード1）にして、公開とコミットを止める。"""
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
secrets = [v for v in (os.environ.get("RAKUTEN_APP_ID"), os.environ.get("RAKUTEN_ACCESS_KEY")) if v and len(v) >= 8]
patterns = [re.compile(r"accessKey\s*[=:]\s*[\"']?[A-Za-z0-9_\-]{8,}"),
            re.compile(r"applicationId\s*[=:]\s*[\"']?[A-Za-z0-9_\-]{8,}")]

bad = []
for folder in ("public", "data"):
    for path in (ROOT / folder).rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(s in text for s in secrets) or any(p.search(text) for p in patterns):
            bad.append(str(path.relative_to(ROOT)))

if bad:
    print("楽天の認証情報らしき文字列が見つかったため中止します:", *bad, sep="\n  ")
    sys.exit(1)
print(f"認証情報の漏れチェックOK（{'実キーで照合' if secrets else 'パターンのみで照合'}）")
