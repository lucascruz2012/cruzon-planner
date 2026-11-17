/* CruzOn Finance: guarda o app no aparelho para abrir sem internet.
   A pagina tenta sempre a internet primeiro (nunca fica numa versao velha); icones e PDFs vem do cache.
   O Supabase (conta e dados) nunca passa por aqui. Os caches usam o prefixo "cfinance-" para nao
   misturar com os do CruzOn Planner e do CruzInvest, que ficam no mesmo endereco. */
const VERSAO='cfinance-1.8';
const ESTATICOS=['./','./index.html','./manifest.webmanifest','./icone-192.png','./icone-512.png','./icone-apple.png'];
self.addEventListener('install',ev=>{ev.waitUntil(caches.open(VERSAO).then(c=>Promise.allSettled(ESTATICOS.map(u=>c.add(u)))).then(()=>self.skipWaiting()))});
self.addEventListener('activate',ev=>{ev.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('cfinance-')&&k!==VERSAO).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',ev=>{const req=ev.request;if(req.method!=='GET')return;const url=new URL(req.url);if(url.origin!==self.location.origin)return;
  if(req.mode==='navigate'||url.pathname.endsWith('index.html')||url.pathname.endsWith('/')){
    ev.respondWith(fetch(req).then(r=>{const c=r.clone();caches.open(VERSAO).then(k=>k.put(req,c));return r}).catch(()=>caches.match(req,{ignoreSearch:true}).then(r=>r||caches.match('./index.html'))));return}
  ev.respondWith(caches.match(req).then(hit=>{const net=fetch(req).then(r=>{if(r&&r.status===200){const c=r.clone();caches.open(VERSAO).then(k=>k.put(req,c))}return r}).catch(()=>hit);return hit||net}))});
