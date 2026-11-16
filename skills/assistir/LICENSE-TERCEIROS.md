# Créditos de terceiros

## /watch (claude-video), Bradley Bonanno, licença MIT

Algumas ideias da extração de quadros e das legendas em `scripts/assistir.py` foram adaptadas da skill /watch
(https://github.com/bradautomates/claude-video): seleção de trocas de cena com `select=gt(scene,..)` + `showinfo`
para obter o minuto de cada quadro, queda para amostragem uniforme quando há poucas cenas, remoção de quadros
repetidos por miniatura 16x16 e junção de legenda rolante do YouTube. O código foi reescrito, não copiado.

MIT License

Copyright (c) 2026 Bradley Bonanno

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of
the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Dependências (instaladas pelo uv, não distribuídas aqui)

yt-dlp (Unlicense), imageio-ffmpeg (BSD-2; o binário ffmpeg embutido é LGPL/GPL conforme build), Pillow (HPND),
faster-whisper (MIT), PyAV (BSD), deno (MIT). Modelo Whisper large-v3-turbo (MIT).
