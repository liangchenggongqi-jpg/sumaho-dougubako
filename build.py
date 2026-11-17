#!/usr/bin/env python3
"""data/ の商品データから静的サイトを public/ に生成する。"""
import datetime as dt
import html
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "public"
E = html.escape

CSS = """
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;color:#222;background:#f6f6f4;line-height:1.7}
a{color:#bf0000}header{background:#fff;border-bottom:1px solid #e5e5e5}header .in,main,footer .in{max-width:860px;margin:0 auto;padding:12px 16px}
header a{text-decoration:none;color:#222;font-weight:700;font-size:18px}nav{font-size:13px}nav a{margin-right:12px;color:#555}
.pr{font-size:12px;color:#666;background:#fff8e1;border:1px solid #f0e0a0;padding:6px 10px;border-radius:6px;margin:12px 0}
.demo{background:#fde8e8;border-color:#f3b4b4;color:#900}
h1{font-size:22px;margin:16px 0 4px}h2{font-size:18px;margin:28px 0 8px;border-left:4px solid #bf0000;padding-left:8px}
.guide{background:#fff;border-radius:8px;padding:4px 16px;border:1px solid #e5e5e5}
.card{display:flex;gap:12px;background:#fff;border:1px solid #e5e5e5;border-radius:8px;padding:12px;margin:10px 0}
.card img,.noimg{width:110px;height:110px;object-fit:contain;flex-shrink:0;background:#fafafa;border-radius:6px}
.rank{font-weight:700;color:#bf0000;font-size:14px}.name{font-size:14px;margin:2px 0 6px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.price{font-size:18px;font-weight:700}.meta{font-size:12px;color:#666}.down{color:#0a7d32;font-weight:700;font-size:13px}
.btn{display:inline-block;margin-top:6px;background:#bf0000;color:#fff;text-decoration:none;padding:6px 14px;border-radius:20px;font-size:13px}
.themes{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px}.themes a{background:#fff;border:1px solid #e5e5e5;border-radius:8px;padding:14px;text-decoration:none;color:#222;font-weight:700}
table{border-collapse:collapse;width:100%;background:#fff;font-size:13px}th,td{border:1px solid #e5e5e5;padding:6px;text-align:left}th{background:#fafafa}
footer{font-size:12px;color:#666;border-top:1px solid #e5e5e5;margin-top:40px;background:#fff}
"""


def stars(avg):
    return "★" * int(round(avg)) + "☆" * (5 - int(round(avg)))


def score(it, m=4.0, c=20):
    # レビュー件数が少ない高評価に引っ張られないよう、ベイズ平均で並べる
    n = it["review_count"]
    return (c * m + n * it["review_avg"]) / (c + n)


def price_info(code, price, hist, today):
    h = hist.get(code, {})
    past = [p for d, p in h.items() if d < today]
    if not past:
        return None
    hi = max(past[-30:])
    if price < hi:
        return {"from": hi, "pct": round((hi - price) / hi * 100)}
    return None


def page(cfg, title, body, snap, rel="", desc=None):
    demo = '<div class="pr demo">これはデモデータです。商品・価格は実在しません。</div>' if snap.get("demo") else ""
    nav = "".join(f'<a href="{rel}t/{t["slug"]}.html">{E(t["title"])}</a>' for t in cfg["themes"])
    full_title = f"{title}｜{cfg['site_title']}" if title != cfg["site_title"] else title
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(full_title)}</title><meta name="description" content="{E(desc or cfg['site_description'])}">
<style>{CSS}</style></head><body>
<header><div class="in"><a href="{rel}index.html">{E(cfg['site_title'])}</a>
<nav>{nav}<a href="{rel}drops.html">値下がり</a><a href="{rel}about.html">運営者情報</a></nav></div></header>
<main><div class="pr">【PR】当サイトは楽天アフィリエイトを利用しており、リンク経由のご購入で運営者に報酬が発生します。価格・在庫は{snap['date']}時点の情報です。最新情報は楽天市場でご確認ください。</div>{demo}
{body}</main>
<footer><div class="in">© {E(cfg['operator_name'])}　|　<a href="https://webservice.rakuten.co.jp/" rel="nofollow">Supported by Rakuten Developers</a></div></footer>
</body></html>"""


def card(it, rank, drop):
    img = f'<img src="{E(it["image"])}" alt="" loading="lazy">' if it["image"] else '<div class="noimg"></div>'
    extras = []
    if it["postage_included"]:
        extras.append("送料無料")
    if it["point_rate"] > 1:
        extras.append(f"ポイント{it['point_rate']}倍")
    d = f'<div class="down">↓ {drop["pct"]}%値下がり（{drop["from"]:,}円→）</div>' if drop else ""
    r = f'<div class="rank">{rank}位</div>' if rank else ""
    return f"""<div class="card">{img}<div>{r}<div class="name">{E(it['name'])}</div>
