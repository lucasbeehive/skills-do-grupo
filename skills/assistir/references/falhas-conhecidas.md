# Falhas conhecidas (não repetir)

Atualizado em 16/11/2026. Cada item foi visto acontecer.

## YouTube

- `player_client=android` era necessário em 08/2026; em 11/2026 passou a atrapalhar ("Requested format is not available" no áudio e legendas automáticas somem). Não usar. O script já não usa.
- Pedir legendas traduzidas automaticamente (por exemplo `pt-PT` ou `pt-en`) dá `HTTP Error 429: Too Many Requests`. Peça só a faixa no idioma falado (`<idioma>-orig`) ou a manual. O script já faz isso.
- Muitos vídeos de uma vez também dão 429. Lotes de até 10, 3 s entre pedidos, e espere 2 a 3 minutos entre lotes. Depois de 1 nova tentativa, marque "sem transcrição" e siga.
- "Sign in to confirm you're not a bot": não use cookies do navegador sem o ok do usuário (é a conta Google dele). Tente 1 vez depois de alguns minutos; se persistir, reporte o erro exato.
- `youtube-transcript-api` e navegador (página de CAPTCHA do Google): bloqueados. Não usar para transcrição.

## Instagram e TikTok

- Em 16/11/2026 reels públicos e vídeos públicos do TikTok baixaram sem login. Post privado, ou mudança do site, pode passar a pedir login: nesse caso, peça ao usuário o arquivo baixado e use o caminho dele.
- Aviso "no impersonation target available" no TikTok é normal; o download funciona.

## Podcasts

- Página do Apple Podcasts: `Unsupported URL`. Use o link do feed RSS ou do arquivo mp3.
- Feed RSS traz o programa inteiro; prefira o link do episódio.

## Transcrição local (Whisper)

- `faster-whisper` 1.2.1 com `av` 19 quebra (`metadata_errors`). O script fixa `av<17`.
- Primeiro uso baixa o modelo (cerca de 1,6 GB) para o cache do Hugging Face. Sem internet nessa hora, falha: tente de novo com internet.
- Sem placa de vídeo leva perto de 40% da duração do áudio.

## Erros comuns e o que dizer ao usuário

O `manifesto.json` já traz o erro em português (`erro`) e a linha original (`erro_original`).

- Vídeo indisponível: apagado, privado ou link errado. Peça para conferir o link.
- 404: endereço não existe. Peça para conferir o link.
- Arquivo não encontrado: peça o caminho certo (arrastar o arquivo para a conversa costuma resolver).
- Código de saída: 0 = ao menos uma fonte deu certo; 2 = nenhuma deu certo; 3 = falta ferramenta (rode `checar`).

## Ferramentas

- Não depender do ffmpeg, yt-dlp ou deno do sistema: o script usa as versões do próprio ambiente (uv). Se algo estranho acontecer, rode `checar`.
