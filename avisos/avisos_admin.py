"""Avisos para o administrador da família CruzOn (Planner, Finance e CruzInvest).

Roda pela rotina do GitHub (.github/workflows/avisos-admin.yml) a cada 15 minutos e avisa,
por e-mail e/ou WhatsApp, o que aconteceu desde a última vez que rodou com sucesso:
  - cadastro novo (com o app de origem e quem indicou);
  - período de teste que terminou;
  - plano mensal ou anual que venceu;
  - recado novo (inclusive "paguei com Pix").

Segredos (GitHub > Settings > Secrets and variables > Actions), nunca no código:
  SUPABASE_SERVICE_KEY   chave service_role do Supabase (Project Settings > API)
  AVISO_EMAIL            e-mail que recebe os avisos
  GMAIL_USER             conta Gmail que envia (pode ser a mesma do AVISO_EMAIL)
  GMAIL_APP_PASSWORD     senha de app do Gmail (16 letras)
  CALLMEBOT_PHONE        opcional: seu WhatsApp com país e DDD (ex.: 5514999998888)
  CALLMEBOT_APIKEY       opcional: chave do CallMeBot para receber no WhatsApp

O repositório é público: o log da rotina mostra só quantidades, nunca nomes ou e-mails.
"""
import json
import os
import re
import smtplib
import sys
import urllib.parse
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

SB_URL = "https://qflpwxyyzimlmnizgltl.supabase.co"
SITE = "https://lucascruz2012.github.io/cruzon-planner/"
APPS = {"planner": "CruzOn Planner", "finance": "CruzOn Finance", "invest": "CruzInvest"}
BR = timezone(timedelta(hours=-3))
MARCA_SINO = "🔔 "


def env(nome):
    return (os.environ.get(nome) or "").strip()


def pede(url, headers=None, data=None, metodo=None):
    req = urllib.request.Request(url, headers=headers or {}, data=data, method=metodo)
    with urllib.request.urlopen(req, timeout=40) as r:
        corpo = r.read().decode("utf-8")
        return json.loads(corpo) if corpo else None


def sb(caminho, corpo=None):
    chave = env("SUPABASE_SERVICE_KEY")
    h = {"apikey": chave, "Authorization": "Bearer " + chave}
    if corpo is None:
        # leitura: tenta de novo se o Supabase oscilar (erros 5xx como 522, ou sem conexão)
        for t in range(3):
            try:
                return pede(SB_URL + caminho, h)
            except urllib.error.HTTPError as e:
                if e.code < 500 or t == 2:
                    raise
            except urllib.error.URLError:
                if t == 2:
                    raise
            time.sleep(15 * (t + 1))
    h.update({"Content-Type": "application/json", "Prefer": "return=minimal"})
    return pede(SB_URL + caminho, h, json.dumps(corpo).encode("utf-8"), "POST")


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def quando(texto):
    if not texto:
        return None
    t = texto.strip().replace("Z", "+00:00").replace(" ", "T")
    m = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?([+-]\d\d:?\d\d)?$", t)
    if not m:
        return None
    frac = ((m.group(2) or "") + "000000")[:6]  # no máximo 6 casas nos segundos
    dt = datetime.fromisoformat(f"{m.group(1)}.{frac}{m.group(3) or '+00:00'}")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def br(dt):
    return dt.astimezone(BR).strftime("%d/%m/%Y %H:%M") if dt else "-"


def inicio_janela(agora):
    """Começa onde a última execução com sucesso começou (assim nada fica de fora nem se repete)."""
    padrao = agora - timedelta(minutes=20)
    repo, token = env("GITHUB_REPOSITORY"), env("GITHUB_TOKEN")
    if not repo or not token:
        return padrao
    try:
        url = f"https://api.github.com/repos/{repo}/actions/workflows/avisos-admin.yml/runs?status=success&per_page=1"
        j = pede(url, {"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"})
        runs = (j or {}).get("workflow_runs") or []
        if runs:
            ultimo = quando(runs[0].get("run_started_at") or runs[0].get("created_at"))
            if ultimo and agora - ultimo < timedelta(days=3):
                return ultimo
    except Exception as e:  # sem histórico: usa os últimos 20 minutos
        print("Aviso: não consegui ler a última execução:", type(e).__name__)
    return padrao


