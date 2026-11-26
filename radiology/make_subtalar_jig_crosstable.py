import math, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import font_manager
from matplotlib.patches import Polygon, FancyArrowPatch, Ellipse, Rectangle, Circle

font_manager.fontManager.addfont("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf")
plt.rcParams["font.family"] = "IPAGothic"

RED = "#d32f2f"; BLUE = "#1565c0"; GRN = "#2e7d32"; ORG = "#ef6c00"; GRY = "#555555"
A4 = (210 / 25.4, 297 / 25.4)


def page():
    fig = plt.figure(figsize=A4)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 210); ax.set_ylim(0, 297); ax.axis("off")
    return fig, ax


def T(ax, x, y, s, size=8, **k):
    ax.text(x, y, s, fontsize=size, va=k.pop("va", "top"), ha=k.pop("ha", "left"), **k)


def scale_bar(ax, x0, y):
    ax.plot([x0, x0 + 100], [y, y], color="k", lw=0.8)
    for i in range(11):
        ax.plot([x0 + 10 * i, x0 + 10 * i], [y - 1.5, y + 1.5], color="k", lw=0.8)
    T(ax, x0 + 50, y + 5, "確認用スケール 100 mm（印刷後に定規で測って100mmならOK）", 6.5, ha="center")


pdf = PdfPages(sys.argv[1])

# ---------------- page 1 ----------------
fig, ax = page()
T(ax, 105, 287, "距踵関節撮影 補助具（くさび2枚重ね）【改訂版 2026-11-26】", 13, ha="center", weight="bold")
T(ax, 105, 280, "足の外側を受像面に密着 ＋ 足の裏を受像面に垂直 ＋ 背屈くさび 14° ＋ 内返しくさび 20° ＋ X線を指先方向へ 30°", 7.6, ha="center", color=RED)
T(ax, 105, 275.5, "素材：硬質発泡スチロール（XPS：スタイロフォーム／ミラフォーム等）200×100×50 mm", 7, ha="center")

# change box
ax.add_patch(Rectangle((10, 248), 190, 24, fc="#fff4e5", ec=ORG, lw=1))
T(ax, 13, 270.5, "前の版（10/23）からの訂正：原スライドで確認", 8.5, weight="bold", color=ORG)
T(ax, 13, 265.5, "① X線の斜入：「頭尾方向（足側）へ30°」→「指先方向へ30°」（足根洞のトンネル＝後内側→前外側の傾きに沿わせる）", 7.3)
T(ax, 13, 260.5, "② 内返しくさびEの向き：厚い縁を「外側」→「内側（母趾側＝管球側）」（外側に置くと外返しになっていた）", 7.3)
T(ax, 13, 255.5, "③ 中心を追加：内果の下・踵の内側（載距突起のあたり）から入れ、外側の足根洞へ抜く", 7.3)
T(ax, 13, 250.8, "角度・置き方（14°＋20°＋30°）と型紙（2・3ページ）は前の版と同じ", 6.8, color=GRY)

# 1) side view (50%)
T(ax, 12, 243, "① 横から見た図（縮尺50%）", 9, weight="bold")
ox, oy, s = 18, 205, 0.5
D = [(ox, oy), (ox + 200 * s, oy), (ox + 200 * s, oy + 50 * s)]
ax.add_patch(Polygon(D, closed=True, fc="#fff3c4", ec="k", lw=0.8))
ang = math.atan2(50, 200)
ux, uy = math.cos(ang), math.sin(ang); nx, ny = -uy, ux
t = 18 * s  # E thickness at mid-section (schematic)
E = [(ox, oy), (ox + 200 * s, oy + 50 * s), (ox + 200 * s + nx * t, oy + 50 * s + ny * t), (ox + nx * t, oy + ny * t)]
ax.add_patch(Polygon(E, closed=True, fc="#cfe3ff", ec="k", lw=0.8))
T(ax, ox + 30, oy + 5.5, "14°", 8, color=RED)
T(ax, ox + 55, oy + 6, "背屈くさび D", 7.5)
T(ax, ox + 22, oy + 19, "内返しくさび E", 7.5, rotation=14)
T(ax, ox, oy - 2, "薄い端＝踵側", 7)
T(ax, ox + 100, oy - 2, "厚い端＝つま先側", 7, ha="right")
T(ax, ox + 50, oy - 7, "底面＝基準面（足の裏を受像面に垂直にする面）", 6.8, ha="center")
T(ax, ox + 102, oy + 22, "足の裏は\nEの斜面に当てる", 6.8)

# 2) toe-side view of E
T(ax, 140, 243, "② つま先側から見た E", 9, weight="bold")
bx, by = 140, 210
ax.add_patch(Polygon([(bx, by), (bx + 50, by), (bx, by + 18.2)], closed=True, fc="#cfe3ff", ec="k", lw=0.8))
T(ax, bx - 1, by + 9, "36.4", 7, ha="right", va="center")
T(ax, bx + 35, by + 4.5, "20°", 8, color=RED)
T(ax, bx, by - 2, "内側（母趾側）\n＝管球側", 7, color=BLUE, weight="bold")
T(ax, bx + 50, by - 2, "外側（小趾側）\n＝受像面側", 7, ha="right")
T(ax, 140, 236, "厚い縁を足の内側（管球側）へ", 8, color=RED, weight="bold")
T(ax, 140, 231.5, "左足用の向き（右足は E を180°回す）", 6.5, color=GRY)

