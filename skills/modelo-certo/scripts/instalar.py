# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Liga (ou desliga) a regra modelo-certo no Claude deste computador.

uv run --script instalar.py            liga
uv run --script instalar.py --checar   confere se está tudo ligado
uv run --script instalar.py --remover  desliga (a pasta da skill fica)

Mexe em dois arquivos da pasta .claude do usuário, sempre com cópia de segurança antes:
- settings.json: o vigia (hook) da ferramenta Agent e o padrão sonnet para agentes;
- CLAUDE.md: uma linha que carrega REGRA.md em toda conversa.
"""
import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path

CLAUDE = Path.home() / ".claude"
SETTINGS = CLAUDE / "settings.json"
CLAUDE_MD = CLAUDE / "CLAUDE.md"
SKILL = Path(__file__).resolve().parent.parent
VIGIA = SKILL / "scripts" / "escolher_modelo.py"
MARCA = "escolher_modelo.py"
IMPORT = "@~/.claude/skills/modelo-certo/REGRA.md"
ENV_KEY = "CLAUDE_CODE_SUBAGENT_MODEL"


def _copia(arquivo):
    if arquivo.exists():
        selo = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(arquivo, arquivo.with_name(f"{arquivo.name}.antes-modelo-certo-{selo}"))


def _ler_settings():
    if not SETTINGS.exists():
        return {}
    return json.loads(SETTINGS.read_text(encoding="utf-8"))  # JSON quebrado: para aqui, não sobrescreve


def _sem_vigia(entradas):
    limpas = []
    for e in entradas:
        e = dict(e)
        e["hooks"] = [h for h in e.get("hooks", []) if MARCA not in h.get("command", "")]
        if e["hooks"]:
            limpas.append(e)
    return limpas


def ligar():
    s = _ler_settings()
    _copia(SETTINGS)
    hooks = s.setdefault("hooks", {})
    pre = _sem_vigia(hooks.get("PreToolUse", []))
    pre.append({"matcher": "Agent", "hooks": [{
        "type": "command",
        "command": f'uv run --quiet --script "{VIGIA.as_posix()}"',
        "timeout": 15,
        "statusMessage": "Conferindo o modelo do agente",
    }]})
    hooks["PreToolUse"] = pre
    s.setdefault("env", {}).setdefault(ENV_KEY, "sonnet")
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    texto = CLAUDE_MD.read_text(encoding="utf-8") if CLAUDE_MD.exists() else ""
    if IMPORT not in texto:
        _copia(CLAUDE_MD)
        CLAUDE_MD.write_text(texto.rstrip() + f"\n\n# modelo-certo (modelo de cada agente)\n{IMPORT}\n", encoding="utf-8")
    print("Ligado. Conferindo...")
    return checar()


def remover():
    s = _ler_settings()
    _copia(SETTINGS)
    hooks = s.get("hooks", {})
    pre = _sem_vigia(hooks.get("PreToolUse", []))
    if pre:
        hooks["PreToolUse"] = pre
    else:
        hooks.pop("PreToolUse", None)
    if s.get("env", {}).get(ENV_KEY) == "sonnet":
        s["env"].pop(ENV_KEY)
        if not s["env"]:
            s.pop("env")
    SETTINGS.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if CLAUDE_MD.exists():
        texto = CLAUDE_MD.read_text(encoding="utf-8")
        if IMPORT in texto:
            _copia(CLAUDE_MD)
            texto = texto.replace(f"\n\n# modelo-certo (modelo de cada agente)\n{IMPORT}\n", "\n").replace(IMPORT, "")
            CLAUDE_MD.write_text(texto.rstrip() + "\n", encoding="utf-8")
    print("Desligado. A pasta da skill continua; apague-a se quiser.")
    return 0


def checar():
    s = _ler_settings()
    itens = {
        "vigia da ferramenta Agent no settings.json": any(
            MARCA in h.get("command", "")
            for e in s.get("hooks", {}).get("PreToolUse", []) if e.get("matcher") == "Agent"
            for h in e.get("hooks", [])),
        "padrão sonnet para agentes": s.get("env", {}).get(ENV_KEY) == "sonnet",
        "regra carregada pelo CLAUDE.md": CLAUDE_MD.exists() and IMPORT in CLAUDE_MD.read_text(encoding="utf-8"),
        "arquivo REGRA.md": (SKILL / "REGRA.md").exists(),
    }
    teste = subprocess.run([sys.executable, str(VIGIA), "--teste"], capture_output=True, text=True)
    itens["vigia decide certo (6 casos)"] = teste.returncode == 0
    for nome, ok in itens.items():
        print(f"[{'ok' if ok else 'FALTA'}] {nome}")
    if teste.returncode:
        print(teste.stderr.strip())
    tudo = all(itens.values())
    print("Tudo certo." if tudo else "Algo faltou: rode de novo sem --checar.")
    return 0 if tudo else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # acentos certos no terminal do Windows
    except (AttributeError, ValueError):
        pass
    if "--remover" in sys.argv:
        sys.exit(remover())
    sys.exit(checar() if "--checar" in sys.argv else ligar())
