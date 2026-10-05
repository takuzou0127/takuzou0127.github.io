# -*- coding: utf-8 -*-
"""
半導体ランキング（SOX全銘柄＋日経半導体株指数の上位10＋SKハイニックス・サムスン電子）

  ❶ 上昇余地を主眼：アナリスト平均目標株価までの上昇率の高い順（S&P500との差・期待値も併記）
  ❷ 安定を主眼    ：S&P比 ÷ 1年の振れ幅 の高い順（指数を上回る見込みを、値動きの大きさで割った値）

数値はすべて Yahoo Finance（yfinance）の実データ。取れなかった銘柄は errors に残し、推定で埋めない。
結果は semi_ranking.json に保存し、semi_ranking.html（公開ページ）がそれを読んで表示する。

置き場所（PC）：C:\\Users\\home\\claude_work\\github_repo\\tools\\fetch-semi-ranking.py
              （同じフォルダに stock-params.py が必要。②-Bと同じ物差し＝EPS修正・PER変化・分類を計算する）
実行：cd C:\\Users\\home\\claude_work\\github_repo
      python tools\\fetch-semi-ranking.py
      → github_repo\\semi_ranking.json ができる。これを git add・commit・push すると公開ページに反映
必要：pip install yfinance
"""
import argparse
import importlib.util
import json
import math
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DEFAULT_OUT = REPO / "semi_ranking.json"

# ---- 対象 ---------------------------------------------------------------
# SOX（PHLX Semiconductor Sector Index）30社。2026年9月の年次入れ替え後の一覧は公式ページをクラウドから読めず、
# 検索で確認できた29社（2026-10-05時点）。残り1社が分かったら足す。--sox-file で差し替えもできる
SOX = ["NVDA", "AVGO", "MU", "ASML", "MRVL", "TSM", "AMAT", "LRCX", "KLAC", "AMD",
       "ADI", "TXN", "INTC", "QCOM", "MPWR", "NXPI", "TER", "COHR", "ALAB", "MCHP",
       "ARM", "CRDO", "ON", "GFS", "ENTG", "MTSI", "RMBS", "LSCC", "AMKR"]

# 日経半導体株指数：ウエート上位9社は報道で確認（2026年4月末）。10位は候補の中から時価総額で決める
# （指数のウエートは時価総額に上限をかけた値なので、上位はほぼ時価総額の順）
NIKKEI_TOP9 = {"285A.T": "キオクシア", "8035.T": "東京エレクトロン", "6857.T": "アドバンテスト",
               "6723.T": "ルネサス", "6146.T": "ディスコ", "6920.T": "レーザーテック",
               "5016.T": "JX金属", "4063.T": "信越化学", "7741.T": "HOYA"}
NIKKEI_10TH_CANDIDATES = {"7735.T": "SCREEN", "6526.T": "ソシオネクスト", "4062.T": "イビデン",
                          "6963.T": "ローム", "3436.T": "SUMCO", "7729.T": "東京精密",
                          "6323.T": "ローツェ", "4186.T": "東京応化"}
KOREA = {"000660.KS": "SKハイニックス", "005930.KS": "サムスン電子"}
HOLDINGS = {"MU", "000660.KS"}

# 確率の目安（expected.html・context.json の期待値ランキングと同じ式）
BASE = {"①": 65, "②": 65, "④": 60, "⑨": 55, "⑥": 50, "⑤": 45, "⑦": 40, "⑧": 30}


