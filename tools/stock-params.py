# -*- coding: utf-8 -*-
"""
銘柄のパラメーター（ブリーフィング②-Bと同じ物差し）を画面に出す

  予想EPS修正（30日・60日）／PER変化（30日）／分類（①②④⑤⑥⑦⑧⑨）／予想株価（人数）／上昇余地／PEG
  ＋ 修正人数（上げた人・下げた人）、ジャンプ倍率（③賭け型の前提）

計算は cloud-memory.md・context.json のルールどおり：
  - EPS修正 ＝ Yahoo「EPS Trend」の Current ÷ 30 Days Ago − 1
  - 使う年度の列：その年度末まで4か月以内なら次の年度（+1y）を主にする（12月決算は9月から来年度）
  - PER変化 ＝（1＋株価の30日騰落）÷（1＋EPS修正30日）− 1
  - EPS予想が5人以下なら ⚠ を付け、分類の根拠にしない

置き場所（PC）：C:\\Users\\home\\claude_work\\github_repo\\tools\\stock-params.py
実行：python stock-params.py 064350.KS
      python stock-params.py 064350.KS 000660.KS 7203.T MU    … 何銘柄でも
必要：pip install yfinance
"""
import sys
from datetime import datetime, timedelta

MIN_ANALYSTS = 6


def pct(a, b):
    return (a / b - 1) * 100 if a and b else None


def fmt(v, unit="%"):
    return "—" if v is None else f"{v:+.1f}{unit}"


def classify(eps30, eps60, per30, peg):
    if eps30 is None or per30 is None:
        return "判定できない（データ不足）"
    if eps30 >= 2:
        if per30 >= 15:
            return "④業績・期待の同時加速型"
        return "②緩やかな再評価型" if per30 >= 5 else "①実績あり・反応未追随"
    if eps30 <= -2:
        return "⑧下方修正型"
    if eps60 is not None and eps60 >= 5 and per30 >= 5:
        return "⑨キャッチアップ型"
    if per30 >= 10:
        return "⑤期待先行型" + ("（⚠決算リスク：PEG≧1.2）" if peg and peg >= 1.2 else "")
    if per30 <= -5:
        return "⑦期待後退型"
    return "⑥様子見型"


def row_of(df, key):
    try:
        return df.loc[key].to_dict()
    except Exception:
        return {}


def price_change_30d(t):
    h = t.history(period="3mo")["Close"].dropna()
    if h.empty:
        return None, None, None
    last_day = h.index[-1]
    before = h[h.index <= last_day - timedelta(days=30)]
    if before.empty:
        return float(h.iloc[-1]), None, last_day
    return float(h.iloc[-1]), float(before.iloc[-1]), last_day


def main_column(info):
    """年度末まで4か月以内なら +1y を主に使う"""
    last_fy = info.get("lastFiscalYearEnd")
    if not isinstance(last_fy, (int, float)):
        return "+1y", "年度末が不明のため来年度"
    fy_end = datetime.fromtimestamp(last_fy) + timedelta(days=365)
    months_left = (fy_end - datetime.now()).days / 30.4
    label = f"{fy_end:%Y年%m月}期"
    if months_left <= 4:
        nxt = fy_end + timedelta(days=365)
        return "+1y", f"来年度（{nxt:%Y年%m月}期）。今年度の{label}は年度末まで{max(months_left, 0):.1f}か月のため"
    return "0y", f"今年度（{label}）"


