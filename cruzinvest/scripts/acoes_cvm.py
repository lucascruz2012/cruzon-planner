"""Gera cruzinvest/dados/acoes.json com os números contábeis oficiais de todas as companhias
abertas, a partir dos demonstrativos entregues à CVM (DFP anual e ITR trimestral, dados abertos).

Para cada ticker (via cadastro FCA da CVM), grava os valores-base em R$ e o período de referência.
O app calcula os indicadores com a cotação do momento:
  P/L = preço × ações / lucro 12m          P/VP = preço × ações / patrimônio líquido
  ROE = lucro 12m / PL                     margem líquida = lucro 12m / receita 12m
  dívida líquida/EBITDA = (empréstimos CP+LP − caixa − aplicações) / (EBIT 12m + D&A 12m)
  liquidez corrente = ativo circulante / passivo circulante
  payout = dividendos e JCP pagos 12m / lucro 12m

"12m" = últimos 12 meses: anual do último DFP + acumulado do ano no último ITR − mesmo acumulado do ano anterior.
Sem dados pessoais. Uso: python3 cruzinvest/scripts/acoes_cvm.py [arquivo_saida]   (só biblioteca padrão)
"""
import csv
import datetime as dt
import io
import json
import sys
import urllib.request
import zipfile

BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/"
SAIDA = sys.argv[1] if len(sys.argv) > 1 else "cruzinvest/dados/acoes.json"
CACHE = {}


def zip_cvm(tipo, ano):
    url = f"{BASE}{tipo.upper()}/DADOS/{tipo}_cia_aberta_{ano}.zip"
    if url in CACHE:
        return CACHE[url]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "cruzinvest-dados/1.0"})
        with urllib.request.urlopen(req, timeout=300) as r:
            CACHE[url] = zipfile.ZipFile(io.BytesIO(r.read()))
    except Exception as e:
        print(f"aviso: {url}: {e}", file=sys.stderr)
        CACHE[url] = None
    return CACHE[url]