def usuarios():
    todos, pagina = [], 1
    while True:
        j = sb(f"/auth/v1/admin/users?page={pagina}&per_page=200")
        lista = (j or {}).get("users") or []
        todos += lista
        if len(lista) < 200:
            return todos
        pagina += 1


def eventos(desde, ate):
    ev = {"cadastros": [], "testes": [], "vencidos": [], "recados": []}
    us = usuarios()
    por_codigo = {u["id"].replace("-", "")[:10]: u for u in us}
    for u in us:
        criado = quando(u.get("created_at"))
        if not criado or not (desde < criado <= ate):
            continue
        meta = u.get("user_metadata") or {}
        quem = por_codigo.get(str(meta.get("ref") or "")[:10])
        ev["cadastros"].append({
            "id": u.get("id"),
            "nome": meta.get("nome") or meta.get("name") or "",
            "email": u.get("email") or "",
            "app": APPS.get(meta.get("app") or "planner", "CruzOn Planner"),
            "quando": criado,
            "indicou": ((quem.get("user_metadata") or {}).get("nome") or quem.get("email")) if quem else "",
        })
    janela = f"and=(acesso_ate.gt.{iso(desde)},acesso_ate.lte.{iso(ate)})"
    for p in sb("/rest/v1/perfis?select=id,nome,email,plano,acesso_ate,isento&" + janela) or []:
        if p.get("isento"):
            continue
        item = {"id": p.get("id"), "nome": p.get("nome") or "", "email": p.get("email") or "", "plano": p.get("plano") or "", "quando": quando(p.get("acesso_ate")), "app": "CruzOn Planner"}
        (ev["testes"] if p.get("plano") == "teste" else ev["vencidos"]).append(item)
    try:  # Finance e CruzInvest (tabela app_acessos, arquivo supabase/15-acesso-por-app.sql)
        por_id = {u["id"]: u for u in us}
        for a in sb("/rest/v1/app_acessos?select=user_id,app,plano,acesso_ate,isento,bloqueado&" + janela) or []:
            if a.get("isento") or a.get("bloqueado"):
                continue
            u = por_id.get(a.get("user_id")) or {}
            item = {"id": a.get("user_id"), "nome": (u.get("user_metadata") or {}).get("nome") or "", "email": u.get("email") or "", "plano": a.get("plano") or "",
                    "quando": quando(a.get("acesso_ate")), "app": APPS.get(a.get("app"), a.get("app") or "")}
            (ev["testes"] if a.get("plano") == "teste" else ev["vencidos"]).append(item)
    except Exception as e:
        print("Aviso: não consegui ler os acessos por app:", type(e).__name__)
    try:
        filtro = f"and=(criado_em.gt.{iso(desde)},criado_em.lte.{iso(ate)})"
        for r in sb("/rest/v1/recados?select=nome,email,texto,criado_em&order=criado_em.asc&" + filtro) or []:
            if (r.get("texto") or "").startswith(MARCA_SINO):  # avisos que o próprio vigia colocou no sino
                continue
            ev["recados"].append({"nome": r.get("nome") or "", "email": r.get("email") or "", "texto": r.get("texto") or "", "quando": quando(r.get("criado_em"))})
    except Exception as e:
        print("Aviso: não consegui ler os recados:", type(e).__name__)
    return ev


