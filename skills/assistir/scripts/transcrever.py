# /// script
# requires-python = ">=3.10"
# dependencies = ["faster-whisper", "av<17", "imageio-ffmpeg"]
# ///
"""Transcreve um áudio com Whisper (faster-whisper, CPU) e grava linhas `[mm:ss] texto`.

Uso:
  uv run transcrever.py AUDIO --saida ARQUIVO.txt [--idioma pt] [--inicio mm:ss] [--fim mm:ss]
  uv run transcrever.py --checar

Chamado por assistir.py só quando o vídeo não tem legenda.
"""
import argparse
import json
import os
import sys
from pathlib import Path

MODELO = "large-v3-turbo"
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def fmt_ts(s):
    s = int(s)
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def parse_time(v):
    if v is None or v == "":
        return None
    parts = [float(p) for p in str(v).split(":")]
    t = 0.0
    for p in parts:
        t = t * 60 + p
    return t


def modelo_em_cache():
    base = Path(os.environ.get("HF_HUB_CACHE") or
                Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub")
    return any(any(d.glob("snapshots/*/model.bin")) for d in base.glob(f"models--*faster-whisper-{MODELO}"))


def checar():
    try:
        import faster_whisper  # noqa: F401
        ok = True
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"erro ao importar: {e}", file=sys.stderr)
    print(json.dumps({"faster_whisper": ok, "modelo_em_cache": modelo_em_cache()}))
    return 0 if ok else 3


def main():
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", nargs="?")
    ap.add_argument("--saida")
    ap.add_argument("--idioma")
    ap.add_argument("--inicio")
    ap.add_argument("--fim")
    ap.add_argument("--checar", action="store_true")
    a = ap.parse_args()
    if a.checar:
        return checar()
    if not a.audio or not a.saida:
        ap.error("informe AUDIO e --saida")
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio

    ini, fim = parse_time(a.inicio), parse_time(a.fim)
    if ini is not None and fim is not None and fim <= ini:
        ap.error("--fim precisa ser maior que --inicio")
    if not modelo_em_cache():
        print("Primeiro uso: baixando o modelo Whisper (cerca de 1,6 GB)...", file=sys.stderr)
    model = WhisperModel(MODELO, device="cpu", compute_type="int8")
    # Recorte feito aqui (sobre o áudio decodificado) para manter o VAD ligado; tempos voltam absolutos.
    audio = decode_audio(a.audio, sampling_rate=16000)
    off = ini or 0.0
    if ini is not None or fim is not None:
        audio = audio[int(off * 16000): int(fim * 16000) if fim is not None else None]
    segs, info = model.transcribe(audio, language=(a.idioma or None), beam_size=1,
                                  condition_on_previous_text=False, vad_filter=True)
    linhas = []
    for s in segs:
        t = s.text.strip()
        if t:
            linhas.append(f"[{fmt_ts(s.start + off)}] {t}")
    Path(a.saida).write_text("\n".join(linhas) + ("\n" if linhas else ""), encoding="utf-8")
    print(json.dumps({"idioma": info.language, "prob": round(info.language_probability, 3),
                      "duracao_s": round(info.duration, 1), "linhas": len(linhas)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
