"""
Renderiza o boletim em HTML:
- email (HTML inline, compativel com clientes de email);
- painel do dia (GitHub Pages);
- indice do painel (lista de todos os boletins).
"""

from __future__ import annotations

import datetime as dt
import os
import re
import urllib.parse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATES = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _links_vagas(cfg: dict) -> list[dict]:
    """Gera links de busca salva de vagas para o perfil."""
    vagas = cfg.get("vagas", {})
    palavras = vagas.get("palavras_chave", [])
    local = vagas.get("localizacao", "Brasil")
    termo = " OR ".join(f'"{p}"' for p in palavras) if palavras else "marketing estrategia"
    links = []
    # LinkedIn
    li = "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(
        {"keywords": " ".join(palavras[:3]) or "marketing estrategia", "location": local}
    )
    links.append({"nome": "LinkedIn Vagas", "url": li})
    # Google Jobs
    gj = "https://www.google.com/search?" + urllib.parse.urlencode(
        {"q": f"vagas {' OR '.join(palavras[:3])} {local}", "ibp": "htl;jobs"}
    )
    links.append({"nome": "Google Empregos", "url": gj})
    # Gupy (plataforma BR comum)
    gupy = "https://portal.gupy.io/job-search/term=" + urllib.parse.quote(palavras[0] if palavras else "marketing")
    links.append({"nome": "Gupy", "url": gupy})
    return links


def _contexto(boletim: dict, cfg: dict, data: dt.date) -> dict:
    secoes = [s for s in boletim.get("secoes", []) if s.get("itens")]
    total = sum(len(s["itens"]) for s in secoes)
    return {
        "titulo_painel": cfg["geral"]["titulo_painel"],
        "nome": cfg["destinatario"]["nome"],
        "data_extenso": _data_extenso(data),
        "data_iso": data.isoformat(),
        "intro": boletim.get("intro", ""),
        "secoes": secoes,
        "total": total,
        "aprenda": boletim.get("aprenda_algo_novo"),
        "vagas": _links_vagas(cfg),
        "ano": data.year,
    }


_MESES = [
    "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
_DIAS = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sabado", "domingo"]


def _data_extenso(data: dt.date) -> str:
    return f"{_DIAS[data.weekday()]}, {data.day} de {_MESES[data.month - 1]} de {data.year}"


def render_email(boletim: dict, cfg: dict, data: dt.date) -> str:
    return _env.get_template("email.html.j2").render(**_contexto(boletim, cfg, data))


def render_painel(boletim: dict, cfg: dict, data: dt.date) -> str:
    return _env.get_template("dashboard.html.j2").render(**_contexto(boletim, cfg, data))


def salvar_painel(html: str, data: dt.date, docs_dir: Path, cfg: dict) -> None:
    """Salva o boletim do dia e regenera o indice."""
    briefings = docs_dir / "briefings"
    briefings.mkdir(parents=True, exist_ok=True)
    (briefings / f"{data.isoformat()}.html").write_text(html, encoding="utf-8")
    (docs_dir / ".nojekyll").touch()
    _regenerar_indice(docs_dir, cfg)


def _regenerar_indice(docs_dir: Path, cfg: dict) -> None:
    briefings = docs_dir / "briefings"
    arquivos = sorted(briefings.glob("*.html"), reverse=True) if briefings.exists() else []
    edicoes = []
    for f in arquivos:
        iso = f.stem
        try:
            d = dt.date.fromisoformat(iso)
            edicoes.append({"data_iso": iso, "rotulo": _data_extenso(d), "url": f"briefings/{iso}.html"})
        except ValueError:
            continue
    html = _env.get_template("index.html.j2").render(
        titulo_painel=cfg["geral"]["titulo_painel"],
        edicoes=edicoes,
        ano=dt.date.today().year,
    )
    (docs_dir / "index.html").write_text(html, encoding="utf-8")
