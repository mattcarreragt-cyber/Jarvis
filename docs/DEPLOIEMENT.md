# 🚀 Déploiement complet de JARVIS — Guide maître

Ce document est le **fil conducteur** du déploiement. Il enchaîne les 4 phases.
Pour les détails de chaque machine, voir les guides dédiés
(`UNRAID_SETUP.md`, `KUBUNTU_SETUP.md`, `RUNPOD_SETUP.md`).

> **Si tu n'y connais rien en informatique**, lis d'abord `GUIDE_DEBUTANT.md` :
> il reprend tout, pas à pas, sans jargon.

---

## Vue d'ensemble : 3 machines, 4 phases

```
   ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
   │   UNRAID     │  LAN   │   KUBUNTU    │ Internet│   RUNPOD     │
   │ (cerveau,    │◄──────►│ (muscle GPU  │  ······►│ (gros muscle │
   │  toujours ON)│  WoL   │  8 Go, dort) │         │  cloud, à la │
   │              │        │              │         │  demande)    │
   └──────────────┘        └──────────────┘        └──────────────┘
      Phase 1                  Phase 3                  Phase 4
   (+ Phase 2 : Home Assistant & Nextcloud, optionnel)
```

- **Unraid** = le chef d'orchestre. Il héberge l'interface web, la base de données,
  la mémoire. **Indispensable**, toujours allumé.
- **Kubuntu** = la carte graphique 8 Go. Fait tourner l'IA (chat, images, vidéo,
  audio, voix). Peut **dormir** : Unraid la réveille par le réseau (Wake-on-LAN).
- **RunPod** = une carte graphique louée dans le cloud, **optionnelle**, pour les
  très gros modèles que 8 Go ne peuvent pas faire tourner.

**Bonne nouvelle :** la Phase 1 seule donne déjà un assistant fonctionnel
(recherche, mémoire, agenda, domotique, système). Le GPU n'ajoute que l'IA lourde.

---

## Phase 1 — Unraid (obligatoire, ~30 min)

**But :** avoir l'interface web qui répond.

1. Ouvre un **terminal Unraid** (icône `>_` en haut à droite de l'interface web).
2. Récupère le code :
   ```bash
   mkdir -p /mnt/user/appdata/jarvis && cd /mnt/user/appdata/jarvis
   git clone -b claude/gallant-euler-h0syfh https://github.com/mattcarreragt-cyber/jarvis.git .
   ```
3. Configure :
   ```bash
   cp .env.example .env
   nano .env
   ```
   Remplis : `POSTGRES_PASSWORD`, `HOST_IP` (l'IP de ton Unraid), et génère
   `SECRET_KEY` + `API_KEY` avec `openssl rand -hex 32`. (Détails : `UNRAID_SETUP.md` §2.)
4. Lance :
   ```bash
   docker compose up -d --build
   ```
5. Vérifie : ouvre `http://IP_DE_TON_UNRAID:3000` dans ton navigateur.

✅ **Test** : tape `cpu et ram de la machine` dans le chat → tu dois voir des stats.
(Plan de test complet : `TESTS.md` Phase 1.)

---

## Phase 2 — Home Assistant + Nextcloud (optionnel, sans GPU)

**But :** piloter ta domotique et chercher dans tes fichiers.

- **Home Assistant** : ajoute `HA_URL` + `HA_TOKEN` dans `.env`, relance
  `docker compose up -d`. (Voir `UNRAID_SETUP.md` §2.)
- **Nextcloud** : ajoute `NEXTCLOUD_URL/USER/PASSWORD` + `NEXTCLOUD_SYNC_ENABLED=true`.
  (Voir `NEXTCLOUD_RAG.md`.)

✅ **Test** : `allume light.salon` (HA) · `cherche dans mon nextcloud …`.

---

## Phase 3 — Kubuntu (GPU local, mode complet, ~1 h)

**But :** activer l'IA (chat intelligent, images, vidéo, audio, voix).

Suis **`KUBUNTU_SETUP.md`** dans l'ordre :
1. Pilotes NVIDIA + Docker + NVIDIA Container Toolkit
2. `docker compose -f docker-compose.kubuntu.yml up -d`
3. Télécharger les modèles : `qwen2.5:7b`, `qwen2.5:14b`, `nomic-embed-text`
4. (images) checkpoint SDXL · (vidéo) AnimateDiff + SVD · (audio) Stable Audio
5. **Wake-on-LAN** : activer dans le BIOS + mettre la MAC dans le `.env` d'Unraid

✅ **Test** : `raconte une blague` → vraie réponse · `génère une image d'un chat`.

---

## Phase 4 — RunPod (cloud, optionnel, gros modèles)

**But :** chat 72B et vidéo haute qualité.

Suis **`RUNPOD_SETUP.md`** : crée un compte, un pod GPU, mets les URLs/clé dans `.env`,
`RUNPOD_ENABLED=true`.

✅ **Test** : `réflexion profonde sur …` → démarre le pod, répond via 72B.

---

## Comprendre les « paliers » (important)

JARVIS choisit **automatiquement** où exécuter chaque tâche :

| Tâche | Où ça tourne |
|-------|--------------|
| Recherche, mémoire, agenda, système | Unraid (toujours) |
| Chat, images, vidéo, audio, voix | Kubuntu (réveillé si besoin) |
| Très gros modèle, vidéo HD | RunPod (si activé) |

Tu n'as **rien à choisir** : tu parles, JARVIS route. Le panneau **⚙ Système** du
dashboard montre l'état de chaque palier en temps réel.

---

## Mettre à jour plus tard

```bash
cd /mnt/user/appdata/jarvis
git pull origin claude/gallant-euler-h0syfh
docker compose up -d --build
```
Les migrations de base de données s'appliquent toutes seules au redémarrage.

---

## Récapitulatif des ports

| Service | Adresse | Rôle |
|---------|---------|------|
| Dashboard | `http://IP_UNRAID:3000` | l'interface JARVIS |
| API | `http://IP_UNRAID:8000/docs` | le cerveau (doc technique) |
| Ollama (Kubuntu) | `http://IP_KUBUNTU:11434` | les modèles de langage |
| ComfyUI (Kubuntu) | `http://IP_KUBUNTU:8188` | images / vidéo / audio |

➡️ **En cas de problème, va voir `DEPANNAGE_COMPLET.md`.**
