# JARVIS OS — Index de la documentation

## 🌟 Commence ici
- **GUIDE_DEBUTANT.md** — pas à pas pour quelqu'un qui n'y connaît rien (zéro jargon)
- **FONCTIONNALITES.md** — catalogue complet de tout ce que JARVIS sait faire (avec exemples)
- **DEPLOIEMENT.md** — guide maître du déploiement (les 4 phases enchaînées)
- **COMPOSANTS_EXPLIQUES.md** — à quoi sert chaque logiciel installé
- **DEPANNAGE_COMPLET.md** — tous les problèmes possibles et leurs solutions
- **MODELES_SANS_RESTRICTION.md** — utiliser des modèles sans bridage (lab local)
- **CYBERSECURITE.md** — module d'audit défensif (SSH, nmap, lynis, CVE, scoring)
- **BUREAU_DISTANT_VPN.md** — Moonlight/Sunshine + WoL, VPN Mullvad, note Tuta Mail
- **MOBILE_ANDROID.md** — PWA / APK Capacitor, wake word « Hey Jarvis », accès mobile

## 🚀 Guides d'installation détaillés (par machine)
- **UNRAID_SETUP.md** — le cœur (interface + base de données + mémoire)
- **KUBUNTU_SETUP.md** — le GPU local (chat, images, vidéo, audio, voix, WoL)
- **RUNPOD_SETUP.md** — le GPU cloud pour gros modèles (optionnel)
- **NEXTCLOUD_RAG.md** — indexer et chercher dans tes fichiers Nextcloud

## ✅ Validation
- **TESTS.md** — tests automatiques + plan de tests manuels par phase

## 🏛️ Conception (référence technique)
- 01_ARCHITECTURE.md · 02_CONTRACTS.md · 03_ROUTER.md · 04_MEMORY.md
- 05_AGENTS.md · 06_SECURITY.md · 07_BUILD_ORDER.md · 08_ORCHESTRATION.md
- 00_PRINCIPLES.md

## 📖 Ordre de lecture conseillé
1. **GUIDE_DEBUTANT.md** (comprendre + installer la base)
2. **COMPOSANTS_EXPLIQUES.md** (savoir à quoi sert quoi)
3. **DEPLOIEMENT.md** → **UNRAID_SETUP.md** (Phase 1)
4. **KUBUNTU_SETUP.md** (Phase 3, le GPU) puis **RUNPOD_SETUP.md** (Phase 4)
5. **TESTS.md** pour valider, **DEPANNAGE_COMPLET.md** en cas de souci

## Les 3 paliers de calcul
| Palier | Machine | Usage | État |
|--------|---------|-------|------|
| 1 | Unraid | orchestration, RAG, mémoire, agenda, système | toujours allumé |
| 2 | Kubuntu (8 Go) | chat, images, vidéo, audio, voix (STT) | se réveille (WoL) |
| 3 | RunPod (cloud) | LLM 72B, vidéo HD | à la demande, optionnel |
