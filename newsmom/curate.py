"""
Curadoria com a IA (Claude).

Recebe os artigos brutos e devolve um boletim estruturado:
- seleciona os mais relevantes para o perfil da Angelica;
- traduz para portugues o que estiver em outra lingua;
- escreve um resumo curto e o "porque importa";
- escreve a secao "Aprenda algo novo".

Se nao houver ANTHROPIC_API_KEY, cai num modo simples (sem IA),
agrupando os artigos por tema sem traducao.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .fetch import Article

PERFIL = (
    "A leitora e uma executiva de marketing e estrategia em uma grande empresa "
    "brasileira de mercado imobiliario e administracao de condominios (Lello). "
    "Ela toma decisoes estrategicas, de lideranca corporativa e de marca. "
    "Le portugues e ingles."
)

_SCHEMA = """
Responda APENAS com um objeto JSON valido (sem markdown, sem ```), neste formato:
{
  "intro": "1-2 frases de bom dia resumindo o clima do dia.",
  "secoes": [
    {
      "chave": "imobiliario",
      "nome": "Mercado Imobiliario",
      "itens": [
        {
          "headline": "Titulo em portugues, claro e objetivo",
          "resumo": "2-3 frases em portugues explicando a noticia",
          "porque_importa": "1 frase: por que isso importa para o trabalho dela",
          "link": "URL original (copie exatamente do candidato)",
          "fonte": "Nome da fonte",
          "idioma_original": "pt ou en"
        }
      ]
    }
  ],
  "aprenda_algo_novo": {
    "titulo": "Titulo curto",
    "corpo": "Um paragrafo (3-5 frases) que ensine algo genuinamente novo e interessante sobre o mundo (ciencia, historia, cultura, economia). Pode usar seu conhecimento; nao precisa vir dos artigos."
  }
}
"""

_INSTRUCOES = f"""Voce e um editor de um boletim matinal executivo, em portugues do Brasil.

PERFIL DA LEITORA: {PERFIL}

Sua tarefa:
1. Para cada tema, escolha os itens MAIS relevantes e importantes para o perfil dela
   (qualidade > quantidade). Descarte ruido, clickbait e duplicatas.
2. Traduza TUDO para portugues do Brasil. Se o titulo original estiver em ingles,
   escreva o headline em portugues (mas mantenha o link original).
3. Em "publicidade", inclua somente os cases realmente importantes/premiados.
4. Em cada item, copie o "link" EXATAMENTE como veio no candidato. Nunca invente links.
5. Respeite o limite maximo de itens por secao informado.
6. Escreva "aprenda_algo_novo" com algo curioso e educativo.
7. Mantenha as secoes na mesma ordem dos temas recebidos. Se um tema nao tiver
   nada de bom, devolva a secao com "itens": [].

{_SCHEMA}
"""


def _agrupar(artigos: list[Article]) -> dict[str, list[Article]]:
    grupos: dict[str, list[Article]] = {}
    for a in artigos:
        grupos.setdefault(a.tema, []).append(a)
    return grupos


def _payload_candidatos(temas: list[dict], artigos: list[Article]) -> tuple[str, dict[int, Article]]:
    grupos = _agrupar(artigos)
    idx = 0
    indice: dict[int, Article] = {}
    blocos = []
    for tema in temas:
        itens = grupos.get(tema["chave"], [])
        linhas = []
        for a in itens:
            indice[idx] = a
            linhas.append(a.to_prompt_dict(idx))
            idx += 1
        blocos.append({"chave": tema["chave"], "nome": tema["nome"], "candidatos": linhas})
    return json.dumps(blocos, ensure_ascii=False), indice


def _extrair_json(texto: str) -> dict[str, Any]:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.split("```", 2)[1]
        if texto.startswith("json"):
            texto = texto[4:]
    inicio = texto.find("{")
    fim = texto.rfind("}")
    if inicio != -1 and fim != -1:
        texto = texto[inicio : fim + 1]
    return json.loads(texto)


def curar_com_ia(temas: list[dict], artigos: list[Article], cfg: dict) -> dict[str, Any]:
    payload, indice = _payload_candidatos(temas, artigos)
    max_itens = cfg["geral"]["max_itens_por_secao"]
    modelo = cfg["geral"]["modelo_ia"]

    from anthropic import Anthropic

    client = Anthropic()  # usa ANTHROPIC_API_KEY do ambiente
    mensagem = (
        f"Maximo de {max_itens} itens por secao.\n\n"
        f"CANDIDATOS (JSON, agrupados por tema):\n{payload}"
    )

    resposta = client.messages.create(
        model=modelo,
        max_tokens=8000,
        system=_INSTRUCOES,
        messages=[{"role": "user", "content": mensagem}],
    )
    texto = "".join(b.text for b in resposta.content if getattr(b, "type", None) == "text")
    dados = _extrair_json(texto)

    # Sanidade: garante que todo link existe entre os candidatos.
    links_validos = {a.link for a in artigos}
    for secao in dados.get("secoes", []):
        secao["itens"] = [i for i in secao.get("itens", []) if i.get("link") in links_validos][:max_itens]
    return dados


def curar_simples(temas: list[dict], artigos: list[Article], cfg: dict) -> dict[str, Any]:
    """Fallback sem IA: agrupa por tema, sem traducao."""
    grupos = _agrupar(artigos)
    max_itens = cfg["geral"]["max_itens_por_secao"]
    secoes = []
    for tema in temas:
        itens = []
        for a in grupos.get(tema["chave"], [])[:max_itens]:
            itens.append(
                {
                    "headline": a.titulo,
                    "resumo": "",
                    "porque_importa": "",
                    "link": a.link,
                    "fonte": a.fonte,
                    "idioma_original": a.idioma,
                }
            )
        secoes.append({"chave": tema["chave"], "nome": tema["nome"], "itens": itens})
    return {
        "intro": "Bom dia! Aqui esta o seu resumo de noticias (modo simples, sem curadoria por IA).",
        "secoes": secoes,
        "aprenda_algo_novo": None,
    }


def curar(temas: list[dict], artigos: list[Article], cfg: dict) -> dict[str, Any]:
    if not artigos:
        return {"intro": "Bom dia! Hoje nao encontramos noticias novas relevantes.", "secoes": [], "aprenda_algo_novo": None}
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return curar_com_ia(temas, artigos, cfg)
        except Exception as exc:
            print(f"! IA indisponivel ({exc}); usando modo simples.")
    else:
        print("! ANTHROPIC_API_KEY ausente; usando modo simples (sem curadoria por IA).")
    return curar_simples(temas, artigos, cfg)
