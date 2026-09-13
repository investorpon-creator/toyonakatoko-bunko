/* 中常塾アプリのサービスワーカー ── 画面の骨組みは端末に置き、中身（kotoba.js等）は毎回ネットを先に見る。
   圏外では最後に読めた中身を出す。版を上げるときは下の VER を一つ進める。 */
const VER = "nakatoko-app-v1";
const SHELL = ["/app/", "/app/index.html", "/app/app.js", "/app/manifest.webmanifest", "/app/icons/icon-192.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(VER).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VER).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(fetch(e.request).then(r => { const cp = r.clone(); caches.open(VER).then(c => c.put(e.request, cp)); return r; })
    .catch(() => caches.match(e.request).then(r => r || caches.match("/app/index.html"))));
});
