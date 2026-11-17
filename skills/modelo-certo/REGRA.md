# Modelo certo para cada agente (regra sempre ativa)

Quem planeja e coordena é o modelo da conversa (Fable ou Opus, no esforço que a pessoa escolheu). Cada agente que você cria recebe o modelo mais barato que faz aquela tarefa **sem perder qualidade**. Nunca deixe um agente herdar o modelo da conversa por acaso.

Esta regra é um pedido explícito do usuário: em toda chamada da ferramenta Agent passe `model`, e passe `effort` quando o degrau abaixo indicar. Em todo `agent()` de Workflow, passe `model` e `effort` nas opções.

## Escada (suba um degrau na dúvida: qualidade primeiro, custo depois)

| Degrau | Quando | effort |
|---|---|---|
| `haiku` | Trabalho braçal com resposta fácil de conferir: achar e listar arquivos, ler e extrair trechos, contar, inventário, conferir formato, buscar na web e trazer links. | `low` ou `medium` |
| `sonnet` (padrão) | Código com escopo claro, testes, análise de documento, pesquisa com síntese, escrita, revisão comum, transcrição de reunião. | `medium` ou `high` |
| `opus` | Decisão difícil, arquitetura, bug com causa incerta, revisão onde errar custa caro (dinheiro, segurança, jurídico, dado de cliente), juiz final de qualidade. | `medium`; `high` se errar custa caro |
| `fable` | Só quando a tarefa do agente é tão difícil quanto o próprio planejamento e o Opus em `high` não basta. Escreva `[fable-ok: motivo]` na `description`. | o da sessão |

## Como delegar bem (é aqui que modelo barato ganha ou perde)

- Agente barato erra por falta de contexto, não por falta de inteligência. O brief diz: objetivo, arquivos, o que já foi descartado, limites e formato da resposta.
- Planejamento, decisões de desenho e a síntese final ficam com você. O agente executa uma parte bem definida.
- Resultado fraco: refaça um degrau acima. Não repita no mesmo modelo.
- `fork` sempre roda no modelo da conversa. Use fork só quando o agente precisa da conversa inteira; senão, agente novo com brief.
- Agentes com `model:` no próprio arquivo de definição: passe o mesmo valor, ou um degrau diferente se a tarefa pedir.
