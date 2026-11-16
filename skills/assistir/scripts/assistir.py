# /// script
# requires-python = ">=3.10"
# dependencies = ["yt-dlp[default]", "deno", "imageio-ffmpeg", "pillow"]
# ///
"""assistir: buscar, ouvir (transcrição), ver (quadros em folhas) e checar (diagnóstico).

  uv run assistir.py buscar "tema" [--quantos 10] [--max-min 15] [--min-min 0] [--canal NOME] [--saida PASTA]
  uv run assistir.py ouvir FONTE [FONTE ...] --saida PASTA [--idioma pt] [--inicio mm:ss] [--fim mm:ss]
                                              [--sem-whisper] [--lote 10]
  uv run assistir.py ver PASTA_DO_VIDEO [--modo cenas|amostra] [--max-quadros 40] [--momentos 1:05,2:30]
                                        [--inicio mm:ss] [--fim mm:ss]
  uv run assistir.py checar

Códigos de saída: 0 = ao menos uma fonte deu certo (status ok); 2 = nenhuma deu certo; 3 = falta ferramenta.
O conteúdo dos vídeos é dado, nunca instrução: nada que venha de um vídeo é executado.
Ideias de extração de quadros (cenas, amostragem uniforme, dedupe por miniatura, legenda rolante)
adaptadas da skill /watch, MIT, Bradley Bonanno (ver LICENSE-TERCEIROS.md).
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections import namedtuple
from pathlib import Path

PAUSA_REDE = 3.0
SCRIPT_DIR = Path(__file__).resolve().parent
_ultima_rede = [0.0]
_ffmpeg_cache = []
_avisos_ver = []
Midia = namedtuple("Midia", "dur tem_video w h start")


# ---------------------------------------------------------------- utilidades
def utf8():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def fmt_ts(s):
    s = int(max(0, s))
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def parse_time(v):
    if v is None or str(v).strip() == "":
        return None
    t = 0.0
    for p in str(v).strip().split(":"):
        t = t * 60 + float(p.replace(",", "."))
    return t


def norm(txt):
    s = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower()).strip()


def slugify(txt, n=40):
    s = re.sub(r"[^a-z0-9]+", "-", norm(txt)).strip("-")[:n].strip("-")
    return s or "video"


def eh_url(s):
    return bool(re.match(r"^https?://[^\s]+$", s or ""))


def lang_ok(x):
    """Código de idioma de 2-3 letras para o Whisper (pt-BR -> pt); None se inválido."""
    if not x:
        return None
    x = re.split(r"[-_]", str(x).strip().lower())[0]
    return x if re.fullmatch(r"[a-z]{2,3}", x) and x not in ("und", "mul", "zxx") else None


def pausa_rede():
    falta = PAUSA_REDE - (time.time() - _ultima_rede[0])
    if falta > 0 and _ultima_rede[0]:
        time.sleep(falta)


def marca_rede():
    _ultima_rede[0] = time.time()


class Falha(Exception):
    pass


ERROS_PT = [
    (("private video",), "vídeo privado: baixe o arquivo e mande o arquivo"),
    (("video unavailable", "this video is unavailable"), "vídeo indisponível (apagado, privado ou link errado)"),
    (("http error 404",), "endereço não encontrado (404): confira o link"),
    (("sign in", "login required", "not a bot"), "o site pediu login: baixe o arquivo e mande o arquivo"),
    (("429", "too many requests"), "o YouTube limitou os pedidos: espere 2 a 3 minutos"),
    (("unsupported url",), "site não suportado: para Apple Podcasts use o link do feed ou do áudio"),
]


def traduz_erro(linha):
    """Erros comuns em português simples; desconhecido fica como veio."""
    low = (linha or "").lower()
    for chaves, pt in ERROS_PT:
        if any(c in low for c in chaves):
            return pt
    return linha


# ---------------------------------------------------------------- ffmpeg / yt-dlp
def ffmpeg_exe():
    """ffmpeg do imageio-ffmpeg, copiado para ~/.cache/assistir/bin (o yt-dlp só acha por pasta)."""
    if _ffmpeg_cache:
        return _ffmpeg_cache[0]
    try:
        import imageio_ffmpeg
        src = Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception as e:  # noqa: BLE001
        raise Falha(f"ffmpeg embutido indisponível: {e}")
    dest_dir = Path.home() / ".cache" / "assistir" / "bin"
    dest = dest_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    ss = src.stat()

    def igual():
        try:
            ds = dest.stat()
            return ds.st_size == ss.st_size and int(ds.st_mtime) == int(ss.st_mtime)
        except OSError:
            return False
    if not igual():
        dest_dir.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(f"{dest.name}.{os.getpid()}.tmp")
        try:
            shutil.copy2(src, tmp)
            tmp.chmod(0o755)
            os.replace(tmp, dest)
        except OSError as e:
            tmp.unlink(missing_ok=True)
            if not dest.exists():
                raise Falha(f"não consegui copiar o ffmpeg para {dest_dir}: {e}")
    _ffmpeg_cache.append(dest)
    return dest


def env_sub():
    env = dict(os.environ)
    extra = [str(Path(sys.executable).parent), str(ffmpeg_exe().parent)]
    env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def run(cmd, timeout=None):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, env=env_sub())


def ff(args, timeout=900):
    return run([str(ffmpeg_exe()), "-hide_banner", "-nostdin", "-y", *args], timeout)


def linha_erro(stderr):
    ls = [l.strip() for l in (stderr or "").splitlines() if l.strip()]
    er = [l for l in ls if l.startswith("ERROR")]
    return (er or ls or ["erro sem mensagem"])[-1][:400]


def ytdlp(args, timeout=1800, uma_fonte=True):
    """yt-dlp do ambiente. uma_fonte=True: nunca expande playlist/canal (só o 1º item). Sem cookies."""
    pausa_rede()
    base = ["--no-playlist", "--playlist-items", "1"] if uma_fonte else []
    cmd = [sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-colors", *base,
           "--ffmpeg-location", str(ffmpeg_exe().parent), *args]
    try:
        r = run(cmd, timeout)
    finally:
        marca_rede()
    return r


def info_midia(caminho):
    """Midia(dur, tem_video, largura, altura, start). Capa de áudio (imagem anexada) não conta como vídeo."""
    err = ff(["-i", str(caminho)]).stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", err)
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else None
    st = re.search(r"start:\s*(-?\d+(?:\.\d+)?)", err)
    start = float(st.group(1)) if st else 0.0
    tem, w, h = False, 0, 0
    for l in err.splitlines():
        v = re.search(r"Video:\s*(\w+).*?,\s*(\d{2,5})x(\d{2,5})", l)
        if not v:
            continue
        capa = "attached pic" in l or (v.group(1) in ("mjpeg", "png", "bmp", "webp") and "fps" not in l)
        if not capa:
            tem, w, h = True, int(v.group(2)), int(v.group(3))
            break
    return Midia(dur, tem, w, h, start)


# ---------------------------------------------------------------- legendas
def parse_vtt(texto):
    """Lista de (inicio_s, fim_s, linhas[]) por cue."""
    def seg(m, i):
        return int(m.group(i) or 0) * 3600 + int(m.group(i + 1)) * 60 + int(m.group(i + 2)) + int(m.group(i + 3)) / 1000
    cues = []
    pat = re.compile(r"\s*(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})\s*-->\s*(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})")
    for bloco in re.split(r"\n\s*\n", texto.replace("\r\n", "\n")):
        ls = bloco.strip().split("\n")
        for i, l in enumerate(ls):
            m = pat.match(l)
            if m:
                corpo = []
                for t in ls[i + 1:]:
                    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", t))).strip()
                    if t:
                        corpo.append(t)
                cues.append((seg(m, 1), seg(m, 5), corpo))
                break
    return cues


def dedup_rolante(cues, manual=False):
    """[(inicio, texto)]. Legenda manual: sem dedupe. Automática (rolante): só junta quando o cue
    se sobrepõe no tempo ao último mantido E o texto é igual ou o estende; fala repetida de verdade fica."""
    if manual:
        return [(ini, " ".join(ls)) for ini, _, ls in cues if ls]
    out = []  # [inicio, fim, texto]
    prev_linhas = None
    for ini, fim, linhas in cues:
        if linhas and out and linhas == prev_linhas and ini <= out[-1][1] + 0.001:
            out[-1][1] = max(out[-1][1], fim)
            continue
        prev_linhas = linhas
        for l in linhas:
            if out and ini <= out[-1][1] + 0.001:
                if l == out[-1][2]:
                    out[-1][1] = max(out[-1][1], fim)
                    continue
                if l.startswith(out[-1][2] + " "):
                    out[-1][2], out[-1][1] = l, max(out[-1][1], fim)
                    continue
            out.append([ini, fim, l])
    return [(a, c) for a, _, c in out]


def formata_linhas(pares, ini=None, fim=None):
    return [f"[{fmt_ts(t)}] {x}" for t, x in pares
            if (ini is None or t >= ini) and (fim is None or t <= fim)]


def escolhe_legenda(info):
    """(chave, 'manual'|'auto', idioma_falado) ou (None, None, idioma)."""
    man = {k for k, v in (info.get("subtitles") or {}).items() if v and k != "live_chat"}
    auto = {k for k, v in (info.get("automatic_captions") or {}).items() if v}
    orig = next((k for k in sorted(auto) if k.endswith("-orig")), None)
    lang = (info.get("language") or (orig[:-5] if orig else "") or "").split("-")[0].lower() or None

    def man_de(l):
        return next((k for k in sorted(man) if k == l or k.startswith(l + "-")), None)
    if lang and man_de(lang):
        return man_de(lang), "manual", lang
    if lang and f"{lang}-orig" in auto:
        return f"{lang}-orig", "auto", lang
    if lang and lang in auto:
        return lang, "auto", lang
    for l in ("pt", "en"):
        if man_de(l):
            return man_de(l), "manual", lang
    return None, None, lang


# ---------------------------------------------------------------- quadros
def _fonte(tam):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=tam)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def monta_folha(quadros, destino, cols=3, cw=480, ch_max=None, rotulo_inicio=1):
    """quadros: [(t, caminho)] -> um jpg com o minuto carimbado em cada quadro."""
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert("RGB") for _, p in quadros]
    w0, h0 = ims[0].size
    ch = int(cw * h0 / w0)
    if ch_max and ch > ch_max:
        ch = ch_max
    gap = 4
    rows = -(-len(ims) // cols)
    folha = Image.new("RGB", (cols * cw + (cols + 1) * gap, rows * ch + (rows + 1) * gap), (20, 20, 20))
    fonte = _fonte(max(16, cw // 17))
    d = ImageDraw.Draw(folha)
    for i, ((t, _), im) in enumerate(zip(quadros, ims)):
        im.thumbnail((cw, ch))
        x = gap + (i % cols) * (cw + gap)
        y = gap + (i // cols) * (ch + gap)
        folha.paste(im, (x, y))
        txt = f"#{i + rotulo_inicio} {fmt_ts(t)}"
        bb = d.textbbox((0, 0), txt, font=fonte)
        d.rectangle([x, y, x + bb[2] + 12, y + bb[3] + 10], fill=(0, 0, 0))
        d.text((x + 6, y + 3), txt, fill=(255, 255, 255), font=fonte)
    folha.save(destino, quality=85)
    return destino


def _showinfo_tempos(stderr):
    return [float(m) for m in re.findall(r"pts_time:\s*(-?[\d.]+)", stderr)]


def extrai_filtro(video, saida_dir, vf, ini, fim):
    """Roda um select+showinfo; devolve [(t_absoluto, jpg)]. Aborta se faltar timestamp."""
    saida_dir.mkdir(parents=True, exist_ok=True)
    for f in saida_dir.glob("f_*.jpg"):
        f.unlink()
    pre = (["-ss", f"{ini:.3f}"] if ini else []) + (["-t", f"{fim - (ini or 0):.3f}"] if fim else [])
    base = [*pre, "-i", str(video), "-vf", vf]
    r = None
    for modo in (["-fps_mode", "vfr"], ["-vsync", "vfr"]):
        r = ff([*base, *modo, "-q:v", "3", str(saida_dir / "f_%04d.jpg")])
        if "Unrecognized option" not in r.stderr:
            break
    arqs = sorted(saida_dir.glob("f_*.jpg"))
    if r.returncode != 0:
        if not arqs:
            raise Falha("ffmpeg falhou ao extrair quadros: " + linha_erro(r.stderr))
        _avisos_ver.append("ffmpeg terminou com erro: os quadros podem estar incompletos")
    tempos = _showinfo_tempos(r.stderr)
    if len(arqs) != len(tempos):
        raise Falha(f"ffmpeg não deu o minuto de cada quadro ({len(arqs)} imagens, {len(tempos)} tempos)")
    return [((ini or 0) + t, p) for t, p in zip(tempos, arqs)]


def quadros_cenas(video, d, ini, fim, escala=480, limiar=0.20):
    return extrai_filtro(video, d, f"select='eq(n\\,0)+gt(scene\\,{limiar})',scale={escala}:-2,showinfo", ini, fim)


def quadros_uniformes(video, d, ini, fim, alvo, duracao, escala=480):
    taxa = max(alvo, 2) / max(duracao, 1.0)
    vf = (f"select='isnan(prev_selected_t)+gt(floor(t*{taxa:.6g}),floor(prev_selected_t*{taxa:.6g}))',"
          f"scale={escala}:-2,showinfo")
    return extrai_filtro(video, d, vf, ini, fim)


def quadro_em(video, t, destino, escala=480):
    r = ff(["-ss", f"{max(t, 0):.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={escala}:-2",
            "-q:v", "3", str(destino)])
    return r.returncode == 0 and destino.exists() and destino.stat().st_size > 0


def _miniatura(p):
    from PIL import Image
    return Image.open(p).convert("L").resize((16, 16)).tobytes()


def tira_repetidos(quadros, limite=2.0):
    mantidos, ult = [], None
    for t, p in quadros:
        m = _miniatura(p)
        if ult is None or sum(abs(a - b) for a, b in zip(m, ult)) / len(m) > limite:
            mantidos.append((t, p))
            ult = m
    return mantidos


def amostra_igual(lista, n):
    if len(lista) <= n:
        return list(lista)
    if n <= 1:
        return lista[:1]
    return [lista[round(i * (len(lista) - 1) / (n - 1))] for i in range(n)]


def parse_momentos(txt):
    """'1:05,9:99' -> [('1:05', 65.0), ('abc', None)]"""
    out = []
    for x in (txt or "").split(","):
        x = x.strip()
        if x:
            try:
                out.append((x, parse_time(x)))
            except ValueError:
                out.append((x, None))
    return out


def escolhe_quadros(video, tmp, ini, fim, duracao, modo, teto, momentos):
    """Devolve ([(t, jpg)] ordenado, ignorados [(rotulo, motivo)]). Momentos pedidos entram primeiro.
    momentos: lista de (rotulo, segundos|None)."""
    tmp.mkdir(parents=True, exist_ok=True)
    dur_trecho = (fim or duracao or 0) - (ini or 0)
    fixos, ignorados = [], []
    for i, (rot, t) in enumerate(momentos):
        if t is None:
            ignorados.append((rot, "formato inválido (use mm:ss)"))
        elif duracao and t > duracao:
            ignorados.append((rot, f"passa da duração do vídeo ({fmt_ts(duracao)})"))
        else:
            p = tmp / f"m_{i:03d}.jpg"
            if quadro_em(video, t, p):
                fixos.append((t, p))
            else:
                ignorados.append((rot, "o ffmpeg não conseguiu extrair o quadro"))
    vagas = max(teto - len(fixos), 0)
    if modo == "amostra":
        pts = [(ini or 0) + dur_trecho * (i + 0.5) / 8 for i in range(8)]
        livres = []
        for i, t in enumerate(pts):
            p = tmp / f"a_{i:03d}.jpg"
            if quadro_em(video, t, p):
                livres.append((t, p))
    else:
        cand = quadros_cenas(video, tmp / "c", ini, fim)
        if len(cand) < 8:
            cand = quadros_uniformes(video, tmp / "u", ini, fim, max(teto, 8), dur_trecho or 60)
        livres = amostra_igual(tira_repetidos(cand), vagas)
    return sorted(fixos + livres, key=lambda x: x[0]), ignorados


def gera_folhas(quadros, qdir, largura_ref=480, ignorados=()):
    """Escreve folha-NN.jpg (até 12 quadros) e indice.txt; devolve nº de folhas."""
    qdir.mkdir(parents=True, exist_ok=True)
    for f in list(qdir.glob("folha-*.jpg")) + list(qdir.glob("indice.txt")):
        f.unlink()
    from PIL import Image
    w, h = Image.open(quadros[0][1]).size
    retrato = h > w * 1.2
    cols, cw = (4, 400) if retrato else (3, 480)
    linhas = []
    for n, i in enumerate(range(0, len(quadros), 12), 1):
        grupo = quadros[i:i + 12]
        nome = f"folha-{n:02d}"
        monta_folha(grupo, qdir / f"{nome}.jpg", cols=cols, cw=cw)
        linhas += [f"{nome} #{k} = {fmt_ts(t)}" for k, (t, _) in enumerate(grupo, 1)]
    linhas += [f"# momento {r} ignorado: {m}" for r, m in ignorados]
    (qdir / "indice.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return -(-len(quadros) // 12)


# ---------------------------------------------------------------- buscar
def cmd_buscar(a):
    termo = " ".join(a.termo.split())
    if not termo:
        print("Diga o tema da busca.")
        return 2
    quer = max(1, a.quantos)
    # "ytsearchN:" vem antes do texto do usuário, então ele nunca vira opção; "--" por garantia.
    # lang=pt: sem isso o YouTube devolve títulos traduzidos para o inglês (visto em 16/11/2026).
    r = ytdlp(["--flat-playlist", "--dump-json", "--extractor-args", "youtube:lang=pt",
               "--", f"ytsearch{min(quer * 3, 50)}:{termo}"], 300, uma_fonte=False)
    if r.returncode != 0 and not r.stdout.strip():
        print("A busca falhou: " + linha_erro(r.stderr))
        return 2
    achados, vistos = [], set()
    canal_f = norm(a.canal) if a.canal else None
    filtra_dur = a.max_min is not None or a.min_min > 0
    for l in r.stdout.splitlines():
        try:
            e = json.loads(l)
        except ValueError:
            continue
        vid = e.get("id") or e.get("url")
        if vid in vistos:
            continue
        vistos.add(vid)
        dur = e.get("duration")
        if filtra_dur and not dur:
            continue
        if dur and ((a.max_min is not None and dur > a.max_min * 60) or dur < a.min_min * 60):
            continue
        canal = e.get("channel") or e.get("uploader") or ""
        if canal_f and canal_f not in norm(canal):
            continue
        link = e.get("url") if eh_url(e.get("url")) else f"https://www.youtube.com/watch?v={e.get('id')}"
        d = e.get("upload_date")
        achados.append({"titulo": e.get("title"), "canal": canal, "duracao_s": dur,
                        "visualizacoes": e.get("view_count"),
                        "data": f"{d[6:8]}/{d[4:6]}/{d[:4]}" if d and len(d) == 8 else None, "link": link})
        if len(achados) >= quer:
            break
    for i, v in enumerate(achados, 1):
        vis = f"{v['visualizacoes']:,}".replace(",", ".") + " vis" if v["visualizacoes"] else "vis ?"
        print(f"{i}. {v['titulo']}\n   {v['canal']} | {fmt_ts(v['duracao_s']) if v['duracao_s'] else '?'} | "
              f"{vis}{' | ' + v['data'] if v['data'] else ''}\n   {v['link']}")
    if not achados:
        print("Nenhum vídeo dentro desses filtros. Tente outro tema ou relaxe a duração.")
    if a.saida:
        s = Path(a.saida).expanduser()
        s.mkdir(parents=True, exist_ok=True)
        (s / "busca.json").write_text(json.dumps({"termo": termo, "resultados": achados},
                                                 ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if achados else 2


# ---------------------------------------------------------------- comando: ouvir
def baixa_json(link):
    r = ytdlp(["--dump-json", "--skip-download", "--", link], 300)
    if r.returncode != 0:
        raise Falha(linha_erro(r.stderr))
    try:
        return json.loads(r.stdout.strip().splitlines()[0])
    except Exception:  # noqa: BLE001
        raise Falha("resposta do yt-dlp sem JSON")


def baixa_legenda(link, chave, tipo, tmp):
    r = ytdlp(["--skip-download", "--write-subs" if tipo == "manual" else "--write-auto-subs",
               "--sub-langs", f"-all,^{re.escape(chave)}$", "--sub-format", "vtt/best",
               "--convert-subs", "vtt", "-P", str(tmp), "-o", "sub", "--", link], 600)
    if r.returncode != 0:
        raise Falha(linha_erro(r.stderr))
    arqs = sorted(tmp.glob("*.vtt"))
    if not arqs:
        raise Falha("a legenda não veio")
    return arqs[0].read_text(encoding="utf-8", errors="replace")


def baixa_audio(link, tmp):
    r = ytdlp(["-f", "bestaudio/best", "-P", str(tmp), "-o", "audio.%(ext)s", "--", link], 3600)
    arqs = [f for f in tmp.glob("audio.*") if f.suffix not in (".part", ".ytdl")]
    if r.returncode != 0 or not arqs:
        raise Falha(linha_erro(r.stderr))
    return arqs[0]


def roda_whisper(audio, saida_txt, idioma, ini, fim, dur=None):
    uv = shutil.which("uv")
    if not uv:
        raise Falha("uv não encontrado no PATH (necessário para o Whisper)")
    cmd = [uv, "run", "--quiet", str(SCRIPT_DIR / "transcrever.py"), str(audio), "--saida", str(saida_txt)]
    if lang_ok(idioma):
        cmd += ["--idioma", lang_ok(idioma)]
    if ini is not None:
        cmd += ["--inicio", str(ini)]
    if fim is not None:
        cmd += ["--fim", str(fim)]
    print("  transcrevendo com Whisper (pode levar alguns minutos)...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env_sub(), timeout=4 * (dur or 3600) + 600)
    if r.returncode != 0:
        raise Falha("Whisper falhou: " + linha_erro(r.stderr))
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        raise Falha("o Whisper terminou, mas a resposta veio num formato inesperado")


def pouca_fala(palavras, dur):
    """Menos de ~20 palavras por minuto, ou menos de 15 no total em mídia com mais de 10 s."""
    if not dur or dur <= 0:
        return False
    return (dur > 10 and palavras < 15) or palavras < 20 * dur / 60


def usa_whisper(ficha, audio, txt, idioma, ini, fim, dur):
    """Roda o Whisper e classifica o resultado. Devolve o status."""
    res = roda_whisper(audio, txt, idioma, ini, fim, dur)
    ficha.update(origem_transcricao="whisper", idioma=lang_ok(res.get("idioma")) or ficha.get("idioma"))
    texto = txt.read_text(encoding="utf-8") if txt.exists() else ""
    palavras = len(re.sub(r"\[[\d:]+\]", " ", texto).split())
    if palavras == 0:
        ficha["origem_transcricao"] = "nenhuma"
        ficha["avisos"].append("o Whisper não encontrou fala: o conteúdo provavelmente está na tela; rode ver")
        return "sem-transcricao"
    trecho = ((fim if fim is not None else dur) or 0) - (ini or 0) if (fim is not None or dur) else None
    if pouca_fala(palavras, trecho):
        ficha["avisos"].append("pouca fala: o conteúdo provavelmente está na tela; rode ver")
    return "ok"


def ouvir_uma(fonte, pasta, a, tmp, ficha):
    """Preenche a pasta e a ficha; devolve o status."""
    pasta.mkdir(parents=True, exist_ok=True)
    avisos = ficha["avisos"]
    ini, fim = parse_time(a.inicio), parse_time(a.fim)
    txt = pasta / "transcricao.txt"
    txt.unlink(missing_ok=True)

    if eh_url(fonte):
        ficha.update(link=fonte, tipo="link")
        if re.search(r"podcasts\.apple\.com", fonte):
            raise Falha("Apple Podcasts por página não funciona: envie o link do feed RSS ou do mp3")
        info = baixa_json(fonte)
        ficha.update(titulo=info.get("title"), canal=info.get("channel") or info.get("uploader"),
                     duracao_s=info.get("duration"))
        chave, tipo, lang = escolhe_legenda(info)
        ficha["idioma"] = lang_ok(lang)
        if chave:
            try:
                pares = dedup_rolante(parse_vtt(baixa_legenda(fonte, chave, tipo, tmp)), manual=(tipo == "manual"))
                linhas = formata_linhas(pares, ini, fim)
                if linhas:
                    txt.write_text("\n".join(linhas) + "\n", encoding="utf-8")
                    ficha["origem_transcricao"] = "legenda-manual" if tipo == "manual" else "legenda-auto"
                    return "ok"
                avisos.append("legenda vazia" if not pares else "a legenda não tem nada no trecho pedido")
            except Exception as e:  # noqa: BLE001
                avisos.append(f"legenda {chave} falhou: {e}")
        if a.sem_whisper:
            avisos.append("sem legenda e --sem-whisper ligado")
            return "sem-transcricao"
        audio = baixa_audio(fonte, tmp)
        if not ficha["duracao_s"]:
            ficha["duracao_s"] = info_midia(audio).dur
        return usa_whisper(ficha, audio, txt, a.idioma or lang, ini, fim, ficha["duracao_s"])

    p = Path(fonte).expanduser()
    if not p.is_file():
        raise Falha(f"arquivo não encontrado: {fonte}")
    p = p.resolve()
    m = info_midia(p)
    ficha.update(titulo=p.stem, duracao_s=m.dur, tipo="arquivo", caminho=str(p))
    if m.tem_video:
        try:
            amostra_local(p, pasta, m.dur, tmp)
        except Exception as e:  # noqa: BLE001
            avisos.append(f"amostra.jpg não saiu: {e}")
    if a.sem_whisper:
        return "sem-transcricao"
    wav = tmp / "audio.wav"
    r = ff(["-i", str(p), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)], 3600)
    if not wav.exists() or wav.stat().st_size == 0:
        raise Falha("não consegui extrair áudio: " + linha_erro(r.stderr))
    wd = info_midia(wav).dur
    if r.returncode != 0 or (m.dur and wd and wd < m.dur * 0.95):
        avisos.append(f"parcial: o áudio extraído tem {fmt_ts(wd or 0)} de {fmt_ts(m.dur or 0)}")
    return usa_whisper(ficha, wav, txt, a.idioma, ini, fim, m.dur)


def amostra_local(video, pasta, dur, tmp):
    dur = dur or 8
    qs = []
    for i in range(8):
        t = dur * (i + 0.5) / 8
        p = tmp / f"am_{i}.jpg"
        if quadro_em(video, t, p, escala=320):
            qs.append((t, p))
    if not qs:
        raise Falha("nenhum quadro extraído")
    monta_folha(qs, pasta / "amostra.jpg", cols=4, cw=320)


def le_manifesto(man_path):
    try:
        m = json.loads(man_path.read_text(encoding="utf-8"))
        if isinstance(m, list):
            return m
        raise ValueError("não é uma lista")
    except FileNotFoundError:
        return []
    except Exception:  # noqa: BLE001
        bak = man_path.with_name("manifesto.json.bak")
        os.replace(man_path, bak)
        print(f"AVISO: manifesto.json estava corrompido; guardei como {bak.name} e comecei outro.")
        return []


def proximo_indice(saida):
    nums = [int(d.name[:2]) for d in saida.iterdir() if d.is_dir() and re.match(r"\d\d-", d.name)]
    return max(nums, default=0) + 1


def cmd_ouvir(a):
    if a.lote < 1:
        print("--lote precisa ser 1 ou mais.")
        return 2
    ini, fim = parse_time(a.inicio), parse_time(a.fim)
    if ini is not None and fim is not None and fim <= ini:
        print("--fim precisa ser maior que --inicio.")
        return 2
    try:
        ffmpeg_exe()
    except Falha as e:
        print(f"Falta ferramenta: {e}")
        return 3
    saida = Path(a.saida).expanduser().resolve()
    saida.mkdir(parents=True, exist_ok=True)
    man_path = saida / "manifesto.json"
    manifesto = le_manifesto(man_path)
    idx = proximo_indice(saida) - 1
    cont = {"ok": 0, "sem-transcricao": 0, "erro": 0, "adiado": 0}
    t_tudo = time.time()
    try:
        for n, fonte in enumerate(a.fontes):
            if n >= a.lote:
                manifesto.append({"fonte": fonte, "pasta": None, "status": "adiado",
                                  "erro": f"passou do limite --lote {a.lote}; rode de novo", "tempo_s": 0})
                cont["adiado"] += 1
                continue
            idx += 1
            t0 = time.time()
            nome = Path(fonte).stem if not eh_url(fonte) else fonte.split("//", 1)[1]
            pasta = saida / f"{idx:02d}-{slugify(nome)}"
            reg = {"fonte": fonte, "pasta": pasta.name, "status": "erro", "erro": None}
            ficha = {"titulo": None, "canal": None, "duracao_s": None, "link": None, "tipo": None,
                     "idioma": None, "origem_transcricao": "nenhuma", "avisos": []}
            try:
                with tempfile.TemporaryDirectory(prefix="assistir-", ignore_cleanup_errors=True) as tmp:
                    reg["status"] = ouvir_uma(fonte, pasta, a, Path(tmp), ficha)
            except Falha as e:
                reg["erro"] = str(e)
            except subprocess.TimeoutExpired as e:
                reg["erro"] = f"tempo esgotado em {Path(str(e.cmd[0])).name if e.cmd else 'um comando'}"
            except Exception as e:  # noqa: BLE001
                reg["erro"] = f"{type(e).__name__}: {e}"
            if reg["erro"]:
                orig = reg["erro"]
                reg["erro"] = traduz_erro(orig)
                if reg["erro"] != orig:
                    reg["erro_original"] = orig
                ficha["erro"] = reg["erro"]
            pasta.mkdir(parents=True, exist_ok=True)
            (pasta / "ficha.json").write_text(json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8")
            if eh_url(fonte) and ficha.get("titulo"):  # renomeia com o título (ficha já está gravada)
                novo = saida / f"{idx:02d}-{slugify(ficha['titulo'])}"
                if novo != pasta:
                    try:
                        if novo.exists():
                            raise OSError("já existe")
                        pasta.rename(novo)
                        pasta, reg["pasta"] = novo, novo.name
                    except OSError as e:
                        ficha["avisos"].append(f"não renomeei a pasta pelo título: {e}")
                        (pasta / "ficha.json").write_text(json.dumps(ficha, ensure_ascii=False, indent=2),
                                                          encoding="utf-8")
            reg.update(origem_transcricao=ficha["origem_transcricao"], avisos=ficha["avisos"])
            reg["tempo_s"] = round(time.time() - t0, 1)
            manifesto.append(reg)
            cont[reg["status"]] += 1
            if reg["status"] == "erro":
                print(f"[{idx}] ERRO  {fonte}\n      {reg['erro']}")
            else:
                print(f"[{idx}] {reg['status'].upper()}  {reg['pasta']}  ({reg['origem_transcricao']}, {reg['tempo_s']} s)")
                for av in ficha["avisos"]:
                    print(f"      aviso: {av}")
            man_path.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        man_path.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    tempo = round(time.time() - t_tudo)
    if cont["ok"] == len(a.fontes):
        print(f"Tudo certo: {cont['ok']} ok em {tempo} s. Detalhes: {man_path}")
    else:
        print(f"Terminou em {tempo} s: {cont['ok']} ok, {cont['sem-transcricao']} sem transcrição, "
              f"{cont['erro']} com erro, {cont['adiado']} adiados (veja manifesto.json). Detalhes: {man_path}")
    return 0 if cont["ok"] else 2


# ---------------------------------------------------------------- comando: ver
def cmd_ver(a):
    try:
        return _ver(a)
    except Falha as e:
        print(f"Erro: {e}")
    except subprocess.TimeoutExpired:
        print("Erro: o ffmpeg ou o download demorou demais e foi interrompido.")
    except Exception as e:  # noqa: BLE001
        print(f"Erro inesperado ao gerar os quadros ({type(e).__name__}): {e}")
    return 2


def _ver(a):
    try:
        ffmpeg_exe()
    except Falha as e:
        print(f"Falta ferramenta: {e}")
        return 3
    _avisos_ver.clear()
    alvo = Path(a.pasta).expanduser().resolve()
    ficha, video, baixou = {}, None, False
    if alvo.is_file():
        video, pasta = alvo, alvo.with_name(alvo.stem + "-assistir")
    elif alvo.is_dir():
        pasta = alvo
        try:
            ficha = json.loads((pasta / "ficha.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
        if ficha.get("caminho") and Path(ficha["caminho"]).is_file():
            video = Path(ficha["caminho"])
        else:
            video = next((f for f in sorted(pasta.glob("video.*")) if f.suffix not in (".part", ".ytdl")), None)
    else:
        print(f"Não achei: {alvo}")
        return 2
    pasta.mkdir(parents=True, exist_ok=True)
    if video is None:
        link = ficha.get("link")
        if not eh_url(link):
            print("Pasta sem vídeo e sem um link válido (http/https) na ficha.json.")
            return 2
        print("Baixando o vídeo em baixa resolução (até 480p)...", flush=True)
        r = ytdlp(["-f", "bv*[height<=480]+ba/b[height<=480]/b", "--merge-output-format", "mp4",
                   "-P", str(pasta), "-o", "video.%(ext)s", "--", link], 3600)
        video = next((f for f in sorted(pasta.glob("video.*")) if f.suffix not in (".part", ".ytdl")), None)
        if r.returncode != 0 or not video:
            print("Download falhou: " + linha_erro(r.stderr))
            return 2
        baixou = True
        print(f"baixou o vídeo em 480p: {video.stat().st_size / 1e6:.1f} MB")
    m = info_midia(video)
    if not m.tem_video:
        print("Esse arquivo não tem imagem (só áudio ou capa de álbum).")
        return 2
    modo = a.modo
    if modo == "amostra" and not m.dur:
        print("Não sei a duração do vídeo: usei o modo cenas no lugar de amostra.")
        modo = "cenas"
    ini, fim = parse_time(a.inicio), parse_time(a.fim)
    if ini is not None and fim is not None and fim <= ini:
        print("--fim precisa ser maior que --inicio.")
        return 2
    moms = parse_momentos(a.momentos)
    with tempfile.TemporaryDirectory(prefix="assistir-q-", ignore_cleanup_errors=True) as tmp:
        qs, ign = escolhe_quadros(video, Path(tmp), ini, fim, m.dur or 0, modo, a.max_quadros, moms)
        for r_, mot in ign:
            print(f"momento {r_} ignorado: {mot}")
        if not qs:
            print("Nenhum quadro extraído.")
            return 2
        n = gera_folhas(qs, pasta / "quadros", 480, ign)
    for av in _avisos_ver:
        print("aviso: " + av)
    print(f"{len(qs)} quadros em {n} folha(s): {pasta / 'quadros'}  (índice: indice.txt)")
    return 0


# ---------------------------------------------------------------- comando: checar
def cmd_checar(_a):
    ok = True

    def lin(bom, txt):
        print(("OK    " if bom else "FALTA ") + txt)
    uv = shutil.which("uv")
    if uv:
        v = subprocess.run([uv, "--version"], capture_output=True, text=True).stdout.strip()
        lin(True, f"uv: {v} ({uv})")
    else:
        lin(False, "uv não está no PATH (instale em https://docs.astral.sh/uv/)")
        ok = False
    try:
        lin(True, f"ffmpeg embutido: {ffmpeg_exe()}")
    except Falha as e:
        lin(False, str(e))
        ok = False
    try:
        import yt_dlp.version as yv
        lin(True, f"yt-dlp: versão {yv.__version__}")
    except Exception as e:  # noqa: BLE001
        lin(False, f"yt-dlp: {e}")
        ok = False
    try:
        dn = shutil.which("deno", path=env_sub()["PATH"])
    except Falha:
        dn = None
    lin(bool(dn), f"deno: ajuda o programa a ler o YouTube ({dn or 'não achei'})")
    if uv:
        r = subprocess.run([uv, "run", "--quiet", str(SCRIPT_DIR / "transcrever.py"), "--checar"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        try:
            j = json.loads(r.stdout.strip().splitlines()[-1])
            lin(j["faster_whisper"], "Whisper (faster-whisper): " + ("pronto" if j["faster_whisper"] else "não carrega"))
            if j["modelo_em_cache"]:
                lin(True, "modelo large-v3-turbo já baixado")
            else:
                print("AVISO modelo large-v3-turbo ainda não baixado: o primeiro uso baixa cerca de 1,6 GB")
        except Exception:  # noqa: BLE001
            lin(False, "Whisper: " + linha_erro(r.stderr))
            ok = False
    print("Tudo certo." if ok else "Há itens faltando acima.")
    return 0 if ok else 3


def main():
    utf8()
    ap = argparse.ArgumentParser(prog="assistir", epilog="Código de saída: 0 = deu certo; 2 = nada deu certo; 3 = falta ferramenta.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("buscar")
    b.add_argument("termo")
    b.add_argument("--quantos", type=int, default=10)
    b.add_argument("--max-min", type=float, default=None)
    b.add_argument("--min-min", type=float, default=0)
    b.add_argument("--canal")
    b.add_argument("--saida")
    o = sub.add_parser("ouvir", epilog="Código de saída: 0 = ao menos uma fonte deu certo; 2 = nenhuma deu certo; 3 = falta ferramenta.")
    o.add_argument("fontes", nargs="+")
    o.add_argument("--saida", required=True)
    o.add_argument("--idioma")
    o.add_argument("--inicio")
    o.add_argument("--fim")
    o.add_argument("--sem-whisper", action="store_true")
    o.add_argument("--lote", type=int, default=10)
    v = sub.add_parser("ver")
    v.add_argument("pasta")
    v.add_argument("--modo", choices=["cenas", "amostra"], default="cenas")
    v.add_argument("--max-quadros", type=int, default=40)
    v.add_argument("--momentos")
    v.add_argument("--inicio")
    v.add_argument("--fim")
    sub.add_parser("checar")
    a = ap.parse_args()
    return {"buscar": cmd_buscar, "ouvir": cmd_ouvir, "ver": cmd_ver, "checar": cmd_checar}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
