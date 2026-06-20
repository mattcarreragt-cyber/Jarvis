# Déploiement JARVIS OS sur Unraid

Guide complet, étape par étape, pour déployer le **chef d'orchestre** (API + Dashboard
+ Postgres + Redis + Qdrant) sur Unraid.

> Unraid = serveur toujours allumé. Kubuntu (GPU) est traité séparément dans
> `KUBUNTU_SETUP.md` et reste optionnel : sans lui, tout le mode keyword
> (recherche, marketing, system, unraid, home assistant, dev) fonctionne déjà.

---

## 0. Pré-requis

- Unraid 6.12+ avec le **Docker** activé (Settings → Docker → Enable : Yes)
- Plugin **Community Applications** installé
- Plugin **Compose Manager** (recommandé) — ou accès SSH au serveur
- ~5 Go d'espace libre sur le cache pour les images Docker
- L'IP LAN de ton serveur Unraid (ex. `192.168.1.50`)

---

## 1. Récupérer le code sur Unraid

Deux options.

### Option A — via git (recommandé, simplifie les mises à jour)

Ouvre un **terminal Unraid** (icône `>_` en haut à droite de l'interface web) :

```bash
# Dossier de travail dans appdata (persistant)
mkdir -p /mnt/user/appdata/jarvis
cd /mnt/user/appdata/jarvis

# Cloner le dépôt sur la branche de travail
git clone -b claude/gallant-euler-h0syfh https://github.com/mattcarreragt-cyber/jarvis.git .
```

> Si `git` n'est pas dispo : installe le plugin **NerdTools** (Community Apps)
> et active `git`, ou utilise l'option B.

### Option B — copie manuelle

Télécharge le repo en `.zip` depuis GitHub, décompresse-le, puis copie le contenu
dans `/mnt/user/appdata/jarvis/` via le partage réseau Unraid (SMB) ou l'explorateur
de fichiers.

---

## 2. Configurer le fichier `.env`

```bash
cd /mnt/user/appdata/jarvis
cp .env.example .env
nano .env
```

Modifie **au minimum** ces valeurs :

```env
# Mets un vrai mot de passe Postgres
POSTGRES_PASSWORD=un-mot-de-passe-solide
DATABASE_URL=postgresql+asyncpg://jarvis:un-mot-de-passe-solide@postgres:5432/jarvis

# L'IP LAN de ton serveur Unraid (le dashboard l'utilise pour joindre l'API)
HOST_IP=192.168.1.50

# Génère deux secrets (voir commande ci-dessous)
SECRET_KEY=...
API_KEY=...
```

Génère des secrets solides :

```bash
# À lancer deux fois (un pour SECRET_KEY, un pour API_KEY)
openssl rand -hex 32
```

> **Mode dev sans auth** : laisse `API_KEY=` vide pour désactiver l'authentification
> (pratique pour les premiers tests sur LAN). Mets une clé en production.

Les sections **Kubuntu** et **Home Assistant** peuvent rester telles quelles pour
l'instant : sans Kubuntu, les capacités GPU sont simplement indisponibles ;
sans `HA_TOKEN`, l'agent domotique répondra « HA_TOKEN non configuré » mais
n'empêchera rien d'autre.

Sauvegarde dans `nano` : `Ctrl+O`, `Entrée`, puis `Ctrl+X`.

---

## 3. Lancer la stack

### Option A — via Compose Manager (interface web)

1. **Settings → Compose Manager → Add New Stack** → nom : `jarvis`
2. Dans le stack, **Edit Stack → Compose File** : colle le chemin ou le contenu de
   `/mnt/user/appdata/jarvis/docker-compose.yml`
3. **Edit Stack → Env File** : pointe vers `/mnt/user/appdata/jarvis/.env`
4. Clique **Compose Up**

### Option B — via terminal (plus simple et fiable)

```bash
cd /mnt/user/appdata/jarvis

# Build + démarrage en arrière-plan
docker compose up -d --build
```

Le premier build prend quelques minutes (compilation du dashboard Next.js +
installation des deps Python). Au démarrage, l'API lance automatiquement les
migrations Alembic puis Uvicorn.

---

## 4. Vérifier que tout tourne

```bash
# État des conteneurs (tous doivent être "Up" / "healthy")
docker compose ps

# Logs de l'API (vérifie "alembic upgrade head" puis "Uvicorn running")
docker compose logs -f api
```

Tu devrais voir dans les logs de l'API :
```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, initial schema
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Teste les endpoints depuis le terminal Unraid :

```bash
# Santé (pas d'auth requise)
curl http://localhost:8000/api/health

# Liste des agents (avec ta clé API si définie)
curl -H "X-API-Key: TA_CLE_API" http://localhost:8000/api/agents
```

---

## 5. Accéder à l'interface

Ouvre dans ton navigateur :

- **Dashboard JARVIS** : `http://192.168.1.50:3000`
- **API (docs Swagger)** : `http://192.168.1.50:8000/docs`

Le StatusBar en bas du dashboard doit afficher en vert : **PG, REDIS, QDRANT**.
**OLLAMA / COMFY / STT** resteront gris tant que Kubuntu n'est pas configuré
(normal). **TTS** dépend de Piper (voir étape 7, optionnel).

---

## 6. Premiers tests fonctionnels

Dans le dashboard, tape :

| Message | Agent attendu |
|---------|---------------|
| `cpu et ram de la machine` | system |
| `état des conteneurs docker` | unraid |
| `espace disque du nas` | unraid |
| `allume light.salon` | home_assistant (→ demande confirmation) |
| ` ```python\nprint(6*7)\n``` ` | dev (sandbox Docker) |

Pour la **recherche / marketing**, ingère d'abord un document via l'icône
**Upload** (en haut à droite du chat), puis demande `cherche dans les documents …`.

---

## 7. (Optionnel) Voix — TTS Piper (CPU Unraid) + STT Whisper (Kubuntu)

### 7a. TTS — Piper en serveur HTTP

JARVIS appelle Piper en **HTTP** (POST `{text}` → WAV). Ajoute ce service au
`docker-compose.yml` puis `docker compose up -d` :

```yaml
  piper:
    image: artibex/piper-http:latest    # serveur HTTP Piper (POST JSON {text} → wav)
    restart: unless-stopped
    command: --model fr_FR-upmc-medium
    ports:
      - "5000:5000"
    volumes:
      - ./piper-data:/data
    networks:
      - jarvis
```

Puis dans `.env` : `PIPER_BASE_URL=http://piper:5000`.

> Le client tente d'abord `POST /` avec `{"text": ...}`, puis `GET /?text=...`.
> Si tu utilises une autre image HTTP Piper, vérifie qu'elle expose l'une de ces
> deux conventions. Sans serveur Piper, la voix de sortie est simplement
> silencieuse (aucune erreur bloquante).

### 7b. STT — Whisper

Le STT (transcription du micro) tourne sur **Kubuntu** (GPU) via le service
`whisper` de `docker-compose.kubuntu.yml` — voir `KUBUNTU_SETUP.md`. Le bouton
micro du dashboard enregistre, envoie l'audio à l'API qui réveille Kubuntu si
besoin, transcrit, puis envoie le texte comme message.

> Le micro nécessite **HTTPS ou localhost** (contrainte navigateur `getUserMedia`).
> En accès LAN via `http://IP:3000`, autorise le micro pour cette origine, ou
> place le dashboard derrière un reverse-proxy HTTPS.

---

## 8. Mises à jour ultérieures

```bash
cd /mnt/user/appdata/jarvis
git pull origin claude/gallant-euler-h0syfh
docker compose up -d --build
```

Les migrations de base de données s'appliquent automatiquement au redémarrage
de l'API.

---

## 9. Sauvegarde

Les données persistantes vivent dans des volumes Docker nommés
(`postgres_data`, `redis_data`, `qdrant_data`). Pour les sauvegarder :

```bash
# Exemple : dump Postgres
docker compose exec postgres pg_dump -U jarvis jarvis > /mnt/user/backups/jarvis_$(date +%F).sql
```

Ajoute `/mnt/user/appdata/jarvis` à ton plan de sauvegarde Unraid habituel
(plugin **Appdata Backup**) pour conserver `.env` et la config.

---

## Dépannage rapide

| Symptôme | Cause probable | Solution |
|----------|----------------|----------|
| API redémarre en boucle | Postgres pas prêt / `DATABASE_URL` faux | `docker compose logs api`, vérifie `.env` |
| `alembic ... command not found` | image pas rebuild après update | `docker compose up -d --build` |
| Dashboard « Erreur de connexion » | `HOST_IP` faux ou `API_KEY` désaccordé | aligner `.env` + rebuild dashboard |
| StatusBar OLLAMA gris | Kubuntu éteint / non configuré | normal — voir `KUBUNTU_SETUP.md` |
| Agent unraid ne voit pas les disques | montage `/var/local/emhttp` absent | vérifier le `volumes:` du service api |
| Agent dev : « Docker indisponible » | socket non monté | vérifier `/var/run/docker.sock` dans le compose |

---

## Récapitulatif des ports (Unraid)

| Service   | Port  | Accès                          |
|-----------|-------|--------------------------------|
| Dashboard | 3000  | `http://IP_UNRAID:3000`        |
| API       | 8000  | `http://IP_UNRAID:8000/docs`   |
| Postgres  | (interne) | réseau `jarvis` uniquement |
| Redis     | (interne) | réseau `jarvis` uniquement |
| Qdrant    | (interne) | réseau `jarvis` uniquement |
| Piper     | 5000  | optionnel (TTS)                |
