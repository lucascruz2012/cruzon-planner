/* CruzInvest: guarda o app no aparelho.
   A pagina tenta sempre a internet primeiro; imagens vem do cache.
   Cotacoes (brapi) e Banco Central nunca passam por aqui. */
const VERSAO = "cruzinvest-2026-11-18c";
const ESTATICOS = ["./", "./index.html", "./manifest.webmanifest", "./logo.svg", "./login-bg.jpg", "./login-bg-m.jpg", "./ci-icone-192.png", "./ci-icone-512.png", "./ci-icone-apple.png"];
self.addEventListener("install", ev => {
  ev.waitUntil(caches.open(VERSAO).then(c => Promise.allSettled(ESTATICOS.map(u => c.add(u)))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", ev => {
  ev.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith("cruzinvest-") && k !== VERSAO).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", ev => {
  const req = ev.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  /* a pagina e os dados publicos (dados/*.json): internet primeiro, cache so sem conexao */
  if (req.mode === "navigate" || url.pathname.endsWith("index.html") || url.pathname.endsWith("/") || url.pathname.includes("/dados/")) {
    ev.respondWith(fetch(req).then(r => { const c = r.clone(); caches.open(VERSAO).then(k => k.put(req, c)); return r; })
      .catch(() => caches.match(req).then(r => r || caches.match("./index.html"))));
    return;
  }
  ev.respondWith(caches.match(req).then(hit => {
    const net = fetch(req).then(r => { if (r && r.status === 200) { const c = r.clone(); caches.open(VERSAO).then(k => k.put(req, c)); } return r; }).catch(() => hit);
    return hit || net;
  }));
});
