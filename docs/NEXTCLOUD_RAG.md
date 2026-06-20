# RAG Nextcloud — Indexation et recherche de tes fichiers locaux

JARVIS synchronise périodiquement ton Nextcloud, extrait le texte de chaque fichier,
et le rend interrogeable depuis le chat. **Lecture seule** : JARVIS ne modifie jamais
ton Nextcloud.

---

## Ce qui est indexé

| Type | Extensions | Contenu extrait |
|------|-----------|-----------------|
| Texte | `.txt` `.md` | texte brut |
| PDF | `.pdf` | texte des pages |
| Word | `.docx` | paragraphes + tableaux |
| Excel | `.xlsx` | toutes les feuilles, cellule par cellule |
| PowerPoint | `.pptx` | texte de chaque diapositive |
| Images | `.png` `.jpg` `.jpeg` `.gif` `.webp` `.bmp` | nom + dossier + **OCR** (texte dans l'image, si tesseract installé) |

> **Formats legacy** (`.doc` `.xls` `.ppt`) : non supportés directement. Nextcloud +
> Collabora/OnlyOffice les convertit automatiquement en format moderne.

> **Analyse visuelle des images** (décrire le *contenu* d'une photo, pas juste son
> texte) : nécessite un modèle vision (LLaVA) sur Kubuntu — voir `KUBUNTU_SETUP.md`.
> En attendant, les images restent trouvables par nom, dossier et texte OCR.

---

## 1. Créer un app password Nextcloud

⚠️ N'utilise **jamais** ton mot de passe principal.

1. Nextcloud → **Paramètres → Sécurité**
2. Section **Mots de passe d'application** → nom : `jarvis` → **Créer**
3. Copie le mot de passe généré (affiché une seule fois)

---

## 2. Configurer `.env` sur Unraid

```bash
cd /mnt/user/appdata/jarvis
nano .env
```

```env
NEXTCLOUD_URL=http://192.168.1.50:8080     # URL de TON Nextcloud (SANS /remote.php)
NEXTCLOUD_USER=matt                         # ton utilisateur
NEXTCLOUD_PASSWORD=xxxx-xxxx-xxxx-xxxx       # l'app password de l'étape 1
NEXTCLOUD_ROOT=/                            # "/" = tout Nextcloud
NEXTCLOUD_SYNC_ENABLED=true                 # active la sync périodique
NEXTCLOUD_SYNC_INTERVAL=3600                # toutes les heures (secondes, min 60)
NEXTCLOUD_MAX_FILE_MB=50                    # ignore les fichiers > 50 Mo
```

Puis redémarre l'API :

```bash
docker compose up -d
```

---

## 3. (Optionnel) Activer l'OCR des images

L'OCR lit le texte présent **dans** les images (scans, captures, affiches).
Il nécessite le binaire `tesseract` dans le conteneur API. Ajoute au `api/Dockerfile` :

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-fra && rm -rf /var/lib/apt/lists/*
```

et `pytesseract` dans `requirements.txt`, puis `docker compose up -d --build`.
Sans ça, les images restent indexées par nom/dossier (pas de plantage).

---

## 4. Utilisation

### Synchronisation
- **Automatique** : toutes les `NEXTCLOUD_SYNC_INTERVAL` secondes (si activée).
- **Manuelle** : icône **☁ (Cloud)** en haut du chat → **SYNCHRONISER MAINTENANT**.
- **API** : `POST /api/nextcloud/sync` · état : `GET /api/nextcloud/status`.

La sync est **incrémentale** : seuls les fichiers nouveaux ou modifiés (etag changé)
sont re-ingérés. Les fichiers supprimés côté Nextcloud sont retirés de l'index.

### Interroger
Dans le chat :
- `mes fichiers nextcloud sur le contrat Xenum`
- `que disent mes documents sur la garantie ?`
- `cherche dans le cloud les chiffres de Q1`

L'agent **nextcloud** renvoie les extraits pertinents avec leur chemin et un score.

---

## 5. Vérifier que ça tourne

```bash
# Test connexion + auth
curl -X POST -H "X-API-Key: TA_CLE" http://localhost:8000/api/nextcloud/ping
# → {"reachable": true}

# État de l'index
curl -H "X-API-Key: TA_CLE" http://localhost:8000/api/nextcloud/status

# Logs de la sync
docker compose logs -f api | grep -i nextcloud
```

---

## Mode keyword aujourd'hui → analyse complète avec Kubuntu

| Capacité | Maintenant (Unraid) | Avec Kubuntu (Ollama) |
|----------|--------------------|----------------------|
| Retrouver les passages | ✅ recherche keyword | ✅ recherche vectorielle (plus précise) |
| Citer les sources | ✅ | ✅ |
| Synthèse / Q&A en langage naturel | ⚠️ extraits bruts | ✅ réponse rédigée (`chat.deep`) |
| Décrire le contenu visuel des images | ❌ (OCR seulement) | ✅ vision (LLaVA) |

La migration est transparente : les chunks sont déjà stockés avec un vecteur
placeholder, prêts à être ré-encodés avec `nomic-embed-text` quand Kubuntu sera en ligne.

---

## Dépannage

| Symptôme | Cause | Solution |
|----------|-------|----------|
| `/ping` → `reachable: false` | URL/user/password faux | vérifier `.env`, app password valide |
| `configured: false` dans status | une des 3 variables NC vide | compléter `.env` + redémarrer l'API |
| Aucun fichier indexé après sync | `NEXTCLOUD_ROOT` pointe sur un dossier vide | mettre `/` ou le bon chemin |
| Sync lente la 1ʳᵉ fois | indexation initiale complète | normal ; les suivantes sont incrémentales |
| Images non décrites | pas de modèle vision | normal sans Kubuntu (voir §3 pour l'OCR) |