def monta(ev):
    partes_txt, partes_html = [], []

    def bloco(titulo, linhas):
        partes_txt.append(titulo.upper() + "\n" + "\n".join("- " + l for l in linhas))
        partes_html.append(f"<h3 style='margin:18px 0 6px;color:#0C1F2B;font-size:15px'>{escape(titulo)}</h3><ul style='margin:0;padding-left:18px'>"
                           + "".join(f"<li style='margin:4px 0'>{escape(l)}</li>" for l in linhas) + "</ul>")

    if ev["cadastros"]:
        bloco(f"Cadastros novos ({len(ev['cadastros'])})", [
            f"{c['nome'] or 'Sem nome'} <{c['email']}> no {c['app']} em {br(c['quando'])}" + (f" · indicado por {c['indicou']}" if c["indicou"] else "")
            for c in ev["cadastros"]])
    if ev["testes"]:
        bloco(f"Períodos de teste que terminaram ({len(ev['testes'])})", [f"{t['nome'] or 'Sem nome'} <{t['email']}> · {t.get('app', 'CruzOn Planner')} · terminou em {br(t['quando'])}" for t in ev["testes"]])
    if ev["vencidos"]:
        bloco(f"Planos que venceram ({len(ev['vencidos'])})", [f"{t['nome'] or 'Sem nome'} <{t['email']}> · {t.get('app', 'CruzOn Planner')} · plano {t['plano'] or '-'} venceu em {br(t['quando'])}" for t in ev["vencidos"]])
    if ev["recados"]:
        bloco(f"Recados novos ({len(ev['recados'])})", [f"{r['nome'] or 'Sem nome'} <{r['email']}>: {r['texto'][:300]}" for r in ev["recados"]])
    total = sum(len(v) for v in ev.values())
    assunto = "CruzOn: " + ", ".join(
        f"{len(ev[k])} {n}" for k, n in [("cadastros", "cadastro(s) novo(s)"), ("testes", "teste(s) encerrado(s)"), ("vencidos", "plano(s) vencido(s)"), ("recados", "recado(s)")] if ev[k])
    rodape_txt = f"\nPara liberar ou renovar o acesso: {SITE} > Ajustes > Perfis de acesso (+1 mês, +1 ano)."
    html = ("<div style='font-family:Arial,Helvetica,sans-serif;color:#263746;max-width:620px'>"
            "<div style='background:#0C1F2B;color:#fff;padding:14px 18px;border-radius:10px 10px 0 0;font-weight:bold'>CruzOn · avisos do administrador</div>"
            "<div style='border:1px solid #E3E8EC;border-top:0;padding:6px 18px 18px;border-radius:0 0 10px 10px'>" + "".join(partes_html) +
            f"<p style='margin-top:18px'><a href='{SITE}' style='background:#00C853;color:#0C1F2B;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:bold'>Abrir o CruzOn Planner</a></p>"
            "<p style='font-size:12px;color:#566674'>Para liberar ou renovar: Ajustes › Perfis de acesso (Planner: +1 mês, +1 ano; Finance e CruzInvest: botão Finance e CruzInvest…).</p></div></div>")
    return total, assunto, "\n\n".join(partes_txt) + "\n" + rodape_txt, html


def copias():
    """E-mails em cópia definidos no Planner (Ajustes › Planos e cobrança), coluna config_app.aviso_cc."""
    try:
        r = sb("/rest/v1/config_app?select=aviso_cc&id=eq.1") or []
        txt = (r[0].get("aviso_cc") if r else "") or ""
        return [x.strip() for x in re.split(r"[,;\s]+", txt) if re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", x.strip())]
    except Exception:
        return []  # coluna ainda não criada (17-aviso-copia.sql)


def manda_email(assunto, texto, html):
    usuario, senha, para = env("GMAIL_USER"), env("GMAIL_APP_PASSWORD").replace(" ", ""), env("AVISO_EMAIL") or env("GMAIL_USER")
    if not (usuario and senha and para):
        print("E-mail não configurado (faltam GMAIL_USER, GMAIL_APP_PASSWORD ou AVISO_EMAIL).")
        return False
    cc = [x for x in copias() if x.lower() != para.lower()]
    m = MIMEMultipart("alternative")
    m["Subject"], m["From"], m["To"] = assunto, f"Avisos CruzOn <{usuario}>", para
    if cc:
        m["Cc"] = ", ".join(cc)
    m.attach(MIMEText(texto, "plain", "utf-8"))
    m.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=40) as s:
        s.login(usuario, senha)
        s.sendmail(usuario, [para] + cc, m.as_string())
    print("E-mail enviado." + (f" Com {len(cc)} cópia(s)." if cc else ""))
    return True


