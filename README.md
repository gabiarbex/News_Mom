# 📰 News Mom — Boletim Estratégico Diário

Agente automático que, **toda manhã útil às 9h (horário de Brasília)**, monta um boletim
de notícias com curadoria por IA e envia por **email** + publica num **painel online**.

Segunda a sexta. **Se algo importante sai no fim de semana, a edição de segunda recupera.**

## O que entra no boletim

- Mercado imobiliário e mercado de condomínios
- Fusões & aquisições (M&A)
- IA para o mundo corporativo e inovação
- Marketing, estratégia corporativa e liderança
- Estratégia de marcas (nacional e internacional)
- Cases de publicidade em destaque (só os mais relevantes)
- Brasil (para ficar bem informada) e regulatório (reforma tributária etc.)
- Vagas com o seu perfil (links de busca atualizados)
- 💡 "Aprenda algo novo" — uma curiosidade do mundo por dia

Tudo em **português** (conteúdo em inglês é traduzido; nenhum outro idioma entra).

## Como funciona (visão geral)

1. Um **GitHub Action agendado** roda o script toda manhã útil.
2. O script busca notícias por tema no **Google News RSS** (sem precisar de chave).
3. A **IA da Claude** seleciona o que importa, traduz, resume e organiza por assunto.
4. Gera o **email** (Gmail/SMTP) e atualiza o **painel** (GitHub Pages).

---

## ⚙️ Configuração (passo a passo)

Você só precisa fazer isto **uma vez**.

### 1. Chave da IA (Claude)
- Crie uma chave em <https://console.anthropic.com> → *API Keys*.
- No GitHub: repositório → **Settings → Secrets and variables → Actions → New repository secret**.
- Nome: `ANTHROPIC_API_KEY` · Valor: sua chave.

> Sem essa chave o boletim ainda funciona, mas em "modo simples" (sem tradução/curadoria).

### 2. Envio de email (Gmail)
No Gmail, ative a verificação em 2 etapas e gere uma **"senha de app"**
(<https://myaccount.google.com/apppasswords>). Use essa senha (não a normal).

Crie os secrets no GitHub:

| Secret          | Valor                                   |
|-----------------|-----------------------------------------|
| `SMTP_HOST`     | `smtp.gmail.com`                        |
| `SMTP_PORT`     | `587`                                   |
| `SMTP_USER`     | seu email (ex: `voce@gmail.com`)        |
| `SMTP_PASSWORD` | a **senha de app** gerada               |
| `MAIL_FROM`     | (opcional) remetente; padrão = SMTP_USER|
| `MAIL_TO`       | destinatário (ex: `angelica.arbex@lello.com.br`) |

### 3. Ativar o painel (GitHub Pages)
- Repositório → **Settings → Pages**.
- Em *Source*, escolha **Deploy from a branch**.
- Branch: a branch do projeto · pasta: **/docs** → *Save*.
- O painel ficará em `https://SEU-USUARIO.github.io/news_mom/`.

### 4. Pronto!
O boletim roda sozinho de segunda a sexta às 9h. Para testar agora:
repositório → **Actions → Boletim Diário → Run workflow**.

---

## 🛠️ Personalização

Tudo é editável no arquivo [`config.yaml`](config.yaml):
- **temas e palavras-chave** de busca;
- **quantidade de itens** por seção;
- **horário/idioma**, destinatário;
- **palavras-chave das vagas** (ajuste para o seu cargo-alvo).

Mudou o horário? Ajuste também o `cron` em
[`.github/workflows/daily-briefing.yml`](.github/workflows/daily-briefing.yml)
(lembre que o cron usa **UTC**; 9h BRT = `0 12 * * 1-5`).

## ▶️ Rodar localmente (opcional, para testar)

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...     # opcional
python -m newsmom.main --teste   # gera o painel em docs/ sem enviar email
```

## 🎙️ Podcast (próxima etapa)

A estrutura já está preparada para gerar um "talk show" matinal em áudio.
Quando quiser ativar, adicionamos a geração do roteiro pela IA + uma voz (TTS)
e o MP3 entra no email e no painel.
