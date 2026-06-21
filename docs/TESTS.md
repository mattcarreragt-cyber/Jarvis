# JARVIS — Plan de tests & validation

Deux niveaux : **tests automatiques** (déjà verts) et **tests manuels** à faire
au déploiement, dans l'ordre.

---

## A. Tests automatiques (CI / local)

```bash
cd api
python -m pytest -q
# Attendu : 175 passed
```

Couverture : router (règles + LLM), 14 agents, mémoire (court/long/faits), RAG
(extraction, recherche, sync Nextcloud), LLM (embeddings/chat/synthèse),
orchestration (WoL + budget VRAM 8 Go + RunPod), images, vidéo (texte→vidéo &
image→vidéo), audio, voix, jobs, agenda, webhooks, galerie, export, sauvegarde,
stats, système.

Typecheck dashboard :
```bash
cd dashboard && npx tsc --noEmit   # Attendu : exit 0
```

---

## B. Tests manuels — déploiement progressif

### Phase 1 — Unraid (sans GPU)

Pré-requis : `docker compose up -d --build` OK, `docker compose ps` tout "Up".

```bash
curl http://localhost:8000/api/health    # PG/REDIS/QDRANT = ok
curl http://localhost:8000/api/agents     # 12 agents listés
```

Dans le dashboard (`http://IP_UNRAID:3000`), tape dans l'ordre :

| # | Message | Agent | Attendu |
|---|---------|-------|---------|
| 1 | `cpu et ram de la machine` | system | stats hôte |
| 2 | `état des conteneurs docker` | unraid | liste conteneurs |
| 3 | `espace disque du nas` | unraid | usage disques |
| 4 | `souviens-toi que je préfère le café noir` | memoire | « ✓ C'est noté » |
| 5 | `que sais-tu sur moi ?` | memoire | contient « café noir » |
| 6 | (icône 🧠) | — | le fait s'affiche, bouton supprimer |
| 7 | ` ```python\nprint(6*7)\n``` ` | dev | `42` (sandbox Docker) |
| 8 | `raconte une blague` | chat | message « Kubuntu indisponible » (normal si éteint) |

✅ **Validé si 1-7 OK.** OLLAMA/COMFY/STT gris = normal (Kubuntu éteint).

---

### Phase 2 — Home Assistant + Nextcloud (sans GPU)

**HA** — `.env` : `HA_URL` + `HA_TOKEN`, puis `docker compose up -d`.

| Message | Attendu |
|---------|---------|
| `liste mes lumières` | états HA (lecture) |
| `allume light.salon` | demande de confirmation → bouton **CONFIRMER** → action |

**Nextcloud** — `.env` : `NEXTCLOUD_URL/USER/PASSWORD` + `NEXTCLOUD_SYNC_ENABLED=true`.

```bash
curl -X POST -H "X-API-Key: TA_CLE" http://localhost:8000/api/nextcloud/ping
# {"reachable": true}
```

| Action | Attendu |
|--------|---------|
| icône ☁ → SYNCHRONISER | fichiers indexés (compteur monte) |
| `cherche dans mon nextcloud <sujet>` | extraits avec chemins |

---

### Phase 3 — Kubuntu (GPU, mode complet)

Pré-requis : `docs/KUBUNTU_SETUP.md` suivi (drivers, Ollama+modèles, ComfyUI,
WoL). `.env` Unraid : `KUBUNTU_*` renseignés.

| Message | Attendu |
|---------|---------|
| `raconte une blague` | vraie réponse LLM (qwen2.5:7b) |
| `analyse ma stratégie marketing` | réponse via qwen2.5:14b (deep) |
| `cherche … nextcloud` | réponse **rédigée** + sources (sémantique) |
| icône RAG → RÉ-INDEXER | embeddings recalculés |
| `génère une image d'un moteur` | image dans le chat |
| `génère une vidéo de 10s d'un chat` | job → icône 🎬 → vidéo |
| 🔊 puis micro | transcription → réponse → voix |

Vérifs santé : StatusBar OLLAMA/COMFY/STT passent au vert.

---

### Phase 4 — RunPod (gros modèles, cloud)

Pré-requis : `docs/RUNPOD_SETUP.md` suivi. `.env` : `RUNPOD_ENABLED=true` +
clé/pod/URLs.

| Message | Attendu |
|---------|---------|
| `réflexion profonde sur X` | démarre le pod → réponse via qwen2.5:72b |
| `gros modèle : analyse ce contrat` | idem (palier xl) |
| `génère une vidéo de 15s …` | passe en **video.hd** (768p) sur RunPod |

```bash
curl https://<podId>-11434.proxy.runpod.net/api/tags   # pod Ollama up
```

⚠️ **Arrête le pod après usage** (RunPod → Stop, ou auto-stop) pour ne pas payer.

---

## C. Checklist de bascule des paliers

| Situation | Comportement attendu |
|-----------|----------------------|
| Kubuntu + RunPod éteints | mode keyword + extraits ; chat répond « GPU indisponible » |
| Kubuntu allumé seul | chat 7-14B, RAG sémantique, image/vidéo 512p, voix |
| RunPod activé | déclencheurs `xl` → 72B ; vidéo → HD 768p ; reste sur Kubuntu sinon |

Tout est **best-effort** : un palier éteint ne casse jamais le reste.