def manda_whatsapp(assunto, texto):
    fone, chave = env("CALLMEBOT_PHONE"), env("CALLMEBOT_APIKEY")
    if not (fone and chave):
        print("WhatsApp não configurado (opcional).")
        return False
    msg = (assunto + "\n\n" + texto)[:1400]
    url = "https://api.callmebot.com/whatsapp.php?" + urllib.parse.urlencode({"phone": fone, "text": msg, "apikey": chave})
    urllib.request.urlopen(url, timeout=40).read()
    print("WhatsApp enviado.")
    return True


def sino(ev):
    """Coloca os avisos também no sino do Planner (recados do administrador)."""
    linhas = []
    for c in ev["cadastros"]:
        linhas.append((c, f"Novo cadastro no {c['app']}" + (f", indicado por {c['indicou']}" if c["indicou"] else "") + ". O período de teste começa no primeiro uso."))
    for t in ev["testes"]:
        linhas.append((t, f"O período de teste do {t.get('app', 'CruzOn Planner')} terminou. Bom momento para oferecer a assinatura."))
    for t in ev["vencidos"]:
        linhas.append((t, f"O plano {t['plano'] or ''} do {t.get('app', 'CruzOn Planner')} venceu.".replace("plano  do", "plano do")))
    corpo = [{"user_id": x.get("id"), "nome": x.get("nome") or None, "email": x.get("email") or None, "texto": MARCA_SINO + txt} for x, txt in linhas if x.get("id")]
    if not corpo:
        return
    try:
        sb("/rest/v1/recados", corpo)
        print(f"Sino: {len(corpo)} aviso(s).")
    except Exception as e:
        print("Aviso: não consegui colocar no sino:", type(e).__name__)


def main():
    if not env("SUPABASE_SERVICE_KEY"):
        print("Falta o segredo SUPABASE_SERVICE_KEY. Nada a fazer.")
        return 0
    agora = datetime.now(timezone.utc)
    desde = inicio_janela(agora)
    ev = eventos(desde, agora)
    total, assunto, texto, html = monta(ev)
    print(f"Janela: {iso(desde)} a {iso(agora)} · " + ", ".join(f"{k}: {len(v)}" for k, v in ev.items()))
    teste = env("AVISO_TESTE").lower() == "true"
    if teste and not total:
        assunto = "CruzOn: teste do vigia (tudo funcionando)"
        texto = f"Este é um e-mail de teste. O vigia conseguiu ler o Supabase e enviar e-mail.\nNa última janela ({br(desde)} a {br(agora)}) não houve novidades."
        html = f"<div style='font-family:Arial,sans-serif;color:#263746'><h3 style='color:#0C1F2B'>✅ O vigia está funcionando</h3><p>{escape(texto)}</p><p>A partir de agora você recebe aqui os cadastros novos, os testes que terminam, os planos que vencem e os avisos de pagamento por Pix.</p></div>"
    elif not total:
        return 0
    configurado = bool(env("GMAIL_APP_PASSWORD") or env("CALLMEBOT_APIKEY"))
    enviou = False
    for envio in (lambda: manda_email(assunto, texto, html), lambda: manda_whatsapp(assunto, texto)):
        try:
            enviou = envio() or enviou
        except Exception as e:
            print("Falha ao enviar:", type(e).__name__)
    if total and (enviou or not configurado):
        sino(ev)
    # se havia como enviar e nada saiu, a execução falha e a próxima tenta de novo a mesma janela
    return 1 if configurado and not enviou else 0


if __name__ == "__main__":
    sys.exit(main())
