"""
Envio do boletim por email via SMTP (ex: Gmail).

Credenciais vem de variaveis de ambiente (Secrets do GitHub):
  SMTP_HOST      ex: smtp.gmail.com
  SMTP_PORT      ex: 587
  SMTP_USER      seu email de envio
  SMTP_PASSWORD  "senha de app" do Gmail (NAO a senha normal)
  MAIL_FROM      (opcional) remetente; padrao = SMTP_USER
  MAIL_TO        (opcional) destinatario; padrao = config.yaml
"""

from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def credenciais_presentes() -> bool:
    return all(os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))


def enviar(assunto: str, html: str, destino_padrao: str) -> bool:
    if not credenciais_presentes():
        print("! SMTP nao configurado; pulando envio de email.")
        return False

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    remetente = os.environ.get("MAIL_FROM", user)
    destino = os.environ.get("MAIL_TO", destino_padrao)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destino
    msg.attach(MIMEText("Seu cliente de email nao suporta HTML. Veja o painel online.", "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=60) as s:
                s.login(user, password)
                s.sendmail(remetente, [destino], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=60) as s:
                s.starttls()
                s.login(user, password)
                s.sendmail(remetente, [destino], msg.as_string())
        print(f"Email enviado para {destino}.")
        return True
    except Exception as exc:
        print(f"! Falha ao enviar email: {exc}")
        return False
