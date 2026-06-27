"""
Busca de noticias via Google News RSS.

Usamos o Google News RSS porque:
- nao precisa de chave de API;
- permite buscar por tema e por idioma (PT-BR / EN);
- ja traz noticias recentes de varias fontes.
"""

from __future__ import annotations

import datetime as dt
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Iterable

import feedparser

# Cabecalhos de idioma do Google News.
_LANG = {
    "pt": {"hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"},
    "en": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
}


@dataclass
class Article:
    titulo: str
    link: str
    fonte: str
    idioma: str
    tema: str
    tema_nome: str
    resumo: str = ""
    publicado: dt.datetime | None = None

    def to_prompt_dict(self, idx: int) -> dict:
        """Versao enxuta enviada para a IA (economiza tokens)."""
        return {
            "id": idx,
            "titulo": self.titulo,
            "fonte": self.fonte,
            "idioma": self.idioma,
            "link": self.link,
            "resumo": self.resumo[:300],
            "publicado": self.publicado.isoformat() if self.publicado else None,
        }


def _build_url(query: str, lang: str, dias: int) -> str:
    params = dict(_LANG.get(lang, _LANG["pt"]))
    q = f"{query} when:{max(dias, 1)}d"
    params["q"] = q
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


def _parse_date(entry) -> dt.datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        val = getattr(entry, key, None) or entry.get(key) if hasattr(entry, "get") else None
        if val:
            try:
                return dt.datetime.fromtimestamp(time.mktime(val), tz=dt.timezone.utc)
            except Exception:
                continue
    return None


def _clean_source(entry, fallback: str) -> str:
    src = entry.get("source") if hasattr(entry, "get") else None
    if isinstance(src, dict) and src.get("title"):
        return src["title"]
    if getattr(entry, "source", None) and getattr(entry.source, "title", None):
        return entry.source.title
    return fallback


def buscar_tema(tema: dict, janela_horas: int, max_itens: int) -> list[Article]:
    """Busca os artigos de um tema (todas as queries)."""
    dias = max(1, round(janela_horas / 24))
    limite = dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(hours=janela_horas)
    artigos: list[Article] = []

    for query in tema.get("queries", []):
        url = _build_url(query["q"], query.get("lang", "pt"), dias)
        try:
            feed = feedparser.parse(url)
        except Exception as exc:  # pragma: no cover - rede
            print(f"  ! erro ao buscar '{query['q']}': {exc}")
            continue

        for entry in feed.entries:
            publicado = _parse_date(entry)
            if publicado and publicado < limite:
                continue
            titulo = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            if not titulo or not link:
                continue
            artigos.append(
                Article(
                    titulo=titulo,
                    link=link,
                    fonte=_clean_source(entry, "Google News"),
                    idioma=query.get("lang", "pt"),
                    tema=tema["chave"],
                    tema_nome=tema["nome"],
                    resumo=(entry.get("summary") or "").strip(),
                    publicado=publicado,
                )
            )

    artigos = _dedup(artigos)
    # Mais recentes primeiro; sem data vai para o fim.
    artigos.sort(key=lambda a: a.publicado or dt.datetime.min.replace(tzinfo=dt.timezone.utc), reverse=True)
    return artigos[:max_itens]


def _norm(titulo: str) -> str:
    return "".join(c.lower() for c in titulo if c.isalnum())[:80]


def _dedup(artigos: Iterable[Article]) -> list[Article]:
    vistos: set[str] = set()
    out: list[Article] = []
    for a in artigos:
        chave = _norm(a.titulo)
        if chave in vistos:
            continue
        vistos.add(chave)
        out.append(a)
    return out


def buscar_tudo(temas: list[dict], janela_horas: int, max_por_tema: int) -> list[Article]:
    todos: list[Article] = []
    for tema in temas:
        print(f"- buscando: {tema['nome']}")
        encontrados = buscar_tema(tema, janela_horas, max_por_tema)
        print(f"  {len(encontrados)} artigos")
        todos.extend(encontrados)
    return todos
