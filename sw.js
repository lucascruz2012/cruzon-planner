/* CruzOn Planner — guarda o aplicativo no aparelho.
   Regra: a pagina sempre tenta a internet primeiro (para voce nunca ficar
   com uma versao velha); imagens e icones vem do cache, que se atualiza
   sozinho em segundo plano. Nada do Supabase passa por aqui. */
const VERSAO = "cruzon-2026-09-15";
const ESTATICOS = [
  "./", "./index.html", "./manifest.webmanifest",
  "./login-bg.jpg", "./icone-192.png", "./icone-512.png", "./icone-apple.png"
];

self.addEventListener("install", ev => {
  ev.waitUntil(
    caches.open(VERSAO)
      .then(c => Promise.allSettled(ESTATICOS.map(u => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", ev => {
  ev.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== VERSAO).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("message", ev => {
  if (ev.data === "atualizar") self.skipWaiting();
});

self.addEventListener("fetch", ev => {
  const req = ev.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;   /* Supabase, Brevo, fontes: nao toca */

  /* a pagina em si: internet primeiro */
  if (req.mode === "navigate" || url.pathname.endsWith("index.html") || url.pathname.endsWith("/")) {
    ev.respondWith(
      fetch(req)
        .then(r => { const c = r.clone(); caches.open(VERSAO).then(k => k.put(req, c)); return r; })
        .catch(() => caches.match(req).then(r => r || caches.match("./index.html")))
    );
    return;
  }

  /* imagens e demais arquivos: cache primeiro, atualizando por tras */
  ev.respondWith(
    caches.match(req).then(cacheado => {
      const rede = fetch(req).then(r => {
        if (r && r.status === 200) { const c = r.clone(); caches.open(VERSAO).then(k => k.put(req, c)); }
        return r;
      }).catch(() => cacheado);
      return cacheado || rede;
    })
  );
});
