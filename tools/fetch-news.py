# -*- coding: utf-8 -*-
"""
ニュース取得スクリプト（毎朝のニュース・ブリーフィングの「実データ」担当）

株価の stock_data.json と同じ考え方で、ニュースの見出し・配信元・配信時刻・URLを
配信元のRSSから取ってきて news_data.json に保存する。Claude はまずこのJSONを読み、
深掘りが必要な記事だけを WebSearch する。

置き場所（PC）：C:\\Users\\home\\claude_work\\fetch-news.py
実行：python fetch-news.py                 … 直近36時間（毎朝 05:20、run-news.ps1 の最初に実行）
      python fetch-news.py --hours 168     … 直近7日（日曜の「今週の日本の流れ」用）
      python fetch-news.py --out C:\\path\\news_data.json

外部ライブラリ不要（標準ライブラリのみ）。yfinance が入っていれば銘柄別ニュースも取る。
取れなかった配信元は errors に残し、黙って空にしない。
"""
import argparse
import html
import json
import re
import ssl
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

JST = timezone(timedelta(hours=9))
DEFAULT_OUT = Path(__file__).resolve().parent / "news_data.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) news-fetch/1.0"

# 地元のニュースを取りたい場合は、市町村名や県名を入れる（例：["横浜市", "神奈川県"]）。
# 空のままなら地元欄は取らない。
LOCAL_AREAS = ["大阪府", "大阪市"]

# ---- 配信元 -------------------------------------------------------------
# 固定URLのRSS。NHK公式RSS（www3.nhk.or.jp/rss/news/catN.xml）は2026-09-23のPC実行で
# 最新記事が2026-08-08で止まっていたため使わない。NHKの記事はGoogleニュース経由で入る。
# Googleニュースの「国内」「ビジネス」トピック（URLは未確認。errors と件数で確かめる）
FIXED_FEEDS = {
    "jp_society":  ("https://news.google.com/rss/headlines/section/topic/NATION?hl=ja&gl=JP&ceid=JP:ja", "Googleニュース: 国内"),
    "jp_economy":  ("https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ja&gl=JP&ceid=JP:ja", "Googleニュース: ビジネス"),
}

# Googleニュース検索RSS（日本語）。カテゴリ → 検索語のリスト
GN_JA = {
    "jp_top":        [None],  # None = Googleニュース日本版のトップニュース
    "jp_politics":   ["国会 OR 首相 OR 政府"],
    "jp_market":     ["日経平均", "日銀 金融政策", "円相場"],
    "jp_semicon":    ["東京エレクトロン", "アドバンテスト", "キオクシア", "ラピダス", "SKハイニックス", "マイクロン 半導体"],
    # 暮らし・季節の話題（サンマの豊漁、キャベツの値段など、食卓や家計に近い時事）
    "jp_life":       ["豊漁 OR 不漁", "野菜 価格 高騰 OR 値下がり", "食品 値上げ", "米 価格", "ガソリン価格",
                      "旬 初物 OR 初競り OR 解禁", "天気 猛暑 OR 台風 OR 大雪 暮らし"],
    "jp_medical":    ["診療報酬改定", "医療従事者 賃上げ", "病院 ベースアップ", "医療 不祥事", "医療事故 病院", "厚生労働省 医療"],
}

# Googleニュース検索RSS（英語）。配信元を絞る検索（ロイターは公式RSSが2020年に終了したためこの方法）
GN_EN = {
    "global_semicon": ["site:reuters.com semiconductor", "site:reuters.com Micron OR \"SK Hynix\" OR Nvidia",
                       "site:asia.nikkei.com semiconductor"],
    "global_macro":   ["site:reuters.com Federal Reserve OR Treasury yields", "site:reuters.com Japan economy OR yen"],
}

# 医療欄は「新聞に取り上げられるレベル」だけにするため、大手報道の記事だけ残す
MAJOR_OUTLETS = [
    "NHK", "日本経済新聞", "日経", "朝日新聞", "読売新聞", "毎日新聞", "産経", "東京新聞", "中日新聞",
    "共同通信", "時事通信", "時事ドットコム", "北海道新聞", "西日本新聞", "神戸新聞", "京都新聞",
    "TBS", "日テレ", "テレ朝", "フジテレビ", "テレビ東京", "FNN", "ANN", "JNN", "Yahoo!ニュース",
    "Reuters", "ロイター", "Bloomberg", "ブルームバーグ", "Nikkei Asia", "Financial Times", "Wall Street Journal",
    "AP", "AFP", "CNBC", "CNN", "BBC", "New York Times",
]

TICKERS_FOR_NEWS = ["MU", "SKHY", "NVDA", "AVGO", "LRCX", "AMD", "TSM"]


def gn_url(query, lang="ja", hours=36):
    if lang == "ja":
        params = "hl=ja&gl=JP&ceid=JP:ja"
    else:
        params = "hl=en-US&gl=US&ceid=US:en"
    if query is None:
        return "https://news.google.com/rss?" + params
    days = max(1, round(hours / 24))
    q = urllib.parse.quote(f"{query} when:{days}d")
    return f"https://news.google.com/rss/search?q={q}&{params}"


def _ssl_context():
    # PCのPython標準の証明書ストアでは一部サイトの証明書を確認できなかった（2026-09-23）。
    # certifi が入っていればその証明書一覧を使い、無ければ標準の挙動に任せる
    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


SSL_CONTEXT = _ssl_context()


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as r:
        return r.read()


def parse_date(text):
    if not text:
        return None
    try:
        d = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(JST)


