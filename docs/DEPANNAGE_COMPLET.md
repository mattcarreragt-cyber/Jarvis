# 🔧 Dépannage complet — tous les problèmes & solutions

Organisé par **symptôme**. Pour chaque cas : cause probable → solution.

> **Réflexe n°1 — regarder les logs.** Sur Unraid :
> ```bash
> cd /mnt/user/appdata/jarvis
> docker compose logs -f api        # le cerveau (le plus utile)
> docker compose logs -f dashboard  # l'interface
> docker compose ps                 # qui tourne / qui est tombé
> ```
> `Ctrl + C` pour quitter l'affichage des logs.

---

## 1. Installation & démarrage (Unraid)

### ❌ `git: command not found`
- **Cause :** git n'est pas installé sur Unraid.
- **Solution :** *Apps* → installe **NerdTools** → active `git`. Ou télécharge le
  ZIP du dépôt et copie-le dans `/mnt/user/appdata/jarvis`.

### ❌ `docker compose: command not found`
- **Cause :** Docker Compose absent / Unraid trop ancien.
- **Solution :** installe le plugin **Compose Manager** (Community Apps), ou mets
  Unraid à jour (6.12+).

### ❌ Le build échoue / reste bloqué très longtemps
- **Cause :** première construction (normal, plusieurs minutes) ou manque d'espace.
- **Solution :** patiente. Si erreur d'espace : libère de la place sur le cache
  (`docker system prune` retire les images inutiles).

### ❌ `docker compose ps` montre l'API en `Restarting` en boucle
- **Cause la plus fréquente :** Postgres pas prêt ou `DATABASE_URL` incorrect.
- **Solution :** vérifie dans `.env` que le mot de passe de `DATABASE_URL` est
  **exactement** le même que `POSTGRES_PASSWORD`. Puis :
  ```bash
  docker compose down && docker compose up -d
  docker compose logs -f api
  ```

### ❌ Logs API : `alembic: command not found` ou erreur de migration
- **Cause :** image construite sans les fichiers de migration (ancienne version).
- **Solution :** reconstruis proprement :
  ```bash
  docker compose build --no-cache api && docker compose up -d
  ```

### ❌ Logs API : `RuntimeError: Form data requires python-multipart`
- **Cause :** dépendance manquante (très vieille image).
- **Solution :** `git pull` puis `docker compose up -d --build` (déjà corrigé dans
  les versions récentes).

---

## 2. Interface (Dashboard)

### ❌ La page `http://IP_UNRAID:3000` ne s'ouvre pas
- **Causes :** mauvaise IP, conteneur dashboard tombé, port occupé.
- **Solutions :**
  - vérifie l'IP d'Unraid ; teste `http://IP_UNRAID:8000/api/health` (l'API).
  - `docker compose ps` → le dashboard est-il `Up` ?
  - un autre service utilise le port 3000 ? change le mapping dans
    `docker-compose.yml` (`"3001:3000"`).

### ❌ « Erreur de connexion à l'API » dans le chat
- **Cause :** le dashboard ne joint pas l'API (mauvais `HOST_IP`, ou `API_KEY`
  différente entre les deux).
- **Solution :** dans `.env`, `HOST_IP` = IP réelle d'Unraid ; si tu as mis une
  `API_KEY`, elle est partagée automatiquement au build → reconstruis le dashboard
  après tout changement : `docker compose up -d --build dashboard`.

### ❌ Le micro ne marche pas (rien ne se passe au clic)
- **Cause :** les navigateurs **interdisent le micro hors HTTPS / localhost**.
- **Solutions :**
  - autorise le micro pour le site dans les réglages du navigateur ;
  - ou place le dashboard derrière un reverse-proxy **HTTPS** (Nginx Proxy Manager
    sur Unraid, par ex.).

### ❌ Les images/vidéos ne s'affichent pas dans la galerie
- **Cause :** la machine GPU (ComfyUI) qui les héberge est éteinte/injoignable.
- **Solution :** allume Kubuntu / vérifie ComfyUI (`http://IP_KUBUNTU:8188`). Le
  proxy de l'API va chercher le média sur le GPU : s'il dort, l'image ne charge pas.

---

## 3. Authentification & sécurité

