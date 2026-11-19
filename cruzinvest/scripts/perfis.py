"""Gera cruzinvest/dados/perfis.json para o "Conheça a empresa" e o "Conheça o fundo" do app.

Ações (por ticker):
  - CVM, FCA: nome, setor, descrição da atividade, site e endereço da sede (para a vista aérea no mapa).
  - Wikidata: liga o ticker da B3 ao artigo da Wikipédia em português.
  - Wikipédia (pt): resumo do artigo e fotos do artigo (Wikimedia Commons, licenças livres).
FIIs e Fiagros (por ticker):
  - CVM, informe trimestral: segmento, mandato, administrador, site e imóveis (nome, endereço, área, vacância).
  - CVM, informe mensal: composição da carteira (imóveis, CRI/CRA, LCI/LCA, cotas de outros FIIs, caixa).

Sem dados pessoais. Uso: python3 cruzinvest/scripts/perfis.py [arquivo_saida]   (só biblioteca padrão)
"""
import csv
import datetime as dt
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile

SAIDA = sys.argv[1] if len(sys.argv) > 1 else "cruzinvest/dados/perfis.json"
UA = {"User-Agent": "CruzInvestDados/1.0 (atualizacao diaria de dados publicos; python-urllib)"}
CVM = "https://dados.cvm.gov.br/dados"


def baixa(url, tentativas=3, cab=None):
    for t in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **(cab or {})}), timeout=120) as r:
                return r.read()
        except Exception as e:
            if t == tentativas - 1:
                print(f"aviso: {url[:100]}: {e}", file=sys.stderr)
                return None
            time.sleep(65 if getattr(e, "code", 0) == 429 else 4 * (t + 1))  # 429: o Wikidata pede 1 consulta por minuto


def zip_cvm(url):
    b = baixa(url)
    return zipfile.ZipFile(io.BytesIO(b)) if b else None


