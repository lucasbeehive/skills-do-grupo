# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Hook PreToolUse da ferramenta Agent: exige modelo escolhido de propósito.

- Sem `model`: bloqueia e devolve a escada para o Claude escolher.
- `model` = fable sem `[fable-ok: motivo]`: bloqueia.
- `fork`: deixa passar (sempre herda a conversa) e lembra disso.
Rode com --teste para a conferência.
"""
import datetime
import json
import sys
from pathlib import Path

LOG = Path.home() / ".claude" / "modelo-certo.log"

ESCADA = (
    "Escolha o modelo do agente de propósito (regra modelo-certo). "
    "haiku: braçal e fácil de conferir (achar, listar, ler, extrair, contar). "
    "sonnet: padrão (código com escopo claro, análise, pesquisa, escrita, revisão comum). "
    "opus: decisão difícil, bug incerto, revisão de alto risco, juiz final (effort medium ou high). "
    "fable: só com [fable-ok: motivo] na description. "
    "Na dúvida, um degrau acima. Refaça a chamada com o parâmetro model."
)


def decidir(tool_input):
    """Devolve (saida_json_ou_None, rotulo_para_log)."""
    tipo = (tool_input.get("subagent_type") or "").strip()
    modelo = (tool_input.get("model") or "").strip().lower()
    if tipo == "fork":
        return ({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "Fork roda no modelo da conversa. Use fork só se o agente precisa da conversa inteira.",
        }}, "fork")
    if not modelo:
        return (_negar("Agente sem modelo escolhido. " + ESCADA), "negado-sem-modelo")
    if "fable" in modelo:
        texto = f"{tool_input.get('description', '')} {tool_input.get('prompt', '')}".lower()
        if "[fable-ok" not in texto:
            return (_negar("Fable em agente só com justificativa: escreva [fable-ok: motivo] na description, "
                           "ou use opus com effort high. " + ESCADA), "negado-fable")
    return (None, f"ok-{modelo}")


def _negar(motivo):
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": motivo,
    }}


def _registrar(rotulo, tool_input):
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')}\t{rotulo}\t"
                    f"{tool_input.get('subagent_type') or 'general-purpose'}\t"
                    f"{(tool_input.get('description') or '')[:60]}\n")
    except OSError:
        pass  # log é só para medir; nunca trava o Claude


def teste():
    casos = [
        ({"prompt": "x"}, "negado-sem-modelo"),
        ({"prompt": "x", "model": "sonnet"}, "ok-sonnet"),
        ({"prompt": "x", "model": "haiku", "subagent_type": "Explore"}, "ok-haiku"),
        ({"prompt": "x", "model": "fable", "description": "planejar"}, "negado-fable"),
        ({"prompt": "x", "model": "fable", "description": "[fable-ok: prova matemática] y"}, "ok-fable"),
        ({"prompt": "x", "subagent_type": "fork"}, "fork"),
    ]
    for entrada, esperado in casos:
        _, rotulo = decidir(entrada)
        assert rotulo == esperado, (entrada, rotulo, esperado)
    print(f"ok: {len(casos)} casos conferidos")


def main():
    if "--teste" in sys.argv:
        teste()
        return
    try:
        dados = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return  # entrada estranha: não bloqueia nada
    if dados.get("tool_name") not in ("Agent", "Task"):
        return
    tool_input = dados.get("tool_input") or {}
    saida, rotulo = decidir(tool_input)
    _registrar(rotulo, tool_input)
    if saida:
        print(json.dumps(saida))  # ASCII puro: acentos viram \u e chegam certos em qualquer terminal


if __name__ == "__main__":
    main()
