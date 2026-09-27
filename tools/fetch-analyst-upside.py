# -*- coding: utf-8 -*-
"""
アナリスト目標株価までの上昇余地ランキング（韓国株・日本株 各ベスト20）

「今の株価 → アナリスト平均目標株価」まで何%あるかを、韓国・日本それぞれの大型株で計算し、
上位20銘柄を analyst_upside.json と analyst_upside.html に保存する。
数値はすべて Yahoo Finance（yfinance）から取った実データ。取れなかった銘柄は errors に残し、推定で埋めない。

対象（その日の構成をネットから取る）：
  韓国：KOSPI＋KOSDAQ の時価総額上位300社（Yahoo の銘柄検索で時価総額順。取れない時は Naver の一覧）
  日本：日経平均225社（日経の公式構成銘柄ページ）
  構成を取れない時は --kr-file / --jp-file にコードを1行1つ書いたテキストを渡す（例：005930 / 7203）

置き場所（PC）：C:\\Users\\home\\claude_work\\fetch-analyst-upside.py
実行：python fetch-analyst-upside.py                       … 両国とも（数分かかる）
      python fetch-analyst-upside.py --market kr           … 韓国だけ
      python fetch-analyst-upside.py --min-analysts 3      … 人数の下限を変える（既定6人＝5人以下は除外）
      python fetch-analyst-upside.py --html C:\\Users\\home\\claude_work\\github_repo\\analyst_upside.html

必要：pip install yfinance
"""
import argparse
import html
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "analyst_upside.json"
DEFAULT_HTML = HERE / "analyst_upside.html"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) analyst-upside/1.0"

# EPS修正のルール（予想5人以下は根拠にしない）に合わせ、既定は6人以上
DEFAULT_MIN_ANALYSTS = 6
TOP_N = 20

# 順位に関係なく、何位にいるかを必ず表示する銘柄（保有・注目）
WATCH = {
    "000660.KS": "SKハイニックス（注文中）",
    "005930.KS": "サムスン電子",
    "6857.T": "アドバンテスト",
    "8035.T": "東京エレクトロン",
    "285A.T": "キオクシア",
}

MARKETS = {
    "kr": {"label": "🇰🇷 韓国株", "universe": "KOSPI＋KOSDAQ 時価総額上位300社", "suffix": ".KS", "cur": "₩"},
    "jp": {"label": "🇯🇵 日本株", "universe": "日経平均225社", "suffix": ".T", "cur": "¥"},
}


