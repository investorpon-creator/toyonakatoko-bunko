#!/usr/bin/env python3
"""豐中常文庫のサイト点検。

使い方（リポジトリの一番上で）:
    python3 tools/site-check/check.py              # いつもの点検
    python3 tools/site-check/check.py --external   # 外部サイトへのリンクも確かめる（ネット接続が要る）

点検すること:
  1. サイト内リンクの切れ（href・src・srcset、https://nakatokojuku.jp/ で始まる絶対URL、#アンカー）
  2. sitemap.xml（載っているURLが実在するか／実在する index.html が載っているか）
  3. 画像の alt・width・height の抜け（警告のみ。失敗にはしない）
  4. JSON-LD（<script type="application/ld+json">）が JSON として正しいか
  5. events.js の構文と、各予定の d（YYYY-MM-DD）・t・url
  6. 検索索引 search-index.json が最新か（tools/build-search-index.py の結果と同じか）
  7. （--external のときだけ）外部リンクを HEAD で確かめる

Python 3 の標準ライブラリだけで動く。events.js などの構文点検には Node.js があれば使う
（無いときは簡易な点検だけ行う）。誤検知は tools/site-check/config.json で除外できる。
終了コード: エラーがあれば 1、無ければ 0（警告だけなら 0）。
"""
import argparse
import datetime
import fnmatch
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
IN_GHA = os.environ.get("GITHUB_ACTIONS") == "true"


# ───────── 結果の記録と表示 ─────────

class Report:
    def __init__(self):
        self.errors = []    # (file, line, msg)
        self.warnings = []

    def error(self, file, line, msg):
        self.errors.append((file, line, msg))

    def warn(self, file, line, msg):
        self.warnings.append((file, line, msg))


def where(file, line):
    if not file:
        return "（全体）"
    return f"{file}:{line}" if line else file


def gha_escape(s):
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def gha(kind, file, line, msg):
    if not IN_GHA:
        return
    parts = []
    if file:
        parts.append(f"file={file}")
        if line:
            parts.append(f"line={line}")
    print(f"::{kind} {','.join(parts)}::{gha_escape(msg)}")


# ───────── 設定 ─────────

def load_config():
    path = HERE / "config.json"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg.setdefault("site_origins", ["https://nakatokojuku.jp"])
    cfg.setdefault("skip_dirs", [".git"])
    for k in ("sitemap_exclude", "ignore_links", "ignore_anchors", "image_warning_skip", "external_skip"):
        cfg.setdefault(k, [])
    return cfg


def rel(p):
    return p.relative_to(ROOT).as_posix()


def site_files(cfg, pattern):
    skip = set(cfg["skip_dirs"])
    out = []
    for p in ROOT.rglob(pattern):
        parts = p.relative_to(ROOT).parts
        if any(part in skip for part in parts[:-1]):
            continue
        if p.is_file():
            out.append(p)
    return sorted(out)


# ───────── HTML の読み取り ─────────