def linhas(z, sufixo):
    if not z:
        return []
    nome = next((n for n in z.namelist() if n.endswith(sufixo)), None)
    if not nome:
        return []
    with z.open(nome) as f:
        return list(csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def escala(r):
    return 1000.0 if (r.get("ESCALA_MOEDA") or "").upper().startswith("MIL") else 1.0


class Demonstrativos:
    """Valores por (cnpj, dt_refer) -> {conta: valor}, só a última versão e o exercício 'ÚLTIMO'."""

    def __init__(self):
        self.ver = {}      # (cnpj, dt) -> versão
        self.bal = {}      # (cnpj, dt) -> {conta: valor}   balanço (posição)
        self.ytd = {}      # (cnpj, dt) -> {conta: valor}   resultado acumulado no ano
        self.desc = {}     # (cnpj, dt) -> {conta: descrição}
        self.consol = set()  # empresas com demonstrativo consolidado

    def carrega(self, z, prefixo, ano):
        for grupo in ("con", "ind"):
            for tabela, alvo in (("BPA", self.bal), ("BPP", self.bal), ("DRE", self.ytd), ("DFC_MI", self.ytd), ("DFC_MD", self.ytd)):
                for r in linhas(z, f"{prefixo}_{tabela}_{grupo}_{ano}.csv"):
                    if (r.get("ORDEM_EXERC") or "").upper() != "ÚLTIMO".upper() and not (r.get("ORDEM_EXERC") or "").startswith("ÚLTIMO") and "LTIMO" not in (r.get("ORDEM_EXERC") or "").upper():
                        continue
                    cnpj, dtr = r["CNPJ_CIA"], r["DT_REFER"]
                    if grupo == "ind" and cnpj in self.consol:
                        continue  # prefere o consolidado
                    if grupo == "con":
                        self.consol.add(cnpj)
                    if alvo is self.ytd and tabela == "DRE":
                        ini = r.get("DT_INI_EXERC") or ""
                        if not ini.endswith("-01-01"):
                            continue  # só o acumulado do ano, não o trimestre isolado
                    k = (cnpj, dtr)
                    v = num(r.get("VL_CONTA"))
                    if v is None:
                        continue
                    versao = int(r.get("VERSAO") or 0)
                    if versao < self.ver.get(k, 0):
                        continue
                    if versao > self.ver.get(k, 0):
                        self.ver[k] = versao
                        self.bal.pop(k, None); self.ytd.pop(k, None); self.desc.pop(k, None)
                    pref = "DFC:" if tabela.startswith("DFC") else ""
                    alvo.setdefault(k, {})[pref + r["CD_CONTA"]] = v * escala(r)
                    self.desc.setdefault(k, {})[pref + r["CD_CONTA"]] = (r.get("DS_CONTA") or "").lower()


def soma_desc(vals, descs, prefixo, termos, sinal=1):
    """Soma as contas folha sob 'prefixo' cuja descrição contém algum dos termos."""
    tot, achou = 0.0, False
    contas = [c for c in vals if c.startswith(prefixo)]
    for c in contas:
        if any(o != c and o.startswith(c + ".") for o in contas):
            continue  # só folhas, para não somar duas vezes
        d = descs.get(c, "")
        if any(t in d for t in termos):
            tot += vals[c] * sinal
            achou = True
    return tot if achou else None


def fluxo12m(dem, cnpj, dt_ult, dt_ant_ano, dt_dfp, fn):
    """Valor dos últimos 12 meses de uma conta de resultado. Sem período completo e válido: None (nunca estima)."""
    for d in (dt_ult,) + (() if dt_ult.endswith("-12-31") else (dt_ant_ano, dt_dfp)):
        if not periodo_valido(dem.ytd.get((cnpj, d))):
            return None
    atual = fn(dem.ytd.get((cnpj, dt_ult), {}), dem.desc.get((cnpj, dt_ult), {}))
    if atual is None:
        return None
    if dt_ult.endswith("-12-31"):
        return atual
    anual = fn(dem.ytd.get((cnpj, dt_dfp), {}), dem.desc.get((cnpj, dt_dfp), {})) if dt_dfp else None
    ant = fn(dem.ytd.get((cnpj, dt_ant_ano), {}), dem.desc.get((cnpj, dt_ant_ano), {})) if dt_ant_ano else None
    if anual is None or ant is None:
        return None
    return anual + atual - ant


def conta(c):
    return lambda v, d: v.get(c)


def lucro(v, d):
    # atribuído aos controladores quando preenchido; algumas companhias deixam 0 nesse campo
    for c in ("3.11.01", "3.11", "3.09"):
        if v.get(c):
            return v[c]
    return None


def periodo_valido(v):
    """Entregas com receita e lucro zerados (erro de preenchimento) não entram no cálculo."""
    return bool(v) and any(v.get(c) for c in ("3.01", "3.11", "3.09", "3.05"))


def da(v, d):
    x = soma_desc(v, d, "DFC:6.01", ["deprecia", "amortiza", "exaust"])
    return abs(x) if x is not None else None


def proventos_pagos(v, d):
    x = soma_desc(v, d, "DFC:6.03", ["dividend", "juros sobre o capital", "juros sobre capital", "jcp"])
    return abs(x) if x is not None else None


def main():
    hoje = dt.date.today()
    anos = [hoje.year, hoje.year - 1]
    dem = Demonstrativos()
    dfp_ano = None
    for a in (hoje.year - 1, hoje.year - 2):
        z = zip_cvm("dfp", a)
        if z and linhas(z, f"dfp_cia_aberta_DRE_con_{a}.csv"):
            dem.carrega(z, "dfp_cia_aberta", a)
            dfp_ano = dfp_ano or a
    acoes = {}
    for a in anos:
        z = zip_cvm("itr", a)
        dem.carrega(z, "itr_cia_aberta", a)
        for r in linhas(z, f"itr_cia_aberta_composicao_capital_{a}.csv"):
            k = (r["CNPJ_CIA"], r["DT_REFER"])
            tot = (num(r.get("QT_ACAO_TOTAL_CAP_INTEGR")) or 0) - (num(r.get("QT_ACAO_TOTAL_TESOURO")) or 0)
            if tot > 0:
                acoes[k] = tot
    if dfp_ano:
        for r in linhas(zip_cvm("dfp", dfp_ano), f"dfp_cia_aberta_composicao_capital_{dfp_ano}.csv"):
            tot = (num(r.get("QT_ACAO_TOTAL_CAP_INTEGR")) or 0) - (num(r.get("QT_ACAO_TOTAL_TESOURO")) or 0)
            if tot > 0:
                acoes[(r["CNPJ_CIA"], r["DT_REFER"])] = tot

    # tickers: cadastro FCA (valores mobiliários negociados)
    tick = {}
    for a in anos:
        for r in linhas(zip_cvm("fca", a), f"fca_cia_aberta_valor_mobiliario_{a}.csv"):
            t = (r.get("Codigo_Negociacao") or "").strip().upper()
            if t and (r.get("Data_Fim_Negociacao") or "") == "" and "aç" in (r.get("Valor_Mobiliario") or "").lower() or (t and "unit" in (r.get("Valor_Mobiliario") or "").lower()):
                tick[t] = r["CNPJ_Companhia"]

    setor = {}
    for a in anos:
        for r in linhas(zip_cvm("fca", a), f"fca_cia_aberta_geral_{a}.csv"):
            if r.get("Setor_Atividade"):
                setor[r["CNPJ_Companhia"]] = r["Setor_Atividade"].strip()

    datas = {}
    for (cnpj, dtr) in list(dem.bal) + list(dem.ytd):
        datas.setdefault(cnpj, set()).add(dtr)

    empresas = {}
    for cnpj, ds in datas.items():
        ult = max(ds)
        ano_ult = int(ult[:4])
        ant = f"{ano_ult - 1}{ult[4:]}"
        dfp = f"{ano_ult - 1}-12-31"
        b = dem.bal.get((cnpj, ult), {})
        e = {"ref": ult}
        e["lucro12m"] = fluxo12m(dem, cnpj, ult, ant, dfp, lucro)
        e["receita12m"] = fluxo12m(dem, cnpj, ult, ant, dfp, conta("3.01"))
        e["ebit12m"] = fluxo12m(dem, cnpj, ult, ant, dfp, conta("3.05"))
        e["da12m"] = fluxo12m(dem, cnpj, ult, ant, dfp, da)
        e["prov12m"] = fluxo12m(dem, cnpj, ult, ant, dfp, proventos_pagos)
        pl_tot, minor = b.get("2.03"), b.get("2.03.09")
        e["pl"] = (pl_tot - minor) if pl_tot is not None and minor is not None and abs(minor) < abs(pl_tot) else pl_tot
        e["ac"], e["pc"] = b.get("1.01"), b.get("2.01")
        caixa = (b.get("1.01.01") or 0) + (b.get("1.01.02") or 0)
        div = None
        if b.get("2.01.04") is not None or b.get("2.02.01") is not None:
            div = (b.get("2.01.04") or 0) + (b.get("2.02.01") or 0)
        e["divLiq"] = (div - caixa) if div is not None else None
        e["acoes"] = acoes.get((cnpj, ult)) or next((acoes[(cnpj, d)] for d in sorted(ds, reverse=True) if (cnpj, d) in acoes), None)
        # algumas companhias informam a quantidade de ações em milhares: patrimônio por ação acima de
        # R$ 1.000 indica isso (nenhuma ação relevante da B3 tem VPA nesse nível)
        if e["acoes"] and e["pl"] and e["pl"] / e["acoes"] > 1000:
            e["acoes"] *= 1000
        e["setor"] = setor.get(cnpj, "")
        empresas[cnpj] = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in e.items()}

    saida = {}
    for t, cnpj in tick.items():
        if cnpj in empresas:
            saida[t] = empresas[cnpj]
    out = {"fonte": "CVM - DFP e ITR de companhias abertas (dados.cvm.gov.br)",
           "gerado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "acoes": saida}
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print(f"{len(saida)} tickers de {len(empresas)} companhias gravados em {SAIDA}")


if __name__ == "__main__":
    main()