def fetch_text(url, encoding=None, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        enc = encoding or r.headers.get_content_charset() or "utf-8"
    return raw.decode(enc, errors="replace")


# ---- 対象銘柄 -------------------------------------------------------------
KR_COUNT = 300


def universe_kr_yahoo(yf, n=KR_COUNT):
    """Yahoo の銘柄検索で、韓国の KOSPI(KSC)・KOSDAQ(KOE) を時価総額の大きい順に n 社。[(symbol, 名前)]"""
    q = yf.EquityQuery("and", [yf.EquityQuery("eq", ["region", "kr"]),
                               yf.EquityQuery("is-in", ["exchange", "KSC", "KOE"])])
    out, seen = [], set()
    for offset in range(0, n, 250):
        res = yf.screen(q, sortField="intradaymarketcap", sortAsc=False, size=min(250, n - offset), offset=offset)
        quotes = (res or {}).get("quotes") or []
        for x in quotes:
            sym = x.get("symbol")
            if sym and sym not in seen and x.get("quoteType", "EQUITY") == "EQUITY":
                seen.add(sym)
                out.append((sym, x.get("shortName") or x.get("longName")))
        if not quotes:
            break
    if len(out) < 100:
        raise RuntimeError(f"Yahooの銘柄検索から{len(out)}社しか取れなかった")
    return out[:n]


def universe_kr_naver(n=KR_COUNT):
    """Naver Finance の時価総額順（KOSPI・KOSDAQ、1ページ50社）。[(symbol, 韓国語名)]"""
    rows = []
    for sosok, suffix in ((0, ".KS"), (1, ".KQ")):
        for page in range(1, n // 50 + 2):
            text = fetch_text(f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page={page}",
                              encoding="euc-kr")
            found = re.findall(r'href="/item/main\.naver\?code=(\d{6})"[^>]*>([^<]+)</a>', text)
            if not found:
                (HERE / "naver_debug.html").write_text(text, encoding="utf-8")
                break
            rows += [(code + suffix, html.unescape(name).strip()) for code, name in found]
    out, seen = [], set()
    for sym, name in rows:
        if sym not in seen:
            seen.add(sym)
            out.append((sym, name))
    if len(out) < 100:
        raise RuntimeError(f"Naverの一覧から{len(out)}社しか読めなかった（読んだページは naver_debug.html に保存）")
    return out  # KOSPI と KOSDAQ を別々に時価総額順で読むので、ここでは件数を切らない


def universe_kr(yf):
    try:
        return universe_kr_yahoo(yf)
    except Exception as e:
        print(f"  Yahooの銘柄検索に失敗（{e}）→ Naverの一覧を使う", file=sys.stderr)
        return universe_kr_naver()


def universe_jp_yahoo(yf, n=225):
    """Yahoo の銘柄検索で、東証(JPX)の時価総額上位 n 社。[(symbol, 名前)]"""
    q = yf.EquityQuery("and", [yf.EquityQuery("eq", ["region", "jp"]),
                               yf.EquityQuery("eq", ["exchange", "JPX"])])
    res = yf.screen(q, sortField="intradaymarketcap", sortAsc=False, size=n)
    out = [(x["symbol"], x.get("shortName") or x.get("longName"))
           for x in (res or {}).get("quotes") or [] if x.get("symbol") and x.get("quoteType", "EQUITY") == "EQUITY"]
    if len(out) < 100:
        raise RuntimeError(f"Yahooの銘柄検索から{len(out)}社しか取れなかった")
    return out


def universe_jp_or_yahoo(yf):
    """日経平均225社。構成ページを読めない時は東証の時価総額上位225社に切り替え、表の見出しにもそう書く"""
    try:
        return universe_jp(), None
    except Exception as e:
        print(f"  日経の構成銘柄ページを読めなかった（{e}）→ Yahooの銘柄検索で東証の時価総額上位225社を使う", file=sys.stderr)
        return universe_jp_yahoo(yf), "東証 時価総額上位225社（日経平均の構成ページを読めなかったため）"


def universe_jp():
    """日経の公式構成銘柄ページから225社のコード。[(code, 名前 or None)]"""
    text = fetch_text("https://indexes.nikkei.co.jp/nkave/index/component?idx=nk225")
    codes = []
    for c in re.findall(r">\s*(\d{3}[0-9A-Z])\s*<", text):
        if c not in codes:
            codes.append(c)
    if not 200 <= len(codes) <= 240:
        raise RuntimeError(f"日経のページから{len(codes)}件のコードを読んだ（225前後ではない＝ページの形が変わった可能性）")
    return [(c, None) for c in codes]


def universe_from_file(path):
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            parts = line.split(None, 1)
            out.append((parts[0], parts[1] if len(parts) > 1 else None))
    return out


# ---- 目標株価の取得 -------------------------------------------------------
def fetch_one(yf, symbol):
    info = yf.Ticker(symbol).info or {}
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    t = info.get("regularMarketTime")
    return {
        "symbol": symbol,
        "name_en": info.get("shortName") or info.get("longName"),
        "currency": info.get("currency"),
        "price": price,
        "price_date": datetime.fromtimestamp(t, JST).strftime("%Y-%m-%d") if isinstance(t, (int, float)) else None,
        "target_mean": info.get("targetMeanPrice"),
        "target_median": info.get("targetMedianPrice"),
        "target_low": info.get("targetLowPrice"),
        "target_high": info.get("targetHighPrice"),
        "analysts": info.get("numberOfAnalystOpinions"),
        "recommendation": info.get("recommendationKey"),
    }


def pct(a, b):
    return round((a / b - 1) * 100, 1) if a and b else None


def rank_market(rows, min_analysts):
    """上昇余地（平均目標÷現在値−1）の高い順。人数が下限未満・目標なしは別に数える"""
    ok, few, no_target = [], [], []
    for r in rows:
        if not r.get("price") or not r.get("target_mean"):
            no_target.append(r["symbol"])
            continue
        r["upside_pct"] = pct(r["target_mean"], r["price"])
        r["upside_median_pct"] = pct(r.get("target_median"), r["price"])
        r["upside_low_pct"] = pct(r.get("target_low"), r["price"])
        (ok if (r.get("analysts") or 0) >= min_analysts else few).append(r)
    ok.sort(key=lambda r: r["upside_pct"], reverse=True)
    for i, r in enumerate(ok, 1):
        r["rank"] = i
    return ok, few, no_target


def run_market(key, args, yf):
    m = MARKETS[key]
    errors = []
    file_arg = getattr(args, f"{key}_file")
    try:
        universe_label = None
        if file_arg:
            uni, universe_label = universe_from_file(file_arg), f"{Path(file_arg).name} の銘柄"
        elif key == "kr":
            uni = universe_kr(yf)
        else:
            uni, universe_label = universe_jp_or_yahoo(yf)
    except Exception as e:
        return {"error": f"対象銘柄の一覧を取れなかった：{e}（--{key}-file でコード一覧を渡せます）"}
    rows = []
    for i, (code, local_name) in enumerate(uni, 1):
        sym = code if "." in code else code + m["suffix"]
        try:
            r = fetch_one(yf, sym)
            r["name_local"] = local_name
            rows.append(r)
        except Exception as e:
            errors.append({"symbol": sym, "error": str(e)[:200]})
        if i % 25 == 0:
            print(f"  {m['label']} {i}/{len(uni)}", file=sys.stderr)
        time.sleep(args.sleep)
    ranked, few, no_target = rank_market(rows, args.min_analysts)
    watch = [{"symbol": s, "label": WATCH[s], **next((r for r in rows if r["symbol"] == s), {})}
             for s in WATCH if s.endswith(m["suffix"])]
    return {
        "label": m["label"], "universe": universe_label or m["universe"], "currency_mark": m["cur"],
        "universe_count": len(uni), "fetched": len(rows),
        "ranked_count": len(ranked), "excluded_few_analysts": len(few), "no_target": len(no_target),
        "top": ranked[:TOP_N], "watch": watch, "errors": errors,
    }


# ---- HTML -----------------------------------------------------------------
CSS = """
body{background:#0f1117;color:#e6e6e6;font-family:-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;font-size:17px;line-height:1.8;margin:0;padding:16px;}
h1{font-size:24px;margin:8px 0 4px;} h2{font-size:22px;margin:36px 0 8px;}
.note{font-size:16px;color:#9aa4b2;} .box{background:#181b24;border:1px solid #2a2e3a;border-radius:8px;padding:14px 16px;margin:14px 0;}
.tbl-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;} table{border-collapse:collapse;min-width:900px;width:100%;}
th,td{padding:8px 10px;border-bottom:1px solid #2a2e3a;white-space:nowrap;text-align:right;} th{color:#9aa4b2;font-weight:normal;font-size:16px;}
td.l,th.l{text-align:left;} .up{color:#3fb950;font-weight:bold;} .down{color:#f85149;font-weight:bold;} .muted{color:#9aa4b2;}
tr.watch td{background:#2a2410;} .warn{color:#e3b341;}
"""


def fmt_price(v, cur):
    if v is None:
        return "—"
    return f"{cur}{v:,.0f}" if v >= 100 else f"{cur}{v:,.2f}"


def fmt_pct(v):
    if v is None:
        return '<span class="muted">—</span>'
    cls = "up" if v > 0 else "down" if v < 0 else "muted"
    return f'<span class="{cls}">{v:+.1f}%</span>'


def row_html(r, cur, rank_text):
    name = r.get("name_local") or r.get("name_en") or r["symbol"]
    # ティッカーは銘柄名のすぐ下に出す（横にスクロールしなくても見えるように）
    sub = " ｜ ".join(x for x in (r["symbol"], r.get("name_en") if r.get("name_en") != name else None) if x)
    name_cell = html.escape(name) + f'<br><span class="note">{html.escape(sub)}</span>'
    cls = ' class="watch"' if r["symbol"] in WATCH else ""
    # スマホで最初に見える位置に「上昇余地・人数」を置く
    return (f"<tr{cls}><td>{rank_text}</td><td class=l>{name_cell}</td>"
            f"<td>{fmt_pct(r.get('upside_pct'))}</td><td>{r.get('analysts') or '—'}人</td>"
            f"<td>{fmt_price(r.get('price'), cur)}</td><td>{fmt_price(r.get('target_mean'), cur)}</td>"
            f"<td>{fmt_pct(r.get('upside_median_pct'))}</td><td>{fmt_pct(r.get('upside_low_pct'))}</td>"
            f"<td class=l>{r['symbol']}</td><td>{r.get('price_date') or '—'}</td></tr>")


HEAD = ("<tr><th>順位</th><th class=l>銘柄</th><th>上昇余地</th><th>人数</th><th>現在値</th><th>平均目標</th>"
        "<th>中央値まで</th><th>最低目標まで</th><th class=l>コード</th><th>株価の日付</th></tr>")


def render_html(data):
    parts = [f"<h1>アナリスト目標株価までの上昇余地 ベスト{TOP_N}</h1>",
             f'<div class="note">取得：{data["generated_at"]}（Yahoo Finance）｜対象はアナリスト{data["min_analysts"]}人以上の銘柄</div>',
             '<div class="box">上昇余地＝アナリスト平均目標株価 ÷ 現在値 − 1。'
             "<b>上昇余地が大きい＝上がりやすい、ではありません。</b>株価が下がったのに目標株価がまだ下がっていない銘柄ほど大きく出ます。"
             "「最低目標まで」がマイナスでなければ、一番弱気のアナリストの目標にも届いていないということです。"
             "目標株価は株価の後を追って修正されやすく、先の値動きを当てる指標ではありません。</div>"]
    for key in ("kr", "jp"):
        mk = data["markets"].get(key)
        if not mk:
            continue
        if "error" in mk:
            parts.append(f'<h2>{MARKETS[key]["label"]}</h2><div class="box warn">{html.escape(mk["error"])}</div>')
            continue
        cur = mk["currency_mark"]
        parts.append(f'<h2>{mk["label"]}（{mk["universe"]}）</h2>')
        parts.append(f'<div class="note">対象{mk["universe_count"]}社 → 取得{mk["fetched"]}社 → 順位づけ{mk["ranked_count"]}社'
                     f'（人数不足で除外{mk["excluded_few_analysts"]}社・目標なし{mk["no_target"]}社・取得失敗{len(mk["errors"])}社）'
                     "｜↔ 表は横にスクロールできます</div>")
        rows = "".join(row_html(r, cur, r["rank"]) for r in mk["top"])
        parts.append(f'<div class="tbl-scroll"><table>{HEAD}{rows}</table></div>')
        if mk["watch"]:
            wrows = []
            for w in mk["watch"]:
                if w.get("rank"):
                    rt = f'{w["rank"]}位'
                elif w.get("upside_pct") is not None:
                    rt = f'圏外<br><span class="note">人数{w.get("analysts") or 0}人</span>'
                else:
                    rt = '<span class="muted">未取得</span>'
                w = {**w, "name_local": w["label"]}
                wrows.append(row_html(w, cur, rt))
            parts.append('<div class="note" style="margin-top:14px">保有・注目の銘柄が何位にいるか（同じ日の値で比較）</div>')
            parts.append(f'<div class="tbl-scroll"><table>{HEAD}{"".join(wrows)}</table></div>')
    body = "\n".join(parts)
    return ('<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>上昇余地ランキング</title><style>{CSS}</style></head><body>{body}"
            '<p class="note">本ページは投資助言ではありません。</p></body></html>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["kr", "jp", "both"], default="both")
    ap.add_argument("--min-analysts", type=int, default=DEFAULT_MIN_ANALYSTS)
    ap.add_argument("--kr-file", help="韓国の対象コード一覧（1行1コード。後ろに名前を書いてもよい）")
    ap.add_argument("--jp-file", help="日本の対象コード一覧（1行1コード）")
    ap.add_argument("--sleep", type=float, default=0.4, help="銘柄ごとの待ち秒（Yahooの回数制限よけ）")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--html", default=str(DEFAULT_HTML))
    ap.add_argument("--from-json", help="取得せず、保存済みのJSONからHTMLだけ作り直す")
    args = ap.parse_args()

    if args.from_json:
        data = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
    else:
        import yfinance as yf
        data = {"generated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
                "min_analysts": args.min_analysts, "markets": {}}
        for key in (["kr", "jp"] if args.market == "both" else [args.market]):
            print(f"{MARKETS[key]['label']} を取得中…", file=sys.stderr)
            data["markets"][key] = run_market(key, args, yf)
        Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"保存：{args.out}", file=sys.stderr)

    # print()＋リダイレクトは Windows で文字化けするので、UTF-8 で直接書く
    Path(args.html).write_text(render_html(data), encoding="utf-8")
    print(f"保存：{args.html}", file=sys.stderr)


if __name__ == "__main__":
    main()
