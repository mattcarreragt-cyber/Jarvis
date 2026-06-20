# JARVIS OS — Index de la documentation

## 🚀 Déploiement (pas à pas)
- **UNRAID_SETUP.md** — déployer le cœur (API + dashboard + DB) sur Unraid
- **KUBUNTU_SETUP.md** — nœud GPU local (Ollama, ComfyUI, AnimateDiff, Whisper, WoL)
- **RUNPOD_SETUP.md** — 3ᵉ palier GPU cloud pour gros modèles (72B, vidéo HD)
- **NEXTCLOUD_RAG.md** — indexation/recherche de tes fichiers Nextcloud

## ✅ Validation
- **TESTS.md** — tests automatiques + plan de tests manuels par phase

## 🏛️ Conception (référence)
- 00_PRINCIPLES.md · 01_ARCHITECTURE.md · 02_CONTRACTS.md · 03_ROUTER.md
- 04_MEMORY.md · 05_AGENTS.md · 06_SECURITY.md · 07_BUILD_ORDER.md · 08_ORCHESTRATION.md

## Ordre conseillé
1. **UNRAID_SETUP.md** → valide la Phase 1 de **TESTS.md**
2. (option) HA + **NEXTCLOUD_RAG.md** → Phase 2
3. **KUBUNTU_SETUP.md** → Phase 3 (mode GPU complet)
4. (option) **RUNPOD_SETUP.md** → Phase 4 (gros modèles)

## Paliers de calcul
| Palier | Machine | Usage |
|--------|---------|-------|
| 1 | Unraid | orchestration, RAG keyword, agents système (toujours allumé) |
| 2 | Kubuntu (8 Go) | LLM 7-14B, embeddings, SDXL, vidéo AnimateDiff, STT |
| 3 | RunPod (cloud) | LLM 72B, vidéo HD (LTX/Hunyuan) — à la demande |