<div class="price">{it['price']:,}円</div>{d}
<div class="meta">{stars(it['review_avg'])} {it['review_avg']:.2f}（{it['review_count']:,}件）／{E(it['shop'])}{'／' + '・'.join(extras) if extras else ''}</div>
<a class="btn" href="{E(it['url'])}" rel="sponsored nofollow noopener" target="_blank">楽天市場で見る</a></div></div>"""


def main():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    snap = json.loads((DATA / "latest.json").read_text(encoding="utf-8"))
    hist_path = DATA / "prices.json"
    hist = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else {}
    today = snap["date"]
    base = cfg["site_url"].rstrip("/") + "/"

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "t").mkdir(parents=True)
    urls = ["index.html", "drops.html", "about.html"]
    drops = []

    for t in cfg["themes"]:
        items = [i for i in snap["themes"].get(t["slug"], []) if i["review_count"] >= cfg["min_review_count"]]
        items.sort(key=score, reverse=True)
        top = items[: cfg["items_per_theme"]]
        for i in items:
            d = price_info(i["code"], i["price"], hist, today)
            if d and d["pct"] >= 5:
                drops.append((d["pct"], t["title"], i, d))

        cheapest = min(top, key=lambda x: x["price"]) if top else None
        most = max(top, key=lambda x: x["review_count"]) if top else None
        summary = ""
        if top:
            summary = f"""<h2>ひと目でわかるまとめ</h2><table>
<tr><th>総合1位（評価×件数）</th><td>{E(top[0]['name'][:60])}…</td></tr>
<tr><th>レビュー数が最多</th><td>{E(most['name'][:60])}…（{most['review_count']:,}件）</td></tr>
<tr><th>上位{len(top)}件で最安</th><td>{E(cheapest['name'][:60])}…（{cheapest['price']:,}円）</td></tr></table>"""
        cards = "".join(card(i, n + 1, price_info(i["code"], i["price"], hist, today)) for n, i in enumerate(top))
        body = f"""<h1>{E(t['title'])}の人気ランキング</h1><p>{E(t['intro'])}</p>
<p class="meta">楽天市場のレビュー評価と件数をもとに毎日自動で集計しています（{today}更新）。レビューが{cfg['min_review_count']}件未満の商品は除外しています。</p>
{summary}<h2>選び方のポイント</h2><div class="guide">{t.get('guide', '')}</div>
<h2>ランキングTOP{len(top)}</h2>{cards or '<p>現在表示できる商品がありません。</p>'}"""
        (OUT / "t" / f"{t['slug']}.html").write_text(
            page(cfg, f"{t['title']}の人気ランキング", body, snap, "../", t["intro"]), encoding="utf-8")
        urls.append(f"t/{t['slug']}.html")

    drops.sort(key=lambda x: x[0], reverse=True)
    drop_cards = "".join(f'<p class="meta">{E(cat)}</p>' + card(i, None, d) for _, cat, i, d in drops[:40])
    (OUT / "drops.html").write_text(page(cfg, "値下がり中の商品", f"""<h1>値下がり中の商品</h1>
<p>直近30日の当サイト記録価格より5%以上安くなった商品です（{today}更新）。</p>
{drop_cards or '<p>今日は値下がり商品がありません。データが数日たまると表示されます。</p>'}""", snap), encoding="utf-8")

    theme_links = "".join(f'<a href="t/{t["slug"]}.html">{E(t["title"])}</a>' for t in cfg["themes"])
    top_drops = "".join(card(i, None, d) for _, _, i, d in drops[:5])
    (OUT / "index.html").write_text(page(cfg, cfg["site_title"], f"""<h1>{E(cfg['site_title'])}</h1>
<p>{E(cfg['site_description'])}</p><h2>カテゴリ</h2><div class="themes">{theme_links}</div>
<h2>今日の値下がり</h2>{top_drops or '<p>価格データを蓄積中です。</p>'}
<p><a href="drops.html">値下がり商品をもっと見る →</a></p>""", snap), encoding="utf-8")

    (OUT / "about.html").write_text(page(cfg, "運営者情報", f"""<h1>運営者情報・免責事項</h1>
<table><tr><th>運営者</th><td>{E(cfg['operator_name'])}</td></tr>
<tr><th>サイトについて</th><td>楽天ウェブサービスのAPIを利用し、商品情報を毎日自動で取得・集計しています。</td></tr></table>
<h2>広告について</h2><p>当サイトは楽天アフィリエイトに参加しています。商品リンクは広告であり、リンク経由で購入されると運営者に報酬が支払われます。</p>
<h2>免責事項</h2><p>掲載している価格・在庫・送料・レビューは取得時点の情報で、変わっている場合があります。購入前に必ず楽天市場の商品ページをご確認ください。</p>""", snap), encoding="utf-8")

    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n", encoding="utf-8")
    sm = "".join(f"<url><loc>{base}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>',
        encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    print(f"生成しました: public/（{len(urls)}ページ、値下がり{len(drops)}件）")


if __name__ == "__main__":
    main()
