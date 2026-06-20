# RunPod — 3ᵉ palier de calcul (GPU cloud) pour gros modèles

JARVIS a trois paliers de calcul :

| Palier | Machine | Pour quoi | Coût |
|--------|---------|-----------|------|
| 1 | **Unraid** | Orchestration, RAG keyword, agents système | toujours allumé |
| 2 | **Kubuntu** | LLM 7-14B, embeddings, images SDXL, vidéo AnimateDiff, STT | élec maison |
| 3 | **RunPod** | Très gros LLM (72B), vidéo HD (LTX/Hunyuan) | à l'heure/seconde |

RunPod sert **uniquement** aux modèles que ta carte 8 Go ne peut pas faire tourner.

---

## Comment marche RunPod (rapide)

RunPod loue des **GPU cloud**. Deux produits :

- **Pod** : une machine GPU (RTX 4090, A100, H100…) que tu démarres/arrêtes. Elle
  tourne comme ton Kubuntu : tu y installes Ollama/ComfyUI, elle expose des URLs
  HTTP publiques (`https://<id>-11434.proxy.runpod.net`). **Tu ne paies que quand
  elle tourne** → JARVIS la démarre à la demande et tu l'arrêtes après.
- **Serverless** : un endpoint auto-scalé, facturé à la seconde (non utilisé ici).

JARVIS utilise le **mode Pod** : le scheduler démarre le pod via l'API REST RunPod
quand une capacité `machine: runpod` est demandée, attend qu'il réponde, puis y
route la requête.

---

## 1. Créer un compte + une clé API

1. Crée un compte sur **runpod.io** et crédite-le (quelques $).
2. **Settings → API Keys → Create API Key** → copie la clé.

---

## 2. Créer un Pod GPU

1. **Pods → Deploy** → choisis un GPU :
   - **RTX 4090 (24 Go)** : suffisant pour `qwen2.5:72b` quantifié + vidéo LTX.
   - **A100 80 Go** : confort maximal (gros contextes, Hunyuan Video).
2. Template : pars d'un template **Ollama** ou **ComfyUI** de la communauté, ou
   un Ubuntu + CUDA où tu installes les deux (comme dans `KUBUNTU_SETUP.md`).
3. **Expose les ports HTTP** 11434 (Ollama) et 8188 (ComfyUI) dans la config du pod.
4. Déploie, puis note :
   - l'**ID du pod** (dans l'URL ou les détails du pod),
   - les **URLs proxy** : `https://<podId>-11434.proxy.runpod.net` (Ollama) et
     `https://<podId>-8188.proxy.runpod.net` (ComfyUI).

### Installer les modèles sur le pod

Une fois le pod démarré, via son terminal web (ou SSH) :

```bash
# Gros LLM
ollama pull qwen2.5:72b

# Vidéo HD : installe les custom nodes ComfyUI (LTX-Video conseillé sur gros GPU)
cd /workspace/ComfyUI/custom_nodes
git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git
# + télécharge le modèle LTX dans models/checkpoints (voir repo LTX)
```

> Astuce : utilise un **Network Volume** RunPod pour conserver les modèles entre
> deux démarrages du pod (sinon re-téléchargement à chaque fois).

---

## 3. Configurer JARVIS (Unraid)

Dans `/mnt/user/appdata/jarvis/.env` :

```env
RUNPOD_ENABLED=true
RUNPOD_API_KEY=ta-cle-api-runpod
RUNPOD_POD_ID=ton-pod-id
RUNPOD_OLLAMA_URL=https://<podId>-11434.proxy.runpod.net
RUNPOD_COMFYUI_URL=https://<podId>-8188.proxy.runpod.net
RUNPOD_START_TIMEOUT=300
```

Puis : `docker compose up -d` (sur Unraid).

---

## 4. Utilisation

### Chat avec le très gros modèle (72B)
Le palier RunPod s'active sur déclencheurs (voir `capabilities.yaml` →
`chat_policy.xl_triggers`). Exemples dans le chat :

- « utilise un **gros modèle** pour analyser ce contrat »
- « **réflexion profonde** sur ma stratégie 2026 »
- « lance ça sur **runpod** »

→ JARVIS démarre le pod si besoin, route vers `qwen2.5:72b`, répond.

### Vidéo HD
Si `RUNPOD_ENABLED=true` et `RUNPOD_COMFYUI_URL` est défini, **toute** demande
vidéo passe automatiquement sur le palier HD (`video.hd`, 768p+) au lieu de
l'AnimateDiff local. Sinon, repli sur Kubuntu (512p).

> Le workflow vidéo HD est dans `config/comfyui_video_hd_workflow.json`
> (tokens `__PROMPT__/__NEG__/__FRAMES__/__FPS__`). **Remplace-le par l'export API
> de ton workflow LTX/Hunyuan** sur le pod en gardant les tokens.

---

## 5. Arrêter le pod (ne pas payer pour rien)

JARVIS **démarre** le pod automatiquement mais ne l'arrête pas tout seul (pour ne
pas couper un job en cours). Trois options :

1. **Manuel** : RunPod → Pods → Stop.
2. **Auto-stop RunPod** : configure un arrêt sur inactivité dans les réglages du pod.
3. **Via API** (avancé) : un appel `POST /pods/{id}/stop` — l'endpoint est déjà
   implémenté (`app/orchestration/runpod.py::stop_pod`), à brancher sur un bouton
   ou un cron si tu veux l'automatiser plus tard.

---

## 6. Vérification

```bash
# Depuis Unraid : le pod répond-il ?
curl https://<podId>-11434.proxy.runpod.net/api/tags     # Ollama
curl https://<podId>-8188.proxy.runpod.net/system_stats  # ComfyUI

# Test bout-en-bout : dans le chat JARVIS
#   "réflexion profonde sur X"  → doit démarrer le pod et répondre via 72B
```

---

## Dépannage

| Symptôme | Cause | Solution |
|----------|-------|----------|
| « RunPod désactivé » | `RUNPOD_ENABLED=false` | passe à `true` + redémarre l'API |
| « URL RunPod ollama non configurée » | URL vide | renseigne `RUNPOD_OLLAMA_URL` |
| « Pod non prêt dans les 300s » | démarrage long / modèle absent | augmente `RUNPOD_START_TIMEOUT`, vérifie les modèles sur le pod |
| Démarrage non déclenché | `RUNPOD_API_KEY`/`POD_ID` manquants | renseigne-les |
| Coût qui file | pod jamais arrêté | active l'auto-stop RunPod |
