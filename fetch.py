#!/usr/bin/env python3
"""楽天市場商品検索API（2026年新仕様）から商品を取得し、data/ に保存する。

必要な環境変数（GitHub Secrets に登録）:
  RAKUTEN_APP_ID      アプリケーションID（UUID形式）
  RAKUTEN_ACCESS_KEY  アクセスキー
  RAKUTEN_AFFILIATE_ID 楽天アフィリエイトID
  SITE_URL            （任意）楽天ウェブサービスに登録したサイトURL。未設定なら config.json の site_url

使い方:
  python fetch.py          本番取得
  python fetch.py --demo   API を使わずサンプルデータで動作確認
"""
import datetime as dt
import json
import os
import pathlib
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
API = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/{ver}"
JST = dt.timezone(dt.timedelta(hours=9))
KEEP_DAYS = 120


def load_cfg():
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def api_get(params, cfg, site_url):
    url = API.format(ver=cfg["api_version"]) + "?" + urllib.parse.urlencode(params)
    origin = "/".join(site_url.split("/")[:3])
    headers = {
        "Referer": site_url,
        "Origin": origin,
        "accessKey": params["accessKey"],
        "User-Agent": "rakuten-auto-site/1.0",
    }
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            for secret in (params["applicationId"], params["accessKey"]):
                if secret:
                    body = body.replace(secret, "***")
            if e.code == 429 or e.code >= 500:
                wait = 3 * (attempt + 1)
                print(f"  HTTP {e.code}、{wait}秒待って再試行", file=sys.stderr)
                time.sleep(wait)
                continue
            raise SystemExit(f"楽天APIエラー HTTP {e.code}: {body}\n"
                             "→ applicationId / accessKey / 登録サイトURL(Referer) を確認してください。")
    raise SystemExit("楽天APIが応答しません（再試行上限）")


def first_image(it):
    imgs = it.get("mediumImageUrls") or []
    if not imgs:
        return ""
    url = imgs[0]["imageUrl"] if isinstance(imgs[0], dict) else imgs[0]
    return url.split("?")[0] + "?_ex=300x300"


def normalize(it):
    return {
        "code": it.get("itemCode", ""),
        "name": it.get("itemName", "").strip(),
        "price": int(it.get("itemPrice") or 0),
        "url": it.get("affiliateUrl") or it.get("itemUrl", ""),
        "image": first_image(it),
        "review_avg": float(it.get("reviewAverage") or 0),
        "review_count": int(it.get("reviewCount") or 0),
        "shop": it.get("shopName", ""),
        "postage_included": it.get("postageFlag") == 0,
        "point_rate": int(it.get("pointRate") or 1),
    }


def fetch_theme(theme, cfg, creds, site_url):
    items = []
    for page in (1, 2):
        params = {
            "applicationId": creds["app_id"],
            "accessKey": creds["access_key"],
            "affiliateId": creds["affiliate_id"],
            "format": "json",
            "formatVersion": 2,
            "keyword": theme["keyword"],
            "sort": "-reviewCount",
            "hits": 30,
            "page": page,
            "availability": 1,
            "imageFlag": 1,
        }
        if theme.get("min_price"):
            params["minPrice"] = theme["min_price"]
        if theme.get("genre_id"):
            params["genreId"] = theme["genre_id"]
        res = api_get(params, cfg, site_url)
        items += [normalize(x.get("Item", x)) for x in res.get("Items", [])]
        time.sleep(1.6)  # 新APIは連続アクセスに厳しいので間隔をあける
    return items


def demo_theme(theme):
    rnd = random.Random(theme["slug"] + dt.date.today().isoformat())
    base = random.Random(theme["slug"])
    out = []
    for i in range(40):
        price = base.randrange(10, 80) * 100 - 20
        out.append({
            "code": f"demo:{theme['slug']}-{i}",
            "name": f"【サンプル】{theme['title']} 商品{i + 1} 人気モデル",
            "price": price - (rnd.choice([0, 0, 0, 300, 500]) if price > 1000 else 0),
            "url": "https://www.rakuten.co.jp/",
            "image": "",
            "review_avg": round(base.uniform(3.4, 4.9), 2),
            "review_count": base.randrange(0, 3000),
            "shop": f"サンプルショップ{base.randrange(1, 9)}",
            "postage_included": base.random() > 0.4,
            "point_rate": base.choice([1, 1, 2, 5, 10]),
        })
    return out


def main():
    demo = "--demo" in sys.argv
    cfg = load_cfg()
    creds = {
        "app_id": os.environ.get("RAKUTEN_APP_ID", ""),
        "access_key": os.environ.get("RAKUTEN_ACCESS_KEY", ""),
        "affiliate_id": os.environ.get("RAKUTEN_AFFILIATE_ID", ""),
    }
    site_url = os.environ.get("SITE_URL") or cfg["site_url"]
    if not demo and not all(creds.values()):
        raise SystemExit("RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY / RAKUTEN_AFFILIATE_ID を設定してください（動作確認だけなら --demo）")

    today = dt.datetime.now(JST).date().isoformat()
    ng = cfg.get("ng_words", [])
    snapshot = {"date": today, "demo": demo, "themes": {}}
    for theme in cfg["themes"]:
        print(f"取得中: {theme['title']}")
        raw = demo_theme(theme) if demo else fetch_theme(theme, cfg, creds, site_url)
        seen, items = set(), []
        for it in raw:
            if not it["code"] or it["code"] in seen or any(w in it["name"] for w in ng):
                continue
            seen.add(it["code"])
            items.append(it)
        snapshot["themes"][theme["slug"]] = items
        print(f"  {len(items)}件")

    DATA.mkdir(exist_ok=True)
    (DATA / "latest.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")

    # 価格履歴（値下がり検出用）
    hist_path = DATA / "prices.json"
    hist = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else {}
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=KEEP_DAYS)).isoformat()
    for items in snapshot["themes"].values():
        for it in items:
            hist.setdefault(it["code"], {})[today] = it["price"]
    hist = {k: {d: p for d, p in v.items() if d >= cutoff} for k, v in hist.items()}
    hist = {k: v for k, v in hist.items() if v}
    hist_path.write_text(json.dumps(hist, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("保存しました: data/latest.json, data/prices.json")


if __name__ == "__main__":
    main()