### ❌ Réponses `401 Unauthorized`
- **Cause :** `API_KEY` définie côté API mais pas (ou pas la même) côté dashboard.
- **Solution :** mets la **même** valeur, reconstruis le dashboard. Pour tester
  vite : laisse `API_KEY=` **vide** (désactive l'auth).

---

## 4. Base de données & mémoire

### ❌ JARVIS oublie tout au redémarrage
- **Cause :** Postgres indisponible (mode dégradé).
- **Solution :** `docker compose ps` → Postgres `healthy` ? Sinon logs Postgres.
  Vérifie que le volume `postgres_data` existe (les données y sont).

### ❌ « base mémoire indisponible » quand tu dis « souviens-toi… »
- **Cause :** idem, Postgres down.
- **Solution :** relance Postgres ; vérifie l'espace disque.

### ❌ La recherche de documents ne renvoie rien
- **Causes :** aucun document ingéré, ou Qdrant down.
- **Solutions :** ingère un document (icône 📤) ; `docker compose ps` → Qdrant ;
  pour Nextcloud, lance une **synchro** (icône ☁).

---

## 5. Kubuntu (GPU local)

### ❌ Voyants OLLAMA / COMFY / STT **gris** dans la barre de statut
- **Cause :** Kubuntu éteint ou pas configuré. **C'est normal** si tu n'as fait que
  la Phase 1.
- **Solution :** voir `KUBUNTU_SETUP.md`. Une fois Kubuntu allumé et joignable, ils
  passent au vert.

### ❌ « Le nœud de calcul (Kubuntu) est indisponible »
- **Causes :** Kubuntu éteint, mauvaise IP, ou Wake-on-LAN qui ne réveille pas.
- **Solutions :**
  - vérifie `KUBUNTU_URL` dans `.env` (IP + port 11434) ;
  - teste depuis Unraid : `curl http://IP_KUBUNTU:11434/api/tags` ;
  - WoL : `KUBUNTU_WOL_ENABLED=true`, `KUBUNTU_MAC` correcte, et **Wake-on-LAN
    activé dans le BIOS** du PC ; augmente `KUBUNTU_WOL_TIMEOUT` si le PC est lent
    à démarrer.

### ❌ `nvidia-smi` ne marche pas sur Kubuntu
- **Cause :** pilotes NVIDIA non installés.
- **Solution :** installe `nvidia-driver-535` (ou la version recommandée), redémarre.

### ❌ Docker sur Kubuntu ne voit pas le GPU
- **Cause :** NVIDIA Container Toolkit absent/mal configuré.
- **Solution :** installe-le et `nvidia-ctk runtime configure --runtime=docker`,
  puis `systemctl restart docker`. Teste : `docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi`.

### ❌ Erreur « out of memory » (VRAM) pendant une génération
- **Cause :** modèle trop gros pour 8 Go, ou plusieurs modèles chargés.
- **Solutions :**
  - mets `OLLAMA_MAX_LOADED_MODELS=1` (déjà dans le compose Kubuntu) ;
  - pour l'image/vidéo, baisse la résolution (`COMFYUI_WIDTH/HEIGHT`, ou 512→384
    dans le workflow) ;
  - JARVIS décharge déjà les LLM avant une image/vidéo/audio — si ça arrive quand
    même, c'est que ComfyUI co-charge trop : ferme les autres usages GPU.

---

## 6. Modèles & génération (Ollama / ComfyUI)

### ❌ Chat : « le modèle n'a pas répondu »
- **Cause :** modèle pas téléchargé sur Ollama.
- **Solution :** `docker exec kubuntu-ollama ollama list` → manque `qwen2.5:7b` ?
  Fais `ollama pull qwen2.5:7b` (et `:14b`, `nomic-embed-text`).

### ❌ Image : « vérifie que le checkpoint SDXL est installé »
- **Cause :** modèle SDXL absent de ComfyUI.
- **Solution :** télécharge `sd_xl_base_1.0.safetensors` dans
  `ComfyUI/models/checkpoints` (voir `KUBUNTU_SETUP.md`). Le nom doit correspondre
  à `COMFYUI_CHECKPOINT`.

### ❌ Vidéo : « ComfyUI a refusé le workflow »
- **Cause :** nœuds personnalisés manquants (AnimateDiff/VideoHelperSuite/SVD) ou
  noms de nœuds différents de ton installation.
- **Solutions :**
  - installe les custom nodes (voir `KUBUNTU_SETUP.md`) ;
  - **remplace le template** : dans ComfyUI, construis un workflow qui marche,
    *Export (API)*, et remplace `config/comfyui_*_workflow.json` en gardant les
    tokens `__PROMPT__`, `__FRAMES__`, `__FPS__`, `__IMAGE__`, `__SECONDS__`.

### ❌ Audio : la génération échoue
- **Cause :** modèle Stable Audio absent.
- **Solution :** télécharge `stable_audio_open_1.0.safetensors` (voir `KUBUNTU_SETUP.md`).

### ❌ La vidéo reste « en cours » très longtemps
- **Cause :** c'est **normal** — sur 8 Go, 10-20 s de vidéo = plusieurs minutes.
  Suis l'avancement dans le panneau **🎬 Jobs**.
- **Si ça ne finit jamais :** regarde les logs ComfyUI sur Kubuntu ; baisse la durée.

---

## 7. RunPod (cloud)

### ❌ « RunPod désactivé »
- **Solution :** `RUNPOD_ENABLED=true` dans `.env`, redémarre l'API.

### ❌ « URL RunPod ollama non configurée »
- **Solution :** renseigne `RUNPOD_OLLAMA_URL` / `RUNPOD_COMFYUI_URL` (les URLs
  proxy de ton pod).