def load_params_module():
    path = HERE / "stock-params.py"
    if not path.exists():
        sys.exit("stock-params.py が同じフォルダにありません（tools フォルダで実行してください）")
    spec = importlib.util.spec_from_file_location("stock_params", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sp_benchmark(arg):
    """S&P500全体の12か月上昇余地(%)。--sp が無ければ briefing.html の②-Bの基準行から読む"""
    if arg is not None:
        return arg, "手入力（--sp）"
    b = REPO / "briefing.html"
    if b.exists():
        m = re.search(r"S&amp;P 500全体の12か月上昇余地\s*<b[^>]*>\+?([-\d.]+)%", b.read_text(encoding="utf-8"))
        if m:
            return float(m.group(1)), "briefing.html の②-B基準行（FactSet）"
    return None, "未取得"


def realized_vol_1y(yf, sym):
    """1年の振れ幅＝過去1年の日次リターンの標準偏差×√252（%）。全銘柄同じ方法で揃える"""
    h = yf.Ticker(sym).history(period="1y")["Close"].dropna()
    if len(h) < 120:
        return None
    r = [math.log(h.iloc[i] / h.iloc[i - 1]) for i in range(1, len(h))]
    mu = sum(r) / len(r)
    sd = math.sqrt(sum((x - mu) ** 2 for x in r) / (len(r) - 1))
    return round(sd * math.sqrt(252) * 100)


def prob(p):
    cls = p.get("classification") or ""
    key = cls[:1]
    if key not in BASE:
        return None, False
    v = BASE[key]
    u, d = p.get("rev_up_30d") or 0, p.get("rev_down_30d") or 0
    if u + d >= 3:
        v += (u - d) / (u + d) * 10
    if p.get("bet_type"):
        v -= 5
    if key == "⑤" and "決算リスク" in cls:
        v -= 5
    stale = d > u  # 業績予想を下げた人が上げた人より多い＝目標株価がまだ直されていない可能性
    if stale:
        v -= 10
    return max(20, min(80, v)), stale


def pct(a, b):
    return round((a / b - 1) * 100, 1) if a and b else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--sp", type=float, default=None, help="S&P500全体の上昇余地(%)")
    ap.add_argument("--sox-file", help="SOXのティッカーを1行1つ書いたファイル（一覧の差し替え）")
    ap.add_argument("--sleep", type=float, default=0.4)
    args = ap.parse_args()

    import yfinance as yf
    mod = load_params_module()
    sox = SOX
    if args.sox_file:
        sox = [l.split("#")[0].strip() for l in Path(args.sox_file).read_text(encoding="utf-8").splitlines()]
        sox = [s for s in sox if s]

    # 日経の10位：候補の時価総額を比べる
    caps = []
    for sym, nm in NIKKEI_10TH_CANDIDATES.items():
        try:
            caps.append(((yf.Ticker(sym).info or {}).get("marketCap") or 0, sym, nm))
        except Exception:
            pass
        time.sleep(args.sleep)
    caps.sort(reverse=True)
    nikkei = dict(NIKKEI_TOP9)
    if caps:
        nikkei[caps[0][1]] = caps[0][2]

    universe = [(s, None, "SOX") for s in sox] + [(s, n, "日経半導体") for s, n in nikkei.items()] + \
               [(s, n, "韓国") for s, n in KOREA.items()]
    sp, sp_src = sp_benchmark(args.sp)

    rows, errors = [], []
    for i, (sym, local, grp) in enumerate(universe, 1):
        print(f"  {i}/{len(universe)} {sym}", file=sys.stderr)
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            p = mod.compute(yf, sym)
            price = p.get("price") or info.get("currentPrice") or info.get("regularMarketPrice")
            tgt, lo, hi = info.get("targetMeanPrice"), info.get("targetLowPrice"), info.get("targetHighPrice")
            vol = realized_vol_1y(yf, sym)
            up = pct(tgt, price)
            pr, stale = prob(p)
            spd = round(up - sp, 1) if up is not None and sp is not None else None
            rows.append({
                "symbol": sym, "name": local or info.get("shortName") or sym, "group": grp,
                "holding": sym in HOLDINGS, "currency": info.get("currency"),
                "price": price, "price_date": p.get("price_date"),
                "target_mean": tgt, "target_low": lo, "target_high": hi,
                "analysts": info.get("numberOfAnalystOpinions"),
                "upside_pct": up, "low_pct": pct(lo, price), "high_pct": pct(hi, price),
                "sp_diff_pt": spd, "vol_1y_pct": vol,
                "stability": round(spd / vol, 2) if spd is not None and vol else None,
                "classification": p.get("classification"), "bet_type": p.get("bet_type"),
                "rev_up_30d": p.get("rev_up_30d"), "rev_down_30d": p.get("rev_down_30d"),
                "eps_rev_30d": p.get("eps_rev_30d"), "per_chg_30d": p.get("per_chg_30d"),
                "prob": round(pr) if pr is not None else None, "stale_target": stale,
                "expected_pct": round(pr / 100 * up, 1) if pr is not None and up is not None else None,
            })
        except Exception as e:
            errors.append({"symbol": sym, "group": grp, "error": str(e)[:200]})
        time.sleep(args.sleep)

    out = {
        "generated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "sp500_upside_pct": sp, "sp500_source": sp_src,
        "vol_note": "1年の振れ幅は過去1年の日次の値動きから計算（全銘柄同じ方法。②-Bのオプション由来の値とは少し違う）",
        "sox_note": f"SOXは検索で確認できた{len(sox)}社（2026年9月の入れ替え後）",
        "nikkei_note": "日経半導体株指数のウエート上位9社（2026年4月末の報道）＋10位は候補の中で時価総額が最大の" +
                       (caps[0][2] if caps else "（取得できず）"),
        "rows": rows, "errors": errors,
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"保存：{args.out}（{len(rows)}銘柄・取得失敗{len(errors)}）", file=sys.stderr)


if __name__ == "__main__":
    main()
