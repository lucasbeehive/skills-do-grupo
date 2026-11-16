# Como instalar uma skill deste repositório

Estas instruções são para o Claude ler e executar. Quem pede é o dono do computador.

## Antes de começar (o que a pessoa precisa ter)

- O aplicativo Claude no computador (Windows ou Mac), usando a aba **Code**. A aba Code faz parte dos planos pagos do Claude.
- Internet e cerca de 2,5 GB livres no disco (a skill `assistir` usa uns 600 MB de programas e, na primeira transcrição sem legenda, baixa um pacote de 1,6 GB).

## O que é instalado

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

Nada pede senha, login ou chave.

## Passos para o Claude

1. **uv.** Rode `uv --version`. Se não existir, instale pelo instalador oficial:
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - Mac (Terminal): `curl -LsSf https://astral.sh/uv/install.sh | sh`
   Depois, abra um terminal novo (ou use o caminho completo que o instalador mostrar) e confirme com `uv --version`.
2. **Baixar.** Baixe `https://github.com/lucasbeehive/skills-do-grupo/archive/refs/heads/main.zip` para uma pasta temporária e extraia (Windows: `Expand-Archive` no PowerShell; Mac: `unzip`). Dentro dele fica a pasta `skills-do-grupo-main`.
3. **Copiar.** Copie a pasta `skills/<nome-da-skill>` (por exemplo `skills/assistir`) para a pasta de skills do usuário:
   - Windows: `C:\Users\<usuário>\.claude\skills\<nome-da-skill>`
   - Mac: `/Users/<usuário>/.claude/skills/<nome-da-skill>`
   Crie a pasta `skills` se não existir. Se a skill já existir, renomeie a antiga para `<nome-da-skill>-antiga-<AAAAMMDD>` antes de copiar. O arquivo `SKILL.md` precisa ficar direto dentro da pasta da skill.
4. **Conferir.** Para a skill `assistir`, rode (no Windows a pasta da skill é, por exemplo, `C:\Users\maria\.claude\skills\assistir`; no Mac, `/Users/maria/.claude/skills/assistir`):
   - `uv run "<pasta da skill>/scripts/assistir.py" checar`
   - `uv run "<pasta da skill>/scripts/teste_rapido.py"`
   A primeira vez demora um pouco porque baixa os programas.
5. **Avisar.** Diga ao usuário, em português simples, o que ficou pronto e uma frase para testar, por exemplo: "Assiste esse vídeo e me resume: <link do YouTube>". Não precisa reiniciar o aplicativo; se a skill não aparecer, rode `/reload-skills` ou abra uma conversa nova.

Não instale nada além do que está nesta lista.
