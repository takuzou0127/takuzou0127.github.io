# クラウドの代行手順（PCの自動作業が止まった日のため）

2026-10-12、ユーザー：「10/7でブリーフィングが止まってる。ニュースも。土日限定のものも。しっかりして欲しい」。
PCの朝の作業が公開できない日に、クラウドのルーチンがこの手順で代わりに出す。**PCが出していればクラウドは何もしない。**

## 共通
1. CLAUDE.md の指示どおり `context.json`・`cloud-memory.md` を全文読む（保有・表記ルール・NISA前提など）
2. `git fetch origin main` して main の最新を見る
3. 判定は各ページの `<title>` の日付（日本時間の今日か）
4. クラウドからは Yahoo・Google News 等に直接つなげない（プロキシで403）。**WebSearch だけで調べる**。WebFetch も多くのサイトで失敗する
5. 確かめられなかった値は「未取得」と書く。推定で埋めない。数字には出典のリンクを付ける
6. ページの頭に「⚠ クラウド代行版」と、止まった理由（分かっていれば）を書く
7. 書いたら main に commit・push（ブランチに置かない）。`cloud-memory.md` に1行「○/○ クラウド代行で○○を出した」と追記
8. 文字サイズ（補足16/本文17/見出し20〜24px）・スマホ幅で横スクロールが出ないこと。既存ページの `<head>`（CSS）をそのまま流用する

## 朝（毎日 6:40 JST）：briefing.html・news.html・bignews.html
- `briefing.html` の title が今日でなければ作る。構成：保有ポートフォリオ（MU×2・000660×1・005930×1、取得単価は cloud-memory）→主要指数→⓪-A 本日の結論→🌊時代のうねり（id は付けない）→①マクロ→①-B→🤖AI→②株価一覧（確かめられた値だけ）→②-B→⑥→⑦-A／⑦-B→今日の一言
- **②-B（table.vt）は自分で作らない**。直前の版（PCが作った最後の版）の②-Bの節（`<h2>②-B` から `</tbody></table></div>` まで）をそのまま残し、「○/○朝のPC版のまま」と注記する。expected.html・semi_ranking.html がこの表を読むため。ヘッダーに `データ取得：YYYY-MM-DD HH:MM JST（PC最終版）` の形の文字列を入れる（expected.html の表示用）
- `news.html` の title が今日でなければ作る（Bloomberg／Yahoo Finance／日経／AI／政治／MLB／Dodgers の節、既存の CSS クラス）
- `bignews.html` が2日以上古ければ、頭に「今週の大ネタ」の節を足す（各社の欄は古いまま残し、そう書く）

## 週末（土・日 11:20 JST）：techcatchup.html・techranking.html
- `techcatchup.html` の title が今週末の日付でなければ作る（前回からの差分・スコアボード・論点・来週の見どころ）
- `techranking.html` は頭の「結論を先に」の上に、その日の更新の枠を足す（順位表そのものはPCの ai_tech_ranking.json が正なので書き換えない）

## PCへの引き継ぎ（PCが戻った時）
- PCの日次更新はクラウド代行版を上書きしてよい（PC版が正）
- PCの push が「non-fast-forward」で失敗する時は、`git pull --no-rebase origin main` してから push。briefing.html 等で衝突したら PC 側の版を採る
