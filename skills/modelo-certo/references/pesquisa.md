# Pesquisa: modelo forte planeja, modelo mais barato executa. Faz sentido?

Data: 16/11/2026. Conferido na fonte original por um agente verificador (cada número abaixo foi lido na página citada).

## Conclusão

Sim. É o desenho que Anthropic, OpenAI, Cursor, Aider, AWS, Microsoft e Google descrevem ou usam. Dois cuidados que todas as fontes repetem: (1) o ganho só vem se o planejador escrever um brief claro, porque a maioria das falhas de sistemas com vários agentes vem de especificação e coordenação, não de modelo fraco; (2) agente custa token, então só se cria agente quando ele traz paralelismo, contexto limpo ou especialização.

## Evidências

| Fonte | O que mostra |
|---|---|
| Anthropic, sistema de pesquisa com vários agentes (jun/2025) | Opus 4 coordenando agentes Sonnet 4 superou Opus 4 sozinho em 90,2% na avaliação interna. Sistemas com vários agentes usam cerca de 15x mais tokens que um chat. |
| Anthropic, ficha técnica do Opus 4.5 | Opus 4.5 com agentes Haiku 4.5: 87,0%, contra 74,8% do Opus sozinho e 92,3% com agentes Opus. Orquestrador forte importa mais: Opus coordenando Sonnet 85,4% contra Sonnet coordenando Sonnet 66,5%. |
| Anthropic, quando usar vários agentes (jan/2026) | Vários agentes gastam de 3 a 10 vezes mais tokens. Valem a pena em 3 casos: contexto poluído, tarefas paralelas, especialização. |
| Anthropic, estratégia do conselheiro (abr/2026) | Chama de "padrão comum" o modelo maior dividir o trabalho e delegar a modelos menores. Sonnet com Opus de conselheiro: +2,7 pontos no SWE-bench Multilingual e 11,9% mais barato por tarefa. |
| Claude Code, documentação de custos | Sonnet faz bem a maior parte das tarefas de código e custa menos que Opus; para agentes simples, use haiku. O próprio Claude Code tem o modo `opusplan` (Opus planeja, Sonnet executa). |
| OpenAI, guia de modelos para agentes | Em produção, escolha o modelo de forma explícita e defina o modelo por agente conforme qualidade, tempo e custo. |
| Cursor, enxame de agentes (jul/2026) | Planejadores com os modelos mais inteligentes, trabalhadores com modelos mais baratos. Qualidade parecida entre as combinações; custo de US$ 1.339 (Opus 4.8 planeja, Composer executa) a US$ 10.565 (GPT-5.5 em tudo). Relato do fornecedor, poucas rodadas. |
| Cursor, agentes de longa duração (jan/2026) | "Usamos o modelo mais adequado para cada papel, não um modelo universal." |
| Aider (jan/2025) | R1 planejando e Sonnet editando: 64,0%, recorde do teste, a US$ 13,29 contra US$ 186,50 do o1 sozinho (61,7%). |
| AWS Bedrock | Roteamento de prompts entre modelos da mesma família: até 30% mais barato sem perder precisão. |
| Microsoft Foundry | Roteador manda o prompt para o modelo mais barato que fique a cerca de 1% a 2% da qualidade do melhor. |
| Google Gemini CLI | Recomenda o modo Auto: Pro para tarefa complexa, Flash para simples. |
| FrugalGPT (Stanford, 2023) | Cascata de modelos igualou o GPT-4 com até 98% menos custo, em testes específicos. |
| RouteLLM (2024) | Roteador entre modelo forte e fraco cortou custo em mais de 2 vezes em alguns casos sem perder qualidade. |

## Riscos e como a skill trata cada um

| Risco (fonte) | Tratamento |
|---|---|
| Agente sem contexto entende errado (Cognition, "Don't build multi-agents", jun/2025) | A regra exige brief com objetivo, arquivos, o que foi descartado e formato. Planejamento e síntese ficam no modelo forte. |
| Falhas vêm mais de especificação e coordenação que do modelo (taxonomia MAST, NeurIPS 2025: 14 modos de falha em 3 grupos) | Mesmo tratamento: o brief é obrigatório, e resultado fraco sobe um degrau. |
| Agentes demais gastam mais do que economizam (Anthropic, 3 a 10x tokens) | A regra não cria agentes; só escolhe o modelo dos que já seriam criados. |
| Modelo barato demais erra em tarefa difícil | Escada com degrau Opus para decisão difícil e alto risco; na dúvida, um degrau acima. |

## Preços usados (US$ por milhão de tokens, entrada / saída)

Fable 5.2: 8 / 40. Opus 5.5: 4 / 20. Sonnet 5.5: 2 / 10. Haiku 5.5: 0,10 / 0,50. Fonte: tabela de preços da API da Anthropic, novembro/2026. Um agente em Sonnet custa um quarto do mesmo agente em Fable; em Haiku, 1/80.

## Fontes

- https://www.anthropic.com/engineering/multi-agent-research-system
- https://assets.claude.com/bf10f64990cfda0ba858290be7b8cc6317685f47.pdf
- https://claude.com/resources/articles/building-multi-agent-systems-when-and-how-to-use-them
- https://claude.com/blog/the-advisor-strategy
- https://code.claude.com/docs/en/costs
- https://code.claude.com/docs/en/model-config
- https://code.claude.com/docs/en/sub-agents
- https://developers.openai.com/api/docs/guides/agents/models
- https://cursor.com/blog/agent-swarm-model-economics
- https://cursor.com/blog/scaling-agents
- https://aider.chat/2025/01/24/r1-sonnet.html
- https://aws.amazon.com/bedrock/intelligent-prompt-routing/
- https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-router
- https://geminicli.com/docs/cli/model/
- https://arxiv.org/abs/2305.05176
- https://arxiv.org/abs/2406.18665
- https://arxiv.org/abs/2503.13657
- https://cognition.com/blog/dont-build-multi-agents

Não consegui abrir (bloqueio 403): o guia prático da OpenAI em openai.com/business. O trecho dele não entrou como evidência.
