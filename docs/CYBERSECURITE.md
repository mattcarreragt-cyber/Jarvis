# 🛡️ Module Cybersécurité — conseiller défensif

Un agent dédié qui **audite tes propres hôtes** (Unraid, Kubuntu, NAS…) par SSH,
détecte les failles de configuration, et propose — voire applique sur ton ordre —
des durcissements.

> **Cadre : tes machines, audit défensif.** Connexions uniquement vers les hôtes
> que tu déclares. Aucune action destructive sans ton clic explicite.

---

## 1. Pré-requis : accès SSH par clé

L'agent se connecte par **clé SSH** (pas de mot de passe stocké). Sur Unraid,
monte une clé privée dans le conteneur API et renseigne son chemin :

```yaml
# docker-compose.yml, service api :
    volumes:
      - /mnt/user/appdata/jarvis/ssh:/keys:ro
    environment:
      CYBER_SSH_KEY_PATH: /keys/id_ed25519
```

La clé **publique** correspondante doit être autorisée sur chaque hôte cible :
```bash
ssh-copy-id -i id_ed25519.pub user@hote
```
Pour les checks qui lisent des fichiers protégés (ex. `/etc/shadow`), l'utilisateur
SSH doit avoir `sudo` sans mot de passe (sinon ces checks sont simplement ignorés).

---

## 2. Déclarer tes hôtes

Dashboard → bouton **🛡️ Cyber** → *Ajouter un hôte* (label, IP/hostname,
utilisateur SSH, port). Ou par API :
```bash
curl -X POST -H "X-API-Key: TA_CLE" -H "Content-Type: application/json" \
  -d '{"label":"unraid","hostname":"192.168.1.50","username":"root","port":22}' \
  http://IP_UNRAID:8000/api/cyber/hosts
```

---

## 3. Lancer un audit

- **Chat** : « **audite unraid** », « quelles **failles** sur kubuntu ? », « **mes machines** »
- **Panneau** : bouton **AUDITER** sur chaque hôte.

L'audit est **100 % lecture**. Checks inclus :

| Check | Détecte |
|-------|---------|
| sshd | login root SSH, auth par mot de passe |
| users | comptes UID 0 en trop |
| passwords | comptes sans mot de passe |
| updates | mises à jour de sécurité en attente |
| ports | ports en écoute sur toutes les interfaces |
| firewall | absence de pare-feu actif |
| docker | conteneurs exposés / privilégiés |
| auth | tentatives de connexion en force brute |
| suid | binaires SUID risqués |
| **nmap** | scan réseau (depuis l'API) : ports/services exposés, services sensibles (Telnet, RDP, Redis, Docker API…) |
| **lynis** | audit système approfondi sur l'hôte : indice de durcissement + avertissements |
| **rootkit** | rkhunter / chkrootkit : indicateurs d'infection et avertissements |
| **cve** | corrélation CVE des paquets installés via OSV.dev (Debian/Ubuntu) |

Chaque finding a une **sévérité** (🟥 critical → ⬜ info), une **recommandation**
et, si possible, une **commande de correctif**.

### Score de sécurité + historique
Chaque audit calcule un **score 0-100** et un **grade A-F** (pénalités pondérées
par sévérité : critical −30, high −15, medium −6, low −2). Affiché dans le chat
et en badge sur l'hôte. Chaque score est **historisé** : le panneau affiche une
**courbe d'évolution** (sparkline) pour suivre le durcissement dans le temps.
API : `GET /api/cyber/hosts/<id>/scores`.

### Rootkits & CVE — pré-requis hôte
- **rkhunter** ou **chkrootkit** : `sudo apt-get install rkhunter` sur l'hôte
  (sinon un finding le recommande). Détection d'indicateurs d'infection.
- **CVE (OSV.dev)** : nécessite un **accès réseau sortant** depuis le conteneur
  API vers `api.osv.dev`. Relève les paquets `dpkg` (Debian/Ubuntu) et signale
  les CVE connues. Sans réseau → check ignoré silencieusement.

### Pré-requis nmap / lynis
- **nmap** : installé automatiquement dans le conteneur API (voir `api/Dockerfile`).
  Scanne l'hôte cible depuis l'API.
- **lynis** : doit être installé **sur l'hôte cible** (`sudo apt-get install lynis`).
  S'il manque, un finding le recommande. Nécessite sudo NOPASSWD pour l'audit complet.

> Analyses poussées = parfois lentes (ex. recherche SUID sur tout le disque).
> C'est voulu : on privilégie l'exhaustivité.

---

## 4. Appliquer un correctif

**Jamais automatique.** Dans le panneau, chaque correctif a un bouton ▶ qui
exécute la commande **après confirmation**. Ou par API :
```bash
curl -X POST -H "X-API-Key: TA_CLE" -H "Content-Type: application/json" \
  -d '{"command":"sudo ufw --force enable"}' \
  http://IP_UNRAID:8000/api/cyber/hosts/<host_id>/remediate
```

> Vérifie toujours la commande avant de l'appliquer (surtout sur un serveur de prod).

---

## 5. Étendre les analyses

Les checks sont dans `api/app/cyber/audit.py` (`_CHECKS`). Ajouter un check =
une fonction `async (run) -> list[Finding]` qui lance une commande de lecture et
parse la sortie. Idées d'extensions : `lynis`, `rkhunter`, scan `nmap` du sous-réseau,
vérification des versions vs CVE, permissions de fichiers sensibles, etc.

---

## 6. Dépannage

| Symptôme | Cause | Solution |
|----------|-------|----------|
| « Connexion SSH impossible » | clé absente / non autorisée / hôte éteint | vérifie `CYBER_SSH_KEY_PATH`, `ssh-copy-id`, le réseau |
| Checks `/etc/shadow` vides | pas de sudo sans mot de passe | configure sudo NOPASSWD pour l'utilisateur d'audit |
| Audit lent | check SUID parcourt le FS | normal ; patiente ou retire ce check |
