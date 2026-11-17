"""Gera cruzinvest/dados/fiis.json com dados públicos de todos os FIIs negociados em bolsa,
a partir do Informe Mensal de FII da CVM (dados.cvm.gov.br):

- vp:   valor patrimonial por cota do informe mais recente;
- rend: rendimento por cota de cada mês dos últimos 13 meses
        (Rendimentos_Distribuir ÷ Cotas_Emitidas; aproximação que fica perto do valor pago).

O arquivo tem dados de todos os fundos, sem nenhuma informação de carteira pessoal.
Uso: python3 cruzinvest/scripts/fiis_cvm.py [arquivo_saida]   (só biblioteca padrão)
"""
import csv
import datetime as dt
import io
import json
import statistics
import sys
import urllib.request
import zipfile

CVM = "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{ano}.zip"
SAIDA = sys.argv[1] if len(sys.argv) > 1 else "cruzinvest/dados/fiis.json"


def zip_cvm(ano):
    req = urllib.request.Request(CVM.format(ano=ano), headers={"User-Agent": "cruzinvest-dados/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return zipfile.ZipFile(io.BytesIO(r.read()))
    except Exception as e:  # ano ainda sem arquivo, por exemplo em janeiro
        print(f"aviso: CVM {ano}: {e}", file=sys.stderr)
        return None


def linhas(z, prefixo):
    nome = next((n for n in z.namelist() if n.startswith(prefixo)), None)
    if not nome:
        return []
    with z.open(nome) as f:
        return list(csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def codigo_do_isin(isin):
    isin = (isin or "").strip().upper()
    # ISIN de cota de FII: BR + 4 letras do código + "CTF" + ...  -> ticker = código + "11"
    if len(isin) == 12 and isin.startswith("BR") and isin[6:9] == "CTF" and isin[2:6].isalpha():
        return isin[2:6]
    return None


def main():
    hoje = dt.date.today()
    zips = [z for z in (zip_cvm(hoje.year - 1), zip_cvm(hoje.year)) if z]
    if not zips:
        sys.exit("nenhum arquivo da CVM disponível")

    geral, comp, ap = {}, {}, {}
    for z in zips:
        for r in linhas(z, "inf_mensal_fii_geral"):
            cod = codigo_do_isin(r.get("Codigo_ISIN"))
            if cod and r.get("Mercado_Negociacao_Bolsa", "S").upper().startswith("S"):
                geral[r["CNPJ_Fundo_Classe"]] = {"codigo": cod, "nome": (r.get("Nome_Fundo_Classe") or "").strip(),
                                                 "seg": (r.get("Segmento_Atuacao") or "").strip()}
        for nome, dest in (("inf_mensal_fii_complemento", comp), ("inf_mensal_fii_ativo_passivo", ap)):
            for r in linhas(z, nome):
                k = (r["CNPJ_Fundo_Classe"], (r.get("Data_Referencia") or "")[:7])
                if not k[1]:
                    continue
                if k not in dest or (num(r.get("Versao")) or 0) >= (num(dest[k].get("Versao")) or 0):
                    dest[k] = r  # fica a versão mais recente de cada informe

    meses_por_cnpj = {}
    for cnpj, mes in comp:
        meses_por_cnpj.setdefault(cnpj, []).append(mes)

    janela = f"{hoje.year - 1}-{hoje.month:02d}"  # 13 meses, cobre atraso na entrega do informe
    escolhido = {}
    for cnpj, g in geral.items():
        meses = sorted(meses_por_cnpj.get(cnpj, []))
        if not meses:
            continue
        ult = meses[-1]
        vp = num(comp[(cnpj, ult)].get("Valor_Patrimonial_Cotas"))
        pl = num(comp[(cnpj, ult)].get("Patrimonio_Liquido")) or 0
        if not vp:
            continue
        rend = []
        for m in meses:
            if m < janela:
                continue
            cotas = num(comp[(cnpj, m)].get("Cotas_Emitidas"))
            dist = num((ap.get((cnpj, m)) or {}).get("Rendimentos_Distribuir"))
            if cotas and dist is not None and dist >= 0:
                rend.append([m, round(dist / cotas, 6)])
        # descarta meses fora da curva (ex.: provisão acumulada de vários meses)
        if len(rend) >= 4:
            med = statistics.median(v for _, v in rend)
            if med > 0:
                rend = [r for r in rend if r[1] <= med * 4]
        t = g["codigo"] + "11"
        chave = (ult >= janela, pl)  # mais de um CNPJ com o mesmo código: o ativo e de maior patrimônio
        if t not in escolhido or chave > escolhido[t][0]:
            escolhido[t] = (chave, {"vp": round(vp, 4), "vpMes": ult, "rend": rend, "nome": g["nome"], "seg": g["seg"]})

    fundos = {t: f for t, (_, f) in sorted(escolhido.items())}
    out = {"fonte": "CVM - Informe Mensal de FII (dados.cvm.gov.br)",
           "gerado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "fundos": fundos}
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print(f"{len(fundos)} FIIs gravados em {SAIDA}")


if __name__ == "__main__":
    main()
