# Como instalar uma skill deste repositório

Estas instruções são para o Claude ler e executar. Quem pede é o dono do computador.

## Antes de começar (o que a pessoa precisa ter)

- O aplicativo Claude no computador (Windows ou Mac), usando a aba **Code**. A aba Code faz parte dos planos pagos do Claude.
- Internet e espaço livre no disco (veja o tamanho na seção da skill, mais abaixo).

Nada pede senha, login ou chave.

## Passos para o Claude

1. **uv.** Rode `uv --version`. Se não existir, instale pelo instalador oficial:
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - Mac (Terminal): `curl -LsSf https://astral.sh/uv/install.sh | sh`
   Depois, abra um terminal novo (ou use o caminho completo que o instalador mostrar) e confirme com `uv --version`.
2. **Baixar.** Baixe `https://github.com/lucasbeehive/skills-do-grupo/archive/refs/heads/main.zip` para uma pasta temporária e extraia (Windows: `Expand-Archive` no PowerShell; Mac: `unzip`). Dentro dele fica a pasta `skills-do-grupo-main`.
3. **Copiar.** Copie a pasta `skills/<nome-da-skill>` (por exemplo `skills/assistir`) para a pasta de skills do usuário:
   - Windows: `C:\Users\<usuário>\.claude\skills\<nome-da-skill>` (por exemplo `C:\Users\maria\.claude\skills\assistir`)
   - Mac: `/Users/<usuário>/.claude/skills/<nome-da-skill>` (por exemplo `/Users/maria/.claude/skills/assistir`)
   Crie a pasta `skills` se não existir. Se a skill já existir, renomeie a antiga para `<nome-da-skill>-antiga-<AAAAMMDD>` antes de copiar. O arquivo `SKILL.md` precisa ficar direto dentro da pasta da skill.
4. **Conferir.** Rode os comandos de conferência da skill, que estão na seção dela abaixo. A primeira vez demora um pouco porque baixa os programas.
5. **Avisar.** Diga ao usuário, em português simples, o que ficou pronto e a frase de teste da skill. Não precisa reiniciar o aplicativo; se a skill não aparecer, rode `/reload-skills` ou abra uma conversa nova.

Não instale nada além do que está listado na seção da skill.

## Skills

### assistir

Assiste vídeos e áudios (fala e tela). Manual: `manuais/Como usar a skill assistir.pdf`.

Espaço em disco: cerca de 2,5 GB livres (uns 600 MB de programas e, na primeira transcrição sem legenda, um pacote de 1,6 GB).

| O quê | Para quê | Como chega |
| --- | --- | --- |
| uv | roda os programas da skill num ambiente separado, sem mexer no resto do computador | instalado no passo 1 |
| Python | linguagem dos programas | o uv baixa sozinho se faltar |
| yt-dlp | lê legendas e baixa áudio e vídeo de YouTube, Instagram, TikTok e podcasts | o uv baixa sozinho no primeiro uso |
| deno | ajuda o yt-dlp a ler o YouTube | o uv baixa sozinho no primeiro uso |
| ffmpeg (imageio-ffmpeg) | tira fotos da tela e separa o áudio | o uv baixa sozinho no primeiro uso |
| Pillow | monta as folhas de fotos com o minuto | o uv baixa sozinho no primeiro uso |
| faster-whisper e o modelo large-v3-turbo | transcreve vídeo sem legenda, no próprio computador | só quando precisar, na primeira vez (1,6 GB) |

Junto vêm pequenas peças que esses programas usam por dentro (por exemplo `pycryptodomex`, do yt-dlp). Tudo fica em pastas próprias: o cache do uv, `~/.cache/assistir` (o ffmpeg da skill) e `~/.cache/huggingface` (o modelo de transcrição). Nada é instalado no sistema além do uv.

Conferir:

- `uv run "<pasta da skill>/scripts/assistir.py" checar`
- `uv run "<pasta da skill>/scripts/teste_rapido.py"`

Frase de teste: "Assiste esse vídeo e me resume: <link do YouTube>".

### modelo-certo

O modelo forte da conversa planeja; cada agente roda no modelo mais barato que entrega a mesma qualidade. Manual: `manuais/Como usar a skill modelo-certo.pdf`.

Espaço em disco: menos de 1 MB. Não baixa programa nenhum além do uv (e do Python, que o uv traz se faltar).

Esta skill precisa ser **ligada** depois de copiada. Ligar mexe em dois arquivos da pasta `.claude` do usuário, sempre com cópia de segurança antes (`<arquivo>.antes-modelo-certo-<data>`):

| Arquivo | O que muda |
| --- | --- |
| `settings.json` | acrescenta um vigia que roda antes de cada agente e o padrão `sonnet` para agentes (`CLAUDE_CODE_SUBAGENT_MODEL`) |
| `CLAUDE.md` | acrescenta uma linha que carrega a regra em toda conversa |

Ligar e conferir (no passo 4):

- `uv run --script "<pasta da skill>/scripts/instalar.py"`
- `uv run --script "<pasta da skill>/scripts/instalar.py" --checar` (tem de terminar com "Tudo certo.")

Desligar quando quiser: `uv run --script "<pasta da skill>/scripts/instalar.py" --remover`.

Frase de teste: "Cria um agente sem escolher modelo, só para eu ver o vigia bloquear." O esperado é o bloqueio com a escada de modelos, e o Claude refazendo a chamada com um modelo escolhido.
