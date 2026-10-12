# -*- coding: utf-8 -*-
"""
PCのClaude Codeの会話を、出先（スマホのクラウドのセッション）から続けるための引き継ぎ。

PCのClaude Codeの Stop フック（Claudeが1回答え終わるたび）から呼ばれ、
その会話の直近のやり取りを handoff/ に書き出して GitHub の main へ push する。
クラウドのセッションは CLAUDE.md の指示で handoff/ の最新ファイルを読む。

- 書き出すのは拓造さんの発言とClaudeの返答の文章だけ（ツールの中身・思考は除く）
- 1会話＝1ファイル（handoff/日付_時刻_会話ID.md）。新しい順に15ファイルだけ残す
- 会話の中で拓造さんが「#非公開」と書いたら、その会話は書き出さない（このリポジトリは公開）
- push は裏で動かすので、Claude Code の画面は待たされない

設定（PCの ~/.claude/settings.json の "hooks"）:
  "Stop": [{"hooks": [{"type": "command",
    "command": "python C:/Users/home/claude_work/github_repo/tools/session-handoff.py"}]}]
※ パスは / で書く（\\ だとJSONの \\U エラーになる）
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, "handoff")
KEEP_FILES = 15          # handoff/ に残すファイル数
KEEP_MESSAGES = 40       # 1会話で残す直近の発言数
MAX_CHARS = 2500         # 1発言の上限（長い返答は頭とお尻だけ残す）
PRIVATE_MARK = "#非公開"
LOCK = os.path.join(REPO, ".git", "handoff.lock")


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def is_noise(text):
    t = text.lstrip()
    return (not t or t.startswith("<command-") or t.startswith("<local-command")
            or t.startswith("<system-reminder>") or t.startswith("Caveat:")
            or t.startswith("[Request interrupted"))


def clip(text):
    text = text.strip()
    if len(text) <= MAX_CHARS:
        return text
    half = MAX_CHARS // 2
    return text[:half] + "\n\n…（途中省略）…\n\n" + text[-half:]


def read_messages(path):
    msgs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") not in ("user", "assistant"):
                continue
            if d.get("isMeta") or d.get("isSidechain"):
                continue
            text = text_of((d.get("message") or {}).get("content"))
            if is_noise(text):
                continue
            who = "拓造さん" if d["type"] == "user" else "Claude"
            # Claudeの返答は1回答の中で複数行に分かれるのでまとめる
            if msgs and msgs[-1][0] == who == "Claude":
                msgs[-1] = (who, msgs[-1][1] + "\n\n" + text, msgs[-1][2])
            else:
                msgs.append((who, text, d.get("timestamp", "")))
    return msgs


def write_handoff(hook):
    transcript = hook.get("transcript_path")
    if not transcript or not os.path.exists(transcript):
        return None
    msgs = read_messages(transcript)
    if not msgs:
        return None
    sid = (hook.get("session_id") or "unknown")[:8]
    os.makedirs(OUT_DIR, exist_ok=True)

    existing = [n for n in os.listdir(OUT_DIR) if n.endswith("_" + sid + ".md")]
    if any(PRIVATE_MARK in t for w, t, _ in msgs if w == "拓造さん"):
        for n in existing:   # 途中から非公開にした会話は消す
            os.remove(os.path.join(OUT_DIR, n))
        return "private"

    now = datetime.now()
    name = existing[0] if existing else now.strftime("%Y-%m-%d_%H%M_") + sid + ".md"
    first_user = next((t for w, t, _ in msgs if w == "拓造さん"), "")
    title = first_user.strip().splitlines()[0][:60] if first_user.strip() else "(無題)"
    lines = [
        "# PCの会話の引き継ぎ：" + title,
        "",
        "- 最終更新：" + now.strftime("%Y-%m-%d %H:%M") + "（PC）",
        "- 作業フォルダ：" + str(hook.get("cwd", "")),
        "- 全%d発言のうち直近%d発言。長い返答は途中を省略" % (len(msgs), min(len(msgs), KEEP_MESSAGES)),
        "",
        "---",
        "",
    ]
    for who, text, _ in msgs[-KEEP_MESSAGES:]:
        lines += ["## " + who, "", clip(text), ""]
    with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    files = sorted(n for n in os.listdir(OUT_DIR) if n.endswith(".md") and n != "README.md")
    for n in files[:-KEEP_FILES]:
        os.remove(os.path.join(OUT_DIR, n))
    return name


def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args),
                          capture_output=True, text=True, encoding="utf-8")


def push():
    # 同時に2つ動かない（PCの日次更新の push とぶつかった時も後で再試行）
    for _ in range(30):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL)
            os.close(fd)
            break
        except FileExistsError:
            if time.time() - os.path.getmtime(LOCK) > 300:
                os.remove(LOCK)
            time.sleep(2)
    else:
        return
    try:
        git("add", "-A", "--", "handoff")
        if git("diff", "--cached", "--quiet", "--", "handoff").returncode == 0:
            return
        # handoff/ だけをコミットする（ほかの作業中のファイルは巻き込まない）
        git("commit", "-m", "handoff: PCの会話の引き継ぎ", "--", "handoff")
        for wait in (0, 2, 4, 8):
            time.sleep(wait)
            git("pull", "--rebase", "--autostash", "origin", "main")
            if git("push", "origin", "HEAD:main").returncode == 0:
                return
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass


def main():
    if "--push" in sys.argv:
        push()
        return
    try:
        hook = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    except ValueError:
        hook = {}
    if write_handoff(hook) is None:
        return
    # push は裏で（画面を待たせない）
    kw = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "stdin": subprocess.DEVNULL}
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "--push"], **kw)


if __name__ == "__main__":
    main()