def linhas(z, nome):
    if not z or nome not in z.namelist():
        return []
    with z.open(nome) as f:
        return list(csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"))


def num(v):
    try:
        return float(str(v).replace(",", "."))
    except Exception:
        return 0.0


def limpa(t, n):
    t = re.sub(r"\s+", " ", (t or "").strip())
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def zips_ano(fmt):
    hoje = dt.date.today()
    out = []
    for a in (hoje.year, hoje.year - 1):
        z = zip_cvm(fmt.format(ano=a))
        if z:
            out.append((a, z))
    return out


# ---------------------------------------------------------------- ações
PARADAS = {"companhia", "energética", "energia", "minas", "gerais", "saneamento", "brasil", "brasileira", "brasileiro", "grupo", "banco",
           "participações", "holding", "industrias", "indústrias", "estado", "paraná", "paulo", "janeiro", "federal", "nacional", "sistema"}


def acoes():
    res = {}
    zs = zips_ano(CVM + "/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_{ano}.zip")
    tk_cnpj, geral, sede = {}, {}, {}
    for a, z in reversed(zs):  # ano mais novo por último: sobrescreve
        for r in linhas(z, f"fca_cia_aberta_valor_mobiliario_{a}.csv"):
            tk = (r.get("Codigo_Negociacao") or "").strip().upper()
            if re.fullmatch(r"[A-Z]{4}\d{1,2}", tk) and not (r.get("Data_Fim_Negociacao") or "").strip():
                tk_cnpj[tk] = r["CNPJ_Companhia"]
        for r in linhas(z, f"fca_cia_aberta_geral_{a}.csv"):
            geral[r["CNPJ_Companhia"]] = r
        for r in linhas(z, f"fca_cia_aberta_endereco_{a}.csv"):
            if "Sede" in (r.get("Tipo_Endereco") or ""):
                sede[r["CNPJ_Companhia"]] = r
    for tk, cnpj in tk_cnpj.items():
        g, e = geral.get(cnpj, {}), sede.get(cnpj)
        end = ""
        if e:
            end = ", ".join(x for x in [(e.get("Logradouro") or "").strip(), (e.get("Bairro") or "").strip(),
                                        (e.get("Cidade") or "").strip() + (" - " + e["Sigla_UF"].strip() if (e.get("Sigla_UF") or "").strip() else "")] if x)
        site = (g.get("Pagina_Web") or "").strip()
        if site and not site.lower().startswith("http"):
            site = "https://" + site.lstrip("/")
        res[tk] = {"t": "acao", "nome": (g.get("Nome_Empresarial") or "").strip(), "setor": (g.get("Setor_Atividade") or "").strip(),
                   "ativ": limpa(g.get("Descricao_Atividade"), 400), "site": site, "sede": end,
                   "desde": (g.get("Data_Constituicao") or "")[:4]}
    # Wikidata: ticker da B3 -> artigo da Wikipédia em português
    q = """SELECT ?tk ?art ?img WHERE { ?item p:P414 ?st . ?st pq:P249 ?tk . FILTER(REGEX(?tk,"^[A-Z]{4}[0-9]{1,2}$"))
           ?art schema:about ?item; schema:isPartOf <https://pt.wikipedia.org/> . OPTIONAL { ?item wdt:P18 ?img } }"""
    b = baixa("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(q), cab={"Accept": "application/sparql-results+json"})
    tk_art, art_img = {}, {}
    if b:
        for x in json.loads(b)["results"]["bindings"]:
            t = urllib.parse.unquote(x["art"]["value"].rsplit("/wiki/", 1)[1]).replace("_", " ")
            tk_art[x["tk"]["value"]] = t
            if x.get("img"):  # foto escolhida no Wikidata para a empresa
                art_img[t] = urllib.parse.unquote(x["img"]["value"].rsplit("/", 1)[1])
    titulos = sorted({tk_art[t] for t in res if t in tk_art})
    wiki = {}
    for i in range(0, len(titulos), 20):
        lote = titulos[i:i + 20]
        url = ("https://pt.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=extracts|images&exintro=1&explaintext=1"
               "&exlimit=20&imlimit=500&titles=" + urllib.parse.quote("|".join(lote)))
        b = baixa(url, tentativas=5)
        time.sleep(6)  # a Wikipédia limita consultas seguidas
        if not b:
            continue
        j = json.loads(b).get("query", {})
        red = {r["from"]: r["to"] for r in j.get("redirects", []) + j.get("normalized", [])}
        por_titulo = {p["title"]: p for p in j.get("pages", {}).values()}
        for t in lote:
            p = por_titulo.get(red.get(t, t))
            if not p or "missing" in p:
                continue
            # só fotos que citam a empresa no nome do arquivo (sigla entre parênteses no resumo, palavras do título)
            chaves = {w.lower() for w in re.findall(r"\(([A-Za-zÀ-ú]{3,12})[;)]", p.get("extract") or "")[:3]}
            chaves |= {w.lower() for w in re.split(r"[\s.,()-]+", p["title"]) if len(w) >= 4 and w.lower() not in PARADAS}
            fotos = [art_img[t]] if t in art_img and re.search(r"\.(jpe?g)$", art_img[t], re.I) else []
            for im in p.get("images", []):
                n = im["title"].split(":", 1)[-1]
                if (re.search(r"\.(jpe?g)$", n, re.I) and n not in fotos
                        and not re.search(r"logo|bandeira|flag|mapa|map|brasão|assinatura|signature|icon|cpmi|cerim|reuni|presidente|ministr|posse|retrato", n, re.I)
                        and any(c in n.lower() for c in chaves)):
                    fotos.append(n)
            wiki[t] = {"wiki": p["title"], "resumo": limpa(p.get("extract"), 700), "fotos": fotos[:5]}
    # endereço da miniatura padrão (960 px), autor e licença de cada foto, para exibir com o crédito certo
    nomes = sorted({f for w in wiki.values() for f in w["fotos"]})
    meta = {}
    for i in range(0, len(nomes), 40):
        lote = nomes[i:i + 40]
        url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=url|extmetadata"
               "&iiurlwidth=960&iiextmetadatafilter=Artist|LicenseShortName&titles=" + urllib.parse.quote("|".join("File:" + n for n in lote)))
        b = baixa(url, tentativas=5)
        time.sleep(3)
        if not b:
            continue
        j = json.loads(b).get("query", {})
        red = {r["to"]: r["from"] for r in j.get("normalized", [])}
        for pg in j.get("pages", {}).values():
            ii = (pg.get("imageinfo") or [{}])[0]
            if not ii.get("thumburl"):
                continue
            em = ii.get("extmetadata") or {}
            autor = re.sub(r"<[^>]+>", "", (em.get("Artist") or {}).get("value", "")).strip()
            nome = red.get(pg["title"], pg["title"]).split(":", 1)[-1]
            meta[nome] = {"url": ii["thumburl"], "pag": ii.get("descriptionurl", ""), "autor": limpa(autor, 60),
                          "lic": (em.get("LicenseShortName") or {}).get("value", "")}
    for w in wiki.values():
        w["fotos"] = [dict(meta[f], nome=f) for f in w["fotos"] if f in meta][:5]
    for tk, v in res.items():
        if tk in tk_art and tk_art[tk] in wiki:
            v.update(wiki[tk_art[tk]])
    return res


# ---------------------------------------------------------------- FIIs
def tk_do_isin(isin):
    isin = (isin or "").strip().upper()
    return isin[2:6] + "11" if re.fullmatch(r"BR[A-Z]{4}CTF\w{3}", isin) else ""


def fiis():
    res = {}
    tri = zips_ano(CVM + "/FII/DOC/INF_TRIMESTRAL/DADOS/inf_trimestral_fii_{ano}.zip")
    men = zips_ano(CVM + "/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{ano}.zip")
    # patrimônio líquido mais recente de cada CNPJ: desempata quando dois fundos declaram o mesmo ISIN (erro de cadastro na CVM)
    pl = {}
    for a, z in men:
        for r in linhas(z, f"inf_mensal_fii_complemento_{a}.csv"):
            c, d = r["CNPJ_Fundo_Classe"], r["Data_Referencia"]
            if c not in pl or d > pl[c][0]:
                pl[c] = (d, num(r.get("Patrimonio_Liquido")))
    linhas_geral = {}
    for a, z in reversed(men):
        for r in sorted(linhas(z, f"inf_mensal_fii_geral_{a}.csv"), key=lambda r: r["Data_Referencia"]):
            linhas_geral[("m", r["CNPJ_Fundo_Classe"])] = r
    for a, z in reversed(tri):
        for r in sorted(linhas(z, f"inf_trimestral_fii_geral_{a}.csv"), key=lambda r: r["Data_Referencia"]):
            linhas_geral[("t", r["CNPJ_Fundo_Classe"])] = r
    cand = {}
    for (_, c), r in linhas_geral.items():
        tk = tk_do_isin(r.get("Codigo_ISIN"))
        if tk:
            cand.setdefault(tk, set()).add(c)
    cnpj_tk, info = {}, {}
    for tk, cs in cand.items():
        c = max(cs, key=lambda c: (pl.get(c, ("", 0))[1], c))
        cnpj_tk[c] = tk
        info[tk] = linhas_geral.get(("t", c)) or linhas_geral[("m", c)]
    for tk, r in info.items():
        site = (r.get("Site") or "").strip()
        if site and not site.lower().startswith("http"):
            site = "https://" + site.lstrip("/")
        res[tk] = {"t": "fii", "nome": (r.get("Nome_Fundo_Classe") or "").strip(), "seg": (r.get("Segmento_Atuacao") or "").strip(),
                   "mandato": (r.get("Mandato") or "").strip(), "gestao": (r.get("Tipo_Gestao") or "").strip(),
                   "adm": (r.get("Nome_Administrador") or "").strip(), "site": site, "desde": (r.get("Data_Funcionamento") or "")[:4]}
    # imóveis do trimestre mais recente de cada fundo
    imv = {}
    for a, z in tri:
        for r in linhas(z, f"inf_trimestral_fii_imovel_{a}.csv"):
            tk = cnpj_tk.get(r["CNPJ_Fundo_Classe"])
            if not tk:
                continue
            d = r["Data_Referencia"]
            cur = imv.get(tk)
            if cur is None or d > cur[0]:
                imv[tk] = (d, [])
                cur = imv[tk]
            if d == cur[0]:
                cur[1].append({"nome": limpa(r.get("Nome_Imovel"), 90), "end": limpa(r.get("Endereco"), 140), "area": round(num(r.get("Area"))),
                               "vac": round(num(r.get("Percentual_Vacancia")), 4), "rec": round(num(r.get("Percentual_Receitas_FII")), 4),
                               "cls": (r.get("Classe") or "").strip()})
    for tk, (d, lst) in imv.items():
        if tk in res:
            vistos, uniq = set(), []
            for i in sorted(lst, key=lambda x: (-x["rec"], -x["area"])):
                k = (i["nome"], i["end"])
                if k not in vistos:
                    vistos.add(k)
                    uniq.append(i)
            res[tk]["imoveis"] = uniq[:15]
            res[tk]["nImoveis"] = len(uniq)
            res[tk]["refImoveis"] = d
    # composição da carteira no mês mais recente
    comp = {}
    for a, z in men:
        for r in linhas(z, f"inf_mensal_fii_ativo_passivo_{a}.csv"):
            tk = cnpj_tk.get(r["CNPJ_Fundo_Classe"])
            if tk and (tk not in comp or r["Data_Referencia"] > comp[tk]["ref"]):
                g = lambda *c: sum(num(r.get(x)) for x in c)
                v = {"imoveis": g("Direitos_Bens_Imoveis"),
                     "cri": g("CRI", "CRI_CRA"), "lci": g("LCI", "LCI_LCA", "Letras_Hipotecarias", "LIG"),
                     "fii": g("FII"), "acoes": g("Acoes", "Acoes_Sociedades_Atividades_FII", "Cotas_Sociedades_Atividades_FII", "Fundo_Acoes", "FIP"),
                     "caixa": g("Disponibilidades", "Titulos_Publicos", "Titulos_Privados", "Fundos_Renda_Fixa"),
                     "outros": g("Debentures", "Notas_Promissorias", "FDIC", "Outras_Cotas_FI", "CEPAC", "Outros_Valores_Mobliarios")}
                if not v["imoveis"]:
                    v["imoveis"] = g("Terrenos", "Imoveis_Renda_Acabados", "Imoveis_Renda_Construcao", "Imoveis_Venda_Acabados", "Imoveis_Venda_Construcao", "Outros_Direitos_Reais")
                comp[tk] = {"ref": r["Data_Referencia"], **v}
    for tk, c in comp.items():
        tot = sum(v for k, v in c.items() if k != "ref")
        if tk in res and tot > 0:
            res[tk]["comp"] = {k: round(v / tot, 4) for k, v in c.items() if k != "ref" and v > 0}
            res[tk]["refComp"] = c["ref"][:7]
    return res


def main():
    out = {"fonte": "CVM (FCA, informes de FII), Wikidata e Wikipédia (fotos: Wikimedia Commons, licenças livres).",
           "gerado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    a = acoes()
    f = fiis()
    if not a and not f:
        sys.exit("nada gerado")
    # se a Wikipédia limitou alguma consulta nesta rodada, mantém o que já havia sido obtido antes
    try:
        with open(SAIDA, encoding="utf-8") as fh:
            ant = json.load(fh)
        for tk, v in a.items():
            o = (ant.get("acoes") or {}).get(tk) or {}
            if not v.get("wiki") and o.get("wiki"):
                v.update({k: o[k] for k in ("wiki", "resumo", "fotos") if k in o})
    except Exception:
        pass
    out["acoes"], out["fiis"] = a, f
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    print(f"{len(a)} ações ({sum(1 for v in a.values() if v.get('wiki'))} com Wikipédia) e {len(f)} fundos "
          f"({sum(1 for v in f.values() if v.get('imoveis'))} com imóveis) gravados em {SAIDA}")


if __name__ == "__main__":
    main()
