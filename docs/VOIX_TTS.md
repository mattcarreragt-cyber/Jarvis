# 🔊 La voix de JARVIS (TTS Piper) + choix de la voix

## Oui, JARVIS parle — 100 % sur Unraid (CPU)

La voix de sortie est gérée par **Piper**, un conteneur CPU sur Unraid
(`unraid-piper`). Aucun GPU, Kubuntu jamais réveillé. Couplé au **Whisper CPU**
(les oreilles) et au **petit LLM CPU** (`chat.local`), tu as une **boucle vocale
entièrement locale** : tu parles → transcription → réponse → JARVIS lit à voix haute.

- Active/coupe la lecture vocale avec le bouton **🔊** du header.
- Quand la voix est active, un **sélecteur** apparaît à côté pour changer de voix.

## Voix françaises disponibles

| Voix | Genre | Note |
|---|---|---|
| `fr_FR-siwis-medium` | féminine, claire | **défaut** |
| `fr_FR-tom-medium` | masculine | assistant |
| `fr_FR-upmc-medium` | féminine | équilibrée |
| `fr_FR-gilles-low` | masculine | rapide, plus robotique |
| `fr_FR-mls-medium` | multi-locuteurs | varié |

Les voix sont **téléchargées automatiquement** au premier usage (depuis
Hugging Face) et mises en cache dans le volume `piper_voices`. La 1ʳᵉ phrase d'une
nouvelle voix prend donc quelques secondes de plus (téléchargement).

## Changer la voix par défaut (serveur)

Dans `.env` sur Unraid :
```ini
PIPER_VOICE=fr_FR-tom-medium
```
puis :
```bash
docker compose up -d piper
```

Le choix fait dans le **dashboard** est mémorisé par navigateur (localStorage) et
**prime** sur le défaut serveur pour cet appareil — pratique si chacun veut sa voix.

## Déploiement

```bash
git pull
docker compose up -d --build piper      # construit + lance le conteneur Piper
```
Teste la voix : active 🔊 dans le dashboard et envoie un message, ou directement :
```bash
curl -s "http://IP_UNRAID:4500/api/voice/voices"     # liste des voix
```

## Dépannage

| Symptôme | Cause / solution |
|---|---|
| Pas de son | 🔊 désactivé, ou navigateur bloque l'autoplay (clique une fois dans la page). |
| `Synthèse vocale indisponible` | Conteneur `piper` pas lancé → `docker compose up -d --build piper`. |
| 1ʳᵉ phrase lente puis OK | Normal : téléchargement de la voix au 1ᵉʳ usage (ensuite en cache). |
| Voix non changée | Le navigateur garde son choix (localStorage) ; resélectionne dans le menu. |