class PageParser(HTMLParser):
    """リンク・画像・id・JSON-LD を、行番号つきで集める。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []      # (line, attr, value, tag)
        self.images = []     # (line, attrs dict)
        self.ids = set()
        self.jsonld = []     # (start_line, text)
        self._in_jsonld = None

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        a = {k: (v if v is not None else "") for k, v in attrs}
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "name" in a:
            self.ids.add(a["name"])
        for attr in ("href", "src", "poster", "data-src"):
            if attr in a and a[attr].strip():
                self.links.append((line, attr, a[attr].strip(), tag))
        for attr in ("srcset", "imagesrcset"):
            if attr in a:
                for cand in a[attr].split(","):
                    url = cand.strip().split(" ")[0]
                    if url:
                        self.links.append((line, attr, url, tag))
        if tag == "meta" and a.get("content", "").startswith(("http://", "https://")):
            self.links.append((line, "content", a["content"].strip(), tag))
        if tag == "img":
            self.images.append((line, a))
        if tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._in_jsonld = [line, ""]

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        if self._in_jsonld is not None:
            self._in_jsonld[1] += data

    def handle_endtag(self, tag):
        if tag == "script" and self._in_jsonld is not None:
            self.jsonld.append(tuple(self._in_jsonld))
            self._in_jsonld = None


_parsed = {}


def parse_html(path):
    if path not in _parsed:
        p = PageParser()
        p.feed(path.read_text(encoding="utf-8"))
        p.close()
        _parsed[path] = p
    return _parsed[path]


# ───────── URL をリポジトリ内のファイルへ ─────────

SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "blob:", "sms:", "about:")


def classify(url, cfg):
    """('skip'|'external'|'internal', 値)。internal なら (パス, アンカー) を返す。"""
    u = url.strip()
    low = u.lower()
    if not u or low.startswith(SKIP_SCHEMES) or "${" in u or "{{" in u:
        return "skip", None
    for origin in cfg["site_origins"]:
        if low == origin or low.startswith(origin + "/") or low.startswith(origin + "#") or low.startswith(origin + "?"):
            rest = u[len(origin):] or "/"
            if rest[0] != "/":
                rest = "/" + rest
            return "internal", rest
    if low.startswith("//"):
        return "external", "https:" + u
    if re.match(r"^[a-z][a-z0-9+.-]*:", low):
        return ("external", u) if low.startswith(("http://", "https://")) else ("skip", None)
    return "internal", u


def resolve(src_file, ref):
    """ref（相対・/始まり）を、リポジトリ内のファイルの Path と、アンカーへ。
    戻り値: (Path または None, アンカー, 探した場所の一覧)"""
    ref, _, frag = ref.partition("#")
    ref = ref.split("?", 1)[0]
    frag = urllib.parse.unquote(frag)
    if ref == "":
        return src_file, frag, [rel(src_file)]
    path = urllib.parse.unquote(ref)
    if path.startswith("/"):
        base = ROOT
        path = path.lstrip("/")
    else:
        base = src_file.parent
    target = (base / path)
    try:
        target = Path(os.path.normpath(target))
        target.relative_to(ROOT)
    except ValueError:
        return None, frag, ["（サイトの外を指している）"]
    tried = []
    cands = []
    if ref.endswith("/") or path == "":
        cands.append(target / "index.html")
    else:
        cands += [target, target / "index.html", target.with_name(target.name + ".html")]
    for c in cands:
        try:
            tried.append(rel(c))
        except ValueError:
            pass
        if c.is_file():
            return c, frag, tried
    return None, frag, tried


def ignored_link(cfg, src_rel, value):
    for rule in cfg["ignore_links"]:
        f = rule.get("file", "*")
        t = rule.get("target", "")
        if not fnmatch.fnmatch(src_rel, f):
            continue
        if t.endswith("*") and value.startswith(t[:-1]):
            return True
        if value == t:
            return True
    return False


def ignored_anchor(cfg, page_rel, anchor):
    for rule in cfg["ignore_anchors"]:
        pats = rule.get("anchor", [])
        pats = [pats] if isinstance(pats, str) else pats
        if fnmatch.fnmatch(page_rel, rule.get("page", "*")) and any(fnmatch.fnmatch(anchor, a) for a in pats):
            return True
    return False


def check_one_link(rep, cfg, src, line, value, externals, label="リンク"):
    src_rel = rel(src)
    kind, ref = classify(value, cfg)
    if kind == "skip":
        return
    if kind == "external":
        externals.setdefault(ref, []).append((src_rel, line))
        return
    if ignored_link(cfg, src_rel, value):
        return
    target, frag, tried = resolve(src, ref)
    if target is None:
        rep.error(src_rel, line, f"{label}先のファイルがありません: {value}\n"
                                 f"    探した場所: {', '.join(tried) or '（なし）'}")
        return
    if frag and target.suffix == ".html":
        ids = parse_html(target).ids
        if frag not in ids and not ignored_anchor(cfg, rel(target), frag):
            rep.error(src_rel, line, f"{label}先のアンカー #{frag} が {rel(target)} にありません: {value}")


def walk_json_urls(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "@id":
                continue  # @id は「名札」で、リンクではない
            yield from walk_json_urls(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_json_urls(v)
    elif isinstance(obj, str) and obj.startswith(("http://", "https://")):
        yield obj


# ───────── 1・3・4：HTML の点検 ─────────

def check_html(rep, cfg, externals):
    pages = site_files(cfg, "*.html")
    n_links = 0
    for page in pages:
        src_rel = rel(page)
        p = parse_html(page)
        for line, attr, value, tag in p.links:
            n_links += 1
            check_one_link(rep, cfg, page, line, value, externals)

        # JSON-LD
        for start, text in p.jsonld:
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                rep.error(src_rel, start + e.lineno - 1,
                          f"JSON-LD が JSON として正しくありません（{e.lineno - 1 + start} 行目 {e.colno} 文字目）: {e.msg}")
                continue
            for url in walk_json_urls(data):
                if classify(url, cfg)[0] == "internal":
                    n_links += 1
                    check_one_link(rep, cfg, page, start, url, externals, label="JSON-LD のURL")

        # 画像（警告のみ）
        if any(fnmatch.fnmatch(src_rel, g) for g in cfg["image_warning_skip"]):
            continue
        for line, a in p.images:
            name = a.get("src", "（src なし）") or "（src が空。JavaScript で入れる画像）"
            if "alt" not in a:
                rep.warn(src_rel, line, f"画像に alt がありません（飾りの画像なら alt=\"\" と書く）: {name}")
            missing = [k for k in ("width", "height") if k not in a]
            if missing:
                rep.warn(src_rel, line, f"画像に {'・'.join(missing)} がありません（表示のがたつきの元）: {name}")
    return len(pages), n_links


# ───────── 2：sitemap.xml ─────────

def check_sitemap(rep, cfg):
    path = ROOT / "sitemap.xml"
    if not path.exists():
        rep.error("sitemap.xml", 0, "sitemap.xml がありません")
        return
    text = path.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        rep.error("sitemap.xml", e.position[0], f"sitemap.xml が XML として正しくありません: {e}")
        return
    lines = text.splitlines()

    def line_of(s):
        for i, l in enumerate(lines, 1):
            if s in l:
                return i
        return 0

    listed = set()
    seen = set()
    for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
        url = (loc.text or "").strip()
        ln = line_of(url)
        if url in seen:
            rep.error("sitemap.xml", ln, f"同じURLが二度載っています: {url}")
        seen.add(url)
        kind, ref = classify(url, cfg)
        if kind != "internal" or not url.startswith(("http://", "https://")):
            rep.error("sitemap.xml", ln, f"このサイトのURLではありません: {url}")
            continue
        target, _, tried = resolve(ROOT / "index.html", ref)
        if target is None:
            rep.error("sitemap.xml", ln, f"載っているURLのページがありません: {url}\n"
                                         f"    探した場所: {', '.join(tried)}")
        else:
            listed.add(rel(target))
            if not ref.split("#")[0].endswith("/") and target.name == "index.html":
                rep.warn("sitemap.xml", ln, f"フォルダのURLは末尾に / を付けてください: {url}")

    exclude = set(cfg["sitemap_exclude"])
    for p in site_files(cfg, "index.html"):
        r = rel(p)
        if r in listed or r in exclude:
            continue
        url = "https://nakatokojuku.jp/" + urllib.parse.quote(r[: -len("index.html")])
        rep.error("sitemap.xml", 0, f"{r} が sitemap.xml に載っていません。\n"
                                    f"    載せるなら <loc>{url}</loc> を足す。載せないなら "
                                    f"tools/site-check/config.json の sitemap_exclude に \"{r}\" を足す。")


# ───────── 5：events.js ─────────

NODE_EXTRACT = r"""
const fs = require('fs'), vm = require('vm');
const file = process.argv[2];
const ctx = {window: {}, document: undefined};
try {
  vm.runInNewContext(fs.readFileSync(file, 'utf8'), ctx, {filename: file});
} catch (e) {
  console.log(JSON.stringify({error: String(e && e.message || e), stack: String(e && e.stack || '')}));
  process.exit(0);
}
console.log(JSON.stringify({events: ctx.window.NAKATOKO_EVENTS === undefined ? null : ctx.window.NAKATOKO_EVENTS}));
"""


def node_syntax_errors(path):
    """node --check で構文を確かめる。(行, メッセージ) か None。node が無ければ 'nonode'。"""
    node = shutil.which("node")
    if not node:
        return "nonode"
    r = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
    if r.returncode == 0:
        return None
    out = r.stderr
    m = re.search(re.escape(str(path)) + r":(\d+)", out)
    line = int(m.group(1)) if m else 0
    msg = next((l for l in out.splitlines() if re.match(r"^\w*Error", l)), out.strip().splitlines()[-1] if out.strip() else "構文エラー")
    return line, msg


def check_js_syntax(rep, cfg):
    has_node = True
    for p in site_files(cfg, "*.js"):
        if p.name.endswith(".min.js"):
            continue
        res = node_syntax_errors(p)
        if res == "nonode":
            has_node = False
            break
        if res:
            rep.error(rel(p), res[0], f"JavaScript の構文が正しくありません: {res[1]}")
    return has_node


def check_events(rep, cfg, externals, has_node):
    path = ROOT / "events.js"
    if not path.exists():
        rep.error("events.js", 0, "events.js がありません")
        return 0
    src = path.read_text(encoding="utf-8")

    # 各予定の書かれた行（コメントを除いた配列の中の {...}）
    nocomment = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), src, flags=re.S)
    m = re.search(r"window\.NAKATOKO_EVENTS\s*=\s*\[(.*?)\];", nocomment, re.S)
    if not m:
        rep.error("events.js", 0, "window.NAKATOKO_EVENTS = [ ... ]; が見つかりません")
        return 0
    obj_lines = [nocomment.count("\n", 0, m.start(1) + o.start()) + 1
                 for o in re.finditer(r"\{[^{}]*\}", m.group(1))]

    events = None
    if has_node:
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(NODE_EXTRACT)
            helper = f.name
        try:
            r = subprocess.run([shutil.which("node"), helper, str(path)], capture_output=True, text=True)
        finally:
            os.unlink(helper)
        try:
            res = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            res = {"error": r.stderr.strip() or "読み込めませんでした"}
        if "error" in res:
            lm = re.search(r"events\.js:(\d+)", res.get("stack", ""))
            rep.error("events.js", int(lm.group(1)) if lm else 0, f"events.js を実行できません: {res['error']}")
            return 0
        events = res["events"]
        if not isinstance(events, list):
            rep.error("events.js", 0, "window.NAKATOKO_EVENTS が配列になっていません")
            return 0
    else:
        # Node が無いときの簡易な読み取り（書き方の決まりに沿っている前提）
        events = []
        for o in re.finditer(r"\{[^{}]*\}", m.group(1)):
            fields = {k: json.loads('"' + v + '"') for k, v in re.findall(r'(\w+)\s*:\s*"((?:[^"\\]|\\.)*)"', o.group(0))}
            events.append(fields)

    for i, ev in enumerate(events):
        line = obj_lines[i] if i < len(obj_lines) and len(obj_lines) == len(events) else 0
        label = f"{i + 1} 件目の予定"
        if not isinstance(ev, dict):
            rep.error("events.js", line, f"{label}が {{...}} の形になっていません")
            continue
        d = ev.get("d")
        if not isinstance(d, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
            rep.error("events.js", line, f"{label}の d（日付）が YYYY-MM-DD の形ではありません: {d!r}")
        else:
            try:
                datetime.date.fromisoformat(d)
            except ValueError:
                rep.error("events.js", line, f"{label}の d（日付）がありえない日付です: {d}")
        for key, name in (("t", "t（題）"), ("url", "url（申込先）")):
            v = ev.get(key)
            if not isinstance(v, str) or not v.strip():
                rep.error("events.js", line, f"{label}（{d}）に {name} がありません")
        url = ev.get("url")
        if isinstance(url, str) and url.strip():
            if not re.match(r"^(https?://|/)", url):
                rep.error("events.js", line, f"{label}（{d}）の url は https:// か / で始めてください: {url}")
            else:
                check_one_link(rep, cfg, path, line, url, externals, label=f"{label}（{d}）の url の")
    return len(events)


# ───────── 6：検索索引 ─────────

def check_search_index(rep):
    script = ROOT / "tools" / "build-search-index.py"
    current = ROOT / "search-index.json"
    if not script.exists():
        rep.error("tools/build-search-index.py", 0, "索引を作るスクリプトがありません")
        return
    sys.dont_write_bytecode = True  # tools/__pycache__ を作らない
    spec = importlib.util.spec_from_file_location("build_search_index", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "search-index.json"
        mod.OUT = out
        # 表示用の relative_to(ROOT) が失敗しないよう、出力の表示は抑える
        real_stderr = sys.stderr
        sys.stderr = open(os.devnull, "w")
        try:
            try:
                mod.main()
            except ValueError:
                pass  # 書き出した後の表示（relative_to）での失敗は無視
        finally:
            sys.stderr.close()
            sys.stderr = real_stderr
        if not out.exists():
            rep.error("search-index.json", 0, "索引を作り直せませんでした（tools/build-search-index.py の失敗）")
            return
        fresh = out.read_bytes()
    if not current.exists() or current.read_bytes() != fresh:
        rep.error("search-index.json", 0,
                  "検索索引が古くなっています。索引を作り直してください:\n"
                  "    python3 tools/build-search-index.py\n"
                  "    git add search-index.json")


# ───────── 7：外部リンク（--external のときだけ） ─────────

UA = "Mozilla/5.0 (compatible; nakatokojuku-site-check/1.0)"


def probe(url):
    def req(method):
        r = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status
    try:
        return req("HEAD"), None
    except urllib.error.HTTPError as e:
        if e.code in (400, 403, 405, 501):
            try:
                return req("GET"), None
            except urllib.error.HTTPError as e2:
                return e2.code, None
            except Exception as e2:  # noqa: BLE001
                return None, str(e2)
        return e.code, None
    except Exception as e:  # noqa: BLE001
        return None, str(getattr(e, "reason", e))


def check_external(rep, cfg, externals):
    skip = set(cfg["external_skip"])
    urls = [u for u in externals if urllib.parse.urlsplit(u).hostname not in skip]
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = dict(zip(urls, ex.map(probe, urls)))
    for url in urls:
        status, err = results[url]
        places = externals[url]
        f, line = places[0]
        more = f"（ほか {len(places) - 1} か所）" if len(places) > 1 else ""
        if err:
            rep.error(f, line, f"外部リンクにつながりません: {url}{more}\n    理由: {err}")
        elif status in (401, 403, 429):
            rep.warn(f, line, f"外部リンクが機械からの確認を断りました（HTTP {status}。手で開いて確かめる）: {url}{more}")
        elif status >= 400:
            rep.error(f, line, f"外部リンクが切れています（HTTP {status}）: {url}{more}")
    return len(urls)


# ───────── 本体 ─────────

def main():
    ap = argparse.ArgumentParser(description="豐中常文庫のサイト点検")
    ap.add_argument("--external", action="store_true", help="外部サイトへのリンクも HEAD で確かめる")
    ap.add_argument("--no-warnings", action="store_true", help="警告（画像の alt など）を表示しない")
    args = ap.parse_args()

    cfg = load_config()
    rep = Report()
    externals = {}

    n_pages, n_links = check_html(rep, cfg, externals)
    check_sitemap(rep, cfg)
    has_node = check_js_syntax(rep, cfg)
    n_events = check_events(rep, cfg, externals, has_node)
    check_search_index(rep)
    n_ext = check_external(rep, cfg, externals) if args.external else None

    print("■ 豐中常文庫 サイト点検")
    print(f"  HTML {n_pages} ページ・サイト内リンク {n_links} 本・開催予定 {n_events} 件を点検")
    if not has_node:
        print("  （Node.js が見つからないので、JavaScript の構文点検は省きました）")
    if n_ext is None:
        print(f"  外部リンク {len(externals)} 本は点検していません（--external で点検）")
    else:
        print(f"  外部リンク {n_ext} 本を点検")
    print()

    if rep.warnings and not args.no_warnings:
        print(f"── 警告 {len(rep.warnings)} 件（失敗にはしません）──")
        for f, line, msg in rep.warnings:
            print(f"  ⚠ {where(f, line)}  {msg}")
            gha("warning", f, line, msg)
        print()

    if rep.errors:
        print(f"── エラー {len(rep.errors)} 件 ──")
        for f, line, msg in rep.errors:
            print(f"  ✖ {where(f, line)}  {msg}")
            gha("error", f, line, msg)
        print()
        print(f"✖ エラーが {len(rep.errors)} 件あります。上の「ファイル:行」を開いて直してください。")
        print("  誤検知のときは tools/site-check/config.json で除外できます。")
        return 1
    print("✔ エラーはありませんでした。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
