/* 中常塾アプリのサービスワーカー
   ・画面の骨組みと中身（kotoba.js・tayori.js・kaidan.js・events.js）は、入れたときに端末へ置く。
   ・開くたびにネットを先に見て（ブラウザの控えも確かめ直す）、読めたら端末の控えを新しくする。
   ・圏外なら、最後に読めた控えを出す。画面（ページ）の控えが無いときだけ /app/ を出す。
   版を上げるとき：この sw.js を書き換えたら下の VER を一つ進める（v4 → v5）。
   中身のファイル（events.js など）を直すだけなら、版を上げなくても次に開いたときに新しくなる。 */
const VER = "nakatoko-app-v4";
const PRE = "nakatoko-app-";
const SHELL = [
  "/app/", "/app/app.js", "/app/manifest.webmanifest",
  "/app/icons/icon-192.png", "/app/icons/icon-512.png", "/app/icons/icon-maskable-512.png", "/app/icons/apple-touch-icon.png",
  "/kotoba.js", "/tayori.js", "/bunko/kaidan/kaidan.js", "/events.js", "/favicon.svg"
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VER)
    .then(c => c.addAll(SHELL.map(u => new Request(u, {cache: "reload"}))))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k.startsWith(PRE) && k !== VER).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  const nav = req.mode === "navigate";
  // ページは #… を除いた /app/ にまとめて控える（index.html と /app/ を二重に持たない）
  const key = nav && (url.pathname === "/app/" || url.pathname === "/app/index.html") ? "/app/" : req;
  e.respondWith(
    (nav ? fetch(req) : fetch(req, {cache: "no-cache"})).then(r => {
      if (r.ok) { const cp = r.clone(); caches.open(VER).then(c => c.put(key, cp)); }
      return r;
    }).catch(() => caches.match(key, {ignoreSearch: true}).then(r => r || (nav ? caches.match("/app/") : Response.error())))
  );
});
