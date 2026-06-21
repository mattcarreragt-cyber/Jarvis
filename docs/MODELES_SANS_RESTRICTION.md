# 🔓 Modèles & IA sans restriction (lab local)

Comment faire tourner JARVIS avec des modèles **sans bridage**, sur chaque
modalité (texte, RAG, image, vidéo, audio). Pour un usage **local, privé, de
laboratoire**.

> Cadre : usage perso et **légal**. Les modèles open locaux n'ont aucun filtre,
> mais ça ne dispense pas du droit (pas de contenu illégal type CSAM, pas de
> représentation de personnes réelles sans consentement).

---

## 1. Le point clé : local = pas de modération serveur

ChatGPT / Claude filtrent **côté serveur** (tu ne contrôles rien). Les modèles
**open-weight que tu exécutes chez toi** (via Ollama / ComfyUI) n'ont **aucun
filtre externe**. La seule « retenue » qui reste est :
- pour le **texte** : un *alignement* parfois entraîné dans le modèle (refus,
  avertissements). Ça se contourne en **changeant de modèle** et avec un **prompt
  neutre** ;
- pour **image / vidéo / audio** : **rien** — ComfyUI ne charge aucun *safety
  checker* par défaut. C'est déjà « débridé » en local.

---

## 2. Faut-il entraîner sa propre IA ? → Non

Inutile et coûteux pour cet objectif. La communauté publie déjà des **fine-tunes
sans bridage**, prêts à l'emploi. Catégories :

| Type | Comportement | Exemples (familles) |
|------|--------------|---------------------|
| **Uncensored / abliterated** | refus quasi supprimés | `dolphin-*`, `*-abliterated`, `nous-hermes2` |
| **Base (non-instruct)** | aucun alignement, mais brut à piloter | `*-base` |
| **Instruct standard** | utile + un peu de refus | `qwen2.5`, `llama3.1` (défaut actuel) |

L'entraînement (LoRA) ne sert que si tu veux un **style/persona** spécifique —
pas pour « enlever les garde-fous » (les modèles ci-dessus le font déjà).

---

## 3. Activer le mode dans JARVIS

### a) Persona neutre (prompts sans « nanny »)
Dans `.env` (Unraid) :
```env
UNRESTRICTED_MODE=true
```
Effet : les agents **texte/RAG/marketing** utilisent un prompt système neutre qui
répond directement, sans avertissements superflus ni refus d'une demande
légitime. (Voir `app/llm/persona.py`.) Redémarre l'API.

### b) Modèles sans bridage (texte) — par agent/capacité
Édite `config/capabilities.yaml` (rechargé à chaud) et remplace les modèles :
```yaml
  chat.fast:
    model: dolphin-mistral          # au lieu de qwen2.5:7b
  chat.deep:
    model: dolphin-mixtral          # ou nous-hermes2-mixtral
  chat.xl:                          # (RunPod)
    model: dolphin-llama3:70b
```
Puis, sur Kubuntu, télécharge-les :
```bash
docker exec kubuntu-ollama ollama pull dolphin-mistral
docker exec kubuntu-ollama ollama pull dolphin-mixtral      # vérifie qu'il tient en VRAM
```
> ⚠️ **8 Go VRAM** : reste sur des modèles 7-8B (`dolphin-mistral`,
> `llama3-...-abliterated:8b`). Les Mixtral/70B → palier **RunPod** (cloud).

> Tu peux aussi mettre à jour `CHAT_MODEL_FAST/DEEP` dans `app/llm/ollama.py`
> (valeurs par défaut), mais éditer `capabilities.yaml` suffit.

---

## 4. Par modalité : qu'est-ce qui change ?

| Agent / modalité | Débridage | Quoi faire |
|------------------|-----------|------------|
| **chat / dev** | modèle + persona | `UNRESTRICTED_MODE=true` + modèle uncensored |
| **recherche / nextcloud (RAG)** | la **synthèse** utilise le LLM | idem : modèle uncensored → réponses sans refus |
| **marketing** | génération via LLM | idem |
| **image** (SDXL) | **déjà libre** | éventuellement un checkpoint communautaire non filtré dans `COMFYUI_CHECKPOINT` |
| **vidéo** (AnimateDiff/SVD) | **déjà libre** | rien (ou modèle/LoRA de ton choix) |
| **audio** (Stable Audio) | **déjà libre** | rien |
| **embeddings / mémoire** | pas de notion de refus | rien |

Autrement dit : **un seul levier réel = le modèle de texte**. Le reste est déjà
sans filtre en local.

---

## 5. Faut-il « reprendre beaucoup de code » ? → Non

L'architecture sépare déjà **modèle** et **code** :
- les modèles sont dans `capabilities.yaml` (par capacité, rechargé à chaud) ;
- le ton/refus est dans `app/llm/persona.py`, piloté par `UNRESTRICTED_MODE` ;
- images/vidéo/audio passent par des **workflows** que tu peux remplacer
  (checkpoints/LoRA au choix) sans toucher au code.

Tu changes des **réglages**, pas le moteur.

---

## 6. Récap express

1. `.env` → `UNRESTRICTED_MODE=true`
2. `capabilities.yaml` → mets des modèles `dolphin-*` / `*-abliterated`
3. `ollama pull` ces modèles sur Kubuntu (≤ 8 Go local, sinon RunPod)
4. Image/vidéo/audio : déjà sans filtre — change le checkpoint si tu veux
5. Pas d'entraînement nécessaire

Le panneau **⚙ Système** affiche si le mode non restreint est actif.
