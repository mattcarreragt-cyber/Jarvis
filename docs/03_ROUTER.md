# 03 — Router (routage hybride)

Le Router décide quel agent traite une requête. Choix retenu : **hybride**,
construit en deux temps pour rester dégradable.

## Pourquoi hybride

- **Règles seules** : rapides, déterministes, mais rigides et pénibles à maintenir.
- **LLM seul** : flexibles, comprend le langage naturel, mais plus lents et
  non déterministes.
- **Hybride** : on prend le meilleur des deux, et on peut démarrer 100 % règles
  puis brancher le LLM sans changer le contrat.

## Algorithme

```
def route(request) -> AgentSpec:
    # Passe 1 — règles (rapide, déterministe)
    if request.force_agent:
        return registry[request.force_agent]

    scored = score_by_keywords(request.message, registry)   # match keywords/regex
    best, second = top_two(scored)

    if best.score >= HIGH_CONFIDENCE and best.score - second.score >= MARGIN:
        return best.agent            # confiance suffisante → pas de LLM

    # Passe 2 — fallback LLM function-calling (ambigu)
    return llm_select_agent(request.message, registry)       # Ollama tool-calling
```

- `HIGH_CONFIDENCE` et `MARGIN` sont configurables.
- Le fallback LLM reçoit la liste des `AgentSpec.description` comme « tools » et
  doit en sélectionner exactement un (ou `none` → agent de conversation par défaut).

## Garde-fous

- **Timeout LLM** : si le fallback dépasse N ms, repli sur le meilleur score règles.
- **Agent par défaut** : un agent « conversation » répond si aucun agent métier
  ne correspond (pas d'erreur 500 pour une question banale).
- **Traçabilité** : chaque décision de routage est loggée (`intent`, `agent`,
  `method=rules|llm`, `score`) en base pour audit et amélioration des règles.

## Évolution

Les logs de routage alimentent l'affinage des `keywords` des agents. À terme,
on peut entraîner un classifieur léger si le volume le justifie — mais ce n'est
pas nécessaire au départ.