def compute(yf, symbol):
    """②-Bと同じ物差しを計算して dict で返す（上昇余地ランキングからも使う）"""
    t = yf.Ticker(symbol)
    info = t.info or {}
    col, col_note = main_column(info)
    other = "0y" if col == "+1y" else "+1y"

    trend, rev, est = t.eps_trend, t.eps_revisions, t.earnings_estimate
    tr, tr_other = row_of(trend, col), row_of(trend, other)
    eps30 = pct(tr.get("current"), tr.get("30daysAgo"))
    eps60 = pct(tr.get("current"), tr.get("60daysAgo"))
    rv, es = row_of(rev, col), row_of(est, col)
    n_eps = es.get("numberOfAnalysts")

    price, price_30, last_day = price_change_30d(t)
    px30 = pct(price, price_30)
    per30 = ((1 + px30 / 100) / (1 + eps30 / 100) - 1) * 100 if px30 is not None and eps30 is not None else None

    tgt = info.get("targetMeanPrice")
    peg = info.get("trailingPegRatio") or info.get("pegRatio")
    trailing_eps, fwd_eps = info.get("trailingEps"), tr.get("current")
    jump = fwd_eps / trailing_eps if fwd_eps and trailing_eps and trailing_eps > 0 else None

    few = n_eps is not None and n_eps < MIN_ANALYSTS
    return {
        "name": info.get("longName") or info.get("shortName") or symbol,
        "currency": info.get("currency") or "",
        "column": col, "column_note": col_note, "other_column": other,
        "eps_30daysAgo": tr.get("30daysAgo"), "eps_current": fwd_eps,
        "eps_rev_30d": eps30, "eps_rev_60d": eps60,
        "eps_rev_30d_other": pct(tr_other.get("current"), tr_other.get("30daysAgo")),
        "price": price, "price_date": f"{last_day:%Y-%m-%d}" if last_day is not None else None,
        "price_chg_30d": px30, "per_chg_30d": per30,
        "classification": "⚠ 予想5人以下のため分類しない" if few else classify(eps30, eps60, per30, peg),
        "bet_type": bool(jump and jump >= 2), "jump": jump,
        "target_mean": tgt, "target_analysts": info.get("numberOfAnalystOpinions"),
        "upside_pct": pct(tgt, price), "peg": peg,
        "fwd_pe": price / fwd_eps if price and fwd_eps and fwd_eps > 0 else None,
        "eps_analysts": n_eps, "rev_up_30d": rv.get("upLast30days"), "rev_down_30d": rv.get("downLast30days"),
    }


def show(yf, symbol):
    c = compute(yf, symbol)
    cur, col = c["currency"], c["column"]
    print("=" * 64)
    print(f"{c['name']}（{symbol}）")
    print(f"  株価 {cur} {c['price']:,.0f}（{c['price_date']} 終値）" if c["price"] else "  株価 取得できず")
    print(f"  使った年度の列：{c['column_note']}")
    print("-" * 64)
    print(f"  予想EPS修正（30日）: {fmt(c['eps_rev_30d'])}   （60日: {fmt(c['eps_rev_60d'])}）"
          f"   EPS {c['eps_30daysAgo'] or 0:,.0f} → {c['eps_current'] or 0:,.0f}")
    print(f"     参考：もう一方の年度の列（{c['other_column']}）の30日修正: {fmt(c['eps_rev_30d_other'])}")
    print(f"  株価の30日騰落    : {fmt(c['price_chg_30d'])}")
    print(f"  PER変化（30日）   : {fmt(c['per_chg_30d'])}")
    print(f"  分類              : {c['classification']}")
    if c["bet_type"]:
        print(f"     ＋③賭け型の前提：予想EPSが実績の {c['jump']:.1f} 倍（外れると実質のPERが跳ね上がる）")
    print("-" * 64)
    print(f"  予想株価（平均）  : {cur} {c['target_mean']:,.0f}（{c['target_analysts']}人）"
          if c["target_mean"] else "  予想株価          : 取得できず")
    print(f"  上昇余地          : {fmt(c['upside_pct'])}")
    print(f"  PEG               : {c['peg']:.2f}" if c["peg"] else "  PEG               : —")
    print(f"  予想PER（{col}）   : {c['fwd_pe']:.1f}倍" if c["fwd_pe"] else f"  予想PER（{col}）   : —")
    n = c["eps_analysts"]
    print(f"  EPS予想の人数     : {n if n is not None else '—'}人"
          f"   直近30日に上げた人 {c['rev_up_30d'] if c['rev_up_30d'] is not None else '—'}"
          f"・下げた人 {c['rev_down_30d'] if c['rev_down_30d'] is not None else '—'}")
    if c["jump"]:
        print(f"  ジャンプ倍率      : {c['jump']:.2f}倍（予想EPS÷実績EPS）")


def main():
    syms = sys.argv[1:] or ["064350.KS"]
    import yfinance as yf
    for s in syms:
        try:
            show(yf, s)
        except Exception as e:
            print(f"{s}: 取得できなかった（{e}）")
    print("=" * 64)
    print("※ Yahoo Finance の値。投資助言ではありません。")


if __name__ == "__main__":
    main()