def parse_rss(raw, default_source):
    """RSS 2.0 / RDF(RSS 1.0) の item を (title, source, published, url) で返す"""
    root = ET.fromstring(raw)
    items = []
    for it in root.iter():
        if not it.tag.endswith("item"):
            continue
        get = lambda name: next((c for c in it if c.tag.split("}")[-1] == name), None)
        t, l = get("title"), get("link")
        d = get("pubDate")
        if d is None:
            d = get("date")  # RDF(RSS 1.0) は dc:date
        s = get("source")
        title = html.unescape((t.text or "").strip()) if t is not None else ""
        source = (s.text or "").strip() if s is not None and s.text else default_source
        # Googleニュースの見出しは「見出し - 媒体名」なので媒体名を外す
        if source and title.endswith(" - " + source):
            title = title[: -len(" - " + source)]
        items.append({
            "title": title,
            "source": source,
            "published": parse_date(d.text if d is not None else None),
            "url": (l.text or "").strip() if l is not None else "",
        })
    return items


def _outlet_hit(outlet, source):
    # 英字の短い名前（AP・ANN等）は単語単位で照合する（"Japan"・"Channel"に当たらないように）
    if outlet.isascii() and len(outlet) <= 4:
        return re.search(rf"(?<![A-Za-z]){re.escape(outlet)}(?![A-Za-z])", source) is not None
    return outlet.lower() in source.lower()


def tier_of(source):
    return "大手報道" if any(_outlet_hit(m, source or "") for m in MAJOR_OUTLETS) else "その他"


def norm_title(t):
    return re.sub(r"[\s　「」『』【】（）()・、。,.!?！？:：\-–—]", "", t)[:40]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=36)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    now = datetime.now(JST)
    since = now - timedelta(hours=args.hours)
    buckets, errors = {}, []

    def add(category, feed_label, url, default_source):
        try:
            got = parse_rss(fetch(url), default_source)
        except Exception as e:  # noqa: BLE001 取得失敗は記録して続行
            errors.append({"category": category, "feed": feed_label, "url": url, "error": f"{type(e).__name__}: {e}"})
            return
        for it in got:
            it["feed"] = feed_label
            buckets.setdefault(category, []).append(it)

    for cat, (url, label) in FIXED_FEEDS.items():
        add(cat, label, url, "")
    for cat, queries in GN_JA.items():
        for q in queries:
            add(cat, f"Googleニュース: {q or 'トップ'}", gn_url(q, "ja", args.hours), "")
    for cat, queries in GN_EN.items():
        for q in queries:
            add(cat, f"Google News: {q}", gn_url(q, "en", args.hours), "")
    for area in LOCAL_AREAS:
        add("jp_local", f"Googleニュース: {area}", gn_url(area, "ja", args.hours), "")

    try:
        import yfinance as yf  # 任意
        for tk in TICKERS_FOR_NEWS:
            try:
                for n in yf.Ticker(tk).news or []:
                    c = n.get("content", n)
                    ts = c.get("pubDate") or c.get("providerPublishTime")
                    pub = (datetime.fromtimestamp(ts, JST) if isinstance(ts, (int, float)) else parse_date(ts))
                    prov = c.get("provider")
                    url = c.get("canonicalUrl") or c.get("link") or ""
                    buckets.setdefault("ticker_news", []).append({
                        "title": c.get("title", ""),
                        "source": prov.get("displayName", "") if isinstance(prov, dict) else (c.get("publisher") or ""),
                        "published": pub,
                        "url": url.get("url", "") if isinstance(url, dict) else url,
                        "feed": f"Yahoo Finance: {tk}",
                    })
            except Exception as e:  # noqa: BLE001
                errors.append({"category": "ticker_news", "feed": f"Yahoo Finance: {tk}", "error": f"{type(e).__name__}: {e}"})
    except ImportError:
        errors.append({"category": "ticker_news", "feed": "Yahoo Finance", "error": "yfinance 未インストール"})

    out = {}
    for cat, items in buckets.items():
        seen, kept = set(), []
        for it in sorted(items, key=lambda x: x["published"] or since, reverse=True):
            if it["published"] and it["published"] < since:
                continue
            key = norm_title(it["title"])
            if not key or key in seen:
                continue
            seen.add(key)
            it["tier"] = tier_of(it["source"])
            if cat == "jp_medical" and it["tier"] != "大手報道":
                continue  # 医療は新聞・大手報道レベルのものだけ
            it["published"] = it["published"].isoformat(timespec="minutes") if it["published"] else None
            kept.append(it)
        out[cat] = kept

    result = {
        "generated_at": now.isoformat(timespec="seconds"),
        "window_hours": args.hours,
        "categories": {
            "jp_top": "日本の主要ニュース", "jp_society": "社会・事件", "jp_politics": "政治",
            "jp_economy": "経済", "jp_life": "暮らし・季節の話題", "jp_market": "日本の市場（日経平均・日銀・円）", "jp_semicon": "日本の半導体・保有銘柄",
            "jp_medical": "医療（大手報道のみ）", "jp_local": "地元", "global_semicon": "海外・半導体（ロイター・日経アジア）",
            "global_macro": "海外・マクロ（ロイター）", "ticker_news": "銘柄別（Yahoo Finance）",
        },
        "counts": {k: len(v) for k, v in out.items()},
        "errors": errors,
        "items": out,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {args.out}: " + ", ".join(f"{k}={v}" for k, v in result["counts"].items())
          + (f" / errors={len(errors)}" if errors else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
