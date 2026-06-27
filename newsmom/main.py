"""
Orquestrador do boletim diario.

Fluxo:
  1. carrega config;
  2. define a janela de busca (segunda recupera o fim de semana);
  3. busca noticias por tema;
  4. cura com a IA (Claude) -> traduz, resume, organiza;
  5. renderiza email + painel;
  6. salva o painel (GitHub Pages) e envia o email.

Uso:
  python -m newsmom.main            # roda o boletim do dia
  python -m newsmom.main --teste    # nao envia email, so gera o painel
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from . import curate, emailer, fetch, render

RAIZ = Path(__file__).resolve().parent.parent


def carregar_config(caminho: Path) -> dict:
    with open(caminho, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def janela_horas(cfg: dict, hoje: dt.date) -> int:
    g = cfg["geral"]
    # weekday(): segunda = 0
    if hoje.weekday() == 0:
        return g["janela_horas_segunda"]
    return g["janela_horas_dia"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Boletim diario de noticias")
    parser.add_argument("--teste", action="store_true", help="nao envia email")
    parser.add_argument("--config", default=str(RAIZ / "config.yaml"))
    parser.add_argument("--docs", default=str(RAIZ / "docs"))
    args = parser.parse_args(argv)

    cfg = carregar_config(Path(args.config))
    tz = ZoneInfo(cfg["geral"]["fuso_horario"])
    agora = dt.datetime.now(tz)
    hoje = agora.date()

    # Fim de semana: nao roda (o agendador ja evita, mas garantimos).
    if hoje.weekday() >= 5:
        print(f"Hoje e {hoje} (fim de semana). Nada a fazer.")
        return 0

    horas = janela_horas(cfg, hoje)
    print(f"== Boletim de {hoje} | janela de {horas}h ==")

    artigos = fetch.buscar_tudo(
        cfg["temas"], horas, cfg["geral"]["max_candidatos_por_tema"]
    )
    print(f"Total de candidatos: {len(artigos)}")

    boletim = curate.curar(cfg["temas"], artigos, cfg)

    email_html = render.render_email(boletim, cfg, hoje)
    painel_html = render.render_painel(boletim, cfg, hoje)

    docs_dir = Path(args.docs)
    render.salvar_painel(painel_html, hoje, docs_dir, cfg)
    print(f"Painel salvo em {docs_dir}.")

    assunto = f"Bom dia! Seu boletim de {hoje.strftime('%d/%m')}"
    if args.teste:
        print("Modo --teste: email NAO enviado.")
    else:
        emailer.enviar(assunto, email_html, cfg["destinatario"]["email"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
