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

Chaque finding a une **sévérité** (🟥 critical → ⬜ info), une **recommandation**
et, si possible, une **commande de correctif**.

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
