# /// script
# requires-python = ">=3.10"
# dependencies = ["imageio-ffmpeg", "pillow"]
# ///
"""Autoteste offline da skill assistir: vídeo sintético + extração de quadros + folhas + legendas + slugs.
Sem internet e sem Whisper. Saída 0 se tudo passar."""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assistir as A  # noqa: E402

VTT_ROLANTE = """WEBVTT
Kind: captions
Language: pt

00:00:00.000 --> 00:00:02.000 align:start position:0%
olá pessoal<00:00:00.500><c> hoje</c>

00:00:02.000 --> 00:00:02.010 align:start position:0%
olá pessoal hoje

00:00:02.010 --> 00:00:04.000 align:start position:0%
olá pessoal hoje
vamos falar de pix

00:00:04.000 --> 00:00:04.010
vamos falar de pix

00:00:04.010 --> 00:00:06.000
vamos falar de pix
e de pagamentos

00:01:05.000 --> 00:01:06.000
a b

00:01:06.000 --> 00:01:07.000
a b c

01:02:03.000 --> 01:02:04.000
hora longa

01:02:10.000 --> 01:02:11.000
sim.

01:02:20.000 --> 01:02:21.000
sim.
"""


def main():
    A.utf8()
    t0 = time.time()
    # slugs
    s = A.slugify("Olá, Mundo! Ação & Pagamentos — Beehive " * 5)
    assert s == s.lower() and s.isascii() and len(s) <= 40 and not s.startswith("-"), s
    assert A.slugify("Ç ã é") == "c-a-e" and A.slugify("???") == "video"
    # timestamps
    assert A.fmt_ts(65) == "01:05" and A.fmt_ts(3725) == "1:02:05" and A.parse_time("1:05") == 65
    # legenda rolante
    pares = A.dedup_rolante(A.parse_vtt(VTT_ROLANTE))
    textos = [x for _, x in pares]
    assert textos == ["olá pessoal hoje", "vamos falar de pix", "e de pagamentos", "a b c", "hora longa",
                      "sim.", "sim."], textos  # fala repetida de verdade fica
    lin = A.formata_linhas(pares)
    assert lin[0] == "[00:00] olá pessoal hoje" and lin[1] == "[00:02] vamos falar de pix", lin
    assert lin[3] == "[01:05] a b c" and lin[4].startswith("[1:02:03]"), lin
    assert len(A.formata_linhas(pares, ini=3, fim=100)) == 2
    man = A.dedup_rolante(A.parse_vtt("WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nigual\n\n00:00:01.000 --> 00:00:03.000\nigual\n"),
                          manual=True)
    assert len(man) == 2, man  # legenda manual nunca é deduplicada
    assert A.lang_ok("pt-BR") == "pt" and A.lang_ok("und") is None and A.lang_ok("portuguese") is None
    assert "limitou" in A.traduz_erro("ERROR: HTTP Error 429: Too Many Requests")
    assert "indisponível" in A.traduz_erro("ERROR: Video unavailable") and A.traduz_erro("xyz") == "xyz"
    assert A.pouca_fala(5, 60) and not A.pouca_fala(200, 60) and A.pouca_fala(10, 30)
    # escolha de legenda
    info = {"language": "pt", "subtitles": {}, "automatic_captions": {"pt-orig": [1], "pt": [1], "en": [1]}}
    assert A.escolhe_legenda(info)[:2] == ("pt-orig", "auto")
    info["subtitles"] = {"pt": [1]}
    assert A.escolhe_legenda(info)[:2] == ("pt", "manual")
    assert A.escolhe_legenda({"automatic_captions": {"en": [1], "fr": [1]}})[0] is None  # nunca traduzida

    with tempfile.TemporaryDirectory(prefix="assistir-teste-") as tmp:
        tmp = Path(tmp)
        v = tmp / "sint.mp4"
        sz = "s=640x360:r=10:d=5"
        r = A.ff(["-f", "lavfi", "-i", f"testsrc2={sz}", "-f", "lavfi", "-i", f"color=c=red:{sz}",
                  "-f", "lavfi", "-i", f"smptebars={sz}", "-f", "lavfi", "-i", f"color=c=green:{sz}",
                  "-f", "lavfi", "-i", "sine=frequency=440:duration=20",
                  "-filter_complex", "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0[v]",
                  "-map", "[v]", "-map", "4:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                  "-c:a", "aac", "-shortest", str(v)])
        assert v.exists(), r.stderr[-400:]
        dur, tem_video, w, h, _st = A.info_midia(v)
        assert 19 <= dur <= 21 and tem_video and (w, h) == (640, 360), (dur, tem_video, w, h)

        cen = A.quadros_cenas(v, tmp / "c", None, None)
        assert len(cen) >= 4, len(cen)
        ts = [t for t, _ in cen]
        assert ts == sorted(ts) and ts[0] < 0.5, ts
        assert any(abs(t - 5) < 0.6 for t in ts) and any(abs(t - 15) < 0.6 for t in ts), ts

        uni = A.quadros_uniformes(v, tmp / "u", None, None, 8, dur)
        tu = [t for t, _ in uni]
        assert len(uni) >= 6 and tu == sorted(tu), tu

        rec = A.quadros_cenas(v, tmp / "r", 5, 12)  # trecho: tempos absolutos
        assert rec and all(4.5 <= t <= 12.5 for t, _ in rec), [t for t, _ in rec]

        qs, ign = A.escolhe_quadros(v, tmp / "e", None, None, dur, "cenas", 10,
                                    [("0:07", 7.0), ("9:99", 639.0), ("abc", None)])
        assert [r for r, _ in ign] == ["9:99", "abc"], ign  # momentos descartados são reportados
        assert len(qs) <= 10
        tq = [t for t, _ in qs]
        assert tq == sorted(tq) and any(abs(t - 7) < 0.01 for t in tq), tq
        am, _ = A.escolhe_quadros(v, tmp / "am", None, None, dur, "amostra", 40, [])
        assert len(am) == 8

        n = A.gera_folhas(qs, tmp / "quadros", 480, ign)
        assert n == 1 and (tmp / "quadros" / "folha-01.jpg").stat().st_size > 5000
        idx = (tmp / "quadros" / "indice.txt").read_text(encoding="utf-8").splitlines()
        assert len(idx) == len(qs) + 2 and idx[0].startswith("folha-01 #1 = 00:0"), idx
        assert idx[-2] == "# momento 9:99 ignorado: passa da duração do vídeo (00:20)", idx
        # mais de 12 quadros => 2 folhas
        muitos = (qs * 4)[:15]
        assert A.gera_folhas(sorted(muitos, key=lambda x: x[0]), tmp / "q2", 480) == 2

        # ---- ouvir com Whisper simulado
        def whisper_falso(palavras):
            def f(audio, saida_txt, idioma, ini, fim, dur=None):
                saida_txt.write_text(("[00:01] " + " ".join(["fala"] * palavras) + "\n") if palavras else "", encoding="utf-8")
                return {"idioma": "pt"}
            return f
        base = dict(idioma=None, inicio=None, fim=None, sem_whisper=False, lote=10)
        A.roda_whisper = whisper_falso(0)
        fic = {"avisos": [], "duracao_s": None, "origem_transcricao": "nenhuma"}
        with tempfile.TemporaryDirectory() as t2:
            st = A.ouvir_uma(str(v), Path(t2) / "p", argparse.Namespace(**base), Path(t2), fic)
        assert st == "sem-transcricao" and fic["avisos"], (st, fic)
        A.roda_whisper = whisper_falso(5)
        fic = {"avisos": [], "duracao_s": None, "origem_transcricao": "nenhuma"}
        with tempfile.TemporaryDirectory() as t2:
            st = A.ouvir_uma(str(v), Path(t2) / "p", argparse.Namespace(**base), Path(t2), fic)
        assert st == "ok" and any("pouca fala" in x for x in fic["avisos"]), (st, fic)

        # ---- lote, manifesto, códigos de saída, colisão de índice
        A.roda_whisper = whisper_falso(80)
        saida = tmp / "saida"
        (saida / "05-antigo").mkdir(parents=True)
        (saida / "manifesto.json").write_text("{quebrado", encoding="utf-8")
        rc = A.cmd_ouvir(argparse.Namespace(**{**base, "fontes": [str(v)] * 3, "saida": str(saida), "lote": 1}))
        man = json.loads((saida / "manifesto.json").read_text(encoding="utf-8"))
        assert rc == 0 and [m["status"] for m in man] == ["ok", "adiado", "adiado"], man
        assert (saida / "manifesto.json.bak").exists() and (saida / "06-sint").is_dir()
        rc = A.cmd_ouvir(argparse.Namespace(**{**base, "fontes": [str(v)], "saida": str(saida)}))
        assert rc == 0 and (saida / "07-sint").is_dir()  # sem colisão
        rc = A.cmd_ouvir(argparse.Namespace(**{**base, "fontes": [str(tmp / "nao-existe.mp4")], "saida": str(saida)}))
        assert rc == 2, rc
        assert A.cmd_ouvir(argparse.Namespace(**{**base, "fontes": [str(v)], "saida": str(saida), "lote": 0})) == 2
    print(f"Autoteste OK em {time.time() - t0:.1f} s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
