#!/usr/bin/env python3
"""サイト内検索の索引（search-index.json）を作る。

使い方（リポジトリの一番上で）:
    python3 tools/build-search-index.py

全HTMLページから、タイトル・URL・見出し・本文を取り出し、見出しごとの節に分けて
search-index.json に書き出す。/search/ のページがこれを読み、ブラウザの中だけで検索する。
あわせて tayori.js（たより）・events.js（催し）・bunko/kaidan/kaidan.js（一節ずつの階段）
の項目も索引に入れる。

標準ライブラリだけで動く（追加のインストール不要）。
ページを足したり本文を直したりしたら、これを実行して search-index.json もコミットする。
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "search-index.json"

# 索引に入れないファイル（リポジトリ直下からの相対パス）
EXCLUDE = {"404.html", "search/index.html"}

# 中身ごと読み飛ばす要素
SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "nav", "footer",
             "button", "select", "textarea", "head", "form", "iframe"}
# 中身ごと読み飛ばす class（ヘッダーのナビなど、どのページにもある部分）
SKIP_CLASSES = {"topbar"}
# 節の区切りにする見出し
HEADING_TAGS = {"h1", "h2", "h3", "h4"}
HEADING_CLASSES = {"chapter-heading"}  # 倭姫命世記の翻刻テキストの章見出し
# 改行相当として扱う要素（前後の文字をつなげない）
BLOCK_TAGS = {"p", "div", "section", "article", "li", "ul", "ol", "dl", "dt", "dd",
              "br", "tr", "td", "th", "table", "blockquote", "figure", "figcaption",
              "header", "main", "aside", "pre", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
              "summary", "details"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
             "meta", "param", "source", "track", "wbr"}

SEP = "\u0001"  # ブロックの切れ目（あとで空白に置きかえる）
CJK = r"　-〿぀-ヿ㐀-鿿豈-﫿＀-￯"


def clean(text):
    """空白を整える。HTMLの改行で日本語の語が割れないよう、和文どうしの間の改行は詰める。"""
    # ソースの改行・字下げ（改行を含む空白）は、和文どうしの間なら詰める
    text = re.sub(rf"(?<=[{CJK}])[ \t\f\v]*[\r\n][ \t\r\n\f\v]*(?=[{CJK}])", "", text)
    text = re.sub(r"[ \t\r\n\f\v]+", " ", text)
    # 「度 會 神 道」のように一字ずつ空けた飾りの文字列は、空白を詰める
    text = re.sub(rf"(?:[{CJK}] ){{2,}}[{CJK}]", lambda m: m.group(0).replace(" ", ""), text)
    text = re.sub(rf"[ {SEP}]*{SEP}[ {SEP}]*", " ", text)
    return text.strip()


class Extractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.in_title = False
        self.stack = []          # [(tag, id, flags)]
        self.skip_depth = 0
        self.sections = []       # [{"h":..., "a":..., "note":..., "buf": [...]}]
        self.heading = None      # 見出しを読んでいる最中なら {"buf": [], "a": ...}
        self._new_section("", "", "")

    def _new_section(self, heading, anchor, note):
        self.sections.append({"h": heading, "a": anchor, "note": note, "buf": []})

    def _ancestor(self, key):
        for tag, ident, flags in reversed(self.stack):
            if key == "section_id" and ident and tag in ("section", "article"):
                return ident
            if key == "honkoku" and ident == "viewer-text":
                return True
        return None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = set((a.get("class") or "").split())
        ident = a.get("id") or ""
        if tag == "title" and not self.stack_has("body"):
            self.in_title = True
        skip = (tag in SKIP_TAGS or classes & SKIP_CLASSES
                or "hidden" in a or a.get("aria-hidden") == "true")
        is_heading = tag in HEADING_TAGS or bool(classes & HEADING_CLASSES)
        if tag not in VOID_TAGS:
            self.stack.append((tag, ident, {"skip": bool(skip), "heading": is_heading}))
        if skip:
            self.skip_depth += 1 if tag not in VOID_TAGS else 0
            return
        if self.skip_depth:
            return
        if tag == "img" and a.get("alt"):
            pass  # 画像の代替文は本文に入れない（重複が多いため）
        if is_heading and self.heading is None and tag not in VOID_TAGS:
            anchor = ident or self._ancestor("section_id") or ""
            self.heading = {"buf": [], "a": anchor}
        if tag in BLOCK_TAGS:
            self._emit(SEP)

    def stack_has(self, tag):
        return any(t == tag for t, _, _ in self.stack)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag in VOID_TAGS:
            if tag == "br" and not self.skip_depth:
                self._emit(SEP)
            return
        # 対応する開きタグまで戻す（閉じ忘れに強くする）
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                popped = self.stack[i:]
                del self.stack[i:]
                break
        else:
            return
        for t, ident, flags in reversed(popped):
            if flags["skip"]:
                self.skip_depth -= 1
            elif flags["heading"] and self.heading is not None and not self.skip_depth:
                h = clean("".join(self.heading["buf"]))
                note = "「翻刻テキスト」のタブ" if self._ancestor("honkoku") else ""
                anchor = self.heading["a"]
                self.heading = None
                if h:
                    self._new_section(h, anchor, note)
        if tag in BLOCK_TAGS and not self.skip_depth:
            self._emit(SEP)

    def handle_data(self, data):
        if self.in_title:
            self.title += data
            return
        if self.skip_depth or not self.stack_has("body"):
            return
        self._emit(data)

    def _emit(self, s):
        if self.heading is not None:
            self.heading["buf"].append(s)
        else:
            self.sections[-1]["buf"].append(s)


def page_url(rel):
    p = rel.as_posix()
    if p == "index.html":
        return "/"
    if p.endswith("/index.html"):
        return "/" + p[: -len("index.html")]
    return "/" + p


def short_title(title):
    t = clean(title)
    return re.split(r"[｜|]", t)[0].strip() or t


def index_html(path):
    rel = path.relative_to(ROOT)
    ex = Extractor()
    ex.feed(path.read_text(encoding="utf-8"))
    ex.close()
    title = short_title(ex.title)
    url = page_url(rel)
    entries = []
    for sec in ex.sections:
        body = clean("".join(sec["buf"]))
        if not body and not sec["h"]:
            continue
        e = {"t": title, "u": url, "h": sec["h"], "b": body}
        if sec["a"]:
            e["a"] = sec["a"]
        if sec["note"]:
            e["n"] = sec["note"]
        entries.append(e)
    # 本文がない見出しだけの節は、次の節と区別がつかないので落とす
    return [e for e in entries if e["b"] or e is entries[0]]


def strip_js_comments(src):
    """/* ... */ のコメント（書き方の例が入っている）を取り除く。"""
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


def jdate(d):
    """2026-09-05 → 2026年9月5日"""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", d or "")
    return f"{m.group(1)}年{int(m.group(2))}月{int(m.group(3))}日" if m else (d or "")


def js_string(s):
    return json.loads('"' + s + '"')


def index_tayori():
    path = ROOT / "tayori.js"
    if not path.exists():
        return []
    src = strip_js_comments(path.read_text(encoding="utf-8"))
    out = []
    pat = re.compile(r'\{\s*d\s*:\s*"([^"]*)"\s*,\s*t\s*:\s*"((?:[^"\\]|\\.)*)"(?:\s*,\s*url\s*:\s*"([^"]*)")?')
    for d, t, url in pat.findall(src):
        out.append({"t": "中常だより", "u": url or "/tayori/", "h": jdate(d), "b": js_string(t),
                    "d": d, "k": "tayori"})
    return out


def index_events():
    path = ROOT / "events.js"
    if not path.exists():
        return []
    src = strip_js_comments(path.read_text(encoding="utf-8"))
    m = re.search(r"window\.NAKATOKO_EVENTS\s*=\s*\[(.*?)\];", src, re.S)
    if not m:
        return []
    out = []
    for obj in re.findall(r"\{[^{}]*\}", m.group(1)):
        fields = dict((k, js_string(v)) for k, v in re.findall(r'(\w+)\s*:\s*"((?:[^"\\]|\\.)*)"', obj))
        if "d" not in fields:
            continue
        body = fields.get("t", "")
        if fields.get("v"):
            body += "　会場：" + fields["v"]
        if fields.get("addr"):
            body += "（" + fields["addr"] + "）"
        out.append({"t": "開催予定", "u": "/taiken/", "h": jdate(fields["d"]),
                    "b": body, "d": fields["d"], "k": "event"})
    return out


def index_kaidan():
    path = ROOT / "bunko" / "kaidan" / "kaidan.js"
    if not path.exists():
        return []
    src = strip_js_comments(path.read_text(encoding="utf-8"))
    m = re.search(r"window\.NAKATOKO_KAIDAN\s*=\s*(\[.*?\]);", src, re.S)
    if not m:
        return []
    out = []
    for k in json.loads(m.group(1)):
        out.append({"t": "一節ずつの階段", "u": k.get("url") or "/bunko/kaidan/", "h": k.get("t", ""),
                    "b": k.get("s", ""), "d": k.get("d", ""), "k": "tayori"})
    return out


def main():
    entries = []
    pages = sorted(p for p in ROOT.rglob("*.html")
                   if ".git" not in p.parts and p.relative_to(ROOT).as_posix() not in EXCLUDE)
    for p in pages:
        entries.extend(index_html(p))
    entries.extend(index_kaidan())
    entries.extend(index_tayori())
    entries.extend(index_events())
    data = {"v": 1, "entries": entries}
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    chars = sum(len(e["b"]) for e in entries)
    print(f"{OUT.relative_to(ROOT)}: {len(pages)} ページ, {len(entries)} 節, 本文 {chars} 字", file=sys.stderr)


if __name__ == "__main__":
    main()
