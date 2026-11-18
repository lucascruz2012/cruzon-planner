"""Gera cruzinvest/dados/rend_fiis.json com o histórico de rendimentos por cota (últimos 13 meses)
de todos os FIIs e Fiagros da B3, para o app calcular o DY de 12 meses do fundo inteiro,
independente de quando o usuário comprou as cotas.

- Lista de fundos: lista pública da brapi (/api/quote/list, sem token), tickers terminados em 11.
- Rendimentos: Yahoo Finance (/v8/finance/chart/<ticker>.SA?events=div), data-ex e valor por cota.
  O Yahoo pode atrasar alguns dias para registrar o anúncio mais recente; o app completa com os
  proventos oficiais da B3 que o usuário importou.

Sem dados pessoais. Uso: python3 cruzinvest/scripts/rendimentos_fiis.py [arquivo_saida]   (só biblioteca padrão)
"""
import datetime as dt
import json
import re
import sys
import time
import urllib.request

SAIDA = sys.argv[1] if len(sys.argv) > 1 else "cruzinvest/dados/rend_fiis.json"
UA = {"User-Agent": "Mozilla/5.0 (cruzinvest-dados)"}


def get_json(url, tentativas=3):
    for t in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                return json.loads(r.read())
        except Exception as e:
            if t == tentativas - 1:
                print(f"aviso: {url[:90]}: {e}", file=sys.stderr)
                return None
            time.sleep(3 * (t + 1))


def fundos_b3():
    out, pagina = set(), 1
    while True:
        j = get_json(f"https://brapi.dev/api/quote/list?limit=2000&page={pagina}")
        if not j:
            break
        for s in j.get("stocks") or []:
            t = (s.get("stock") or "").upper()
            if re.fullmatch(r"[A-Z]{4}11B?", t) and (s.get("type") == "fund" or s.get("sector") in (None, "Miscellaneous", "Finance")):
                out.add(t)
        if not j.get("totalPages") or pagina >= j["totalPages"]:
            break
        pagina += 1
        time.sleep(1)
    return sorted(out)


def main():
    tks = fundos_b3()
    if not tks:
        sys.exit("lista de fundos vazia")
    limite = time.time() - 400 * 86400
    res, sem = {}, 0
    for t in tks:
        j = get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{t}.SA?range=13mo&interval=1mo&events=div")
        time.sleep(0.4)
        try:
            ev = (((j or {}).get("chart") or {}).get("result") or [{}])[0].get("events", {}).get("dividends", {})
        except Exception:
            ev = {}
        lst = sorted([dt.datetime.fromtimestamp(v["date"], dt.timezone.utc).strftime("%Y-%m-%d"), round(v["amount"], 6)]
                     for v in ev.values() if v.get("date", 0) >= limite and v.get("amount", 0) > 0)
        if lst:
            res[t] = lst
        else:
            sem += 1
    out = {"fonte": "Rendimentos por cota: Yahoo Finance (data-ex). Lista de fundos: brapi.",
           "gerado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "fundos": res}
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"), sort_keys=True)
    print(f"{len(res)} fundos com rendimentos gravados em {SAIDA} ({len(tks)} consultados, {sem} sem rendimento no período)")


if __name__ == "__main__":
    main()
