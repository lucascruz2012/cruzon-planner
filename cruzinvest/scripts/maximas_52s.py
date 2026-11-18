"""Gera cruzinvest/dados/max52.json com a máxima e a mínima de 52 semanas de todos os
ativos da B3 (ações, FIIs, ETFs, BDRs), para o app avaliar quedas sem depender de token.

- Lista de tickers: lista pública da brapi (/api/quote/list, sem token).
- Máxima/mínima: Yahoo Finance (/v7/finance/spark, 1 ano de fechamentos diários, 20 ativos por consulta).
  Máxima = fiftyTwoWeekHigh informado (intradiário); mínima = menor fechamento do período.

Sem dados pessoais. Uso: python3 cruzinvest/scripts/maximas_52s.py [arquivo_saida]   (só biblioteca padrão)
"""
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request

SAIDA = sys.argv[1] if len(sys.argv) > 1 else "cruzinvest/dados/max52.json"
UA = {"User-Agent": "Mozilla/5.0 (cruzinvest-dados)"}


def get_json(url, tentativas=4):
    for t in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            if t == tentativas - 1:
                print(f"aviso: {url[:90]}: {e}", file=sys.stderr)
                return None
            time.sleep(3 * (t + 1))


def tickers_b3():
    out, pagina = [], 1
    while True:
        j = get_json(f"https://brapi.dev/api/quote/list?limit=2000&page={pagina}")
        if not j:
            break
        out += [s["stock"] for s in j.get("stocks") or [] if s.get("stock") and s["stock"].isalnum()]
        if not j.get("totalPages") or pagina >= j["totalPages"]:
            break
        pagina += 1
        time.sleep(1)
    return sorted(set(out))


def main():
    tks = tickers_b3()
    if not tks:
        sys.exit("lista de tickers vazia")
    res, falhas = {}, 0
    for i in range(0, len(tks), 20):
        lote = tks[i:i + 20]
        q = urllib.parse.quote(",".join(t + ".SA" for t in lote), safe=",.")
        j = get_json(f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={q}&range=1y&interval=1d")
        if not j:
            falhas += len(lote)
            continue
        for r in (j.get("spark") or {}).get("result") or []:
            try:
                resp = r["response"][0]
                meta = resp.get("meta") or {}
                closes = [c for c in resp["indicators"]["quote"][0].get("close") or [] if c]
                if len(closes) < 20:
                    continue  # pouco histórico: não dá para falar em 52 semanas
                alta = max(meta.get("fiftyTwoWeekHigh") or 0, max(closes))
                baixa = min(closes)
                res[r["symbol"].replace(".SA", "")] = [round(alta, 4), round(baixa, 4)]
            except Exception:
                continue
        time.sleep(0.8)
    out = {"fonte": "Máxima/mínima de 52 semanas: Yahoo Finance; lista de ativos: brapi.",
           "gerado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "ativos": res}
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"), sort_keys=True)
    print(f"{len(res)} ativos gravados em {SAIDA} ({falhas} sem resposta)")


if __name__ == "__main__":
    main()