### ❌ « Pod non prêt dans les 300s »
- **Causes :** démarrage long, ou modèle pas encore téléchargé sur le pod.
- **Solutions :** augmente `RUNPOD_START_TIMEOUT` ; utilise un **Network Volume**
  RunPod pour garder les modèles entre deux démarrages.

### ❌ Facture qui grimpe
- **Cause :** pod jamais arrêté.
- **Solution :** arrête-le après usage (RunPod → Stop), ou configure l'**auto-stop**
  sur inactivité.

---

## 8. Home Assistant

### ❌ « HA_TOKEN non configuré » / « Home Assistant injoignable »
- **Solutions :** crée un **token longue durée** (Profil HA → Sécurité), mets-le
  dans `HA_TOKEN` ; vérifie `HA_URL` (IP + port 8123) ; redémarre l'API.

### ❌ « allume … » ne fait rien
- **Cause :** c'est **voulu** — les actions demandent une **confirmation**.
- **Solution :** clique le bouton **CONFIRMER** qui apparaît sous le message.

---

## 8bis. Webhooks (déclencheurs externes)

### ❓ Comment déclencher JARVIS depuis Home Assistant ?
1. Dans le dashboard, ouvre le panneau **Webhooks** (icône 🔗), crée un déclencheur
   (ex. nom `brief-matin`, message `résume mes nouveaux fichiers nextcloud`).
2. Copie l'URL fournie (`POST http://IP_UNRAID:8000/api/hooks/<token>`).
3. Dans HA, ajoute une **RESTful Command** :
   ```yaml
   rest_command:
     jarvis_brief:
       url: "http://IP_UNRAID:8000/api/hooks/LE_TOKEN"
       method: POST
   ```
   Puis appelle `rest_command.jarvis_brief` depuis une automatisation HA.

### ❌ Le webhook renvoie 404
- **Cause :** token incorrect ou webhook supprimé/désactivé.
- **Solution :** recopie l'URL exacte depuis le panneau Webhooks.

### ❌ Le webhook répond mais rien ne se passe
- **Normal :** l'exécution est **asynchrone**. Le résultat arrive dans les
  **notifications** (cloche 🔔), source `webhook:<nom>`.

---

## 9. Nextcloud

### ❌ `/ping` renvoie `reachable: false`
- **Solutions :** vérifie `NEXTCLOUD_URL` (sans `/remote.php`), l'utilisateur, et
  surtout utilise un **mot de passe d'application** (pas ton mot de passe principal).

### ❌ La synchro n'indexe aucun fichier
- **Causes :** `NEXTCLOUD_ROOT` pointe sur un dossier vide, ou formats non gérés.
- **Solution :** mets `NEXTCLOUD_ROOT=/` ; formats gérés : txt, md, pdf, docx,
  xlsx, pptx, images.

---

## 10. Réseau

### ❌ Une machine ne joint pas l'autre
- **Causes :** pas sur le même réseau, pare-feu, IP changée (DHCP).
- **Solutions :**
  - mets les machines sur le **même réseau** ;
  - fixe les IP (réservation DHCP sur la box) pour qu'elles ne changent pas ;
  - teste avec `ping IP_AUTRE_MACHINE` et `curl http://IP:PORT`.

---

## 11. Diagnostic rapide — l'ordre à suivre

1. `docker compose ps` → tout est `Up` ?
2. `curl http://localhost:8000/api/health` → PG/REDIS/QDRANT `ok` ?
3. Panneau **⚙ Système** du dashboard → quel palier est rouge ?
4. `docker compose logs -f api` → un message d'erreur clair ?
5. Si GPU : `curl http://IP_KUBUNTU:11434/api/tags` → Ollama répond ?

90 % des problèmes se voient à l'étape 1 ou 4.

---

## 11bis. Sauvegarde & migration

### 💾 Comment sauvegarder le « cerveau » de JARVIS ?
Panneau **⚙ Système** → section **SAUVEGARDE** → **EXPORTER** : télécharge un
JSON contenant tes **faits mémorisés**, **tâches/rappels** et **webhooks**.
Garde ce fichier en lieu sûr (ou dans le plan de backup Unraid).

### ♻️ Restaurer / migrer vers une autre machine
Même panneau → **RESTAURER** → choisis ton fichier JSON. Mode `merge` (défaut) :
ajoute sans écraser. (API : `POST /api/backup/restore?mode=replace` pour remplacer.)

> Ne sont **pas** inclus : les conversations (exportables par session via
> l'historique) ni les médias (fichiers physiques sur le GPU).

---

## 12. Tout réinitialiser (dernier recours)

```bash
cd /mnt/user/appdata/jarvis
docker compose down            # arrête tout (garde les données)
docker compose up -d --build   # reconstruit et relance
```
Pour **effacer aussi les données** (⚠️ irréversible) : `docker compose down -v`.

> En cas de blocage, copie les 30 dernières lignes de `docker compose logs api`
> et demande de l'aide : l'erreur y est presque toujours.
