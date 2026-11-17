---
name: modelo-certo
description: "Faz cada agente do Claude rodar no modelo mais barato que entrega a mesma qualidade, enquanto o planejamento fica no modelo forte da conversa (Fable ou Opus). Use para ligar, conferir ou desligar a regra neste computador ('instala o modelo certo', 'confere o modelo certo', 'desliga o modelo certo'), para ver quanto os agentes estão usando cada modelo ('relatório do modelo certo') ou para decidir o modelo de um agente."
user-invocable: true
---

# /modelo-certo

O planejamento fica com o modelo da conversa. Cada agente roda no degrau certo da escada (haiku, sonnet, opus; fable só com justificativa). A regra está em [REGRA.md](REGRA.md) e vale em toda conversa depois de ligada.

## Três peças

1. **Regra** (`REGRA.md`): carregada em toda conversa por uma linha no `CLAUDE.md` do usuário. Diz qual modelo usar em cada tipo de tarefa.
2. **Vigia** (`scripts/escolher_modelo.py`): roda antes de cada agente. Se o agente vier sem modelo escolhido, ou com Fable sem `[fable-ok: motivo]`, ele bloqueia e devolve a escada para o Claude escolher. Registra cada decisão em `~/.claude/modelo-certo.log`.
3. **Rede de segurança**: `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` no `settings.json`, para o que escapar do vigia.

## Comandos (rode a partir da pasta da skill)

- Ligar: `uv run --script scripts/instalar.py`
- Conferir: `uv run --script scripts/instalar.py --checar`
- Desligar: `uv run --script scripts/instalar.py --remover`

Ligar e desligar fazem cópia de segurança de `settings.json` e `CLAUDE.md` antes de mexer (`*.antes-modelo-certo-<data>`). Funciona na hora, sem reiniciar o aplicativo.

## Relatório

Quando pedirem o relatório, leia `~/.claude/modelo-certo.log` (colunas: data, decisão, tipo de agente, descrição) e diga em linguagem simples quantos agentes rodaram em cada modelo e quantos foram bloqueados e corrigidos.

## Limites

- O vigia cobre a ferramenta Agent. Agentes de Workflow seguem a regra escrita (o Claude passa `model` em cada `agent()`), mas o vigia não os confere.
- `fork` sempre roda no modelo da conversa; o vigia só lembra disso.
- Escolher o degrau é julgamento do Claude. A escada e o bloqueio reduzem o erro, não zeram.

O porquê, com fontes: [references/pesquisa.md](references/pesquisa.md).