# 3) plantar schematic
T(ax, 12, 190, "③ X線の向き（模式図：左足を足の裏の側から見た図）", 9, weight="bold")
cx, cy = 52, 136
ax.add_patch(Ellipse((cx, cy + 6), 28, 56, fc="#f6e1d3", ec="k", lw=0.8))
ax.add_patch(Ellipse((cx + 1, cy - 18), 20, 20, fc="#f6e1d3", ec="k", lw=0.8))
ax.plot([cx + 18, cx + 18], [cy - 32, cy + 34], color=BLUE, lw=3)
T(ax, cx + 20, cy + 34, "受像面\n（足の外側\n　を密着）", 7, color=BLUE)
T(ax, cx, cy + 38, "つま先", 7, ha="center")
T(ax, cx + 1, cy - 30, "踵", 7, ha="center")
T(ax, cx - 27, cy + 14, "内側\n(母趾側)", 7, ha="center")
T(ax, cx + 30, cy - 4, "外側", 7, ha="center")
ex, ey = cx - 11, cy - 16
c30, s30 = math.cos(math.radians(30)), math.sin(math.radians(30))
bx2, by2 = ex + 33 * c30, ey + 33 * s30
sx, sy = ex - 24 * c30, ey - 24 * s30
ax.add_patch(FancyArrowPatch((sx, sy), (bx2, by2), arrowstyle="-|>", mutation_scale=12, color=RED, lw=2))
ax.plot([sx, sx + 34], [sy, sy], color=GRY, lw=0.8, ls="--")
T(ax, sx + 16, sy + 7, "30°", 8, color=RED, weight="bold")
ax.add_patch(Circle((ex, ey), 1.6, fc=ORG, ec="k", lw=0.5))
T(ax, 12, ey + 8, "入口：内果の下・\n踵の内側\n（載距突起のあたり）", 6.8, color=ORG)
qx = cx + 12; qy = ey + (qx - ex) * math.tan(math.radians(30))
ax.add_patch(Circle((qx, qy), 1.6, fc=ORG, ec="k", lw=0.5))
T(ax, qx + 8, qy + 3, "出口：足根洞", 6.8, color=ORG)
T(ax, 12, 101, "※ 骨は描いていない向きだけの模式図。破線＝受像面に垂直な向き。足根洞のトンネルは後内側→前外側に斜めに走るので、\n   内側の踵から入れて指先方向へ傾けるとトンネルに沿う。", 6.3, color=GRY)

# usage text
T(ax, 104, 190, "④ 使い方", 9, weight="bold")
lines = [
    ("共通", True),
    ("・足の外側を受像面に密着。補助具の底面（Dの平らな面）を", False),
    ("  受像面に垂直に置き、足の裏をEの斜面にぴったり当てる", False),
    ("  → 背屈14°と内返し20°が同時に決まる", False),
    ("・向きの確認：足の裏が少し管球の方（内側）を向けば正しい。", False),
    ("  受像面の方を向いたら E が逆（外返しになっている）", False),
    ("・X線は受像面に垂直から、指先方向へ30°。中心は③の入口", False),
    ("・固定：面ファスナーのベルトで足と補助具を一緒に巻く", False),
    ("A　膝を伸ばして、患側を下に側臥位", True),
    ("・足の外側を台の上の受像面へ。X線は上から入れ、", False),
    ("  指先の方へ30°傾ける", False),
    ("B　ストレッチャー上（仰臥位・つま先を天井へ）＝クロステーブル", True),
    ("・受像面を足の外側に垂直に立てる。管球は内側", False),
    ("  （患側の下腿を少し挙上し、健側を離して通り道をあける）", False),
    ("・X線は水平から、指先方向＝天井の方へ30°傾ける", False),
    ("  （管球を低めに置き、斜め上へ向ける）", False),
    ("・中心・距離・条件は施設の手順に従う", False),
]
y = 184
for s_, b in lines:
    T(ax, 104, y, s_, 7.2, weight="bold" if b else "normal", color=BLUE if b else "k")
    y -= 4.6

# individual variation + how to make
T(ax, 12, 93, "⑤ 角度の個体差（原スライド：n=25、計測 浜脇整形外科 小村哲也氏）", 9, weight="bold")
T(ax, 14, 87.5, "背屈 平均13.6°（SD1.8）／内返し 平均19.8°（SD3.2）／斜入 平均31.3°（SD3.9）。補助具は平均の値。写真で足根洞が暗いトンネル\nとして抜けているか、後・中・前の関節面が見えるかを確かめ、合わない人は斜入の角度で数度足し引きする。", 7)

T(ax, 12, 75, "⑥ 作り方（型紙は2・3ページ）", 9, weight="bold")
steps = [
    "1. ブロック1個目 → 2ページ目の型紙を両方の側面（200×50の面）に貼り、対角線で切る → 背屈くさびDが2個とれる（同じ形）。",
    "2. ブロック2個目 → 3ページ目の型紙を両方の端面（100×50の面）に貼り、線で切る → 内返しくさびE（厚さ36.4→0）。",
    "   残りの上側（厚さ13.6→50、斜めの面がやはり20°）も反対側の足用のEとして使える。",
    "3. Dの斜面にEの平らな面を重ねる。Dの厚い端＝つま先側、Eの厚い縁＝足の内側（管球側）。Eの傾きはDの傾きと90°ちがう方向。",
    "4. 左右：Eを180°回して（厚い縁を反対側にして）貼れば反対の足用。1セットで兼用するなら、DとEを面ファスナーで留めて付け替える。",
    "5. 仮止め（強力両面テープ）→ 足を当てて「足の裏が管球側を向くか」確認 → 本止め（『発泡スチロール用』接着剤）。",
    "6. 全体をビニールテープで巻く（尖った縁の補強と清拭のため）。『右』『左』『つま先↑』『内側（管球側）』を記入。",
    "7. 患者さんに使う前に、補助具だけを臨床条件で1回撮影して、継ぎ目が写らないか確認。",
]
y = 69.5
for s_ in steps:
    T(ax, 14, y, s_, 6.6); y -= 4.4
T(ax, 12, 31, "※ 新潟救急撮影研究会「距踵関節撮影 I法の攻略方法」（設計：三菱神戸病院 高井夏樹氏）のスライドから再構成。原スライドの補助具は200×100×50mmの\n   ブロック2個を1回の斜め切りで作る方式で、この設計図は同じ角度を「くさび2枚重ね」で作る別の作り方。重ねによる角度の誤差は1°未満。", 6.3, color=GRY)
T(ax, 105, 16, "購入：2〜3個（左右を固定で作るなら3個、失敗用の予備に＋1個）", 8, ha="center")
pdf.savefig(fig); plt.close(fig)

# ---------------- page 2: D template (1:1) ----------------
fig, ax = page()
T(ax, 105, 285, "背屈くさび D：側面の型紙（原寸 1:1）— 14.0°", 11, ha="center")
x0, y0 = 5, 175
ax.add_patch(Rectangle((x0, y0), 200, 50, fc="none", ec="k", lw=0.8))
ax.plot([x0, x0 + 200], [y0 + 50, y0], color=RED, lw=0.9)
T(ax, x0, y0 + 54, "50 mm（厚い端＝つま先側）", 6.5)
T(ax, x0 + 100, y0 - 3, "200 mm", 6.5, ha="center")
T(ax, x0 + 150, y0 + 40, "D（上側：裏返すと同じ形）", 7)
T(ax, x0 + 60, y0 + 12, "D（下側）", 7)
T(ax, 105, 160, "ブロックの200×50の側面2面に、角を合わせて1枚ずつ貼る（2枚印刷）。赤線＝切る線", 6.8, ha="center")
T(ax, 105, 155, "反対側の面に貼る時は裏から見た向きになるので、赤線が『同じ角どうし』を結んでいるか確認", 6.8, ha="center")
scale_bar(ax, 55, 110)
T(ax, 105, 20, "印刷は「実際のサイズ（100%）」で。拡大・縮小しない", 7, ha="center", color=RED)
pdf.savefig(fig); plt.close(fig)

# ---------------- page 3: E template (1:1) ----------------
fig, ax = page()
T(ax, 105, 285, "内返しくさび E：端面の型紙（原寸 1:1）— 20°", 11, ha="center")
h = 100 * math.tan(math.radians(20))
for i, (yy, ttl) in enumerate([(205, "端面その1"), (125, "端面その2（もう一方の端）")]):
    x0 = 55
    T(ax, 105, yy + 57, ttl, 7.5, ha="center")
    ax.add_patch(Rectangle((x0, yy), 100, 50, fc="none", ec="k", lw=0.8))
    ax.plot([x0, x0 + 100], [yy + h, yy], color=RED, lw=0.9)
    T(ax, x0 - 2, yy + h / 2, f"{h:.1f}", 6.5, ha="right", va="center")
    T(ax, x0 + 102, yy + 25, "50", 6.5, va="center")
    T(ax, x0 + 15, yy + 8, "E", 8)
    T(ax, x0 + 60, yy + 44, f"残り（{50 - h:.1f}→50）", 6.5)
    T(ax, x0, yy - 2, "厚い縁（36.4）\n＝足の内側（管球側）へ", 6.5, color=BLUE)
T(ax, 105, 108, "ブロックの100×50の端面2面に貼る。2面で『36.4mmの点』が同じ長い辺の側にくるように（ねじれ防止）", 6.8, ha="center")
T(ax, 105, 103, "使う時は、厚い縁（36.4mmの側）を足の内側（母趾側＝管球側）に向ける", 6.8, ha="center", color=RED)
scale_bar(ax, 55, 85)
T(ax, 105, 20, "印刷は「実際のサイズ（100%）」で。拡大・縮小しない", 7, ha="center", color=RED)
pdf.savefig(fig); plt.close(fig)
pdf.close()
print("ok")
